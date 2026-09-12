package com.civicsense.data.remote

import com.civicsense.data.model.Report
import com.civicsense.data.model.ReportCategory
import com.civicsense.data.model.ReportStatus
import com.civicsense.data.model.SeverityLevel
import com.civicsense.data.model.TimelineStage
import org.json.JSONObject
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Pure, deterministic mapper that translates backend JSON reports and canonical
 * 11 server lifecycle states to Android citizen domain models.
 */
object ReportStatusMapper {

    private val DISPLAY_DATE_FORMATTER = DateTimeFormatter.ofPattern("dd MMM yyyy, hh:mm a", Locale.getDefault())

    /**
     * Maps the 11 backend server lifecycle states to citizen-facing ReportStatus.
     */
    fun mapServerStatus(serverStatus: String?): ReportStatus {
        if (serverStatus.isNullOrBlank()) return ReportStatus.SUBMITTED
        return when (serverStatus.uppercase(Locale.ROOT)) {
            "SUBMITTED" -> ReportStatus.SUBMITTED
            "AI_PROCESSING", "AI_PROCESSED", "VERIFICATION_REQUIRED" -> ReportStatus.UNDER_REVIEW
            "VERIFIED", "PRIORITIZED" -> ReportStatus.CONFIRMED
            "ASSIGNED" -> ReportStatus.ASSIGNED
            "IN_PROGRESS" -> ReportStatus.IN_PROGRESS
            "RESOLVED", "RESOLUTION_VERIFIED" -> ReportStatus.RESOLVED
            "CLOSED" -> ReportStatus.CLOSED
            "QUEUED_OFFLINE" -> ReportStatus.QUEUED_OFFLINE
            else -> ReportStatus.SUBMITTED
        }
    }

    /**
     * Maps operational priority or AI severity strings to citizen-facing SeverityLevel.
     */
    fun mapSeverity(priority: String?, aiSeverity: String?): SeverityLevel {
        val raw = (priority?.ifBlank { null } ?: aiSeverity?.ifBlank { null })?.uppercase(Locale.ROOT)
        return when (raw) {
            "CRITICAL" -> SeverityLevel.CRITICAL
            "HIGH" -> SeverityLevel.HIGH
            "MEDIUM" -> SeverityLevel.MEDIUM
            "LOW" -> SeverityLevel.LOW
            else -> SeverityLevel.MEDIUM
        }
    }

    /**
     * Maps server or edge category string to ReportCategory.
     */
    fun mapCategory(rawCategory: String?): ReportCategory {
        if (rawCategory.isNullOrBlank()) return ReportCategory.OTHER
        val normalized = rawCategory.trim().replace("_", " ").uppercase(Locale.ROOT)
        return when {
            normalized.contains("ROAD") || normalized.contains("POTHOLE") -> ReportCategory.ROAD_DAMAGE
            normalized.contains("GARBAGE") || normalized.contains("WASTE") -> ReportCategory.GARBAGE
            normalized.contains("WATER") || normalized.contains("LEAK") || normalized.contains("PIPE") -> ReportCategory.WATER_LEAKAGE
            normalized.contains("INFRASTRUCTURE") -> ReportCategory.INFRASTRUCTURE
            normalized.contains("NOT SURE") -> ReportCategory.NOT_SURE
            else -> ReportCategory.OTHER
        }
    }

    /**
     * Formats an ISO-8601 string to a human-readable display string.
     */
    fun formatDate(isoString: String?): String {
        if (isoString.isNullOrBlank()) return "Recently"
        return try {
            val offsetDateTime = try {
                OffsetDateTime.parse(isoString)
            } catch (_: Exception) {
                val normalized = if (!isoString.endsWith("Z", ignoreCase = true) &&
                    !isoString.contains("+") &&
                    !Regex("-\\d{2}:?\\d{2}$").containsMatchIn(isoString)) {
                    "${isoString}Z"
                } else {
                    isoString
                }
                val instant = try {
                    Instant.parse(normalized)
                } catch (_: Exception) {
                    Instant.parse(isoString)
                }
                instant.atZone(ZoneId.systemDefault()).toOffsetDateTime()
            }
            offsetDateTime.atZoneSameInstant(ZoneId.systemDefault()).format(DISPLAY_DATE_FORMATTER)
        } catch (_: Exception) {
            isoString
        }
    }

    /**
     * Derives a concise, clean report title from description and category.
     */
    fun deriveTitle(description: String, category: ReportCategory, addressHint: String?): String {
        val firstLine = description.lines().firstOrNull { it.isNotBlank() }?.trim() ?: ""
        if (firstLine.isNotEmpty() && firstLine.length <= 50) {
            return firstLine
        }
        if (firstLine.length > 50) {
            return firstLine.take(47) + "…"
        }
        val loc = addressHint?.ifBlank { null }
        return if (loc != null) {
            "${category.shortName} near $loc"
        } else {
            "${category.shortName} report"
        }
    }

    /**
     * Builds the 6-stage resolution timeline reflecting the current server state.
     */
    fun buildTimeline(
        serverStatus: String,
        createdAt: String,
        updatedAt: String? = null,
        assignedDepartment: String? = null,
        reassignmentRequired: Boolean = false
    ): List<TimelineStage> {
        val rank = when (serverStatus.uppercase(Locale.ROOT)) {
            "SUBMITTED" -> 1
            "AI_PROCESSING", "AI_PROCESSED", "VERIFICATION_REQUIRED" -> 2
            "VERIFIED", "PRIORITIZED" -> 3
            "ASSIGNED" -> 4
            "IN_PROGRESS" -> 5
            "RESOLVED", "RESOLUTION_VERIFIED" -> 6
            "CLOSED" -> 6
            else -> 1
        }

        val formattedCreated = formatDate(createdAt)
        val formattedUpdated = if (!updatedAt.isNullOrBlank()) formatDate(updatedAt) else formattedCreated
        val isClosed = serverStatus.equals("CLOSED", ignoreCase = true)

        val confirmedDesc = if (reassignmentRequired) {
            "Triage team is reassigning issue to the appropriate division."
        } else {
            "Verification confirmed by municipal engineer."
        }

        val assignedDesc = if (!assignedDepartment.isNullOrBlank()) {
            "Assigned to $assignedDepartment."
        } else {
            "Work order issued to municipal maintenance crew."
        }

        val stageConfigs = listOf(
            Triple(ReportStatus.SUBMITTED, "Report received and evidence cryptographically recorded.", formattedCreated),
            Triple(ReportStatus.UNDER_REVIEW, "Triage team is verifying the issue location and severity.", formattedUpdated),
            Triple(ReportStatus.CONFIRMED, confirmedDesc, formattedUpdated),
            Triple(ReportStatus.ASSIGNED, assignedDesc, formattedUpdated),
            Triple(ReportStatus.IN_PROGRESS, "On-site repair and defect remediation.", formattedUpdated),
            Triple(
                if (isClosed) ReportStatus.CLOSED else ReportStatus.RESOLVED,
                if (isClosed) "Issue resolved and officially closed." else "Final inspection and defect closure.",
                formattedUpdated
            )
        )

        return stageConfigs.mapIndexed { index, (status, desc, date) ->
            val stageRank = index + 1
            when {
                stageRank < rank -> TimelineStage(
                    status = status,
                    date = date,
                    description = desc,
                    isCompleted = true,
                    isCurrent = false
                )
                stageRank == rank -> TimelineStage(
                    status = status,
                    date = date,
                    description = desc,
                    isCompleted = true,
                    isCurrent = true
                )
                else -> TimelineStage(
                    status = status,
                    date = null,
                    description = desc,
                    isCompleted = false,
                    isCurrent = false
                )
            }
        }
    }

    /**
     * Parses a backend ReportRead JSON object into a domain Report.
     */
    fun parseReport(json: JSONObject, apiBaseUrl: String): Report {
        val trackingId = json.optString("tracking_id").ifBlank { json.optString("id") }
        val description = json.optString("description", "")
        val rawCategory = if (json.has("category") && !json.isNull("category")) json.optString("category") else null
        val category = mapCategory(rawCategory)
        val serverStatus = json.optString("status", "SUBMITTED")
        val status = mapServerStatus(serverStatus)

        val priority = if (json.has("priority") && !json.isNull("priority")) json.optString("priority") else null
        var aiSeverity: String? = null
        val aiArray = json.optJSONArray("ai_analyses")
        if (aiArray != null && aiArray.length() > 0) {
            val firstAi = aiArray.optJSONObject(0)
            if (firstAi != null && firstAi.has("severity")) {
                aiSeverity = firstAi.optString("severity")
            }
        }
        val severity = mapSeverity(priority, aiSeverity)

        val createdAt = json.optString("created_at", "")
        val updatedAt = json.optString("updated_at", "")
        val dateTime = formatDate(createdAt)

        val latitude = json.optDouble("latitude", Double.NaN).let { if (it.isNaN()) null else it }
        val longitude = json.optDouble("longitude", Double.NaN).let { if (it.isNaN()) null else it }
        val addressHint = if (json.has("address_hint") && !json.isNull("address_hint")) {
            json.optString("address_hint")
        } else {
            "Location unlisted"
        }
        val postalPin = if (json.has("citizen_postal_code") && !json.isNull("citizen_postal_code")) {
            json.optString("citizen_postal_code")
        } else {
            ""
        }

        // Evidence Image resolution
        var resolvedImageUri: String? = null
        val evidencesArray = json.optJSONArray("evidences")
        if (evidencesArray != null) {
            for (i in 0 until evidencesArray.length()) {
                val ev = evidencesArray.optJSONObject(i) ?: continue
                val evType = ev.optString("evidence_type", "IMAGE")
                val storageUri = ev.optString("storage_uri", "")
                if (evType.equals("IMAGE", ignoreCase = true) && storageUri.isNotBlank()) {
                    resolvedImageUri = if (storageUri.startsWith("http://") || storageUri.startsWith("https://")) {
                        storageUri
                    } else {
                        val base = apiBaseUrl.trimEnd('/')
                        val path = if (storageUri.startsWith("/")) storageUri else "/$storageUri"
                        "$base$path"
                    }
                    break
                }
            }
        }

        val assignedDepartment = if (json.has("department") && !json.isNull("department")) {
            json.optString("department").ifBlank { null }
        } else null
        val reassignmentRequired = json.optBoolean("reassignment_required", false)

        val title = deriveTitle(description, category, addressHint)
        val timeline = buildTimeline(serverStatus, createdAt, updatedAt, assignedDepartment, reassignmentRequired)

        return Report(
            id = trackingId,
            title = title,
            description = description,
            category = category,
            status = status,
            severity = severity,
            dateTime = dateTime,
            address = addressHint,
            postalPin = postalPin,
            latitude = latitude,
            longitude = longitude,
            imageUri = resolvedImageUri,
            mockImageDrawableRes = null,
            isImageProcessingComplete = true,
            timeline = timeline,
            serverStatus = serverStatus,
            assignedDepartment = assignedDepartment,
            reassignmentRequired = reassignmentRequired
        )
    }
}
