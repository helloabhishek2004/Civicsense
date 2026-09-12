package com.civicsense.core.edge

import android.util.Log

/**
 * Deterministic text preprocessing and lightweight linguistic hint extraction.
 *
 * IMPORTANT: Structured keyword matches are preprocessing hints only,
 * never presented or counted as machine learning inference.
 */
object CivicTextPreprocessor {

    private const val TAG = "CivicSenseText"
    const val MAX_TEXT_LENGTH = 5000

    private val SEVERITY_DICTIONARY = setOf(
        "large", "deep", "massive", "severe", "huge", "collapsed", "flooded",
        "hazardous", "broken", "major", "heavy", "terrible", "dangerous", "caved"
    )

    private val URGENCY_DICTIONARY = setOf(
        "urgent", "emergency", "immediately", "critical", "soon", "accident",
        "risk", "hazard", "threat", "danger", "dying", "burst"
    )

    private val CATEGORY_DICTIONARY = setOf(
        "pothole", "crater", "road", "pavement", "street", "garbage", "trash",
        "waste", "dump", "debris", "leak", "leaking", "pipe", "water", "sewage",
        "drain", "drainage", "overflow", "streetlight", "light", "lamp",
        "footpath", "sidewalk", "manhole", "cover", "wire", "cable"
    )

    private val LOCATION_DICTIONARY = setOf(
        "near", "opposite", "road", "street", "junction", "cross", "corner",
        "bridge", "lane", "highway", "school", "hospital", "market", "bus stop",
        "station", "gate", "park", "temple", "church", "mosque", "building"
    )

    private val SAFETY_DICTIONARY = setOf(
        "pedestrian", "children", "traffic", "vehicle", "electric", "shock",
        "fire", "slippery", "fall", "injury", "wheelchair", "elderly"
    )

    /**
     * Executes normalization, statistics calculation, and transparent linguistic feature extraction.
     */
    fun preprocess(rawText: String): TextStructuredFeatures {
        Log.d(TAG, "[CivicSense][Text] Normalization started")

        val boundedRaw = if (rawText.length > MAX_TEXT_LENGTH) {
            rawText.take(MAX_TEXT_LENGTH)
        } else {
            rawText
        }

        // 1. Whitespace Normalization: Trim and collapse consecutive whitespaces/newlines to single spaces
        val cleaned = boundedRaw
            .trim()
            .replace(Regex("[ \\t\\r\\n]+"), " ")

        val charCount = cleaned.length
        val words = if (cleaned.isBlank()) emptyList() else cleaned.split(" ").filter { it.isNotBlank() }
        val wordCount = words.size

        // 2. Tokenize lowercased words with punctuation stripped for dictionary lookup
        val normalizedTokens = words.map { word ->
            word.lowercase().replace(Regex("[^a-z0-9]"), "")
        }.filter { it.isNotEmpty() }.toSet()

        // 3. Extract Structured Hints
        val severityMatches = SEVERITY_DICTIONARY.filter { it in normalizedTokens }
        val urgencyMatches = URGENCY_DICTIONARY.filter { it in normalizedTokens }
        val categoryMatches = CATEGORY_DICTIONARY.filter { it in normalizedTokens }
        val locationMatches = LOCATION_DICTIONARY.filter { it in normalizedTokens }
        val safetyMatches = SAFETY_DICTIONARY.filter { it in normalizedTokens }

        Log.d(TAG, "[CivicSense][Text] Text normalized: $charCount characters, $wordCount words")

        return TextStructuredFeatures(
            rawText = boundedRaw,
            cleanedText = cleaned,
            characterCount = charCount,
            wordCount = wordCount,
            language = "en",
            severityTerms = severityMatches,
            urgencyTerms = urgencyMatches,
            categoryTerms = categoryMatches,
            locationTerms = locationMatches,
            safetyTerms = safetyMatches
        )
    }
}
