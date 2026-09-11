package com.civicsense.core.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

data class CivicCustomColors(
    val success: Color,
    val onSuccess: Color,
    val successContainer: Color,
    val onSuccessContainer: Color,
    val warning: Color,
    val onWarning: Color,
    val warningContainer: Color,
    val onWarningContainer: Color,
    val critical: Color,
    val onCritical: Color,
    val criticalContainer: Color,
    val onCriticalContainer: Color
)

val LocalCivicColors = staticCompositionLocalOf {
    CivicCustomColors(
        success = CivicSuccess,
        onSuccess = Color.White,
        successContainer = CivicSuccessContainer,
        onSuccessContainer = OnCivicSuccessContainer,
        warning = CivicWarning,
        onWarning = Color.White,
        warningContainer = CivicWarningContainer,
        onWarningContainer = OnCivicWarningContainer,
        critical = CivicCritical,
        onCritical = Color.White,
        criticalContainer = CivicCriticalContainer,
        onCriticalContainer = OnCivicCriticalContainer
    )
}

private val LightColorScheme = lightColorScheme(
    primary = CivicGreen,
    onPrimary = Color.White,
    primaryContainer = CivicGreenContainer,
    onPrimaryContainer = OnCivicGreenContainer,
    secondary = CivicGreenDark,
    onSecondary = Color.White,
    secondaryContainer = CivicSurfaceVariant,
    onSecondaryContainer = CivicTextPrimary,
    tertiary = CivicInfo,
    onTertiary = Color.White,
    tertiaryContainer = CivicInfoContainer,
    onTertiaryContainer = OnCivicInfoContainer,
    background = CivicBackground,
    onBackground = CivicTextPrimary,
    surface = CivicSurface,
    onSurface = CivicTextPrimary,
    surfaceVariant = CivicSurfaceVariant,
    onSurfaceVariant = CivicTextSecondary,
    outline = CivicOutline,
    outlineVariant = CivicOutlineVariant,
    error = CivicCritical,
    onError = Color.White,
    errorContainer = CivicCriticalContainer,
    onErrorContainer = OnCivicCriticalContainer
)

private val DarkColorScheme = darkColorScheme(
    primary = CivicGreenDarkTheme,
    onPrimary = CivicGreenContainerDark,
    primaryContainer = CivicGreenContainerDark,
    onPrimaryContainer = CivicTextPrimaryDark,
    secondary = CivicGreenLight,
    onSecondary = CivicGreenDark,
    secondaryContainer = CivicSurfaceVariantDark,
    onSecondaryContainer = CivicTextPrimaryDark,
    background = CivicBackgroundDark,
    onBackground = CivicTextPrimaryDark,
    surface = CivicSurfaceDark,
    onSurface = CivicTextPrimaryDark,
    surfaceVariant = CivicSurfaceVariantDark,
    onSurfaceVariant = CivicTextSecondaryDark,
    outline = CivicOutlineDark,
    outlineVariant = CivicOutlineDark,
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6)
)

@Composable
fun CivicSenseTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme
    val civicColors = CivicCustomColors(
        success = CivicSuccess,
        onSuccess = Color.White,
        successContainer = CivicSuccessContainer,
        onSuccessContainer = OnCivicSuccessContainer,
        warning = CivicWarning,
        onWarning = Color.White,
        warningContainer = CivicWarningContainer,
        onWarningContainer = OnCivicWarningContainer,
        critical = CivicCritical,
        onCritical = Color.White,
        criticalContainer = CivicCriticalContainer,
        onCriticalContainer = OnCivicCriticalContainer
    )

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as? Activity)?.window
            if (window != null) {
                WindowCompat.getInsetsController(window, view).apply {
                    isAppearanceLightStatusBars = !darkTheme
                    isAppearanceLightNavigationBars = !darkTheme
                }
            }
        }
    }

    CompositionLocalProvider(LocalCivicColors provides civicColors) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = Typography,
            shapes = Shapes,
            content = content
        )
    }
}

val MaterialTheme.civicColors: CivicCustomColors
    @Composable
    get() = LocalCivicColors.current
