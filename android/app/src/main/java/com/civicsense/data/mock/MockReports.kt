package com.civicsense.data.mock

import com.civicsense.R
import com.civicsense.data.model.Report
import com.civicsense.data.model.ReportCategory
import com.civicsense.data.model.ReportStatus
import com.civicsense.data.model.SeverityLevel
import com.civicsense.data.model.TimelineStage

object MockReports {

    fun getInitialSeedReports(): List<Report> {
        return listOf(
            Report(
                id = "CS-2026-00101",
                title = "Pothole near the bus stop",
                description = "Large, hazardous pothole approximately 15 cm deep located right in the bus bay lane. Causes two-wheelers to swerve abruptly into oncoming traffic.",
                category = ReportCategory.ROAD_DAMAGE,
                status = ReportStatus.UNDER_REVIEW,
                severity = SeverityLevel.HIGH,
                dateTime = "10 Sep 2026, 09:30 AM",
                address = "Near Kariavattom Bus Terminal, NH 66, Thiruvananthapuram",
                postalPin = "695581",
                latitude = 8.5615,
                longitude = 76.8850,
                mockImageDrawableRes = R.drawable.img_pothole_sample,
                isImageProcessingComplete = true,
                timeline = listOf(
                    TimelineStage(ReportStatus.SUBMITTED, "10 Sep 2026, 09:30 AM", "Report received and evidence cryptographically recorded.", isCompleted = true, isCurrent = false),
                    TimelineStage(ReportStatus.UNDER_REVIEW, "10 Sep 2026, 10:15 AM", "Triage team is verifying the issue location and severity.", isCompleted = true, isCurrent = true),
                    TimelineStage(ReportStatus.CONFIRMED, null, "Verification by municipal ward engineer.", isCompleted = false, isCurrent = false),
                    TimelineStage(ReportStatus.ASSIGNED, null, "Work order issued to PWD road maintenance crew.", isCompleted = false, isCurrent = false),
                    TimelineStage(ReportStatus.IN_PROGRESS, null, "Repair and surface patching.", isCompleted = false, isCurrent = false),
                    TimelineStage(ReportStatus.RESOLVED, null, "Final inspection and defect closure.", isCompleted = false, isCurrent = false)
                )
            ),
            Report(
                id = "CS-2026-00084",
                title = "Garbage accumulation near the market",
                description = "Overflowing community trash dump near vegetable vendor area. Attracting stray animals and obstructing pedestrian pathway for the past three days.",
                category = ReportCategory.GARBAGE,
                status = ReportStatus.SUBMITTED,
                severity = SeverityLevel.MEDIUM,
                dateTime = "08 Sep 2026, 04:15 PM",
                address = "Market Junction, Kazhakkoottam, Thiruvananthapuram",
                postalPin = "695582",
                latitude = 8.5694,
                longitude = 76.8711,
                mockImageDrawableRes = R.drawable.img_garbage_sample,
                isImageProcessingComplete = true,
                timeline = listOf(
                    TimelineStage(ReportStatus.SUBMITTED, "08 Sep 2026, 04:15 PM", "Report submitted and queued for sanitation review.", isCompleted = true, isCurrent = true),
                    TimelineStage(ReportStatus.UNDER_REVIEW, null, "Sanitation supervisor routing to area compactor team.", isCompleted = false, isCurrent = false),
                    TimelineStage(ReportStatus.CONFIRMED, null, "Locality verification confirmed.", isCompleted = false, isCurrent = false),
                    TimelineStage(ReportStatus.ASSIGNED, null, "Assigned to Ward 12 Sanitation Team.", isCompleted = false, isCurrent = false),
                    TimelineStage(ReportStatus.IN_PROGRESS, null, "Waste collection and bin sanitization in progress.", isCompleted = false, isCurrent = false),
                    TimelineStage(ReportStatus.RESOLVED, null, "Area cleared and photo audit approved.", isCompleted = false, isCurrent = false)
                )
            ),
            Report(
                id = "CS-2026-00062",
                title = "Water leakage near residential road",
                description = "Continuous fresh water gushing from underground pipeline joint along the edge of the sub-road. Ground has softened and water is pooling near gates.",
                category = ReportCategory.WATER_LEAKAGE,
                status = ReportStatus.RESOLVED,
                severity = SeverityLevel.MEDIUM,
                dateTime = "02 Sep 2026, 11:00 AM",
                address = "Near Sreekaryam Junction, Lane 4, Thiruvananthapuram",
                postalPin = "695017",
                latitude = 8.5442,
                longitude = 76.9189,
                mockImageDrawableRes = R.drawable.img_water_sample,
                isImageProcessingComplete = true,
                timeline = listOf(
                    TimelineStage(ReportStatus.SUBMITTED, "02 Sep 2026, 11:00 AM", "Report logged with water authority.", isCompleted = true, isCurrent = false),
                    TimelineStage(ReportStatus.UNDER_REVIEW, "02 Sep 2026, 11:45 AM", "Water supply board engineer prioritized leak.", isCompleted = true, isCurrent = false),
                    TimelineStage(ReportStatus.CONFIRMED, "02 Sep 2026, 01:00 PM", "Main transmission line valve leak confirmed.", isCompleted = true, isCurrent = false),
                    TimelineStage(ReportStatus.ASSIGNED, "02 Sep 2026, 02:30 PM", "Plumbing maintenance emergency squad assigned.", isCompleted = true, isCurrent = false),
                    TimelineStage(ReportStatus.IN_PROGRESS, "03 Sep 2026, 09:00 AM", "Pipe joint replaced and pressure tested.", isCompleted = true, isCurrent = false),
                    TimelineStage(ReportStatus.RESOLVED, "04 Sep 2026, 03:30 PM", "Pipe repaired, road reinstated, issue resolved.", isCompleted = true, isCurrent = true)
                )
            ),
            Report(
                id = "CS-2026-00073",
                title = "Broken streetlight and damaged footpath",
                description = "High mast light fixture cracked and unlit for over a week, alongside broken pedestrian pavers that pose tripping risks at night.",
                category = ReportCategory.INFRASTRUCTURE,
                status = ReportStatus.IN_PROGRESS,
                severity = SeverityLevel.MEDIUM,
                dateTime = "05 Sep 2026, 08:20 PM",
                address = "Main Avenue, Near Technopark Phase 1 Gate, Thiruvananthapuram",
                postalPin = "695581",
                latitude = 8.5583,
                longitude = 76.8814,
                mockImageDrawableRes = R.drawable.img_infrastructure_sample,
                isImageProcessingComplete = true,
                timeline = listOf(
                    TimelineStage(ReportStatus.SUBMITTED, "05 Sep 2026, 08:20 PM", "Report submitted.", isCompleted = true, isCurrent = false),
                    TimelineStage(ReportStatus.UNDER_REVIEW, "06 Sep 2026, 09:00 AM", "Electrical & civic works department assessed issue.", isCompleted = true, isCurrent = false),
                    TimelineStage(ReportStatus.CONFIRMED, "06 Sep 2026, 11:30 AM", "Safety hazard verified.", isCompleted = true, isCurrent = false),
                    TimelineStage(ReportStatus.ASSIGNED, "07 Sep 2026, 10:00 AM", "Work order issued to streetlight division.", isCompleted = true, isCurrent = false),
                    TimelineStage(ReportStatus.IN_PROGRESS, "08 Sep 2026, 02:00 PM", "Replacement LED luminaire ordered and fixture under repair.", isCompleted = true, isCurrent = true),
                    TimelineStage(ReportStatus.RESOLVED, null, "Final illumination check.", isCompleted = false, isCurrent = false)
                )
            ),
            Report(
                id = "CS-2026-00095",
                title = "Deep asphalt depression on junction road",
                description = "Substantial depression following monsoon run-off near the turn-off, causing traffic slowdowns and low-clearance vehicle scraping.",
                category = ReportCategory.ROAD_DAMAGE,
                status = ReportStatus.CONFIRMED,
                severity = SeverityLevel.HIGH,
                dateTime = "09 Sep 2026, 02:45 PM",
                address = "Pangappara Junction, NH 66, Thiruvananthapuram",
                postalPin = "695581",
                latitude = 8.5501,
                longitude = 76.8972,
                mockImageDrawableRes = R.drawable.img_pothole_sample,
                isImageProcessingComplete = true,
                timeline = listOf(
                    TimelineStage(ReportStatus.SUBMITTED, "09 Sep 2026, 02:45 PM", "Report submitted.", isCompleted = true, isCurrent = false),
                    TimelineStage(ReportStatus.UNDER_REVIEW, "09 Sep 2026, 03:30 PM", "Classified as structural surface failure.", isCompleted = true, isCurrent = false),
                    TimelineStage(ReportStatus.CONFIRMED, "10 Sep 2026, 11:00 AM", "Confirmed by Ward Inspection Officer.", isCompleted = true, isCurrent = true),
                    TimelineStage(ReportStatus.ASSIGNED, null, "Queued for asphalt re-laying.", isCompleted = false, isCurrent = false),
                    TimelineStage(ReportStatus.IN_PROGRESS, null, "Hot-mix asphalt application.", isCompleted = false, isCurrent = false),
                    TimelineStage(ReportStatus.RESOLVED, null, "Surface quality certification.", isCompleted = false, isCurrent = false)
                )
            )
        )
    }
}
