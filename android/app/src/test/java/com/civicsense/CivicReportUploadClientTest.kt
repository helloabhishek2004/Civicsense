package com.civicsense

import com.civicsense.core.edge.ClientProcessingInfo
import com.civicsense.core.edge.ImageQualityMetrics
import com.civicsense.core.edge.PreprocessedImageResult
import com.civicsense.core.edge.ProcessedReportPackage
import com.civicsense.core.edge.TextStructuredFeatures
import com.civicsense.core.edge.UploadState
import com.civicsense.core.network.CivicReportUploadClient
import com.civicsense.core.network.UploadResult
import com.civicsense.data.model.LocationSource
import com.civicsense.data.model.ReportLocation
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.File
import java.util.UUID

class CivicReportUploadClientTest {

    private lateinit var server: MockWebServer
    private lateinit var client: CivicReportUploadClient

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        client = CivicReportUploadClient(baseUrl = server.url("/").toString().removeSuffix("/"))
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    private fun createSamplePackage(description: String = "Broken streetlight on 5th avenue creating hazard"): ProcessedReportPackage {
        val clientReportId = UUID.randomUUID().toString()
        val location = ReportLocation(
            latitude = 12.9716,
            longitude = 77.5946,
            address = "MG Road, Bangalore",
            postalPin = "560001",
            source = LocationSource.CURRENT_LOCATION
        )
        val textFeatures = TextStructuredFeatures(
            rawText = description,
            cleanedText = description,
            characterCount = description.length,
            wordCount = description.split(" ").size,
            language = "en",
            severityTerms = listOf("hazard"),
            urgencyTerms = listOf("hazard"),
            categoryTerms = listOf("streetlight"),
            locationTerms = listOf("avenue"),
            safetyTerms = listOf("hazard")
        )
        val imageMetrics = ImageQualityMetrics(
            width = 640,
            height = 480,
            aspectRatio = 1.33f,
            fileSizeBytes = 45000L,
            mimeType = "image/jpeg",
            sha256 = "abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            brightness = 0.52f,
            isBlurry = false,
            usable = true,
            feedbackMessage = "The image looks good and sharp."
        )
        val imageResult = PreprocessedImageResult(
            originalUri = null,
            previewFile = File("fake_preview.jpg"),
            metrics = imageMetrics,
            isSuccess = true
        )
        return ProcessedReportPackage(
            clientReportId = clientReportId,
            timestamp = "2026-09-12T10:00:00Z",
            contractVersion = "1.0.0",
            categoryHint = "Lighting",
            location = location,
            textFeatures = textFeatures,
            imageResult = imageResult,
            clientProcessing = ClientProcessingInfo(
                enabled = true,
                processorVersion = "1.0.0",
                imagePreprocessed = true,
                textPreprocessed = true,
                embeddingGenerated = false
            )
        )
    }

    @Test
    fun buildJsonPayload_constructsCompliantPayload() {
        val pkg = createSamplePackage()
        val json = client.buildJsonPayload(pkg)

        assertEquals(pkg.clientReportId, json.getString("client_report_id"))
        assertEquals(pkg.textFeatures.cleanedText, json.getString("description"))

        val loc = json.getJSONObject("location")
        assertEquals(12.9716, loc.getDouble("latitude"), 0.0001)
        assertEquals(77.5946, loc.getDouble("longitude"), 0.0001)

        val edgeMeta = json.getJSONObject("edge_metadata")
        assertEquals("1.0.0", edgeMeta.getString("contract_version"))
        assertEquals("Lighting", edgeMeta.getString("category_hint"))

        val clientProc = edgeMeta.getJSONObject("client_processing")
        assertTrue(clientProc.getBoolean("enabled"))
        assertEquals("1.0.0", clientProc.getString("processor_version"))
        assertTrue(clientProc.getBoolean("image_preprocessed"))
        assertTrue(clientProc.getBoolean("text_preprocessed"))
        assertFalse(clientProc.getBoolean("embedding_generated"))

        val textFeat = edgeMeta.getJSONObject("text_features")
        assertEquals(pkg.textFeatures.cleanedText, textFeat.getString("cleaned_text"))
        assertEquals(1, textFeat.getJSONArray("category_terms").length())
    }

    @Test
    fun uploadReport_succeedsOnHttp201() = runTest {
        val pkg = createSamplePackage()
        server.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody("""{"id":"rep-uuid-1234","client_report_id":"${pkg.clientReportId}","status":"SUBMITTED"}""")
                .addHeader("Content-Type", "application/json")
        )

        var finalState: UploadState? = null
        val result = client.uploadReport(pkg) { state ->
            finalState = state
        }

        assertTrue(result is UploadResult.Success)
        val success = result as UploadResult.Success
        assertEquals("rep-uuid-1234", success.serverTrackingId)
        assertEquals(pkg.clientReportId, success.clientReportId)
        assertEquals(201, success.statusCode)
        assertEquals(UploadState.SUBMITTED, finalState)

        // Verify request received by server
        val recorded = server.takeRequest()
        assertEquals("/api/v1/reports", recorded.path)
        assertEquals(pkg.clientReportId, recorded.getHeader("X-Idempotency-Key"))
        assertEquals("application/json; charset=utf-8", recorded.getHeader("Content-Type"))
    }

    @Test
    fun uploadReport_rejectsClientErrorsImmediatelyWithoutRetry() = runTest {
        val pkg = createSamplePackage()
        server.enqueue(
            MockResponse()
                .setResponseCode(422)
                .setBody("""{"detail":"Validation error in coordinates"}""")
                .addHeader("Content-Type", "application/json")
        )

        var finalState: UploadState? = null
        val result = client.uploadReport(pkg) { state ->
            finalState = state
        }

        assertTrue(result is UploadResult.Error)
        val error = result as UploadResult.Error
        assertEquals(422, error.statusCode)
        assertFalse("422 errors must NOT be retryable", error.isRetryable)
        assertEquals(UploadState.FAILED, finalState)
        // Exactly 1 request made, no redundant retries
        assertEquals(1, server.requestCount)
    }

    @Test
    fun uploadReport_fallsBackToOfflineQueuedOnServerError() = runTest {
        val pkg = createSamplePackage()
        // Enqueue 3 consecutive 503 Service Unavailable responses
        repeat(3) {
            server.enqueue(
                MockResponse()
                    .setResponseCode(503)
                    .setBody("""{"error":{"message":"Municipal service temporarily unavailable"}}""")
            )
        }

        var finalState: UploadState? = null
        val result = client.uploadReport(pkg) { state ->
            finalState = state
        }

        assertTrue(result is UploadResult.OfflineQueued)
        val queued = result as UploadResult.OfflineQueued
        assertEquals(pkg.clientReportId, queued.clientReportId)
        assertEquals(UploadState.FAILED, finalState)
        assertEquals(3, server.requestCount)
    }

    @Test
    fun buildJsonPayload_includesCitizenFieldsAndBase64Image() {
        val tempFile = File.createTempFile("test_preview", ".jpg").apply {
            writeBytes(byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0xFF.toByte()))
            deleteOnExit()
        }

        val sample = createSamplePackage().copy(
            citizenName = "Priya Sharma",
            citizenPhone = "9876543210",
            imageResult = PreprocessedImageResult(
                previewFile = tempFile,
                metrics = ImageQualityMetrics(
                    width = 640,
                    height = 480,
                    aspectRatio = 1.33f,
                    fileSizeBytes = 3L,
                    sha256 = "dummy"
                ),
                isSuccess = true
            )
        )

        val json = client.buildJsonPayload(sample)
        assertEquals("Priya Sharma", json.getString("citizen_name"))
        assertEquals("9876543210", json.getString("citizen_phone"))

        val evidenceArray = json.getJSONArray("evidence")
        assertEquals(1, evidenceArray.length())
        val ev = evidenceArray.getJSONObject(0)
        assertTrue(ev.has("data_base64"))
        assertTrue(ev.getString("data_base64").isNotEmpty())
    }

    @Test
    fun buildJsonPayload_includesEmailAndPostalCode() {
        val sample = createSamplePackage().copy(
            citizenName = "CivicSense Test User",
            citizenPhone = "9874563210",
            citizenEmail = "civicsense.test@example.com",
            citizenPostalCode = "695001"
        )

        val json = client.buildJsonPayload(sample)
        assertEquals("CivicSense Test User", json.getString("citizen_name"))
        assertEquals("9874563210", json.getString("citizen_phone"))
        assertEquals("civicsense.test@example.com", json.getString("citizen_email"))
        assertEquals("695001", json.getString("citizen_postal_code"))
    }

    @Test
    fun buildJsonPayload_handlesMissingOptionalEmailAndPostalCode() {
        val sample = createSamplePackage().copy(
            citizenName = "CivicSense Test User",
            citizenPhone = "9874563210",
            citizenEmail = null,
            citizenPostalCode = "   " // blank string
        )

        val json = client.buildJsonPayload(sample)
        assertEquals("CivicSense Test User", json.getString("citizen_name"))
        assertEquals("9874563210", json.getString("citizen_phone"))
        assertFalse(json.has("citizen_email"))
        assertFalse(json.has("citizen_postal_code"))
    }

    @Test
    fun buildJsonPayload_includesCategory() {
        val sample = createSamplePackage().copy(
            category = "Road Damage",
            categoryHint = "Road damage"
        )

        val json = client.buildJsonPayload(sample)
        assertEquals("Road Damage", json.getString("category"))
        assertEquals("Road damage", json.getJSONObject("edge_metadata").getString("category_hint"))
    }
}
