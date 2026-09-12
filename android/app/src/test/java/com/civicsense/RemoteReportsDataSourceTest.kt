package com.civicsense

import com.civicsense.data.model.ReportCategory
import com.civicsense.data.model.ReportStatus
import com.civicsense.data.remote.RemoteReportsDataSource
import kotlinx.coroutines.test.runTest
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException

class RemoteReportsDataSourceTest {

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    private val sampleListJson = """
        {
            "items": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "tracking_id": "REP-202609-AAA111",
                    "status": "IN_PROGRESS",
                    "category": "Road Damage",
                    "citizen_id": "czn_test_123",
                    "description": "Pothole on Main Road",
                    "latitude": 8.5615,
                    "longitude": 76.8850,
                    "address_hint": "Main Road",
                    "created_at": "2026-09-12T10:00:00Z"
                },
                {
                    "id": "123e4567-e89b-12d3-a456-426614174001",
                    "tracking_id": "REP-202609-BBB222",
                    "status": "RESOLVED",
                    "category": "Garbage",
                    "citizen_id": "czn_test_123",
                    "description": "Waste pile cleared",
                    "latitude": 8.5620,
                    "longitude": 76.8860,
                    "address_hint": "North Street",
                    "created_at": "2026-09-11T12:00:00Z"
                }
            ],
            "total": 2,
            "page": 1,
            "page_size": 50,
            "total_pages": 1
        }
    """.trimIndent()

    private val sampleDetailJson = """
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "tracking_id": "REP-202609-AAA111",
            "status": "CLOSED",
            "category": "Water Leakage",
            "citizen_id": "czn_test_123",
            "description": "Pipe leaking",
            "latitude": 8.5615,
            "longitude": 76.8850,
            "address_hint": "Market Road",
            "created_at": "2026-09-10T10:00:00Z",
            "updated_at": "2026-09-12T11:00:00Z",
            "evidences": [
                {
                    "evidence_type": "IMAGE",
                    "storage_uri": "/uploads/rep_fixed.jpg",
                    "mime_type": "image/jpeg",
                    "file_size_bytes": 10240
                }
            ],
            "ai_analyses": [
                {
                    "predicted_category": "Water Leakage",
                    "confidence": 0.95,
                    "severity": "HIGH"
                }
            ],
            "verifications": [
                {
                    "from_status": "RESOLVED",
                    "to_status": "CLOSED",
                    "created_at": "2026-09-12T11:00:00Z",
                    "notes": "Verified by citizen"
                }
            ]
        }
    """.trimIndent()

    @Test
    fun fetchReports_parsesItemsSuccessfully() = runTest {
        val client = OkHttpClient.Builder()
            .addInterceptor(Interceptor { chain ->
                val url = chain.request().url.toString()
                assertTrue(url.contains("citizen_id=czn_test_123"))
                Response.Builder()
                    .request(chain.request())
                    .protocol(Protocol.HTTP_1_1)
                    .code(200)
                    .message("OK")
                    .body(sampleListJson.toResponseBody(jsonMediaType))
                    .build()
            })
            .build()

        val dataSource = RemoteReportsDataSource(
            baseUrl = "http://localhost:8000",
            client = client,
            citizenIdProvider = { "czn_test_123" }
        )

        val reports = dataSource.fetchReports()
        assertEquals(2, reports.size)
        assertEquals("REP-202609-AAA111", reports[0].id)
        assertEquals(ReportStatus.IN_PROGRESS, reports[0].status)
        assertEquals(ReportCategory.ROAD_DAMAGE, reports[0].category)

        assertEquals("REP-202609-BBB222", reports[1].id)
        assertEquals(ReportStatus.RESOLVED, reports[1].status)
        assertEquals(ReportCategory.GARBAGE, reports[1].category)
    }

    @Test
    fun fetchReports_throwsOnHttpError() = runTest {
        val client = OkHttpClient.Builder()
            .addInterceptor(Interceptor { chain ->
                Response.Builder()
                    .request(chain.request())
                    .protocol(Protocol.HTTP_1_1)
                    .code(500)
                    .message("Internal Server Error")
                    .body("{}".toResponseBody(jsonMediaType))
                    .build()
            })
            .build()

        val dataSource = RemoteReportsDataSource(
            baseUrl = "http://localhost:8000",
            client = client,
            citizenIdProvider = { "czn_test_123" }
        )

        var thrown = false
        try {
            dataSource.fetchReports()
        } catch (e: IOException) {
            thrown = true
            assertTrue(e.message?.contains("500") == true)
        }
        assertTrue("IOException expected on HTTP 500", thrown)
    }

    @Test
    fun fetchReport_returnsParsedReportOnSuccess() = runTest {
        val client = OkHttpClient.Builder()
            .addInterceptor(Interceptor { chain ->
                val url = chain.request().url.toString()
                assertTrue(url.contains("/api/v1/reports/REP-202609-AAA111"))
                Response.Builder()
                    .request(chain.request())
                    .protocol(Protocol.HTTP_1_1)
                    .code(200)
                    .message("OK")
                    .body(sampleDetailJson.toResponseBody(jsonMediaType))
                    .build()
            })
            .build()

        val dataSource = RemoteReportsDataSource(
            baseUrl = "http://localhost:8000",
            client = client,
            citizenIdProvider = { "czn_test_123" }
        )

        val report = dataSource.fetchReport("REP-202609-AAA111")
        assertNotNull(report)
        assertEquals("REP-202609-AAA111", report?.id)
        assertEquals(ReportStatus.CLOSED, report?.status)
        assertEquals("CLOSED", report?.serverStatus)
        assertEquals(ReportCategory.WATER_LEAKAGE, report?.category)
        assertEquals("http://localhost:8000/uploads/rep_fixed.jpg", report?.imageUri)
    }

    @Test
    fun fetchReport_returnsNullOn404() = runTest {
        val client = OkHttpClient.Builder()
            .addInterceptor(Interceptor { chain ->
                Response.Builder()
                    .request(chain.request())
                    .protocol(Protocol.HTTP_1_1)
                    .code(404)
                    .message("Not Found")
                    .body("{}".toResponseBody(jsonMediaType))
                    .build()
            })
            .build()

        val dataSource = RemoteReportsDataSource(
            baseUrl = "http://localhost:8000",
            client = client,
            citizenIdProvider = { "czn_test_123" }
        )

        val report = dataSource.fetchReport("REP-NONEXISTENT")
        assertNull(report)
    }
}
