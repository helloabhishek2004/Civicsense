package com.civicsense.core.network

import android.util.Log
import com.civicsense.core.edge.ProcessedReportPackage
import com.civicsense.core.edge.UploadState
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Result representing the outcome of a reliable report upload.
 */
sealed interface UploadResult {
    data class Success(
        val serverTrackingId: String,
        val clientReportId: String,
        val statusCode: Int,
        val durationMs: Long
    ) : UploadResult

    data class OfflineQueued(
        val clientReportId: String,
        val message: String
    ) : UploadResult

    data class Error(
        val message: String,
        val statusCode: Int? = null,
        val isRetryable: Boolean = false,
        val cause: Throwable? = null
    ) : UploadResult
}

/**
 * Production-minded HTTP client for submitting processed report packages
 * to the CivicSense FastAPI backend.
 */
class CivicReportUploadClient(
    private val baseUrl: String = DEFAULT_BASE_URL,
    private val client: OkHttpClient = createDefaultOkHttpClient()
) {

    companion object {
        private const val TAG = "CivicSenseUpload"
        // Injected from local.properties (e.g. LAN IP for physical device) or defaults to emulator
        val DEFAULT_BASE_URL: String = try {
            com.civicsense.BuildConfig.API_BASE_URL
        } catch (_: Throwable) {
            "http://10.0.2.2:8000"
        }
        const val MAX_RETRIES = 3
        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()

        fun createDefaultOkHttpClient(): OkHttpClient {
            return OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(15, TimeUnit.SECONDS)
                .writeTimeout(15, TimeUnit.SECONDS)
                .retryOnConnectionFailure(false) // Managed explicitly in upload loop
                .build()
        }

        fun encodeBase64(bytes: ByteArray): String {
            val androidResult = try {
                android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP)
            } catch (_: Throwable) {
                null
            }
            return if (!androidResult.isNullOrBlank()) {
                androidResult
            } else {
                java.util.Base64.getEncoder().encodeToString(bytes)
            }
        }
    }

    /**
     * Uploads the packaged report evidence with bounded exponential backoff.
     */
    suspend fun uploadReport(
        reportPackage: ProcessedReportPackage,
        onStateChange: (UploadState) -> Unit = {}
    ): UploadResult {
        val totalStart = System.currentTimeMillis()
        val truncatedId = reportPackage.clientReportId.take(8)
        Log.i(TAG, "[CivicSense][Upload] Upload started: clientReportId=$truncatedId...")

        // 1. Client-Side Validation
        if (reportPackage.textFeatures.cleanedText.length < 5) {
            onStateChange(UploadState.FAILED)
            return UploadResult.Error("Description must be at least 5 characters", statusCode = 400, isRetryable = false)
        }

        // 2. Build Canonical JSON Payload
        val buildStart = System.currentTimeMillis()
        Log.i("CivicSenseSubmit", "REQUEST_BUILD_START")
        val jsonPayload = buildJsonPayload(reportPackage)
        val payloadBytes = jsonPayload.toString().toByteArray(Charsets.UTF_8)
        val requestBody = payloadBytes.toRequestBody(JSON_MEDIA_TYPE)
        val buildDuration = System.currentTimeMillis() - buildStart
        Log.i("CivicSenseSubmit", "REQUEST_BUILD_COMPLETE duration_ms=$buildDuration")

        val targetUrl = "$baseUrl/api/v1/reports"
        Log.i(TAG, "[CivicSense][Upload] Target URL: $targetUrl")
        Log.i("CivicSenseSubmit", "HTTP_REQUEST_HEADERS_READY Content-Type=application/json X-Client-Report-ID=${reportPackage.clientReportId}")
        Log.i("CivicSenseSubmit", "HTTP_REQUEST_BODY_READY bytes=${payloadBytes.size}")

        // Safe Diagnostic Audit (field names and presence only, NEVER logging private values)
        val fieldNames = mutableListOf<String>()
        val keyIterator = jsonPayload.keys()
        while (keyIterator.hasNext()) {
            fieldNames.add(keyIterator.next())
        }
        val imgFile = reportPackage.imageResult?.previewFile
        val imgPresent = imgFile != null && imgFile.exists()
        val imgByteSize = if (imgPresent) imgFile!!.length() else 0L
        val citizenIdPresent = !reportPackage.citizenId.isNullOrBlank()
        val citizenNamePresent = !reportPackage.citizenName.isNullOrBlank()
        val citizenPhonePresent = !reportPackage.citizenPhone.isNullOrBlank()
        val citizenEmailPresent = !reportPackage.citizenEmail.isNullOrBlank()
        val citizenPostalCodePresent = !reportPackage.citizenPostalCode.isNullOrBlank()
        val categoryPresent = !reportPackage.category.isNullOrBlank()

        Log.i(
            "CivicSenseSubmit",
            "HTTP_REQUEST_AUDIT method=POST url=$targetUrl fields=$fieldNames image_present=$imgPresent image_bytes=$imgByteSize category_present=$categoryPresent category=${reportPackage.category} citizen_id_present=$citizenIdPresent citizen_name_present=$citizenNamePresent citizen_phone_present=$citizenPhonePresent citizen_email_present=$citizenEmailPresent citizen_postal_code_present=$citizenPostalCodePresent"
        )

        val request = Request.Builder()
            .url(targetUrl)
            .header("Content-Type", "application/json")
            .header("X-Client-Report-ID", reportPackage.clientReportId)
            .header("X-Idempotency-Key", reportPackage.clientReportId)
            .post(requestBody)
            .build()

        var attempt = 0
        var backoffMs = 1000L

        while (attempt < MAX_RETRIES) {
            attempt++
            val attemptStart = System.currentTimeMillis()
            try {
                if (attempt > 1) {
                    onStateChange(UploadState.RETRYING)
                    Log.i("CivicSenseSubmit", "RETRY_START attempt=$attempt backoff_ms=$backoffMs")
                    Log.w(TAG, "[CivicSense][Upload] Retrying upload (attempt $attempt of $MAX_RETRIES) after ${backoffMs}ms backoff")
                    delay(backoffMs)
                    backoffMs *= 2
                }

                onStateChange(UploadState.UPLOADING)
                Log.i("CivicSenseSubmit", "HTTP_REQUEST_START method=POST url=$targetUrl attempt=$attempt")
                Log.d(TAG, "[CivicSense][Network] POST $targetUrl attempt $attempt started")

                val response = client.newCall(request).execute()
                val statusCode = response.code
                val responseBody = response.body?.string() ?: ""
                val attemptDuration = System.currentTimeMillis() - attemptStart
                Log.i("CivicSenseSubmit", "HTTP_RESPONSE status=$statusCode duration_ms=$attemptDuration attempt=$attempt")

                if (response.isSuccessful) {
                    val durationMs = System.currentTimeMillis() - totalStart
                    val trackingId = try {
                        val obj = JSONObject(responseBody)
                        when {
                            obj.has("tracking_id") -> obj.getString("tracking_id")
                            obj.has("id") -> obj.getString("id")
                            else -> "REP-${reportPackage.clientReportId.take(6).uppercase()}"
                        }
                    } catch (_: Exception) {
                        "REP-${reportPackage.clientReportId.take(6).uppercase()}"
                    }

                    Log.i(TAG, "[CivicSense][Upload] Upload completed: HTTP $statusCode (trackingId=$trackingId) in attempt ${attempt} (${attemptDuration}ms, total ${durationMs}ms)")
                    Log.i(TAG, "[CivicSense][Report] Submission completed in ${durationMs} ms")
                    onStateChange(UploadState.SUBMITTED)
                    return UploadResult.Success(
                        serverTrackingId = trackingId,
                        clientReportId = reportPackage.clientReportId,
                        statusCode = statusCode,
                        durationMs = durationMs
                    )
                }

                // Handle 4xx Client Errors (Non-retryable)
                if (statusCode in 400..499) {
                    val errorMsg = parseErrorMessage(responseBody, statusCode)
                    Log.w("CivicSenseSubmit", "HTTP_FAILURE type=ClientError statusCode=$statusCode message=$errorMsg")
                    Log.e(TAG, "[CivicSense][Backend] Server rejected payload with HTTP $statusCode after ${attemptDuration}ms: $errorMsg")
                    onStateChange(UploadState.FAILED)
                    return UploadResult.Error(
                        message = errorMsg,
                        statusCode = statusCode,
                        isRetryable = false
                    )
                }

                // 5xx Server Errors (Retryable)
                Log.w("CivicSenseSubmit", "HTTP_FAILURE type=ServerError statusCode=$statusCode attempt=$attempt")
                Log.w(TAG, "[CivicSense][Backend] Server error HTTP $statusCode after ${attemptDuration}ms, attempt $attempt failed")

            } catch (ce: CancellationException) {
                Log.i(TAG, "[CivicSense][Upload] Upload cancelled by user/lifecycle")
                onStateChange(UploadState.IDLE)
                throw ce
            } catch (ioe: IOException) {
                val attemptDuration = System.currentTimeMillis() - attemptStart
                Log.w("CivicSenseSubmit", "HTTP_FAILURE type=${ioe.javaClass.simpleName} message=${ioe.message} attempt=$attempt duration_ms=$attemptDuration")
                Log.w(TAG, "[CivicSense][Network] Network failure on attempt $attempt after ${attemptDuration}ms (${ioe.javaClass.simpleName}: ${ioe.message})")
                if (attempt >= MAX_RETRIES) {
                    Log.i("CivicSenseSubmit", "OFFLINE_FALLBACK reason=MAX_RETRIES_EXCEEDED cause=${ioe.javaClass.simpleName}")
                    onStateChange(UploadState.FAILED)
                    return UploadResult.OfflineQueued(
                        clientReportId = reportPackage.clientReportId,
                        message = "Network connection unavailable. Report preserved locally on this device."
                    )
                }
            } catch (e: Exception) {
                val attemptDuration = System.currentTimeMillis() - attemptStart
                Log.e("CivicSenseSubmit", "HTTP_FAILURE type=${e.javaClass.simpleName} message=${e.message} attempt=$attempt duration_ms=$attemptDuration")
                Log.e(TAG, "[CivicSense][Upload] Unexpected upload failure on attempt $attempt after ${attemptDuration}ms", e)
                onStateChange(UploadState.FAILED)
                return UploadResult.Error(
                    message = e.message ?: "Upload failed",
                    isRetryable = false,
                    cause = e
                )
            }
        }

        Log.i("CivicSenseSubmit", "OFFLINE_FALLBACK reason=MAX_RETRIES_REACHED")
        onStateChange(UploadState.FAILED)
        return UploadResult.OfflineQueued(
            clientReportId = reportPackage.clientReportId,
            message = "Server unreachable. Report preserved locally on this device."
        )
    }

    fun buildJsonPayload(reportPackage: ProcessedReportPackage): JSONObject {
        val root = JSONObject()

        // 1. Client Report ID & Timestamp
        root.put("client_report_id", reportPackage.clientReportId)

        // 2. Citizen Identity Fields (Optional, from local citizen profile / installation)
        if (!reportPackage.citizenId.isNullOrBlank()) {
            root.put("citizen_id", reportPackage.citizenId)
        }
        if (!reportPackage.citizenName.isNullOrBlank()) {
            root.put("citizen_name", reportPackage.citizenName)
        }
        if (!reportPackage.citizenPhone.isNullOrBlank()) {
            root.put("citizen_phone", reportPackage.citizenPhone)
        }
        if (!reportPackage.citizenEmail.isNullOrBlank()) {
            root.put("citizen_email", reportPackage.citizenEmail)
        }
        if (!reportPackage.citizenPostalCode.isNullOrBlank()) {
            root.put("citizen_postal_code", reportPackage.citizenPostalCode)
        }

        // 3. Location
        val loc = JSONObject().apply {
            put("latitude", reportPackage.location.latitude ?: 0.0)
            put("longitude", reportPackage.location.longitude ?: 0.0)
            put("address_hint", reportPackage.location.address ?: "Location unlisted")
        }
        root.put("location", loc)

        // 4. Description
        root.put("description", reportPackage.textFeatures.cleanedText)

        // 5. Category (from citizen selection)
        if (!reportPackage.category.isNullOrBlank()) {
            root.put("category", reportPackage.category)
        }

        // 6. Evidence List (includes base64 payload of edge-processed preview image)
        val evidenceArray = JSONArray()
        reportPackage.imageResult?.let { img ->
            if (img.isSuccess && img.metrics != null) {
                val ev = JSONObject().apply {
                    put("evidence_type", "IMAGE")
                    put("storage_uri", img.previewFile?.name ?: "preview.jpg")
                    put("file_hash", img.metrics.sha256)
                    put("mime_type", img.metrics.mimeType)
                    put("file_size_bytes", img.metrics.fileSizeBytes)

                    if (img.previewFile != null && img.previewFile.exists()) {
                        try {
                            val base64Data = encodeBase64(img.previewFile.readBytes())
                            put("data_base64", base64Data)
                        } catch (e: Exception) {
                            Log.w(TAG, "Failed to encode preview image bytes: ${e.message}")
                        }
                    }

                    put("metadata_json", JSONObject().apply {
                        put("is_preview", true)
                        put("width", img.metrics.width)
                        put("height", img.metrics.height)
                        put("aspect_ratio", img.metrics.aspectRatio)
                        put("usable", img.metrics.usable)
                        img.metrics.brightness?.let { put("brightness", it) }
                        img.metrics.isBlurry?.let { put("is_blurry", it) }
                    })
                }
                evidenceArray.put(ev)
            }
        }
        root.put("evidence", evidenceArray)

        // 6. Edge Processing Metadata
        val edgeMeta = JSONObject().apply {
            put("contract_version", reportPackage.contractVersion)
            put("category_hint", reportPackage.categoryHint ?: JSONObject.NULL)

            // client_processing
            put("client_processing", JSONObject().apply {
                put("enabled", reportPackage.clientProcessing.enabled)
                put("processor_version", reportPackage.clientProcessing.processorVersion)
                put("image_preprocessed", reportPackage.clientProcessing.imagePreprocessed)
                put("text_preprocessed", reportPackage.clientProcessing.textPreprocessed)
                put("embedding_generated", false)
            })

            // image_quality
            reportPackage.imageResult?.metrics?.let { q ->
                put("image_quality", JSONObject().apply {
                    put("width", q.width)
                    put("height", q.height)
                    put("aspect_ratio", q.aspectRatio)
                    put("file_size_bytes", q.fileSizeBytes)
                    put("mime_type", q.mimeType)
                    put("sha256", q.sha256)
                    q.brightness?.let { put("brightness", it) }
                    q.isBlurry?.let { put("is_blurry", it) }
                    put("usable", q.usable)
                    put("feedback_message", q.feedbackMessage)
                })
            }

            // text_features
            put("text_features", JSONObject().apply {
                put("raw_text", reportPackage.textFeatures.rawText)
                put("cleaned_text", reportPackage.textFeatures.cleanedText)
                put("character_count", reportPackage.textFeatures.characterCount)
                put("word_count", reportPackage.textFeatures.wordCount)
                put("language", reportPackage.textFeatures.language)
                put("severity_terms", JSONArray(reportPackage.textFeatures.severityTerms))
                put("urgency_terms", JSONArray(reportPackage.textFeatures.urgencyTerms))
                put("category_terms", JSONArray(reportPackage.textFeatures.categoryTerms))
                put("location_terms", JSONArray(reportPackage.textFeatures.locationTerms))
                put("safety_terms", JSONArray(reportPackage.textFeatures.safetyTerms))
            })

            put("embedding", JSONObject.NULL)
        }
        root.put("edge_metadata", edgeMeta)

        return root
    }

    private fun parseErrorMessage(body: String, statusCode: Int): String {
        return try {
            val json = JSONObject(body)
            if (json.has("error")) {
                val err = json.getJSONObject("error")
                err.optString("message", "Request failed with HTTP $statusCode")
            } else if (json.has("detail")) {
                json.getString("detail")
            } else {
                "Request failed with HTTP $statusCode"
            }
        } catch (_: Exception) {
            "Request failed with HTTP $statusCode"
        }
    }
}
