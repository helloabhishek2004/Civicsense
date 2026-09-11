package com.civicsense

import com.civicsense.core.navigation.BottomDestination
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class NavigationDestinationsTest {

    @Test
    fun bottomDestinations_notNullAndContainsFourItems() {
        val items = BottomDestination.items
        assertNotNull(items)
        assertEquals(4, items.size)
        assertTrue(items.all { it != null })
        assertTrue(items.all { it.route.isNotBlank() })
        assertTrue(items.all { it.label.isNotBlank() })
    }
}
