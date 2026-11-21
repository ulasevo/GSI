package com.gsi.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Base64
import com.gsi.model.Signal
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream

/**
 * On-device persistent overlay store for Chaperone.
 * Stores locally authored/edited signals, synced LAN archive snapshots, cached cover bitmaps,
 * and LAN server preferences in app-private storage, plus formats clean JSON exports.
 */
object LocalSignalStore {

    private const val OVERLAY_FILE = "local_signals.json"
    private const val LOCAL_COVERS_DIR = "local_covers"
    private const val PREFS_NAME = "chaperone_sync_prefs"
    private const val KEY_LAN_URL = "lan_base_url"
    private const val KEY_LAN_TOKEN = "lan_bearer_token"
    private const val KEY_ACTIVE_P53_OVERRIDE = "active_p53_slug_override"
    private const val KEY_LAST_SYNC_AT = "last_sync_at"

    private fun overlayFile(context: Context): File = File(context.filesDir, OVERLAY_FILE)

    fun localCoversDir(context: Context): File =
        File(context.filesDir, LOCAL_COVERS_DIR).apply { if (!exists()) mkdirs() }

    fun loadOverlaySignals(context: Context): List<Signal> {
        val file = overlayFile(context)
        if (!file.exists()) return emptyList()
        return try {
            val root = JSONObject(file.readText(Charsets.UTF_8))
            val arr = root.optJSONArray("signals") ?: return emptyList()
            (0 until arr.length()).mapNotNull { idx ->
                arr.optJSONObject(idx)?.let { Signal.fromJson(it) }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun writeOverlaySignals(context: Context, signals: List<Signal>) {
        val payload = JSONObject().apply {
            put("schema", 2)
            put("updatedAt", System.currentTimeMillis())
            put("signals", JSONArray().apply { signals.forEach { put(it.toJson()) } })
        }
        val target = overlayFile(context)
        val tmp = File(context.filesDir, "$OVERLAY_FILE.tmp")
        tmp.writeText(payload.toString(2), Charsets.UTF_8)
        if (!tmp.renameTo(target)) {
            target.writeText(payload.toString(2), Charsets.UTF_8)
            tmp.delete()
        }
    }

    fun upsertSignal(context: Context, signal: Signal) {
        val existing = loadOverlaySignals(context).toMutableList()
        val idx = existing.indexOfFirst { it.slug == signal.slug }
        val stamped = signal.copy(updatedAt = System.currentTimeMillis())
        if (idx >= 0) {
            existing[idx] = stamped
        } else {
            existing.add(0, stamped)
        }
        writeOverlaySignals(context, existing)
        if (signal.makeActiveP53 && signal.isP53) {
            setActiveP53Override(context, signal.slug)
        }
    }

    fun upsertPulledSignals(context: Context, pulled: List<Signal>, activeP53Slug: String?) {
        val existingBySlug = loadOverlaySignals(context).associateBy { it.slug }.toMutableMap()
        for (incoming in pulled) {
            val local = existingBySlug[incoming.slug]
            // Preserve unsynced local edits; otherwise adopt latest server state
            if (local == null || !local.pendingSync) {
                existingBySlug[incoming.slug] = incoming.copy(pendingSync = false, isLocalOnly = false)
            }
        }
        writeOverlaySignals(context, existingBySlug.values.toList())
        if (!activeP53Slug.isNullOrBlank()) {
            setActiveP53Override(context, activeP53Slug)
        }
        setLastSyncAt(context, System.currentTimeMillis())
    }

    fun markSlugsSynced(context: Context, slugs: Set<String>) {
        val updated = loadOverlaySignals(context).map { signal ->
            if (signal.slug in slugs) {
                signal.copy(pendingSync = false, isLocalOnly = false)
            } else {
                signal
            }
        }
        writeOverlaySignals(context, updated)
        setLastSyncAt(context, System.currentTimeMillis())
    }

    fun saveCoverBytes(context: Context, slug: String, bytes: ByteArray): String? {
        return try {
            val bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return null
            val outFile = File(localCoversDir(context), "$slug.jpg")
            FileOutputStream(outFile).use { fos ->
                bmp.compress(Bitmap.CompressFormat.JPEG, 90, fos)
            }
            outFile.absolutePath
        } catch (_: Exception) {
            null
        }
    }

    fun readCoverBase64(path: String?): String? {
        if (path.isNullOrBlank()) return null
        val file = File(path)
        if (!file.exists() || !file.isFile) return null
        return try {
            Base64.encodeToString(file.readBytes(), Base64.NO_WRAP)
        } catch (_: Exception) {
            null
        }
    }

    /** Builds a clean, portable JSON export containing the full archive + active P53 state. */
    fun buildExportJson(context: Context, allSignals: List<Signal>, activeP53Slug: String?): String {
        val root = JSONObject().apply {
            put("app", "Chaperone")
            put("schema", 2)
            put("exportedAt", System.currentTimeMillis())
            put("p53CurrentSlug", activeP53Slug ?: "")
            put("signalCount", allSignals.size)
            put("signals", JSONArray().apply { allSignals.forEach { put(it.toJson()) } })
        }
        return root.toString(2) + "\n"
    }

    // --- LAN Sync & P53 Preferences ---

    fun getLanBaseUrl(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getString(KEY_LAN_URL, "http://192.168.1.100:3000") ?: "http://192.168.1.100:3000"
    }

    fun getLanBearerToken(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getString(KEY_LAN_TOKEN, "") ?: ""
    }

    fun saveLanConfig(context: Context, baseUrl: String, bearerToken: String) {
        val cleaned = baseUrl.trim().trimEnd('/')
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_LAN_URL, cleaned)
            .putString(KEY_LAN_TOKEN, bearerToken.trim())
            .apply()
    }

    fun getActiveP53Override(context: Context): String? {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getString(KEY_ACTIVE_P53_OVERRIDE, null)?.takeIf { it.isNotBlank() }
    }

    fun setActiveP53Override(context: Context, slug: String) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_ACTIVE_P53_OVERRIDE, slug.trim())
            .apply()
    }

    fun getLastSyncAt(context: Context): Long {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getLong(KEY_LAST_SYNC_AT, 0L)
    }

    private fun setLastSyncAt(context: Context, timestamp: Long) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putLong(KEY_LAST_SYNC_AT, timestamp)
            .apply()
    }
}
