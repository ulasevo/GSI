package com.gsi.model

import androidx.compose.ui.graphics.Color
import org.json.JSONArray
import org.json.JSONObject

data class ReviewSection(
    val title: String,
    val content: String
)

/**
 * Core domain representation of a Chaperone (GSI) signal.
 * Unified across bundled assets, on-device authored overlays, JSON export, and LAN sync.
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
    val previewUrl: String? = null,
    val releaseYear: String? = null,
    val websitePath: String? = null,
    val isP53: Boolean = false,
    val reviewSections: List<ReviewSection> = emptyList(),
    val localCoverPath: String? = null,
    val isLocalOnly: Boolean = false,
    val pendingSync: Boolean = false,
    val makeActiveP53: Boolean = false,
    val updatedAt: Long = 0L
) {
    val primaryColor: Color
        get() = parseHexColor(primaryHex, fallback = Color(0xFFFFAE00))

    val glowColor: Color
        get() = parseHexColor(glowHex, fallback = Color(0xFFFFAE00))

    val surfaceColor: Color
        get() = parseHexColor(surfaceHex, fallback = Color(0xFF141414))

    fun toJson(): JSONObject = JSONObject().apply {
        put("id", id)
        put("slug", slug)
        put("artist", artist)
        put("track", track)
        put("album", album)
        put("tags", JSONArray(tags))
        put("coverFileName", coverFileName)
        put("primaryHex", primaryHex)
        put("surfaceHex", surfaceHex)
        put("glowHex", glowHex)
        put("transmissionNote", transmissionNote ?: JSONObject.NULL)
        put("spotifyUrl", spotifyUrl ?: JSONObject.NULL)
        put("appleUrl", appleUrl ?: JSONObject.NULL)
        put("previewUrl", previewUrl ?: JSONObject.NULL)
        put("releaseYear", releaseYear ?: JSONObject.NULL)
        put("websitePath", websitePath ?: JSONObject.NULL)
        put("isP53", isP53)
        put("localCoverPath", localCoverPath ?: JSONObject.NULL)
        put("isLocalOnly", isLocalOnly)
        put("pendingSync", pendingSync)
        put("makeActiveP53", makeActiveP53)
        put("updatedAt", updatedAt)
        put(
            "reviewSections",
            JSONArray().apply {
                reviewSections.forEach { sec ->
                    put(
                        JSONObject().apply {
                            put("title", sec.title)
                            put("content", sec.content)
                        }
                    )
                }
            }
        )
    }

    companion object {
        val CHAPERONE_SECTIONS = listOf(
            "Charge",
            "Sonic Attraction",
            "Lyric/Vocal Detail",
            "Version of ulaş",
            "Lore",
            "Reading",
            "Comment"
        )

        val ARCHIVE_TAGS = listOf(
            "bite",
            "ulas",
            "personal",
            "distortion",
            "bassline",
            "dreamy",
            "pop",
            "p53"
        )

        fun slugify(input: String): String {
            return input.lowercase()
                .trim()
                .replace(Regex("[^a-z0-9]+"), "-")
                .trim('-')
        }

        fun parseHexColor(hex: String, fallback: Color): Color {
            return try {
                val clean = hex.trim().removePrefix("#")
                val longVal = clean.toLong(16)
                when (clean.length) {
                    6 -> Color(0xFF000000 or longVal)
                    8 -> Color(longVal)
                    else -> fallback
                }
            } catch (_: Exception) {
                fallback
            }
        }

        fun fromJson(obj: JSONObject): Signal {
            val tagsArray = obj.optJSONArray("tags")
            val tags = mutableListOf<String>()
            if (tagsArray != null) {
                for (i in 0 until tagsArray.length()) {
                    tagsArray.optString(i).takeIf { it.isNotBlank() }?.let { tags.add(it) }
                }
            }
            val sectionsArray = obj.optJSONArray("reviewSections")
            val sections = mutableListOf<ReviewSection>()
            if (sectionsArray != null) {
                for (i in 0 until sectionsArray.length()) {
                    val s = sectionsArray.optJSONObject(i) ?: continue
                    val title = s.optString("title").trim()
                    val content = s.optString("content").trim()
                    if (title.isNotEmpty() && content.isNotEmpty()) {
                        sections.add(ReviewSection(title, content))
                    }
                }
            }
            val slug = obj.optString("slug").ifBlank {
                slugify("${obj.optString("artist")}-${obj.optString("track")}")
            }
            return Signal(
                id = obj.optString("id").ifBlank { "local-$slug" },
                slug = slug,
                artist = obj.optString("artist", "Unknown Artist"),
                track = obj.optString("track", "Unknown Track"),
                album = obj.optString("album", ""),
                tags = tags,
                coverFileName = obj.optString("coverFileName").ifBlank { "$slug.jpg" },
                primaryHex = obj.optString("primaryHex", "#FF65AD"),
                surfaceHex = obj.optString("surfaceHex", "#16121C"),
                glowHex = obj.optString("glowHex", "#FF65AD"),
                transmissionNote = obj.optString("transmissionNote").takeIf { it.isNotBlank() && it != "null" },
                spotifyUrl = obj.optString("spotifyUrl").takeIf { it.isNotBlank() && it != "null" },
                appleUrl = obj.optString("appleUrl").takeIf { it.isNotBlank() && it != "null" },
                previewUrl = obj.optString("previewUrl").takeIf { it.isNotBlank() && it != "null" },
                releaseYear = obj.optString("releaseYear").takeIf { it.isNotBlank() && it != "null" },
                websitePath = obj.optString("websitePath").takeIf { it.isNotBlank() && it != "null" },
                isP53 = obj.optBoolean("isP53", tags.any { it.equals("p53", ignoreCase = true) }),
                reviewSections = sections,
                localCoverPath = obj.optString("localCoverPath").takeIf { it.isNotBlank() && it != "null" },
                isLocalOnly = obj.optBoolean("isLocalOnly", false),
                pendingSync = obj.optBoolean("pendingSync", false),
                makeActiveP53 = obj.optBoolean("makeActiveP53", false),
                updatedAt = obj.optLong("updatedAt", 0L)
            )
        }
    }
}
