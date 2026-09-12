package com.civicsense

import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import com.civicsense.core.navigation.CivicSenseNavHost
import com.civicsense.core.theme.CivicSenseTheme
import com.civicsense.data.model.AppTheme
import com.civicsense.data.repository.PreferenceRepository
import com.civicsense.data.repository.ReportRepository

class MainActivity : ComponentActivity() {

    private lateinit var preferenceRepository: PreferenceRepository
    private lateinit var reportRepository: ReportRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        configureDisplayRefreshRate()

        preferenceRepository = PreferenceRepository(applicationContext)
        reportRepository = ReportRepository.getInstance()
        reportRepository.setDataSource(
            com.civicsense.data.remote.RemoteReportsDataSource(
                preferenceRepository = preferenceRepository
            )
        )

        Log.i("CivicSenseSubmit", "APP_STARTUP resolved_api_base_url=${BuildConfig.API_BASE_URL}")

        setContent {
            val appTheme by preferenceRepository.appThemeFlow.collectAsState(initial = AppTheme.SYSTEM)
            val isDark = when (appTheme) {
                AppTheme.SYSTEM -> isSystemInDarkTheme()
                AppTheme.LIGHT -> false
                AppTheme.DARK -> true
            }

            CivicSenseTheme(darkTheme = isDark) {
                CivicSenseNavHost(
                    preferenceRepository = preferenceRepository,
                    reportRepository = reportRepository
                )
            }
        }
    }

    private fun configureDisplayRefreshRate() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val currentDisplay = display
                if (currentDisplay != null) {
                    val currentMode = currentDisplay.mode
                    val supportedModes = currentDisplay.supportedModes ?: emptyArray()

                    if (BuildConfig.DEBUG) {
                        Log.d(
                            TAG_DISPLAY,
                            "API level: ${Build.VERSION.SDK_INT}. Current mode: id=${currentMode.modeId}, ${currentMode.physicalWidth}x${currentMode.physicalHeight}@${currentMode.refreshRate}Hz"
                        )
                        supportedModes.forEach { mode ->
                            Log.d(
                                TAG_DISPLAY,
                                "Supported mode: id=${mode.modeId}, ${mode.physicalWidth}x${mode.physicalHeight}@${mode.refreshRate}Hz"
                            )
                        }
                    }

                    // Find mode with matching physical resolution and highest refresh rate
                    val highestRefreshMode = supportedModes
                        .filter { it.physicalWidth == currentMode.physicalWidth && it.physicalHeight == currentMode.physicalHeight }
                        .maxByOrNull { it.refreshRate }

                    if (highestRefreshMode != null) {
                        window.attributes = window.attributes.apply {
                            preferredDisplayModeId = highestRefreshMode.modeId
                            preferredRefreshRate = highestRefreshMode.refreshRate
                        }
                        if (BuildConfig.DEBUG) {
                            Log.d(
                                TAG_DISPLAY,
                                "Configured preferredDisplayModeId=${highestRefreshMode.modeId}, preferredRefreshRate=${highestRefreshMode.refreshRate}Hz"
                            )
                        }
                    }
                }
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                @Suppress("DEPRECATION")
                val defaultDisplay = windowManager.defaultDisplay
                val currentMode = defaultDisplay?.mode
                val supportedModes = defaultDisplay?.supportedModes ?: emptyArray()
                val highestRefreshMode = supportedModes
                    .filter { it.physicalWidth == currentMode?.physicalWidth && it.physicalHeight == currentMode?.physicalHeight }
                    .maxByOrNull { it.refreshRate }

                if (highestRefreshMode != null) {
                    window.attributes = window.attributes.apply {
                        preferredDisplayModeId = highestRefreshMode.modeId
                        preferredRefreshRate = highestRefreshMode.refreshRate
                    }
                }
            }
        } catch (e: Exception) {
            Log.w(TAG_DISPLAY, "Failed to configure display refresh rate: ${e.message}")
        }
    }

    companion object {
        private const val TAG_DISPLAY = "CivicSenseDisplay"
    }
}
