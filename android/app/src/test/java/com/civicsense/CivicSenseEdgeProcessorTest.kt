package com.civicsense

import com.civicsense.core.edge.CivicSenseEdgeProcessor
import com.civicsense.core.edge.ClientProcessingInfo
import com.civicsense.core.edge.TextStructuredFeatures
import com.civicsense.data.model.LocationSource
import com.civicsense.data.model.ReportLocation
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.UUID

class CivicSenseEdgeProcessorTest {

    @Test
    fun edgeProcessor_packagesReportEvidenceWithHonestProvenance() {
        val processor = CivicSenseEdgeProcessor.getInstance()
        val clientReportId = UUID.randomUUID().toString()
        val location = ReportLocation(
            latitude = 8.5241,
            longitude = 76.9366,
            address = "Pattom, Trivandrum",
            postalPin = "695004",
            source = LocationSource.CURRENT_LOCATION
        )

        val textFeatures = processor.process(
            context = null,
            rawDescription = "Urgent: Large pothole with dangerous exposed metal near school gate",
            imageUri = null,
            location = location,
            categoryHint = "Road damage",
            clientReportId = clientReportId
        )

        val pkg = textFeatures.reportPackage
        assertEquals(clientReportId, pkg.clientReportId)
        assertEquals("1.0.0", pkg.contractVersion)
        assertEquals("Road damage", pkg.categoryHint)
        assertEquals(location, pkg.location)

        // Verify client processing flags
        assertTrue(pkg.clientProcessing.enabled)
        assertEquals("1.0.0", pkg.clientProcessing.processorVersion)
        assertTrue(pkg.clientProcessing.textPreprocessed)
        assertFalse(pkg.clientProcessing.imagePreprocessed)
        assertFalse("On-device embeddings must NOT be claimed in Phase 1", pkg.clientProcessing.embeddingGenerated)

        // Verify structured text features
        assertEquals("Urgent: Large pothole with dangerous exposed metal near school gate", pkg.textFeatures.cleanedText)
        assertTrue("large" in pkg.textFeatures.severityTerms)
        assertTrue("dangerous" in pkg.textFeatures.severityTerms)
        assertTrue("urgent" in pkg.textFeatures.urgencyTerms)
        assertTrue("pothole" in pkg.textFeatures.categoryTerms)
        assertTrue("near" in pkg.textFeatures.locationTerms)
        assertTrue("school" in pkg.textFeatures.locationTerms)

        // Verify timings recorded
        assertTrue(textFeatures.totalDurationMs >= 0)
        assertTrue(textFeatures.textDurationMs >= 0)
    }
}
