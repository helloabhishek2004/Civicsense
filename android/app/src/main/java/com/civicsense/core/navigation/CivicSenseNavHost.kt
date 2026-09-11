package com.civicsense.core.navigation

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.civicsense.data.model.AppTheme
import com.civicsense.data.model.UserProfile
import com.civicsense.data.repository.PreferenceRepository
import com.civicsense.data.repository.ReportRepository
import com.civicsense.feature.home.HomeScreen
import com.civicsense.feature.onboarding.OnboardingScreen
import com.civicsense.feature.profile.ProfileScreen
import com.civicsense.feature.profile.ProfileSetupScreen
import com.civicsense.feature.report.ReportViewModel
import com.civicsense.feature.report.ReportWizardScreen
import com.civicsense.feature.reports.MyReportsScreen
import com.civicsense.feature.reports.ReportDetailScreen
import com.civicsense.feature.splash.SplashScreen
import kotlinx.coroutines.launch

@Composable
fun CivicSenseNavHost(
    preferenceRepository: PreferenceRepository,
    reportRepository: ReportRepository = ReportRepository.getInstance(),
    navController: NavHostController = rememberNavController(),
    modifier: Modifier = Modifier
) {
    val userProfile by preferenceRepository.userProfileFlow.collectAsState(initial = null)
    val appTheme by preferenceRepository.appThemeFlow.collectAsState(initial = AppTheme.SYSTEM)
    val reports by reportRepository.reports.collectAsState()
    val scope = rememberCoroutineScope()

    val reportViewModel: ReportViewModel = viewModel {
        ReportViewModel(reportRepository)
    }

    NavHost(
        navController = navController,
        startDestination = AppDestinations.SPLASH,
        modifier = modifier.fillMaxSize()
    ) {
        composable(AppDestinations.SPLASH) {
            SplashScreen(
                userProfile = userProfile,
                onNavigateToOnboarding = {
                    navController.navigate(AppDestinations.ONBOARDING) {
                        popUpTo(AppDestinations.SPLASH) { inclusive = true }
                    }
                },
                onNavigateToProfileSetup = {
                    navController.navigate(AppDestinations.PROFILE_SETUP) {
                        popUpTo(AppDestinations.SPLASH) { inclusive = true }
                    }
                },
                onNavigateToHome = {
                    navController.navigate(AppDestinations.MAIN) {
                        popUpTo(AppDestinations.SPLASH) { inclusive = true }
                    }
                }
            )
        }

        composable(AppDestinations.ONBOARDING) {
            OnboardingScreen(
                onFinished = {
                    scope.launch {
                        preferenceRepository.setOnboardingCompleted(true)
                    }
                    navController.navigate(AppDestinations.PROFILE_SETUP) {
                        popUpTo(AppDestinations.ONBOARDING) { inclusive = true }
                    }
                }
            )
        }

        composable(AppDestinations.PROFILE_SETUP) {
            ProfileSetupScreen(
                preferenceRepository = preferenceRepository,
                onProfileCompleted = {
                    navController.navigate(AppDestinations.MAIN) {
                        popUpTo(AppDestinations.PROFILE_SETUP) { inclusive = true }
                    }
                }
            )
        }

        composable(AppDestinations.MAIN) {
            var selectedTab by rememberSaveable { mutableStateOf(BottomDestination.Home.route) }

            // Root tabs back behavior: return to Home first before exiting
            BackHandler(enabled = selectedTab != BottomDestination.Home.route) {
                selectedTab = BottomDestination.Home.route
            }

            Scaffold(
                bottomBar = {
                    CivicSenseBottomBar(
                        currentRoute = selectedTab,
                        onNavigateToDestination = { destination ->
                            selectedTab = destination.route
                        }
                    )
                }
            ) { innerPadding ->
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(innerPadding)
                ) {
                    AnimatedContent(
                        targetState = selectedTab,
                        transitionSpec = { fadeIn() togetherWith fadeOut() },
                        label = "main_tabs"
                    ) { currentRoute ->
                        when (currentRoute) {
                            BottomDestination.Home.route -> {
                                HomeScreen(
                                    userProfile = userProfile ?: UserProfile(),
                                    reports = reports,
                                    onReportIssueClick = {
                                        selectedTab = BottomDestination.Report.route
                                    },
                                    onSeeAllReportsClick = {
                                        selectedTab = BottomDestination.MyReports.route
                                    },
                                    onReportClick = { reportId ->
                                        navController.navigate(AppDestinations.reportDetailRoute(reportId))
                                    },
                                    onRefresh = {
                                        reportRepository.refreshReports()
                                    }
                                )
                            }
                            BottomDestination.MyReports.route -> {
                                MyReportsScreen(
                                    reports = reports,
                                    onReportClick = { reportId ->
                                        navController.navigate(AppDestinations.reportDetailRoute(reportId))
                                    },
                                    onStartReport = {
                                        selectedTab = BottomDestination.Report.route
                                    },
                                    onRefresh = {
                                        reportRepository.refreshReports()
                                    }
                                )
                            }
                            BottomDestination.Report.route -> {
                                ReportWizardScreen(
                                    viewModel = reportViewModel,
                                    onFinishWizard = {
                                        selectedTab = BottomDestination.Home.route
                                    },
                                    onViewCreatedReport = { reportId ->
                                        selectedTab = BottomDestination.Home.route
                                        navController.navigate(AppDestinations.reportDetailRoute(reportId))
                                    }
                                )
                            }
                            BottomDestination.Profile.route -> {
                                ProfileScreen(
                                    userProfile = userProfile ?: UserProfile(),
                                    currentTheme = appTheme,
                                    onThemeChanged = { newTheme ->
                                        scope.launch {
                                            preferenceRepository.setAppTheme(newTheme)
                                        }
                                    },
                                    onViewOnboardingAgain = {
                                        navController.navigate(AppDestinations.ONBOARDING)
                                    },
                                    onResetDemoData = {
                                        scope.launch {
                                            preferenceRepository.resetAll()
                                            reportRepository.resetDemoData()
                                            reportViewModel.resetWizard()
                                            navController.navigate(AppDestinations.SPLASH) {
                                                popUpTo(AppDestinations.MAIN) { inclusive = true }
                                            }
                                        }
                                    },
                                    onEditProfile = {
                                        navController.navigate(AppDestinations.PROFILE_SETUP)
                                    }
                                )
                            }
                        }
                    }
                }
            }
        }

        composable(
            route = AppDestinations.REPORT_DETAIL,
            arguments = listOf(navArgument("reportId") { type = NavType.StringType })
        ) { backStackEntry ->
            val reportId = backStackEntry.arguments?.getString("reportId") ?: ""
            val report = reports.find { it.id == reportId }
            ReportDetailScreen(
                report = report,
                onNavigateBack = { navController.popBackStack() }
            )
        }
    }
}
