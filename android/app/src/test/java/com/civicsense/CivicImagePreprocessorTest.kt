package com.civicsense

import com.civicsense.core.edge.CivicImagePreprocessor
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File

class CivicImagePreprocessorTest {

    @get:Rule
    val tempFolder = TemporaryFolder()

    private val preprocessor = CivicImagePreprocessor

    @Test
    fun calculateInSampleSize_computesCorrectPowerOfTwoSubsampling() {
        // Under max dimension (1280): no subsampling needed
        assertEquals(1, preprocessor.calculateInSampleSize(800, 600, 1280))
        assertEquals(1, preprocessor.calculateInSampleSize(1280, 720, 1280))

        // High resolution phone photos: 4032 x 3024 (e.g. 12MP)
        // halfMax is 2016. 2016 / 1 >= 1280 -> inSampleSize becomes 2.
        assertEquals(2, preprocessor.calculateInSampleSize(4032, 3024, 1280))

        // Ultra high resolution: 8000 x 6000
        // halfMax is 4000. 4000/1 >= 1280 -> 2. 4000/2=2000 >= 1280 -> 4. 4000/4=1000 < 1280 -> inSampleSize 4.
        assertEquals(4, preprocessor.calculateInSampleSize(8000, 6000, 1280))
    }

    @Test
    fun computeSha256_computesDeterministicHashOfFile() {
        val testFile = tempFolder.newFile("test_evidence.dat")
        testFile.writeText("CivicSense Test Evidence Content")

        val hash = preprocessor.computeSha256(testFile)

        // SHA-256 of "CivicSense Test Evidence Content" (UTF-8 bytes):
        // echo -n "CivicSense Test Evidence Content" | sha256sum
        assertEquals(64, hash.length)
        // Consistent hash across repeated computations
        assertEquals(hash, preprocessor.computeSha256(testFile))
    }

    @Test
    fun determineUsability_identifiesLowResolutionDarkOverexposedAndBlurry() {
        // 1. Resolution too low
        val tooSmall = preprocessor.determineUsability(
            brightness = 0.5f,
            isBlurry = false,
            width = 48,
            height = 48
        )
        assertFalse(tooSmall.first)
        assertTrue(tooSmall.second.contains("resolution is too low", ignoreCase = true))

        // 2. Dark lighting
        val dark = preprocessor.determineUsability(
            brightness = 0.10f,
            isBlurry = false,
            width = 640,
            height = 480
        )
        assertTrue(dark.first)
        assertTrue(dark.second.contains("dark", ignoreCase = true))

        // 3. Overexposed
        val bright = preprocessor.determineUsability(
            brightness = 0.95f,
            isBlurry = false,
            width = 640,
            height = 480
        )
        assertTrue(bright.first)
        assertTrue(bright.second.contains("overexposed", ignoreCase = true))

        // 4. Blurry
        val blurry = preprocessor.determineUsability(
            brightness = 0.50f,
            isBlurry = true,
            width = 640,
            height = 480
        )
        assertTrue(blurry.first)
        assertTrue(blurry.second.contains("blurry", ignoreCase = true))

        // 5. Good quality
        val good = preprocessor.determineUsability(
            brightness = 0.55f,
            isBlurry = false,
            width = 640,
            height = 480
        )
        assertTrue(good.first)
        assertTrue(good.second.contains("sharp", ignoreCase = true))
    }
}
