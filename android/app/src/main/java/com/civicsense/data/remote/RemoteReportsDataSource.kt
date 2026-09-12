package com.civicsense.data.remote

import android.util.Log
import com.civicsense.core.network.CivicReportUploadClient
import com.civicsense.data.model.Report
import com.civicsense.data.repository.PreferenceRepository
import com.civicsense.data.repository.ReportsDataSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.IOException

/**
 * Production-quality remote reports data source that fetches the citizen's reports
 * and single report details from the CivicSense FastAPI backend.
 */
class RemoteReportsDataSource(
    private val baseUrl: String = CivicReportUploadClient.DEFAULT_BASE_URL,
    private val client: OkHttpClient = CivicReportUploadClient.createDefaultOkHttpClient(),
    private val preferenceRepository: PreferenceRepository? = null,
    private val citizenIdProvider: (suspend () -> String)? = null
) : ReportsDataSource {

    constructor(
        preferenceRepository: PreferenceRepository,
        baseUrl: String = CivicReportUploadClient.DEFAULT_BASE_URL,
        client: OkHttpClient = CivicReportUploadClient.createDefaultOkHttpClient()
    ) : this(
        baseUrl = baseUrl,
        client = client,
        preferenceRepository = preferenceRepository,
        citizenIdProvider = null
    )

    companion object {
        private const val TAG = "CivicSenseSync"
    }

    override suspend fun fetchReports(): List<Report> = withContext(Dispatchers.IO) {
        val citizenId = citizenIdProvider?.invoke() ?: preferenceRepository?.getOrCreateCitizenId().orEmpty()
        val url = "${baseUrl.trimEnd('/')}/api/v1/reports?citizen_id=$citizenId&page_size=50"
        Log.i(TAG, "Fetching citizen reports: url=$url")

        val request = Request.Builder()
            .url(url)
            .header("Accept", "application/json")
            .get()
            .build()

        try {
            val response = client.newCall(request).execute()
            val statusCode = response.code
            val body = response.body?.string().orEmpty()

            if (!response.isSuccessful) {
                Log.w(TAG, "Failed to fetch reports: HTTP $statusCode body=$body")
                throw IOException("Server returned HTTP $statusCode")
            }

            val json = JSONObject(body)
            val itemsArray = json.optJSONArray("items") ?: return@withContext emptyList()
            val resultList = mutableListOf<Report>()

            for (i in 0 until itemsArray.length()) {
                val itemObj = itemsArray.optJSONObject(i) ?: continue
                try {
                    val report = ReportStatusMapper.parseReport(itemObj, baseUrl)
                    resultList.add(report)
                } catch (e: Exception) {
                    Log.w(TAG, "Skipping malformed report item at index $i: ${e.message}")
                }
            }

            Log.i(TAG, "Successfully fetched ${resultList.size} reports for citizen $citizenId")
            resultList
        } catch (e: Exception) {
            Log.e(TAG, "Network error fetching citizen reports: ${e.message}")
            throw e
        }
    }

    override suspend fun fetchReport(identifier: String): Report? = withContext(Dispatchers.IO) {
        if (identifier.isBlank()) return@withContext null
        val url = "${baseUrl.trimEnd('/')}/api/v1/reports/$identifier"
        Log.i(TAG, "Fetching single report detail: url=$url")

        val request = Request.Builder()
            .url(url)
            .header("Accept", "application/json")
            .get()
            .build()

        try {
            val response = client.newCall(request).execute()
            val statusCode = response.code
            val body = response.body?.string().orEmpty()

            if (statusCode == 404) {
                Log.w(TAG, "Report $identifier not found on server (HTTP 404)")
                return@withContext null
            }

            if (!response.isSuccessful) {
                Log.w(TAG, "Failed to fetch report detail $identifier: HTTP $statusCode body=$body")
                throw IOException("Server returned HTTP $statusCode")
            }

            val json = JSONObject(body)
            val report = ReportStatusMapper.parseReport(json, baseUrl)
            Log.i(TAG, "Successfully fetched report $identifier (status=${report.status})")
            report
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching report detail for $identifier: ${e.message}")
            throw e
        }
    }
}
