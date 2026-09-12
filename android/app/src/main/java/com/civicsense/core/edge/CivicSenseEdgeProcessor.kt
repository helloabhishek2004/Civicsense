package com.civicsense.core.edge

import android.content.Context
import android.net.Uri
import android.util.Log
import com.civicsense.data.model.ReportLocation
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.UUID

/**
 * Top-level edge processing coordinator for Phase 1.
 * Orchestrates image validation, preview generation, text normalization,
 * and canonical payload packaging.
 */
class CivicSenseEdgeProcessor(
    private val imagePreprocessor: CivicImagePreprocessor = CivicImagePreprocessor,
    private val textPreprocessor: CivicTextPreprocessor = CivicTextPreprocessor
) {

    companion object {
        private const val TAG = "CivicSenseEdge"
        const val PROCESSOR_VERSION = "1.0.0"

        @Volatile
        private var instance: CivicSenseEdgeProcessor? = null

        fun getInstance(): CivicSenseEdgeProcessor {
            return instance ?: synchronized(this) {
                instance ?: CivicSenseEdgeProcessor().also { instance = it }
            }
        }
    }

    data class ProcessingResult(
        val reportPackage: ProcessedReportPackage,
        val totalDurationMs: Long,
        val imageDurationMs: Long,
        val textDurationMs: Long
    )

    /**
     * Executes the edge preprocessing pipeline on background thread.
     */
    fun process(
        context: Context? = null,
        rawDescription: String,
        imageUri: Uri?,
        location: ReportLocation,
        category: String? = null,
        categoryHint: String? = null,
        clientReportId: String = UUID.randomUUID().toString(),
        citizenId: String? = null,
        citizenName: String? = null,
        citizenPhone: String? = null,
        citizenEmail: String? = null,
        citizenPostalCode: String? = null
    ): ProcessingResult {
        val totalStart = System.currentTimeMillis()
        val truncatedId = clientReportId.take(8)
        Log.i(TAG, "[CivicSense][Report] Submission started: clientReportId=$truncatedId...")
        Log.i(TAG, "[CivicSense][Edge] Preprocessing started")

        // 1. Image Preprocessing (if image attached and context available)
        val imageStart = System.currentTimeMillis()
        Log.i("CivicSenseSubmit", "IMAGE_PREP_START has_image=${imageUri != null}")
        val imageResult = if (context != null && imageUri != null) {
            imagePreprocessor.preprocess(context, imageUri)
        } else {
            null
        }
        val imageDurationMs = System.currentTimeMillis() - imageStart
        Log.i("CivicSenseSubmit", "IMAGE_PREP_COMPLETE duration_ms=$imageDurationMs success=${imageResult?.isSuccess ?: false}")

        // 2. Text Preprocessing
        val textStart = System.currentTimeMillis()
        Log.i("CivicSenseSubmit", "FEATURE_EXTRACTION_START")
        val textFeatures = textPreprocessor.preprocess(rawDescription)
        val textDurationMs = System.currentTimeMillis() - textStart
        Log.i("CivicSenseSubmit", "FEATURE_EXTRACTION_COMPLETE duration_ms=$textDurationMs terms_count=${textFeatures.categoryTerms.size + textFeatures.severityTerms.size}")

        // 3. Package into Canonical Versioned Evidence Contract
        val isoTimestamp = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }.format(Date())

        val reportPackage = ProcessedReportPackage(
            clientReportId = clientReportId,
            timestamp = isoTimestamp,
            location = location,
            category = category,
            categoryHint = categoryHint ?: category,
            textFeatures = textFeatures,
            imageResult = imageResult,
            citizenId = citizenId,
            citizenName = citizenName,
            citizenPhone = citizenPhone,
            citizenEmail = citizenEmail,
            citizenPostalCode = citizenPostalCode,
            clientProcessing = ClientProcessingInfo(
                enabled = true,
                processorVersion = PROCESSOR_VERSION,
                imagePreprocessed = imageResult?.isSuccess == true,
                textPreprocessed = true,
                embeddingGenerated = false
            ),
            contractVersion = "1.0.0"
        )

        val totalDurationMs = System.currentTimeMillis() - totalStart
        Log.i(TAG, "[CivicSense][Edge] Evidence package created in ${totalDurationMs} ms (image=${imageDurationMs}ms, text=${textDurationMs}ms)")

        return ProcessingResult(
            reportPackage = reportPackage,
            totalDurationMs = totalDurationMs,
            imageDurationMs = imageDurationMs,
            textDurationMs = textDurationMs
        )
    }
}
