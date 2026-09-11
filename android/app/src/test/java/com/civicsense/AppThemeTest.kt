package com.civicsense

import com.civicsense.data.model.AppTheme
import org.junit.Assert.assertEquals
import org.junit.Test

class AppThemeTest {

    @Test
    fun appTheme_fromStoredValue_handlesAllCases() {
        assertEquals(AppTheme.SYSTEM, AppTheme.fromStoredValue("system"))
        assertEquals(AppTheme.SYSTEM, AppTheme.fromStoredValue("SYSTEM"))
        assertEquals(AppTheme.LIGHT, AppTheme.fromStoredValue("light"))
        assertEquals(AppTheme.DARK, AppTheme.fromStoredValue("dark"))
        assertEquals(AppTheme.SYSTEM, AppTheme.fromStoredValue(null))
        assertEquals(AppTheme.SYSTEM, AppTheme.fromStoredValue("unknown_value"))
    }

    @Test
    fun appTheme_keysAndDisplayNamesAreCorrect() {
        assertEquals("system", AppTheme.SYSTEM.storageKey)
        assertEquals("light", AppTheme.LIGHT.storageKey)
        assertEquals("dark", AppTheme.DARK.storageKey)

        assertEquals("System default", AppTheme.SYSTEM.displayName)
        assertEquals("Light", AppTheme.LIGHT.displayName)
        assertEquals("Dark", AppTheme.DARK.displayName)
    }
}
