package com.civicsense.core.util

import android.content.Context
import android.net.Uri
import androidx.core.content.FileProvider
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object CameraHelper {

    /**
     * Creates a temporary file in cacheDir/images and returns a content URI
     * generated through FileProvider.
     */
    fun createTempPictureUri(context: Context): Uri {
        val imagesDir = File(context.cacheDir, "images").apply {
            if (!exists()) {
                mkdirs()
            }
        }
        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val tempFile = File(imagesDir, "temp_capture_${timestamp}.jpg")
        val authority = "${context.packageName}.fileprovider"

        return FileProvider.getUriForFile(context, authority, tempFile)
    }

    /**
     * Optional utility to clean up cached temporary camera captures.
     */
    fun clearTempImages(context: Context) {
        try {
            val imagesDir = File(context.cacheDir, "images")
            if (imagesDir.exists() && imagesDir.isDirectory) {
                imagesDir.listFiles()?.forEach { file ->
                    if (file.name.startsWith("temp_capture_")) {
                        file.delete()
                    }
                }
            }
        } catch (_: Exception) {
            // Non-critical cache cleanup failure
        }
    }
}
