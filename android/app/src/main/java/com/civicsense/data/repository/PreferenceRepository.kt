package com.civicsense.data.repository

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.civicsense.data.model.AppTheme
import com.civicsense.data.model.UserProfile
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "civicsense_preferences")

class PreferenceRepository(private val context: Context) {

    private object PreferencesKeys {
        val FULL_NAME = stringPreferencesKey("user_full_name")
        val MOBILE_NUMBER = stringPreferencesKey("user_mobile_number")
        val EMAIL = stringPreferencesKey("user_email")
        val LOCALITY = stringPreferencesKey("user_locality")
        val POSTAL_PIN = stringPreferencesKey("user_postal_pin")
        val ONBOARDING_COMPLETED = booleanPreferencesKey("onboarding_completed")
        val PROFILE_COMPLETED = booleanPreferencesKey("profile_completed")
        val APP_THEME = stringPreferencesKey("app_theme_mode")
    }

    val userProfileFlow: Flow<UserProfile> = context.dataStore.data.map { preferences ->
        UserProfile(
            fullName = preferences[PreferencesKeys.FULL_NAME] ?: "",
            mobileNumber = preferences[PreferencesKeys.MOBILE_NUMBER] ?: "",
            email = preferences[PreferencesKeys.EMAIL] ?: "",
            locality = preferences[PreferencesKeys.LOCALITY] ?: "",
            postalPin = preferences[PreferencesKeys.POSTAL_PIN] ?: "",
            isOnboardingCompleted = preferences[PreferencesKeys.ONBOARDING_COMPLETED] ?: false,
            isProfileCompleted = preferences[PreferencesKeys.PROFILE_COMPLETED] ?: false
        )
    }

    val appThemeFlow: Flow<AppTheme> = context.dataStore.data.map { preferences ->
        AppTheme.fromStoredValue(preferences[PreferencesKeys.APP_THEME])
    }

    suspend fun setAppTheme(theme: AppTheme) {
        context.dataStore.edit { preferences ->
            preferences[PreferencesKeys.APP_THEME] = theme.storageKey
        }
    }

    suspend fun saveProfile(
        fullName: String,
        mobileNumber: String,
        email: String,
        locality: String,
        postalPin: String
    ) {
        context.dataStore.edit { preferences ->
            preferences[PreferencesKeys.FULL_NAME] = fullName.trim()
            preferences[PreferencesKeys.MOBILE_NUMBER] = mobileNumber.trim()
            preferences[PreferencesKeys.EMAIL] = email.trim()
            preferences[PreferencesKeys.LOCALITY] = locality.trim()
            preferences[PreferencesKeys.POSTAL_PIN] = postalPin.trim()
            preferences[PreferencesKeys.PROFILE_COMPLETED] = true
            preferences[PreferencesKeys.ONBOARDING_COMPLETED] = true
        }
    }

    suspend fun setOnboardingCompleted(completed: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[PreferencesKeys.ONBOARDING_COMPLETED] = completed
        }
    }

    suspend fun resetAll() {
        context.dataStore.edit { preferences ->
            preferences.clear()
        }
    }
}
