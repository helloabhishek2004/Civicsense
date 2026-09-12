package com.civicsense.core.edge

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import android.util.Log
import androidx.core.content.FileProvider
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream
import java.security.MessageDigest
import java.util.UUID
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * Production-minded image preprocessing pipeline for edge validation,
 * orientation correction, low-resolution preview generation, EXIF stripping,
 * and lightweight quality metric calculation.
 */
object CivicImagePreprocessor {

    private const val TAG = "CivicSenseImage"
    const val MAX_INPUT_SIZE_BYTES = 25 * 1024 * 1024L // 25 MB
    const val MAX_PREVIEW_DIMENSION = 640              // Max dimension (width or height)
    const val PREVIEW_JPEG_QUALITY = 82                // Visual balance between size and quality

    /**
     * Executes the complete image preprocessing pipeline.
     */
    fun preprocess(context: Context, imageUri: Uri): PreprocessedImageResult {
        val startTime = System.currentTimeMillis()
        Log.d(TAG, "[CivicSense][Image] Preprocessing started")

        // 1. Validation & Input Bounds
        val validation = validateInput(context, imageUri)
        if (!validation.isValid) {
            Log.w(TAG, "[CivicSense][Image] Validation failed: ${validation.errorMessage}")
            return PreprocessedImageResult(
                originalUri = imageUri,
                isSuccess = false,
                errorMessage = validation.errorMessage
            )
        }

        try {
            // 2. Memory-Safe Bitmap Decoding with Downsampling
            val sampleSize = calculateInSampleSize(validation.rawWidth, validation.rawHeight, MAX_PREVIEW_DIMENSION)
            val decodeOptions = BitmapFactory.Options().apply {
                inSampleSize = sampleSize
                inPreferredConfig = Bitmap.Config.ARGB_8888
            }

            val rawBitmap = context.contentResolver.openInputStream(imageUri)?.use { stream ->
                BitmapFactory.decodeStream(stream, null, decodeOptions)
            } ?: return PreprocessedImageResult(
                originalUri = imageUri,
                isSuccess = false,
                errorMessage = "Failed to decode image data"
            )

            // 3. EXIF Orientation Normalization
            val orientationDegrees = getExifOrientationDegrees(context, imageUri)
            val uprightBitmap = if (orientationDegrees != 0) {
                val matrix = Matrix().apply { postRotate(orientationDegrees.toFloat()) }
                Bitmap.createBitmap(rawBitmap, 0, 0, rawBitmap.width, rawBitmap.height, matrix, true).also {
                    if (it != rawBitmap) rawBitmap.recycle()
                }
            } else {
                rawBitmap
            }
            Log.d(TAG, "[CivicSense][Image] Orientation normalized (rotation: ${orientationDegrees}°)")

            // 4. Delegate to preprocessBitmap
            val previewsDir = File(context.cacheDir, "previews").apply { if (!exists()) mkdirs() }
            val authority = "${context.packageName}.fileprovider"

            return preprocessBitmap(
                sourceBitmap = uprightBitmap,
                outputDir = previewsDir,
                originalUri = imageUri,
                fileProviderAuthority = authority
            )
        } catch (oom: OutOfMemoryError) {
            Log.e(TAG, "[CivicSense][Image] OutOfMemoryError during image preprocessing", oom)
            return PreprocessedImageResult(
                originalUri = imageUri,
                isSuccess = false,
                errorMessage = "Insufficient memory to process image. Please try a smaller photo."
            )
        } catch (e: Exception) {
            Log.e(TAG, "[CivicSense][Image] Error during preprocessing", e)
            return PreprocessedImageResult(
                originalUri = imageUri,
                isSuccess = false,
                errorMessage = "Image preprocessing failed: ${e.message ?: "Unknown error"}"
            )
        }
    }

    /**
     * Preprocesses a Bitmap directly: downscales to maxDimension,
     * strips EXIF metadata by recompressing to fresh JPEG in outputDir,
     * and calculates quality metrics (brightness, blur, hash, dimensions).
     */
    fun preprocessBitmap(
        sourceBitmap: Bitmap,
        outputDir: File,
        originalUri: Uri? = null,
        fileProviderAuthority: String? = null
    ): PreprocessedImageResult {
        val startTime = System.currentTimeMillis()
        try {
            if (!outputDir.exists()) outputDir.mkdirs()

            // 1. Exact Preview Downscaling preserving Aspect Ratio
            val finalPreviewBitmap = scaleToMaxDimension(sourceBitmap, MAX_PREVIEW_DIMENSION)

            val previewWidth = finalPreviewBitmap.width
            val previewHeight = finalPreviewBitmap.height
            val aspectRatio = if (previewHeight > 0) previewWidth.toFloat() / previewHeight else 1.0f

            // 2. Save Cleaned Preview (Strips all device/camera EXIF)
            val previewFile = File(outputDir, "preview_${UUID.randomUUID().toString().take(8)}.jpg")

            FileOutputStream(previewFile).use { out ->
                finalPreviewBitmap.compress(Bitmap.CompressFormat.JPEG, PREVIEW_JPEG_QUALITY, out)
                out.flush()
            }
            val previewBytes = previewFile.length()

            // 3. Compute Quality Metrics & Hash
            val sha256Hash = computeSha256(previewFile)
            val brightness = estimateBrightness(finalPreviewBitmap)
            val isBlurry = estimateBlurry(finalPreviewBitmap)

            val (usable, feedback) = determineUsability(brightness, isBlurry, previewWidth, previewHeight)

            if (finalPreviewBitmap != sourceBitmap) {
                finalPreviewBitmap.recycle()
            }

            val previewUri = Uri.fromFile(previewFile)

            val metrics = ImageQualityMetrics(
                width = previewWidth,
                height = previewHeight,
                aspectRatio = (aspectRatio * 1000).roundToInt() / 1000f,
                fileSizeBytes = previewBytes,
                mimeType = "image/jpeg",
                sha256 = sha256Hash,
                brightness = brightness,
                isBlurry = isBlurry,
                usable = usable,
                feedbackMessage = feedback
            )

            val durationMs = System.currentTimeMillis() - startTime
            Log.d(TAG, "[CivicSense][Image] Preview generated: ${previewWidth}x${previewHeight}, ${previewBytes / 1024} KB in ${durationMs} ms")
            Log.d(TAG, "[CivicSense][Image] Quality check completed: usable=$usable, brightness=$brightness")

            return PreprocessedImageResult(
                previewFile = previewFile,
                previewUri = previewUri,
                originalUri = originalUri,
                metrics = metrics,
                isSuccess = true
            )
        } catch (e: Exception) {
            Log.e(TAG, "[CivicSense][Image] Error during preprocessBitmap", e)
            return PreprocessedImageResult(
                originalUri = originalUri,
                isSuccess = false,
                errorMessage = "Bitmap preprocessing failed: ${e.message ?: "Unknown error"}"
            )
        }
    }

    private data class InputValidationResult(
        val isValid: Boolean,
        val rawWidth: Int = 0,
        val rawHeight: Int = 0,
        val errorMessage: String? = null
    )

    private fun validateInput(context: Context, uri: Uri): InputValidationResult {
        return try {
            val contentResolver = context.contentResolver

            // Check if file is readable
            val stream: InputStream = contentResolver.openInputStream(uri)
                ?: return InputValidationResult(false, errorMessage = "Cannot access selected image file")

            // Check size if possible
            val availableBytes = stream.use { it.available().toLong() }
            if (availableBytes > MAX_INPUT_SIZE_BYTES) {
                return InputValidationResult(false, errorMessage = "Image file is too large (max 25MB allowed)")
            }

            // Decode bounds only
            val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            contentResolver.openInputStream(uri)?.use { s ->
                BitmapFactory.decodeStream(s, null, options)
            }

            if (options.outWidth <= 0 || options.outHeight <= 0) {
                InputValidationResult(false, errorMessage = "Corrupted or unsupported image format")
            } else {
                InputValidationResult(true, rawWidth = options.outWidth, rawHeight = options.outHeight)
            }
        } catch (se: SecurityException) {
            InputValidationResult(false, errorMessage = "Missing read permission for selected image")
        } catch (e: Exception) {
            InputValidationResult(false, errorMessage = "Unable to read image: ${e.message ?: "unreadable"}")
        }
    }

    fun calculateInSampleSize(width: Int, height: Int, maxDim: Int): Int {
        var inSampleSize = 1
        val maxOriginal = max(width, height)
        if (maxOriginal > maxDim) {
            val halfMax = maxOriginal / 2
            while ((halfMax / inSampleSize) >= maxDim) {
                inSampleSize *= 2
            }
        }
        return max(1, inSampleSize)
    }

    private fun getExifOrientationDegrees(context: Context, uri: Uri): Int {
        return try {
            context.contentResolver.openInputStream(uri)?.use { stream ->
                val exif = ExifInterface(stream)
                when (exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)) {
                    ExifInterface.ORIENTATION_ROTATE_90 -> 90
                    ExifInterface.ORIENTATION_ROTATE_180 -> 180
                    ExifInterface.ORIENTATION_ROTATE_270 -> 270
                    else -> 0
                }
            } ?: 0
        } catch (_: Exception) {
            0
        }
    }

    private fun scaleToMaxDimension(source: Bitmap, maxDim: Int): Bitmap {
        val srcWidth = source.width
        val srcHeight = source.height
        val maxCurrent = max(srcWidth, srcHeight)
        if (maxCurrent <= maxDim) return source

        val ratio = maxDim.toFloat() / maxCurrent
        val targetWidth = max(1, (srcWidth * ratio).roundToInt())
        val targetHeight = max(1, (srcHeight * ratio).roundToInt())

        return Bitmap.createScaledBitmap(source, targetWidth, targetHeight, true)
    }

    fun computeSha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { stream ->
            val buffer = ByteArray(8192)
            var read: Int
            while (stream.read(buffer).also { read = it } != -1) {
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    /**
     * Computes average perceived luminance across a 32x32 sample.
     * Normalized output: 0.0 (pitch black) to 1.0 (pure white).
     */
    fun estimateBrightness(bitmap: Bitmap): Float {
        return try {
            val sampleSize = 32
            val sampled = Bitmap.createScaledBitmap(bitmap, sampleSize, sampleSize, true)
            var totalLuminance = 0.0

            val pixels = IntArray(sampleSize * sampleSize)
            sampled.getPixels(pixels, 0, sampleSize, 0, 0, sampleSize, sampleSize)
            if (sampled != bitmap) sampled.recycle()

            for (pixel in pixels) {
                val r = (pixel shr 16) and 0xFF
                val g = (pixel shr 8) and 0xFF
                val b = pixel and 0xFF
                // Standard ITU-R BT.601 perceptual luminance formula
                val lum = 0.299 * r + 0.587 * g + 0.114 * b
                totalLuminance += lum
            }

            val avgLum = totalLuminance / (pixels.size * 255.0)
            ((avgLum * 100).roundToInt()) / 100f
        } catch (_: Exception) {
            0.50f
        }
    }

    /**
     * Lightweight focus / sharpness estimate:
     * Computes mean variance of adjacent horizontal and vertical pixel differences.
     * If variance is lower than threshold, flag as potentially blurry.
     */
    fun estimateBlurry(bitmap: Bitmap): Boolean {
        return try {
            val sampleW = min(64, bitmap.width)
            val sampleH = min(64, bitmap.height)
            val sampled = Bitmap.createScaledBitmap(bitmap, sampleW, sampleH, true)

            val pixels = IntArray(sampleW * sampleH)
            sampled.getPixels(pixels, 0, sampleW, 0, 0, sampleW, sampleH)
            if (sampled != bitmap) sampled.recycle()

            var edgeDiffSum = 0.0
            var count = 0

            for (y in 0 until sampleH - 1) {
                for (x in 0 until sampleW - 1) {
                    val p = pixels[y * sampleW + x]
                    val pRight = pixels[y * sampleW + (x + 1)]
                    val pDown = pixels[(y + 1) * sampleW + x]

                    val lumCurrent = ((p shr 16 and 0xFF) * 0.299 + (p shr 8 and 0xFF) * 0.587 + (p and 0xFF) * 0.114)
                    val lumRight = ((pRight shr 16 and 0xFF) * 0.299 + (pRight shr 8 and 0xFF) * 0.587 + (pRight and 0xFF) * 0.114)
                    val lumDown = ((pDown shr 16 and 0xFF) * 0.299 + (pDown shr 8 and 0xFF) * 0.587 + (pDown and 0xFF) * 0.114)

                    val diff = Math.abs(lumCurrent - lumRight) + Math.abs(lumCurrent - lumDown)
                    edgeDiffSum += diff
                    count++
                }
            }

            val meanEdgeDiff = if (count > 0) edgeDiffSum / count else 20.0
            // Low edge difference across sample indicates lack of high-frequency detail (blurry)
            meanEdgeDiff < 4.5
        } catch (_: Exception) {
            false
        }
    }

    fun determineUsability(
        brightness: Float,
        isBlurry: Boolean,
        width: Int,
        height: Int
    ): Pair<Boolean, String> {
        if (width < 64 || height < 64) {
            return Pair(false, "Image resolution is too low to inspect.")
        }
        if (brightness < 0.15f) {
            return Pair(true, "The image may be dark. Ensure adequate lighting.")
        }
        if (brightness > 0.90f) {
            return Pair(true, "The image appears overexposed. Ensure clear lighting.")
        }
        if (isBlurry) {
            return Pair(true, "The image may be blurry. Consider retaking it.")
        }
        return Pair(true, "The image looks good and sharp.")
    }

    /**
     * Cleans up preview files older than 2 hours.
     */
    fun cleanupOldPreviews(context: Context) {
        try {
            val previewsDir = File(context.cacheDir, "previews")
            if (previewsDir.exists() && previewsDir.isDirectory) {
                val now = System.currentTimeMillis()
                previewsDir.listFiles()?.forEach { f ->
                    if (now - f.lastModified() > 2 * 60 * 60 * 1000) {
                        f.delete()
                    }
                }
            }
        } catch (_: Exception) {
            // Non-critical cache cleanup
        }
    }
}
