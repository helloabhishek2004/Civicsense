package com.civicsense

import com.civicsense.core.edge.CivicTextPreprocessor
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CivicTextPreprocessorTest {

    @Test
    fun preprocess_normalizesWhitespaceAndCountsCorrectly() {
        val raw = "   Large   pothole   near   the   school gate.\n\nDangerous for children!   "
        val result = CivicTextPreprocessor.preprocess(raw)

        assertEquals("Large pothole near the school gate. Dangerous for children!", result.cleanedText)
        assertEquals(result.cleanedText.length, result.characterCount)
        assertEquals(9, result.wordCount)
        assertEquals("en", result.language)
    }

    @Test
    fun preprocess_extractsStructuredKeywordHintsAccurately() {
        val text = "Severe water leak from broken pipe near hospital. Emergency situation with heavy traffic hazard."
        val result = CivicTextPreprocessor.preprocess(text)

        // Severity hints
        assertTrue("Must detect 'severe' in severity hints", "severe" in result.severityTerms)
        assertTrue("Must detect 'broken' in severity hints", "broken" in result.severityTerms)
        assertTrue("Must detect 'heavy' in severity hints", "heavy" in result.severityTerms)

        // Urgency hints
        assertTrue("Must detect 'emergency' in urgency hints", "emergency" in result.urgencyTerms)
        assertTrue("Must detect 'hazard' in urgency hints", "hazard" in result.urgencyTerms)

        // Category hints
        assertTrue("Must detect 'leak' in category hints", "leak" in result.categoryTerms)
        assertTrue("Must detect 'pipe' in category hints", "pipe" in result.categoryTerms)
        assertTrue("Must detect 'water' in category hints", "water" in result.categoryTerms)

        // Location hints
        assertTrue("Must detect 'near' in location hints", "near" in result.locationTerms)
        assertTrue("Must detect 'hospital' in location hints", "hospital" in result.locationTerms)

        // Safety hints
        assertTrue("Must detect 'traffic' in safety hints", "traffic" in result.safetyTerms)
    }

    @Test
    fun preprocess_handlesEmptyAndBlankTextSafely() {
        val emptyResult = CivicTextPreprocessor.preprocess("")
        assertEquals("", emptyResult.cleanedText)
        assertEquals(0, emptyResult.characterCount)
        assertEquals(0, emptyResult.wordCount)
        assertTrue(emptyResult.categoryTerms.isEmpty())
        assertTrue(emptyResult.severityTerms.isEmpty())

        val blankResult = CivicTextPreprocessor.preprocess("   \t\n   ")
        assertEquals("", blankResult.cleanedText)
        assertEquals(0, blankResult.characterCount)
        assertEquals(0, blankResult.wordCount)
    }

    @Test
    fun preprocess_boundsExcessivelyLongDescriptions() {
        val longText = "a".repeat(6000)
        val result = CivicTextPreprocessor.preprocess(longText)

        assertEquals(CivicTextPreprocessor.MAX_TEXT_LENGTH, result.rawText.length)
        assertEquals(CivicTextPreprocessor.MAX_TEXT_LENGTH, result.cleanedText.length)
        assertEquals(CivicTextPreprocessor.MAX_TEXT_LENGTH, result.characterCount)
    }

    @Test
    fun preprocess_preservesMeaningfulPunctuationAndCaseInOutput() {
        val input = "Road crater on NH-66, near Technopark! Is anyone fixing this???"
        val result = CivicTextPreprocessor.preprocess(input)

        assertEquals("Road crater on NH-66, near Technopark! Is anyone fixing this???", result.cleanedText)
        assertTrue("road" in result.categoryTerms)
        assertTrue("crater" in result.categoryTerms)
        assertTrue("near" in result.locationTerms)
    }
}
