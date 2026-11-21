package com.gsi.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import android.util.LruCache
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import com.gsi.model.ReviewSection
import com.gsi.model.Signal
import org.json.JSONObject
import java.io.File

object GsiRepository {

    private const val MAX_COVER_EDGE_PX = 640
    private val bitmapCache = LruCache<String, ImageBitmap>(48)
    private val androidBitmapCache = LruCache<String, Bitmap>(24)

    fun invalidateCache() {
        bitmapCache.evictAll()
        androidBitmapCache.evictAll()
    }

    fun hasBundledCover(context: Context, fileName: String): Boolean {
        return try {
            context.assets.open("covers/$fileName").close()
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun loadReviews(context: Context): Pair<Map<String, List<ReviewSection>>, Map<String, List<ReviewSection>>> =
        try {
            val raw = context.assets.open("data/reviews.json").bufferedReader().use { it.readText() }
            val root = JSONObject(raw)
            val byId = parseReviewsObject(root.optJSONObject("reviews"))
            val bySlug = parseReviewsObject(root.optJSONObject("reviewsBySlug"))
            byId to bySlug
        } catch (error: Exception) {
            Log.w("GsiRepository", "Could not load bundled reviews", error)
            emptyMap<String, List<ReviewSection>>() to emptyMap()
        }

    private fun parseReviewsObject(obj: JSONObject?): Map<String, List<ReviewSection>> {
        if (obj == null) return emptyMap()
        val result = mutableMapOf<String, List<ReviewSection>>()
        val ids = obj.keys()
        while (ids.hasNext()) {
            val key = ids.next()
            val sections = obj.optJSONArray(key) ?: continue
            result[key] = (0 until sections.length()).mapNotNull { index ->
                val section = sections.optJSONObject(index) ?: return@mapNotNull null
                val title = section.optString("title").trim()
                val content = section.optString("content").trim()
                if (title.isNotEmpty() && content.isNotEmpty()) ReviewSection(title, content) else null
            }
        }
        return result
    }

    fun loadCurrentP53Slug(context: Context): String? {
        LocalSignalStore.getActiveP53Override(context)?.let { return it }
        return try {
            val raw = context.assets.open("data/p53_config.json").bufferedReader().use { it.readText() }
            JSONObject(raw).optString("p53_current_slug").takeIf { it.isNotBlank() }
        } catch (_: Exception) {
            null
        }
    }

    fun loadSiteBaseUrl(context: Context): String {
        return try {
            val raw = context.assets.open("data/p53_config.json").bufferedReader().use { it.readText() }
            JSONObject(raw).optString("site_url").trim().trimEnd('/').ifBlank {
                "https://cagriulas.github.io/GSI"
            }
        } catch (_: Exception) {
            "https://cagriulas.github.io/GSI"
        }
    }

    /**
     * Loads bundled archive signals and merges on-device authored/synced overlay entries by slug.
     */
    fun loadSignals(context: Context): List<Signal> {
        val bundled = loadBundledSignals(context)
        val overlays = LocalSignalStore.loadOverlaySignals(context)
        if (overlays.isEmpty()) return bundled

        val mergedBySlug = linkedMapOf<String, Signal>()
        // Newly authored local-only signals surface at top of archive
        val bundledSlugs = bundled.map { it.slug }.toSet()
        overlays.filter { it.slug !in bundledSlugs }
            .sortedByDescending { it.updatedAt }
            .forEach { mergedBySlug[it.slug] = it }

        val overlayMap = overlays.associateBy { it.slug }
        for (base in bundled) {
            val override = overlayMap[base.slug]
            mergedBySlug[base.slug] = if (override != null) {
                base.copy(
                    artist = override.artist.ifBlank { base.artist },
                    track = override.track.ifBlank { base.track },
                    album = override.album.ifBlank { base.album },
                    tags = override.tags.ifEmpty { base.tags },
                    primaryHex = override.primaryHex.ifBlank { base.primaryHex },
                    surfaceHex = override.surfaceHex.ifBlank { base.surfaceHex },
                    glowHex = override.glowHex.ifBlank { base.glowHex },
                    transmissionNote = override.transmissionNote ?: base.transmissionNote,
                    spotifyUrl = override.spotifyUrl ?: base.spotifyUrl,
                    appleUrl = override.appleUrl ?: base.appleUrl,
                    previewUrl = override.previewUrl ?: base.previewUrl,
                    releaseYear = override.releaseYear ?: base.releaseYear,
                    isP53 = override.isP53 || base.isP53,
                    reviewSections = override.reviewSections.ifEmpty { base.reviewSections },
                    localCoverPath = override.localCoverPath ?: base.localCoverPath,
                    pendingSync = override.pendingSync,
                    isLocalOnly = override.isLocalOnly,
                    makeActiveP53 = override.makeActiveP53,
                    updatedAt = override.updatedAt
                )
            } else {
                base
            }
        }
        return mergedBySlug.values.toList()
    }

    private fun loadBundledSignals(context: Context): List<Signal> {
        val signals = mutableListOf<Signal>()
        val (reviewsById, reviewsBySlug) = loadReviews(context)

        try {
            val p53Notes = mutableMapOf<String, String>()
            val p53Slugs = mutableSetOf<String>()
            try {
                val p53JsonStr = context.assets.open("data/p53_config.json").bufferedReader().use { it.readText() }
                val p53Obj = JSONObject(p53JsonStr)
                p53Obj.optJSONArray("p53_history")?.let { history ->
                    for (idx in 0 until history.length()) {
                        history.optJSONObject(idx)?.optString("slug")
                            ?.takeIf { it.isNotBlank() }
                            ?.let { p53Slugs.add(it) }
                    }
                }
                if (p53Obj.has("p53_transmission_notes")) {
                    val notesObj = p53Obj.getJSONObject("p53_transmission_notes")
                    val keys = notesObj.keys()
                    while (keys.hasNext()) {
                        val key = keys.next()
                        p53Notes[key] = notesObj.optString(key)
                    }
                }
            } catch (_: Exception) {}

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
                val previewUrl = item.optString("preview_url").takeIf { it.isNotBlank() }
                val releaseYear = item.optString("release_year").takeIf { it.isNotBlank() }

                val note = p53Notes[slug]
                val isP53 = slug in p53Slugs || tags.any { it.equals("p53", ignoreCase = true) }

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
                        previewUrl = previewUrl,
                        releaseYear = releaseYear,
                        websitePath = item.optString("page_url").takeIf {
                            (it.startsWith("entries/") || it.startsWith("p53/")) &&
                                it.endsWith(".html") && !it.contains("..")
                        },
                        isP53 = isP53,
                        reviewSections = reviewsById[id] ?: reviewsBySlug[slug].orEmpty()
                    )
                )
            }
        } catch (e: Exception) {
            Log.e("GsiRepository", "Failed loading bundled catalog", e)
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

    fun loadCoverAndroidBitmap(
        context: Context,
        fileName: String,
        localCoverPath: String? = null,
        maxEdgePx: Int = MAX_COVER_EDGE_PX
    ): Bitmap? {
        val cacheKey = "${localCoverPath ?: fileName}:$maxEdgePx"
        androidBitmapCache.get(cacheKey)?.let { return it }

        // 1. Prefer locally cached cover (from Live Authoring or LAN sync)
        if (!localCoverPath.isNullOrBlank()) {
            val file = File(localCoverPath)
            if (file.exists() && file.isFile) {
                try {
                    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                    BitmapFactory.decodeFile(file.absolutePath, bounds)
                    val opts = BitmapFactory.Options().apply {
                        inSampleSize = calculateInSampleSize(bounds.outWidth, bounds.outHeight, maxEdgePx)
                    }
                    val bmp = BitmapFactory.decodeFile(file.absolutePath, opts)
                    if (bmp != null) {
                        androidBitmapCache.put(cacheKey, bmp)
                        return bmp
                    }
                } catch (_: Exception) {}
            }
        }

        // 2. Fall back to bundled APK assets
        return try {
            val assetPath = "covers/$fileName"
            val boundsOptions = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            context.assets.open(assetPath).use { stream ->
                BitmapFactory.decodeStream(stream, null, boundsOptions)
            }
            val decodeOptions = BitmapFactory.Options().apply {
                inSampleSize = calculateInSampleSize(
                    boundsOptions.outWidth,
                    boundsOptions.outHeight,
                    maxEdgePx
                )
            }
            val bitmap = context.assets.open(assetPath).use { stream ->
                BitmapFactory.decodeStream(stream, null, decodeOptions)
            }
            if (bitmap != null) {
                androidBitmapCache.put(cacheKey, bitmap)
            }
            bitmap
        } catch (_: Exception) {
            null
        }
    }

    fun loadCoverBitmap(
        context: Context,
        fileName: String,
        localCoverPath: String? = null
    ): ImageBitmap? {
        val cacheKey = localCoverPath ?: fileName
        bitmapCache.get(cacheKey)?.let { return it }
        val bmp = loadCoverAndroidBitmap(context, fileName, localCoverPath, MAX_COVER_EDGE_PX)
        val imageBitmap = bmp?.asImageBitmap()
        if (imageBitmap != null) {
            bitmapCache.put(cacheKey, imageBitmap)
        }
        return imageBitmap
    }
}
