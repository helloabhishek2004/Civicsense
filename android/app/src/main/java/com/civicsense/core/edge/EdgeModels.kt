package com.civicsense.core.edge

import android.net.Uri
import com.civicsense.data.model.ReportLocation
import java.io.File

/**
 * Explicit client-side processing metadata flags and versions.
 */
data class ClientProcessingInfo(
    val enabled: Boolean = true,
    val processorVersion: String = "1.0.0",
    val imagePreprocessed: Boolean = false,
    val textPreprocessed: Boolean = false,
    val embeddingGenerated: Boolean = false
)

/**
 * Lightweight on-device image quality metrics and hash integrity.
 */
data class ImageQualityMetrics(
    val width: Int,
    val height: Int,
    val aspectRatio: Float,
    val fileSizeBytes: Long,
    val mimeType: String = "image/jpeg",
    val sha256: String,
    val brightness: Float? = null,
    val isBlurry: Boolean? = null,
    val usable: Boolean = true,
    val feedbackMessage: String = "Image verified"
)

/**
 * Structured linguistic features extracted deterministically on device.
 * Transparent keyword matches are preprocessing hints, NOT AI predictions.
 */
data class TextStructuredFeatures(
    val rawText: String,
    val cleanedText: String,
    val characterCount: Int,
    val wordCount: Int,
    val language: String = "en",
    val severityTerms: List<String> = emptyList(),
    val urgencyTerms: List<String> = emptyList(),
    val categoryTerms: List<String> = emptyList(),
    val locationTerms: List<String> = emptyList(),
    val safetyTerms: List<String> = emptyList()
)

/**
 * Result of on-device image validation, EXIF normalization, preview generation, and quality check.
 */
data class PreprocessedImageResult(
    val previewFile: File? = null,
    val previewUri: Uri? = null,
    val originalUri: Uri? = null,
    val metrics: ImageQualityMetrics? = null,
    val isSuccess: Boolean = true,
    val errorMessage: String? = null
)

/**
 * Canonical versioned data contract packaging all edge-processed report evidence.
 * Prepared for transmission to CivicSense backend API v1.
 */
data class ProcessedReportPackage(
    val clientReportId: String,
    val timestamp: String,
    val location: ReportLocation,
    val category: String? = null,
    val categoryHint: String? = null,
    val textFeatures: TextStructuredFeatures,
    val imageResult: PreprocessedImageResult? = null,
    val citizenId: String? = null,
    val citizenName: String? = null,
    val citizenPhone: String? = null,
    val citizenEmail: String? = null,
    val citizenPostalCode: String? = null,
    val clientProcessing: ClientProcessingInfo = ClientProcessingInfo(
        imagePreprocessed = imageResult?.isSuccess == true,
        textPreprocessed = true,
        embeddingGenerated = false
    ),
    val contractVersion: String = "1.0.0"
)

/**
 * Strict, observable upload lifecycle state.
 */
enum class UploadState {
    IDLE,
    PREPARING,
    PREPROCESSING,
    UPLOADING,
    SUBMITTED,
    FAILED,
    RETRYING
}
