package com.gsi.model

import androidx.compose.ui.graphics.Color

data class ReviewSection(val title: String, val content: String)

/**
 * Core domain representation of an intercepted GSI signal.
 * Mirrors the signals inventory in site/data/catalog.json.
 */
data class Signal(
    val id: String,
    val slug: String,
    val artist: String,
    val track: String,
    val album: String,
    val tags: List<String>,
    val coverFileName: String,
    val primaryHex: String,
    val surfaceHex: String,
    val glowHex: String,
    val transmissionNote: String? = null,
    val spotifyUrl: String? = null,
    val appleUrl: String? = null,
    val websitePath: String? = null,
    val reviewSections: List<ReviewSection> = emptyList()
) {
    val primaryColor: Color
        get() = parseHexColor(primaryHex, fallback = Color(0xFFFFAE00))

    val glowColor: Color
        get() = parseHexColor(glowHex, fallback = Color(0xFFFFAE00))

    val surfaceColor: Color
        get() = parseHexColor(surfaceHex, fallback = Color(0xFF141414))

    companion object {
        fun parseHexColor(hex: String, fallback: Color): Color {
            return try {
                val clean = hex.trim().removePrefix("#")
                val longVal = clean.toLong(16)
                if (clean.length == 6) {
                    Color(0xFF000000 or longVal)
                } else if (clean.length == 8) {
                    Color(longVal)
                } else {
                    fallback
                }
            } catch (_: Exception) {
                fallback
            }
        }
    }
}
