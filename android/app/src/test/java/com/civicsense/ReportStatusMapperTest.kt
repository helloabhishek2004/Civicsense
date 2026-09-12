package com.civicsense

import com.civicsense.data.model.ReportCategory
import com.civicsense.data.model.ReportStatus
import com.civicsense.data.model.SeverityLevel
import com.civicsense.data.remote.ReportStatusMapper
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ReportStatusMapperTest {

    @Test
    fun mapServerStatus_mapsAllElevenCanonicalStatesAccurately() {
        assertEquals(ReportStatus.SUBMITTED, ReportStatusMapper.mapServerStatus("SUBMITTED"))
        assertEquals(ReportStatus.UNDER_REVIEW, ReportStatusMapper.mapServerStatus("AI_PROCESSING"))
        assertEquals(ReportStatus.UNDER_REVIEW, ReportStatusMapper.mapServerStatus("AI_PROCESSED"))
        assertEquals(ReportStatus.UNDER_REVIEW, ReportStatusMapper.mapServerStatus("VERIFICATION_REQUIRED"))
        assertEquals(ReportStatus.CONFIRMED, ReportStatusMapper.mapServerStatus("VERIFIED"))
        assertEquals(ReportStatus.CONFIRMED, ReportStatusMapper.mapServerStatus("PRIORITIZED"))
        assertEquals(ReportStatus.ASSIGNED, ReportStatusMapper.mapServerStatus("ASSIGNED"))
        assertEquals(ReportStatus.IN_PROGRESS, ReportStatusMapper.mapServerStatus("IN_PROGRESS"))
        assertEquals(ReportStatus.RESOLVED, ReportStatusMapper.mapServerStatus("RESOLVED"))
        assertEquals(ReportStatus.RESOLVED, ReportStatusMapper.mapServerStatus("RESOLUTION_VERIFIED"))
        assertEquals(ReportStatus.CLOSED, ReportStatusMapper.mapServerStatus("CLOSED"))
    }

    @Test
    fun mapServerStatus_handlesCaseInsensitivityAndFallbacks() {
        assertEquals(ReportStatus.SUBMITTED, ReportStatusMapper.mapServerStatus("submitted"))
        assertEquals(ReportStatus.UNDER_REVIEW, ReportStatusMapper.mapServerStatus("ai_processing"))
        assertEquals(ReportStatus.RESOLVED, ReportStatusMapper.mapServerStatus("resolved"))
        assertEquals(ReportStatus.CLOSED, ReportStatusMapper.mapServerStatus("closed"))
        assertEquals(ReportStatus.SUBMITTED, ReportStatusMapper.mapServerStatus(null))
        assertEquals(ReportStatus.SUBMITTED, ReportStatusMapper.mapServerStatus(""))
        assertEquals(ReportStatus.SUBMITTED, ReportStatusMapper.mapServerStatus("UNKNOWN_FUTURE_STATE"))
    }

    @Test
    fun mapSeverity_mapsCorrectly() {
        assertEquals(SeverityLevel.CRITICAL, ReportStatusMapper.mapSeverity("CRITICAL", null))
        assertEquals(SeverityLevel.HIGH, ReportStatusMapper.mapSeverity("HIGH", null))
        assertEquals(SeverityLevel.MEDIUM, ReportStatusMapper.mapSeverity("MEDIUM", null))
        assertEquals(SeverityLevel.LOW, ReportStatusMapper.mapSeverity("LOW", null))
        assertEquals(SeverityLevel.CRITICAL, ReportStatusMapper.mapSeverity(null, "CRITICAL"))
        assertEquals(SeverityLevel.MEDIUM, ReportStatusMapper.mapSeverity(null, null))
    }

    @Test
    fun mapCategory_mapsCorrectly() {
        assertEquals(ReportCategory.ROAD_DAMAGE, ReportStatusMapper.mapCategory("Road Damage"))
        assertEquals(ReportCategory.ROAD_DAMAGE, ReportStatusMapper.mapCategory("ROAD_DAMAGE"))
        assertEquals(ReportCategory.GARBAGE, ReportStatusMapper.mapCategory("Garbage"))
        assertEquals(ReportCategory.WATER_LEAKAGE, ReportStatusMapper.mapCategory("Water Leakage"))
        assertEquals(ReportCategory.INFRASTRUCTURE, ReportStatusMapper.mapCategory("Infrastructure"))
        assertEquals(ReportCategory.NOT_SURE, ReportStatusMapper.mapCategory("Not sure"))
        assertEquals(ReportCategory.OTHER, ReportStatusMapper.mapCategory("Miscellaneous"))
        assertEquals(ReportCategory.OTHER, ReportStatusMapper.mapCategory(null))
    }

    @Test
    fun buildTimeline_buildsAccurateSixStages() {
        // Test SUBMITTED state
        val timelineSubmitted = ReportStatusMapper.buildTimeline("SUBMITTED", "2026-09-12T10:00:00Z")
        assertEquals(6, timelineSubmitted.size)
        assertTrue(timelineSubmitted[0].isCurrent)
        assertTrue(timelineSubmitted[0].isCompleted)
        assertFalse(timelineSubmitted[1].isCompleted)
        assertFalse(timelineSubmitted[1].isCurrent)

        // Test ASSIGNED state
        val timelineAssigned = ReportStatusMapper.buildTimeline("ASSIGNED", "2026-09-12T10:00:00Z", "2026-09-12T12:00:00Z")
        assertEquals(6, timelineAssigned.size)
        // Stages 1, 2, 3 must be completed
        assertTrue(timelineAssigned[0].isCompleted)
        assertFalse(timelineAssigned[0].isCurrent)
        assertTrue(timelineAssigned[1].isCompleted)
        assertFalse(timelineAssigned[1].isCurrent)
        assertTrue(timelineAssigned[2].isCompleted)
        assertFalse(timelineAssigned[2].isCurrent)
        // Stage 4 (ASSIGNED) is current and completed
        assertEquals(ReportStatus.ASSIGNED, timelineAssigned[3].status)
        assertTrue(timelineAssigned[3].isCompleted)
        assertTrue(timelineAssigned[3].isCurrent)
        // Stage 5 & 6 pending
        assertFalse(timelineAssigned[4].isCompleted)
        assertFalse(timelineAssigned[5].isCompleted)

        // Test CLOSED state
        val timelineClosed = ReportStatusMapper.buildTimeline("CLOSED", "2026-09-12T10:00:00Z", "2026-09-12T16:00:00Z")
        assertEquals(6, timelineClosed.size)
        assertEquals(ReportStatus.CLOSED, timelineClosed[5].status)
        assertTrue(timelineClosed[5].isCompleted)
        assertTrue(timelineClosed[5].isCurrent)
    }

    @Test
    fun parseReport_parsesFullBackendReportReadJson() {
        val json = JSONObject().apply {
            put("id", "123e4567-e89b-12d3-a456-426614174000")
            put("tracking_id", "REP-202609-XYZ123")
            put("status", "IN_PROGRESS")
            put("category", "Road Damage")
            put("citizen_id", "czn_test_123")
            put("description", "Large dangerous pothole in middle of NH 66")
            put("latitude", 8.5615)
            put("longitude", 76.8850)
            put("address_hint", "Near Kariavattom")
            put("citizen_postal_code", "695581")
            put("created_at", "2026-09-12T09:30:00Z")
            put("updated_at", "2026-09-12T11:00:00Z")
            put("priority", "HIGH")
            put("evidences", JSONArray().apply {
                put(JSONObject().apply {
                    put("evidence_type", "IMAGE")
                    put("storage_uri", "/uploads/rep_test_img.jpg")
                })
            })
        }

        val report = ReportStatusMapper.parseReport(json, "http://192.168.1.75:8000")

        assertEquals("REP-202609-XYZ123", report.id)
        assertEquals(ReportStatus.IN_PROGRESS, report.status)
        assertEquals("IN_PROGRESS", report.serverStatus)
        assertEquals(ReportCategory.ROAD_DAMAGE, report.category)
        assertEquals(SeverityLevel.HIGH, report.severity)
        assertEquals("Near Kariavattom", report.address)
        assertEquals("695581", report.postalPin)
        assertEquals(8.5615, report.latitude!!, 0.0001)
        assertEquals(76.8850, report.longitude!!, 0.0001)
        assertEquals("http://192.168.1.75:8000/uploads/rep_test_img.jpg", report.imageUri)
        assertEquals(6, report.timeline.size)
        assertTrue(report.timeline[4].isCurrent) // In progress is stage index 4
    }

    @Test
    fun parseReport_parsesDepartmentAndReassignmentRequired() {
        val json = JSONObject().apply {
            put("id", "rep-dept-123")
            put("tracking_id", "REP-DEPT-001")
            put("status", "ASSIGNED")
            put("category", "Water Leakage")
            put("description", "Broken water pipe flooding the street")
            put("department", "Water Supply & Sewerage")
            put("reassignment_required", false)
            put("created_at", "2026-09-12T10:00:00Z")
        }

        val report = ReportStatusMapper.parseReport(json, "http://localhost:8000")
        assertEquals("Water Supply & Sewerage", report.assignedDepartment)
        assertFalse(report.reassignmentRequired)
        assertTrue(report.timeline[3].description.contains("Water Supply & Sewerage"))
    }

    @Test
    fun buildTimeline_handlesReassignmentRequiredGracefully() {
        val timeline = ReportStatusMapper.buildTimeline(
            serverStatus = "PRIORITIZED",
            createdAt = "2026-09-12T10:00:00Z",
            updatedAt = "2026-09-12T11:00:00Z",
            assignedDepartment = "Roads & Bridges",
            reassignmentRequired = true
        )

        assertEquals(6, timeline.size)
        assertTrue(timeline[2].description.contains("reassigning"))
    }

    @Test
    fun formatDate_handlesBothUtcAndNaiveTimestamps() {
        val withZ = ReportStatusMapper.formatDate("2026-09-12T10:07:04.321792Z")
        assertNotNull(withZ)
        assertTrue(withZ.contains("12 Sep") || withZ.contains("Sep 12") || withZ.contains("2026"))

        val naiveUtc = ReportStatusMapper.formatDate("2026-09-12T10:07:04.321792")
        assertNotNull(naiveUtc)
        assertTrue(naiveUtc.contains("12 Sep") || naiveUtc.contains("Sep 12") || naiveUtc.contains("2026"))

        assertEquals("Recently", ReportStatusMapper.formatDate(null))
        assertEquals("Recently", ReportStatusMapper.formatDate(""))
    }
}
