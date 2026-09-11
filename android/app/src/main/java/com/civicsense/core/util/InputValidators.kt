package com.civicsense.core.util

object InputValidators {

    /**
     * Strictly normalizes Indian mobile numbers.
     * Rules:
     * - Strips whitespace, dashes, and standard delimiters.
     * - If input starts with "+91", strips "+91".
     * - If input contains 12 digits starting with "91", strips the leading "91".
     * - Requires exactly 10 digits starting with 6, 7, 8, or 9.
     * - Does NOT use naive `takeLast(10)`.
     *
     * @return Pair(isValid, normalized10DigitStringOrNull)
     */
    fun normalizeIndianMobile(rawInput: String): Pair<Boolean, String?> {
        val trimmed = rawInput.trim()
        if (trimmed.isEmpty()) return Pair(false, null)

        var cleaned = trimmed.replace(" ", "").replace("-", "")

        if (cleaned.startsWith("+91")) {
            cleaned = cleaned.substring(3)
        } else if (cleaned.startsWith("91") && cleaned.length == 12 && cleaned.all { it.isDigit() }) {
            cleaned = cleaned.substring(2)
        }

        if (cleaned.length == 10 && cleaned.all { it.isDigit() }) {
            val firstDigit = cleaned[0]
            if (firstDigit in '6'..'9') {
                return Pair(true, cleaned)
            }
        }

        return Pair(false, null)
    }

    /**
     * Validates citizen full name (at least 2 characters, non-blank).
     */
    fun isValidFullName(name: String): Boolean {
        return name.trim().length >= 2
    }

    /**
     * Validates email address (optional: blank is valid, non-blank requires basic format).
     */
    fun isValidEmail(email: String): Boolean {
        val trimmed = email.trim()
        if (trimmed.isEmpty()) return true
        return trimmed.length >= 5 && trimmed.contains("@") && trimmed.contains(".") && !trimmed.contains(" ")
    }

    /**
     * Validates Indian Postal PIN code (exactly 6 digits, cannot start with '0').
     */
    fun isValidPostalPin(pin: String): Boolean {
        val cleaned = pin.trim()
        return cleaned.length == 6 && cleaned.all { it.isDigit() } && cleaned[0] != '0'
    }

    /**
     * Validates issue description (minimum 5 characters, up to 300 characters).
     */
    fun isValidDescription(description: String): Boolean {
        val trimmed = description.trim()
        return trimmed.length in 5..300
    }

    /**
     * Calculates time-based greeting for Home screen.
     * Time windows:
     * - 05:00–11:59: "Good morning"
     * - 12:00–16:59: "Good afternoon"
     * - 17:00–20:59: "Good evening"
     * - 21:00–04:59: "Welcome back"
     *
     * Fallback: If name is blank, returns greeting alone without trailing comma.
     */
    fun calculateGreeting(hourOfDay: Int, fullName: String): String {
        val greeting = when (hourOfDay) {
            in 5..11 -> "Good morning"
            in 12..16 -> "Good afternoon"
            in 17..20 -> "Good evening"
            else -> "Welcome back"
        }

        val firstName = fullName.trim().split("\\s+".toRegex()).firstOrNull().orEmpty()
        return if (firstName.isNotEmpty()) {
            "$greeting, $firstName"
        } else {
            greeting
        }
    }
}
