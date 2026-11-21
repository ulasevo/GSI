package com.gsi.data

import android.content.Context
import android.net.Uri
import com.gsi.model.ReviewSection
import com.gsi.model.Signal
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

data class TrackLookupMetadata(
    val track: String,
    val artist: String,
    val album: String,
    val coverUrl: String,
    val previewUrl: String,
    val appleUrl: String,
    val spotifyUrl: String,
    val releaseYear: String
)

data class LanSyncResult(
    val success: Boolean,
    val message: String,
    val count: Int = 0
)

/**
 * Bidirectional LAN Sync and Link Metadata Lookup client for Chaperone Android <-> Node.js.
 * Uses direct iTunes lookup fallback when away from the home LAN.
 */
object LanSyncClient {

    private const val CONNECT_TIMEOUT_MS = 7000
    private const val READ_TIMEOUT_MS = 12000

    private val ALLOWED_MUSIC_HOSTS = setOf(
        "music.apple.com",
        "itunes.apple.com",
        "open.spotify.com"
    )

    fun extractFirstMusicUrl(rawSharedText: String?): String? {
        if (rawSharedText.isNullOrBlank()) return null
        val regex = Regex("https://[^\\s\"'<>]+", RegexOption.IGNORE_CASE)
        return regex.findAll(rawSharedText)
            .map { it.value.trimEnd('.', ',', ';', ')', ']') }
            .firstOrNull { candidate ->
                val host = Uri.parse(candidate).host?.lowercase()?.removePrefix("www.") ?: ""
                host in ALLOWED_MUSIC_HOSTS
            }
    }

    suspend fun pingServer(baseUrl: String, bearerToken: String): LanSyncResult =
        withContext(Dispatchers.IO) {
            try {
                val cleanBase = validateBaseUrl(baseUrl)
                val response = httpRequest("$cleanBase/api/sync/ping", "GET", bearerToken, null)
                val obj = JSONObject(response)
                if (obj.optString("status") == "ok") {
                    LanSyncResult(true, "Connected to Chaperone LAN server")
                } else {
                    LanSyncResult(false, "Unexpected response from server")
                }
            } catch (e: Exception) {
                LanSyncResult(false, e.message ?: "Could not reach LAN server")
            }
        }

    suspend fun lookupLink(
        context: Context,
        rawUrl: String,
        lanBaseUrl: String = LocalSignalStore.getLanBaseUrl(context),
        bearerToken: String = LocalSignalStore.getLanBearerToken(context)
    ): Result<TrackLookupMetadata> = withContext(Dispatchers.IO) {
        val cleanUrl = rawUrl.trim()
        val parsed = Uri.parse(cleanUrl)
        val host = parsed.host?.lowercase()?.removePrefix("www.") ?: ""
        if (parsed.scheme != "https" || host !in ALLOWED_MUSIC_HOSTS) {
            return@withContext Result.failure(IllegalArgumentException("Use an HTTPS Apple Music or Spotify link."))
        }

        // 1. Try local Node.js LAN server first (handles both Apple Music & Spotify seamlessly)
        if (lanBaseUrl.isNotBlank()) {
            try {
                val cleanBase = validateBaseUrl(lanBaseUrl)
                val body = JSONObject().put("url", cleanUrl).toString()
                val res = httpRequest("$cleanBase/api/lookup-link", "POST", bearerToken, body)
                val meta = JSONObject(res).optJSONObject("metadata")
                if (meta != null && meta.optString("track").isNotBlank()) {
                    return@withContext Result.success(
                        TrackLookupMetadata(
                            track = meta.optString("track"),
                            artist = meta.optString("artist"),
                            album = meta.optString("album"),
                            coverUrl = meta.optString("coverUrl"),
                            previewUrl = meta.optString("previewUrl"),
                            appleUrl = meta.optString("appleUrl"),
                            spotifyUrl = meta.optString("spotifyUrl"),
                            releaseYear = meta.optString("releaseYear")
                        )
                    )
                }
            } catch (_: Exception) {
                // Fall through to direct iTunes / Spotify public lookup when off-LAN
            }
        }

        // 2. Direct off-LAN fallback (iTunes Search API / Spotify oEmbed over HTTPS)
        try {
            val direct = directPublicLookup(cleanUrl, host, parsed)
            Result.success(direct)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun directPublicLookup(cleanUrl: String, host: String, parsed: Uri): TrackLookupMetadata {
        if (host == "music.apple.com" || host == "itunes.apple.com") {
            val trackId = parsed.getQueryParameter("i")
                ?.takeIf { it.all(Char::isDigit) }
                ?: parsed.lastPathSegment?.takeIf { it.all(Char::isDigit) }

            if (!trackId.isNullOrBlank()) {
                val json = httpRequest(
                    "https://itunes.apple.com/lookup?id=$trackId&entity=song",
                    "GET",
                    "",
                    null
                )
                parseItunesResponse(json, fallbackApple = cleanUrl)?.let { return it }
            }

            val segments = parsed.pathSegments.filterNot {
                it.matches(Regex("^(us|tr|gb|ca|album|song|\\d+)$", RegexOption.IGNORE_CASE))
            }
            val term = segments.joinToString(" ").replace("-", " ").trim()
            if (term.isNotBlank()) {
                val encoded = URLEncoder.encode(term, "UTF-8")
                val json = httpRequest(
                    "https://itunes.apple.com/search?term=$encoded&entity=song&limit=2",
                    "GET",
                    "",
                    null
                )
                parseItunesResponse(json, fallbackApple = cleanUrl)?.let { return it }
            }
        } else if (host == "open.spotify.com") {
            val encoded = URLEncoder.encode(cleanUrl, "UTF-8")
            val oembed = JSONObject(
                httpRequest("https://open.spotify.com/oembed?url=$encoded", "GET", "", null)
            )
            val title = oembed.optString("title").trim()
            val thumb = oembed.optString("thumbnail_url").trim()
            if (title.isNotBlank()) {
                try {
                    val searchJson = httpRequest(
                        "https://itunes.apple.com/search?term=${URLEncoder.encode(title, "UTF-8")}&entity=song&limit=2",
                        "GET",
                        "",
                        null
                    )
                    parseItunesResponse(searchJson, fallbackSpotify = cleanUrl)?.let { found ->
                        return if (found.coverUrl.isBlank()) found.copy(coverUrl = thumb) else found
                    }
                } catch (_: Exception) {}
            }
            return TrackLookupMetadata(
                track = title.ifBlank { "Untitled Signal" },
                artist = "",
                album = "",
                coverUrl = thumb,
                previewUrl = "",
                appleUrl = "",
                spotifyUrl = cleanUrl,
                releaseYear = ""
            )
        }
        throw IllegalStateException("Could not resolve track metadata from link.")
    }

    private fun parseItunesResponse(
        json: String,
        fallbackApple: String = "",
        fallbackSpotify: String = ""
    ): TrackLookupMetadata? {
        val results = JSONObject(json).optJSONArray("results") ?: return null
        for (i in 0 until results.length()) {
            val item = results.optJSONObject(i) ?: continue
            val track = item.optString("trackName").trim()
            val artist = item.optString("artistName").trim()
            if (track.isBlank() || artist.isBlank()) continue
            val art = item.optString("artworkUrl100")
                .replace(Regex("/\\d+x\\d+bb\\.(jpg|png|webp)$", RegexOption.IGNORE_CASE), "/600x600bb.$1")
            val year = item.optString("releaseDate").take(4).takeIf { it.all(Char::isDigit) } ?: ""
            return TrackLookupMetadata(
                track = track,
                artist = artist,
                album = item.optString("collectionName").trim(),
                coverUrl = art,
                previewUrl = item.optString("previewUrl").trim(),
                appleUrl = item.optString("trackViewUrl").ifBlank { fallbackApple },
                spotifyUrl = fallbackSpotify,
                releaseYear = year
            )
        }
        return null
    }

    suspend fun downloadCoverToLocal(context: Context, slug: String, coverUrl: String): String? =
        withContext(Dispatchers.IO) {
            if (coverUrl.isBlank()) return@withContext null
            try {
                val conn = (URL(coverUrl).openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"
                    connectTimeout = CONNECT_TIMEOUT_MS
                    readTimeout = READ_TIMEOUT_MS
                }
                if (conn.responseCode in 200..299) {
                    val bytes = conn.inputStream.use { it.readBytes() }
                    if (bytes.isNotEmpty() && bytes.size <= 5 * 1024 * 1024) {
                        return@withContext LocalSignalStore.saveCoverBytes(context, slug, bytes)
                    }
                }
                null
            } catch (_: Exception) {
                null
            }
        }

    suspend fun pullArchiveBundle(
        context: Context,
        baseUrl: String,
        bearerToken: String
    ): LanSyncResult = withContext(Dispatchers.IO) {
        try {
            val cleanBase = validateBaseUrl(baseUrl)
            val raw = httpRequest("$cleanBase/api/sync/bundle", "GET", bearerToken, null)
            val root = JSONObject(raw)
            val arr = root.optJSONArray("signals") ?: JSONArray()
            val pulled = mutableListOf<Signal>()

            for (i in 0 until arr.length()) {
                val item = arr.optJSONObject(i) ?: continue
                val slug = item.optString("slug")
                if (slug.isBlank()) continue

                val tagsArr = item.optJSONArray("tags") ?: JSONArray()
                val tags = (0 until tagsArr.length()).mapNotNull {
                    tagsArr.optString(it).takeIf { t -> t.isNotBlank() }
                }

                val secArr = item.optJSONArray("reviewSections") ?: JSONArray()
                val sections = (0 until secArr.length()).mapNotNull { idx ->
                    val s = secArr.optJSONObject(idx) ?: return@mapNotNull null
                    val title = s.optString("title").trim()
                    val content = s.optString("content").trim()
                    if (title.isNotEmpty() && content.isNotEmpty()) ReviewSection(title, content) else null
                }

                val coverFileName = item.optString("coverFileName").ifBlank { "$slug.jpg" }
                val remoteCoverRel = item.optString("coverUrl")
                var localCoverPath: String? = null
                if (!GsiRepository.hasBundledCover(context, coverFileName) && remoteCoverRel.startsWith("/covers/")) {
                    localCoverPath = downloadCoverToLocal(context, slug, "$cleanBase$remoteCoverRel")
                }

                pulled.add(
                    Signal(
                        id = item.optString("id").ifBlank { "sig-$slug" },
                        slug = slug,
                        artist = item.optString("artist", "Unknown Artist"),
                        track = item.optString("track", "Unknown Track"),
                        album = item.optString("album", ""),
                        tags = tags,
                        coverFileName = coverFileName,
                        primaryHex = item.optString("primaryHex", "#FF65AD"),
                        surfaceHex = item.optString("surfaceHex", "#141414"),
                        glowHex = item.optString("glowHex", "#FF65AD"),
                        transmissionNote = item.optString("transmissionNote").takeIf { it.isNotBlank() && it != "null" },
                        spotifyUrl = item.optString("spotifyUrl").takeIf { it.isNotBlank() && it != "null" },
                        appleUrl = item.optString("appleUrl").takeIf { it.isNotBlank() && it != "null" },
                        previewUrl = item.optString("previewUrl").takeIf { it.isNotBlank() && it != "null" },
                        releaseYear = item.optString("releaseYear").takeIf { it.isNotBlank() && it != "null" },
                        websitePath = item.optString("websitePath").takeIf { it.isNotBlank() && it != "null" },
                        isP53 = item.optBoolean("isP53", tags.contains("p53")),
                        reviewSections = sections,
                        localCoverPath = localCoverPath,
                        isLocalOnly = false,
                        pendingSync = false
                    )
                )
            }

            val p53Slug = root.optString("p53CurrentSlug").takeIf { it.isNotBlank() }
            LocalSignalStore.upsertPulledSignals(context, pulled, p53Slug)
            GsiRepository.invalidateCache()
            LanSyncResult(true, "Pulled ${pulled.size} signals from LAN archive", pulled.size)
        } catch (e: Exception) {
            LanSyncResult(false, e.message ?: "Failed to pull LAN bundle")
        }
    }

    suspend fun pushPendingSignals(
        context: Context,
        baseUrl: String,
        bearerToken: String,
        pendingSignals: List<Signal>
    ): LanSyncResult = withContext(Dispatchers.IO) {
        if (pendingSignals.isEmpty()) {
            return@withContext LanSyncResult(true, "Everything is already synced.", 0)
        }
        try {
            val cleanBase = validateBaseUrl(baseUrl)
            val payloadSignals = JSONArray()
            for (signal in pendingSignals) {
                val obj = signal.toJson()
                LocalSignalStore.readCoverBase64(signal.localCoverPath)?.let { b64 ->
                    obj.put("coverBase64", b64)
                }
                payloadSignals.put(obj)
            }
            val body = JSONObject().apply {
                put("signals", payloadSignals)
                LocalSignalStore.getActiveP53Override(context)?.let { put("p53CurrentSlug", it) }
            }.toString()

            val res = httpRequest("$cleanBase/api/sync/push", "POST", bearerToken, body)
            val json = JSONObject(res)
            val publishedArr = json.optJSONArray("slugs") ?: JSONArray()
            val syncedSlugs = (0 until publishedArr.length()).map { publishedArr.optString(it) }.toSet()
            LocalSignalStore.markSlugsSynced(context, syncedSlugs)
            GsiRepository.invalidateCache()
            LanSyncResult(true, "Pushed ${syncedSlugs.size} signal(s) & rebuilt web archive", syncedSlugs.size)
        } catch (e: Exception) {
            LanSyncResult(false, e.message ?: "LAN sync push failed")
        }
    }

    private fun validateBaseUrl(raw: String): String {
        val trimmed = raw.trim().trimEnd('/')
        val parsed = Uri.parse(trimmed)
        if (parsed.scheme != "http" && parsed.scheme != "https") {
            throw IllegalArgumentException("Server URL must start with http:// or https://")
        }
        if (parsed.host.isNullOrBlank()) {
            throw IllegalArgumentException("Invalid LAN server address")
        }
        return trimmed
    }

    private fun httpRequest(
        urlStr: String,
        method: String,
        bearerToken: String,
        jsonBody: String?
    ): String {
        val conn = (URL(urlStr).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = CONNECT_TIMEOUT_MS
            readTimeout = READ_TIMEOUT_MS
            setRequestProperty("Accept", "application/json")
            if (bearerToken.isNotBlank()) {
                setRequestProperty("Authorization", "Bearer ${bearerToken.trim()}")
            }
            if (jsonBody != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
            }
        }
        if (jsonBody != null) {
            conn.outputStream.use { os -> os.write(jsonBody.toByteArray(Charsets.UTF_8)) }
        }
        val code = conn.responseCode
        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
        val text = stream?.use { BufferedReader(InputStreamReader(it)).readText() } ?: ""
        if (code !in 200..299) {
            val errMsg = try {
                JSONObject(text).optString("error").ifBlank { "HTTP $code" }
            } catch (_: Exception) {
                "HTTP $code"
            }
            throw IllegalStateException(errMsg)
        }
        return text
    }
}
