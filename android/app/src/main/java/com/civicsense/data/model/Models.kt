package com.civicsense.data.model

import com.civicsense.core.util.InputValidators

enum class AppTheme(val displayName: String, val storageKey: String) {
    SYSTEM("System default", "system"),
    LIGHT("Light", "light"),
    DARK("Dark", "dark");

    companion object {
        fun fromStoredValue(value: String?): AppTheme =
            entries.firstOrNull { it.storageKey.equals(value, ignoreCase = true) } ?: SYSTEM
    }
}

enum class LocationSource(val displayName: String) {
    NONE("Not set"),
    CURRENT_LOCATION("Device GPS / Network"),
    MAP_SELECTION("Selected on map"),
    MANUAL("Manually specified")
}

enum class LocationStatus {
    NONE,
    PERMISSION_REQUIRED,
    PERMISSION_DENIED,
    SERVICES_DISABLED,
    FETCHING,
    COORDINATES_FOUND,
    ADDRESS_RESOLVING,
    RESOLVED,
    FAILED,
    MANUAL
}

data class ReportLocation(
    val latitude: Double? = null,
    val longitude: Double? = null,
    val address: String? = null,
    val postalPin: String? = null,
    val source: LocationSource = LocationSource.NONE
) {
    val hasCoordinates: Boolean
        get() = latitude != null && longitude != null

    val displayAddress: String
        get() = address?.ifBlank { null } ?: if (hasCoordinates) {
            String.format(java.util.Locale.US, "Lat: %.4f, Long: %.4f", latitude, longitude)
        } else {
            "Location unlisted"
        }
}

enum class ReportCategory(val displayName: String, val shortName: String) {
    ROAD_DAMAGE("Road damage / pothole", "Road damage"),
    GARBAGE("Garbage accumulation / illegal dumping", "Waste & Garbage"),
    WATER_LEAKAGE("Water leakage / broken pipe", "Water leakage"),
    INFRASTRUCTURE("Damaged public infrastructure", "Infrastructure"),
    OTHER("Other civic issue", "Other"),
    NOT_SURE("Not sure / Need help identifying", "Not sure");

    val backendCategory: String
        get() = when (this) {
            ROAD_DAMAGE -> "Road Damage"
            GARBAGE -> "Garbage"
            WATER_LEAKAGE -> "Water Leakage"
            INFRASTRUCTURE -> "Infrastructure"
            OTHER -> "Other"
            NOT_SURE -> "Other"
        }
}

enum class ReportStatus(val displayName: String) {
    QUEUED_OFFLINE("Saved offline"),
    SUBMITTED("Submitted"),
    UNDER_REVIEW("Under review"),
    CONFIRMED("Confirmed"),
    ASSIGNED("Assigned"),
    IN_PROGRESS("In progress"),
    RESOLVED("Resolved"),
    CLOSED("Closed")
}

enum class SeverityLevel(val displayName: String) {
    LOW("Low"),
    MEDIUM("Medium"),
    HIGH("High"),
    CRITICAL("Critical")
}

enum class ImageQualityFeedback(val message: String, val isWarning: Boolean) {
    GOOD("The image looks good and sharp.", false),
    TOO_DARK("The image may be dark. Ensure adequate lighting.", true),
    BLURRY("The image may be blurry. Consider retaking it.", true)
}

enum class ImageProcessingStage(val label: String) {
    IDLE("Idle"),
    PREPARING("Preparing image…"),
    CHECKING_QUALITY("Checking image quality…"),
    ANALYZING("Verifying evidence…"),
    READY("Image ready")
}

data class ImageProcessingState(
    val stage: ImageProcessingStage = ImageProcessingStage.IDLE,
    val feedback: ImageQualityFeedback = ImageQualityFeedback.GOOD,
    val isComplete: Boolean = false
)

data class TimelineStage(
    val status: ReportStatus,
    val date: String?,
    val description: String,
    val isCompleted: Boolean,
    val isCurrent: Boolean
)

enum class OnboardingState {
    LOADING,
    NEEDS_BOARDING,
    NEEDS_PROFILE,
    READY
}

data class UserProfile(
    val fullName: String = "",
    val mobileNumber: String = "",
    val email: String = "",
    val locality: String = "",
    val postalPin: String = "",
    val isOnboardingCompleted: Boolean = false,
    val isProfileCompleted: Boolean = false
) {
    val isProfileValid: Boolean
        get() = InputValidators.isValidFullName(fullName) &&
                InputValidators.normalizeIndianMobile(mobileNumber).first
}

fun resolveOnboardingState(profile: UserProfile?): OnboardingState {
    if (profile == null) return OnboardingState.LOADING
    if (!profile.isOnboardingCompleted) return OnboardingState.NEEDS_BOARDING
    if (!profile.isProfileCompleted || !profile.isProfileValid) return OnboardingState.NEEDS_PROFILE
    return OnboardingState.READY
}

data class Report(
    val id: String,
    val title: String,
    val description: String,
    val category: ReportCategory,
    val status: ReportStatus,
    val severity: SeverityLevel,
    val dateTime: String,
    val address: String = "Location unlisted",
    val postalPin: String = "",
    val latitude: Double? = null,
    val longitude: Double? = null,
    val imageUri: String? = null,
    val mockImageDrawableRes: Int? = null,
    val isImageProcessingComplete: Boolean = true,
    val timeline: List<TimelineStage> = emptyList(),
    val serverStatus: String? = null,
    val assignedDepartment: String? = null,
    val reassignmentRequired: Boolean = false
)
