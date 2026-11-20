package com.gsi.data

import android.content.Context
import android.graphics.BitmapFactory
import android.util.Log
import android.util.LruCache
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import com.gsi.model.Signal
import com.gsi.model.ReviewSection
import org.json.JSONObject

object GsiRepository {

    private const val MAX_COVER_EDGE_PX = 512
    private val bitmapCache = LruCache<String, ImageBitmap>(32)

    private fun loadReviews(context: Context): Map<String, List<ReviewSection>> = try {
        val raw = context.assets.open("data/reviews.json").bufferedReader().use { it.readText() }
        val reviews = JSONObject(raw).getJSONObject("reviews")
        val result = mutableMapOf<String, List<ReviewSection>>()
        val ids = reviews.keys()
        while (ids.hasNext()) {
            val id = ids.next()
            val sections = reviews.getJSONArray(id)
            result[id] = (0 until sections.length()).map { index ->
                val section = sections.getJSONObject(index)
                ReviewSection(section.getString("title"), section.getString("content"))
            }
        }
        result
    } catch (error: Exception) {
        Log.w("GsiRepository", "Could not load bundled reviews", error)
        emptyMap()
    }

    fun loadCurrentP53Slug(context: Context): String? = try {
        val raw = context.assets.open("data/p53_config.json").bufferedReader().use { it.readText() }
        JSONObject(raw).optString("p53_current_slug").takeIf { it.isNotBlank() }
    } catch (_: Exception) {
        null
    }

    fun loadSignals(context: Context): List<Signal> {
        val signals = mutableListOf<Signal>()
        val reviews = loadReviews(context)

        try {
            // 1. Read p53 transmission notes if available
            val p53Notes = mutableMapOf<String, String>()
            try {
                val p53JsonStr = context.assets.open("data/p53_config.json").bufferedReader().use { it.readText() }
                val p53Obj = JSONObject(p53JsonStr)
                if (p53Obj.has("p53_transmission_notes")) {
                    val notesObj = p53Obj.getJSONObject("p53_transmission_notes")
                    val keys = notesObj.keys()
                    while (keys.hasNext()) {
                        val key = keys.next()
                        p53Notes[key] = notesObj.optString(key)
                    }
                }
            } catch (_: Exception) {}

            // 2. Read catalog.json
            val catalogStr = context.assets.open("data/catalog.json").bufferedReader().use { it.readText() }
            val root = JSONObject(catalogStr)
            val signalsArray = root.optJSONArray("signals") ?: return emptyList()

            for (i in 0 until signalsArray.length()) {
                val item = signalsArray.getJSONObject(i)
                val slug = item.optString("slug", "")
                val id = item.optString("signal_id", "sig-$i")
                val artist = item.optString("artist", "Unknown Artist")
                val track = item.optString("track", "Unknown Track")
                val album = item.optString("album", "")

                val tags = mutableListOf<String>()
                val tagsArray = item.optJSONArray("tags")
                if (tagsArray != null) {
                    for (t in 0 until tagsArray.length()) {
                        tags.add(tagsArray.getString(t))
                    }
                }

                val coverObj = item.optJSONObject("cover")
                val coverPath = coverObj?.optString("path", "") ?: ""
                val coverFileName = if (coverPath.contains("/")) coverPath.substringAfterLast("/") else "$slug.jpg"

                val paletteObj = item.optJSONObject("palette")
                val primaryHex = paletteObj?.optString("primary", "#FFAE00") ?: "#FFAE00"
                val surfaceHex = paletteObj?.optString("surface", "#141414") ?: "#141414"
                val glowHex = paletteObj?.optString("glow", "#FFAE00") ?: "#FFAE00"

                val linksObj = item.optJSONObject("links")
                val spotifyUrl = linksObj?.optJSONObject("spotify")?.optString("url")?.takeIf { it.isNotBlank() }
                val appleUrl = linksObj?.optJSONObject("apple")?.optString("url")?.takeIf { it.isNotBlank() }

                val note = p53Notes[slug]

                signals.add(
                    Signal(
                        id = id,
                        slug = slug,
                        artist = artist,
                        track = track,
                        album = album,
                        tags = tags,
                        coverFileName = coverFileName,
                        primaryHex = primaryHex,
                        surfaceHex = surfaceHex,
                        glowHex = glowHex,
                        transmissionNote = note,
                        spotifyUrl = spotifyUrl,
                        appleUrl = appleUrl,
                        websitePath = item.optString("page_url").takeIf {
                            (it.startsWith("entries/") || it.startsWith("p53/")) &&
                                it.endsWith(".html") && !it.contains("..")
                        },
                        reviewSections = reviews[id].orEmpty()
                    )
                )
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }

        return signals
    }

    private fun calculateInSampleSize(width: Int, height: Int, maxEdge: Int): Int {
        var sampleSize = 1
        var longestEdge = maxOf(width, height)
        while (longestEdge > maxEdge) {
            sampleSize *= 2
            longestEdge /= 2
        }
        return sampleSize
    }

    fun loadCoverBitmap(context: Context, fileName: String): ImageBitmap? {
        bitmapCache.get(fileName)?.let { return it }

        return try {
            val assetPath = "covers/$fileName"
            val boundsOptions = BitmapFactory.Options().apply {
                inJustDecodeBounds = true
            }
            context.assets.open(assetPath).use { stream ->
                BitmapFactory.decodeStream(stream, null, boundsOptions)
            }
            val decodeOptions = BitmapFactory.Options().apply {
                inSampleSize = calculateInSampleSize(
                    boundsOptions.outWidth,
                    boundsOptions.outHeight,
                    MAX_COVER_EDGE_PX
                )
            }
            val bitmap = context.assets.open(assetPath).use { stream ->
                BitmapFactory.decodeStream(stream, null, decodeOptions)
            }
            val imageBitmap = bitmap?.asImageBitmap()
            if (imageBitmap != null) {
                bitmapCache.put(fileName, imageBitmap)
            }
            imageBitmap
        } catch (_: Exception) {
            null
        }
    }
}
