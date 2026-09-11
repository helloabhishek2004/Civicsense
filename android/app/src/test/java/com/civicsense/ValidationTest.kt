package com.civicsense

import com.civicsense.core.util.InputValidators
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ValidationTest {

    @Test
    fun indianMobileValidation_strictNormalizationRules() {
        // Invalid lengths & blank
        assertFalse(InputValidators.normalizeIndianMobile("").first)
        assertFalse(InputValidators.normalizeIndianMobile("   ").first)
        assertFalse(InputValidators.normalizeIndianMobile("123").first)
        assertFalse(InputValidators.normalizeIndianMobile("98765").first)

        // Valid 10-digit starting with 6-9
        val valid1 = InputValidators.normalizeIndianMobile("9876543210")
        assertTrue(valid1.first)
        assertEquals("9876543210", valid1.second)

        val valid7 = InputValidators.normalizeIndianMobile("7012345678")
        assertTrue(valid7.first)
        assertEquals("7012345678", valid7.second)

        val valid6 = InputValidators.normalizeIndianMobile("6282000000")
        assertTrue(valid6.first)
        assertEquals("6282000000", valid6.second)

        // Invalid leading digits (< 6)
        assertFalse(InputValidators.normalizeIndianMobile("1234567890").first)
        assertFalse(InputValidators.normalizeIndianMobile("5555555555").first)
        assertFalse(InputValidators.normalizeIndianMobile("0987654321").first)

        // With +91 prefix
        val withPlus91 = InputValidators.normalizeIndianMobile("+91 9876543210")
        assertTrue(withPlus91.first)
        assertEquals("9876543210", withPlus91.second)

        val withPlus91NoSpace = InputValidators.normalizeIndianMobile("+919876543210")
        assertTrue(withPlus91NoSpace.first)
        assertEquals("9876543210", withPlus91NoSpace.second)

        // With 12-digit 91 prefix
        val with12Digits = InputValidators.normalizeIndianMobile("919876543210")
        assertTrue(with12Digits.first)
        assertEquals("9876543210", with12Digits.second)

        // With dashes / spaces
        val formatted = InputValidators.normalizeIndianMobile("98765-43210")
        assertTrue(formatted.first)
        assertEquals("9876543210", formatted.second)
    }

    @Test
    fun fullNameValidation_requiresMinimumTwoCharacters() {
        assertFalse(InputValidators.isValidFullName(""))
        assertFalse(InputValidators.isValidFullName("   "))
        assertFalse(InputValidators.isValidFullName("A"))
        assertTrue(InputValidators.isValidFullName("Ab"))
        assertTrue(InputValidators.isValidFullName("Abhishek Nair"))
    }

    @Test
    fun emailValidation_optionalOrWellFormed() {
        assertTrue(InputValidators.isValidEmail(""))
        assertTrue(InputValidators.isValidEmail("   "))
        assertFalse(InputValidators.isValidEmail("notanemail"))
        assertFalse(InputValidators.isValidEmail("invalid@com"))
        assertFalse(InputValidators.isValidEmail("space @example.com"))
        assertTrue(InputValidators.isValidEmail("user@example.com"))
    }

    @Test
    fun postalPinValidation_requiresExactlySixDigitsAndNonZeroStart() {
        assertFalse(InputValidators.isValidPostalPin(""))
        assertFalse(InputValidators.isValidPostalPin("69558")) // 5 digits
        assertFalse(InputValidators.isValidPostalPin("6955812")) // 7 digits
        assertFalse(InputValidators.isValidPostalPin("095581")) // Leading 0
        assertFalse(InputValidators.isValidPostalPin("abc695")) // Non digits
        assertTrue(InputValidators.isValidPostalPin("695581")) // Exactly 6 digits
    }

    @Test
    fun descriptionValidation_requiresAtLeastFiveCharacters() {
        assertFalse(InputValidators.isValidDescription(""))
        assertFalse(InputValidators.isValidDescription("Poth"))
        assertTrue(InputValidators.isValidDescription("Pothole on main avenue road"))
    }

    @Test
    fun timeBasedGreeting_calculatesCorrectTimeWindows() {
        // Morning: 05:00 - 11:59
        assertEquals("Good morning, Abhishek", InputValidators.calculateGreeting(5, "Abhishek Nair"))
        assertEquals("Good morning, Abhishek", InputValidators.calculateGreeting(11, "Abhishek Nair"))

        // Afternoon: 12:00 - 16:59
        assertEquals("Good afternoon, Abhishek", InputValidators.calculateGreeting(12, "Abhishek Nair"))
        assertEquals("Good afternoon, Abhishek", InputValidators.calculateGreeting(16, "Abhishek Nair"))

        // Evening: 17:00 - 20:59
        assertEquals("Good evening, Abhishek", InputValidators.calculateGreeting(17, "Abhishek Nair"))
        assertEquals("Good evening, Abhishek", InputValidators.calculateGreeting(20, "Abhishek Nair"))

        // Night / Early morning: 21:00 - 04:59
        assertEquals("Welcome back, Abhishek", InputValidators.calculateGreeting(21, "Abhishek Nair"))
        assertEquals("Welcome back, Abhishek", InputValidators.calculateGreeting(23, "Abhishek Nair"))
        assertEquals("Welcome back, Abhishek", InputValidators.calculateGreeting(2, "Abhishek Nair"))

        // Blank name fallback
        assertEquals("Good morning", InputValidators.calculateGreeting(9, ""))
        assertEquals("Welcome back", InputValidators.calculateGreeting(22, "   "))
    }
}
