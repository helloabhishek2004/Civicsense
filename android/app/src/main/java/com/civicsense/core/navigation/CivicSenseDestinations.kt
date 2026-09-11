package com.civicsense.core.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Assignment
import androidx.compose.material.icons.automirrored.outlined.Assignment
import androidx.compose.material.icons.filled.AddCircle
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.outlined.AddCircleOutline
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Person
import androidx.compose.ui.graphics.vector.ImageVector

sealed class BottomDestination(
    val route: String,
    val label: String,
    val selectedIcon: ImageVector,
    val unselectedIcon: ImageVector
) {
    data object Home : BottomDestination(
        route = "home",
        label = "Home",
        selectedIcon = Icons.Filled.Home,
        unselectedIcon = Icons.Outlined.Home
    )

    data object MyReports : BottomDestination(
        route = "my_reports",
        label = "My Reports",
        selectedIcon = Icons.AutoMirrored.Filled.Assignment,
        unselectedIcon = Icons.AutoMirrored.Outlined.Assignment
    )

    data object Report : BottomDestination(
        route = "report_wizard",
        label = "Report",
        selectedIcon = Icons.Filled.AddCircle,
        unselectedIcon = Icons.Outlined.AddCircleOutline
    )

    data object Profile : BottomDestination(
        route = "profile",
        label = "Profile",
        selectedIcon = Icons.Filled.Person,
        unselectedIcon = Icons.Outlined.Person
    )

    companion object {
        val items: List<BottomDestination>
            get() = listOf(Home, MyReports, Report, Profile)
    }
}

object AppDestinations {
    const val SPLASH = "splash"
    const val ONBOARDING = "onboarding"
    const val PROFILE_SETUP = "profile_setup"
    const val MAIN = "main"

    // Report wizard sub-routes
    const val REPORT_INTRO = "report_intro"
    const val REPORT_IMAGE = "report_image"
    const val REPORT_DESCRIPTION = "report_description"
    const val REPORT_LOCATION = "report_location"
    const val REPORT_REVIEW = "report_review"
    const val REPORT_SUBMISSION = "report_submission"
    const val REPORT_SUCCESS = "report_success/{reportId}"

    fun reportSuccessRoute(reportId: String): String = "report_success/$reportId"

    // Detail route
    const val REPORT_DETAIL = "report_detail/{reportId}"
    fun reportDetailRoute(reportId: String): String = "report_detail/$reportId"
}
