package com.civicsense.feature.splash

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.civicsense.R
import com.civicsense.data.model.OnboardingState
import com.civicsense.data.model.UserProfile
import com.civicsense.data.model.resolveOnboardingState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.delay

@Composable
fun SplashScreen(
    userProfile: UserProfile?,
    onNavigateToOnboarding: () -> Unit,
    onNavigateToProfileSetup: () -> Unit,
    onNavigateToHome: () -> Unit,
    modifier: Modifier = Modifier
) {
    val alphaAnim = remember { Animatable(0f) }
    var hasNavigated by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        alphaAnim.animateTo(
            targetValue = 1f,
            animationSpec = tween(durationMillis = 600)
        )
    }

    val onboardingState = remember(userProfile) {
        resolveOnboardingState(userProfile)
    }

    LaunchedEffect(onboardingState) {
        if (!hasNavigated && onboardingState != OnboardingState.LOADING) {
            delay(500) // Brief natural transition, no artificial 3-5s delay
            if (!hasNavigated) {
                hasNavigated = true
                when (onboardingState) {
                    OnboardingState.NEEDS_BOARDING -> onNavigateToOnboarding()
                    OnboardingState.NEEDS_PROFILE -> onNavigateToProfileSetup()
                    OnboardingState.READY -> onNavigateToHome()
                    OnboardingState.LOADING -> { /* maintain splash screen */ }
                }
            }
        }
    }

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier.alpha(alphaAnim.value)
        ) {
            Image(
                painter = painterResource(id = R.drawable.ic_civicsense_path_logo),
                contentDescription = "CivicSense Logo",
                modifier = Modifier.size(96.dp)
            )

            Spacer(modifier = Modifier.height(20.dp))

            Text(
                text = "CivicSense",
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Report. Verify. Improve.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
