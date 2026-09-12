package com.civicsense

import com.civicsense.data.model.OnboardingState
import com.civicsense.data.model.UserProfile
import com.civicsense.data.model.resolveOnboardingState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OnboardingStateTest {

    @Test
    fun nullProfile_resolvesToLoading() {
        val state = resolveOnboardingState(null)
        assertEquals(OnboardingState.LOADING, state)
    }

    @Test
    fun freshInstall_emptyProfile_resolvesToNeedsBoarding() {
        val profile = UserProfile()
        val state = resolveOnboardingState(profile)
        assertEquals(OnboardingState.NEEDS_BOARDING, state)
    }

    @Test
    fun onboardingNotCompleted_resolvesToNeedsBoarding() {
        val profile = UserProfile(
            fullName = "Abhishek S",
            mobileNumber = "9874563210",
            isOnboardingCompleted = false,
            isProfileCompleted = true
        )
        val state = resolveOnboardingState(profile)
        assertEquals(OnboardingState.NEEDS_BOARDING, state)
    }

    @Test
    fun onboardingCompleted_butProfileNotCompleted_resolvesToNeedsProfile() {
        val profile = UserProfile(
            fullName = "",
            mobileNumber = "",
            isOnboardingCompleted = true,
            isProfileCompleted = false
        )
        val state = resolveOnboardingState(profile)
        assertEquals(OnboardingState.NEEDS_PROFILE, state)
    }

    @Test
    fun onboardingCompleted_profileMarkedCompleted_butNameBlank_resolvesToNeedsProfile() {
        val profile = UserProfile(
            fullName = " ",
            mobileNumber = "9874563210",
            isOnboardingCompleted = true,
            isProfileCompleted = true
        )
        assertFalse(profile.isProfileValid)
        val state = resolveOnboardingState(profile)
        assertEquals(OnboardingState.NEEDS_PROFILE, state)
    }

    @Test
    fun onboardingCompleted_profileMarkedCompleted_butInvalidMobile_resolvesToNeedsProfile() {
        val profile = UserProfile(
            fullName = "Abhishek S",
            mobileNumber = "12345", // invalid mobile
            isOnboardingCompleted = true,
            isProfileCompleted = true
        )
        assertFalse(profile.isProfileValid)
        val state = resolveOnboardingState(profile)
        assertEquals(OnboardingState.NEEDS_PROFILE, state)
    }

    @Test
    fun returningUser_validProfile_resolvesToReady() {
        val profile = UserProfile(
            fullName = "Abhishek S",
            mobileNumber = "9874563210",
            email = "abhishek@example.com",
            postalPin = "695001",
            isOnboardingCompleted = true,
            isProfileCompleted = true
        )
        assertTrue(profile.isProfileValid)
        val state = resolveOnboardingState(profile)
        assertEquals(OnboardingState.READY, state)
    }
}
