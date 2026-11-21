package com.gsi.share

import android.app.PendingIntent
import android.content.ClipData
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.graphics.drawable.Icon
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import android.service.chooser.ChooserAction
import androidx.core.content.FileProvider
import com.gsi.data.GsiRepository
import com.gsi.model.Signal
import java.io.File

/**
 * Native Android handoff utilities for Chaperone's 9:16 Story Card Studio:
 * - FileProvider URI resolution scoped strictly to cacheDir/shared_cards/
 * - Direct Image-to-Clipboard copy (ClipData.newUri) for instant pasting into Instagram/Discord/Messages
 * - Enriched Android Sharesheet / Quick Share with thumbnail preview and custom ChooserActions
 * - MediaStore Save to Gallery (Pictures/Chaperone)
 */
object ShareBridge {

    fun uriForCardFile(context: Context, file: File): Uri {
        val authority = "${context.packageName}.fileprovider"
        return FileProvider.getUriForFile(context, authority, file)
    }

    fun canonicalSignalUrl(context: Context, signal: Signal): String {
        val base = GsiRepository.loadSiteBaseUrl(context)
        val path = signal.websitePath ?: if (signal.isP53) "p53/${signal.slug}.html" else "entries/${signal.slug}.html"
        return "$base/${path.trimStart('/')}"
    }

    /** Copies the rendered 9:16 PNG URI directly to the Android system clipboard. */
    fun copyCardImageToClipboard(context: Context, pngFile: File): Boolean {
        return try {
            val uri = uriForCardFile(context, pngFile)
            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
                ?: return false
            val clip = ClipData.newUri(context.contentResolver, "Chaperone Story Card", uri)
            clipboard.setPrimaryClip(clip)
            true
        } catch (_: Exception) {
            false
        }
    }

    fun copyCanonicalLink(context: Context, signal: Signal): Boolean {
        return try {
            val url = canonicalSignalUrl(context, signal)
            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
                ?: return false
            val clip = ClipData.newPlainText("Chaperone Link", url)
            clipboard.setPrimaryClip(clip)
            true
        } catch (_: Exception) {
            false
        }
    }

    /**
     * Launches the native Pixel / Android Sharesheet (including Quick Share) with:
     * - 9:16 PNG attached via FileProvider URI + temporary read grant
     * - Rich ClipData thumbnail preview
     * - Canonical link in EXTRA_TEXT
     * - Custom ChooserAction to open the web page or copy link directly from Sharesheet
     */
    fun launchRichShareSheet(context: Context, signal: Signal, pngFile: File) {
        val uri = uriForCardFile(context, pngFile)
        val canonicalUrl = canonicalSignalUrl(context, signal)
        val shareCaption = "${signal.track} — ${signal.artist}\n$canonicalUrl"

        val sendIntent = Intent(Intent.ACTION_SEND).apply {
            type = "image/png"
            putExtra(Intent.EXTRA_STREAM, uri)
            putExtra(Intent.EXTRA_TITLE, "${signal.track} — ${signal.artist}")
            putExtra(Intent.EXTRA_TEXT, shareCaption)
            clipData = ClipData.newRawUri("Chaperone 9:16 Card", uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }

        val chooser = Intent.createChooser(sendIntent, "Share 9:16 Card · Quick Share").apply {
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            val openWebIntent = Intent(Intent.ACTION_VIEW, Uri.parse(canonicalUrl))
            val pendingOpen = PendingIntent.getActivity(
                context,
                signal.slug.hashCode(),
                openWebIntent,
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            )
            val openAction = ChooserAction.Builder(
                Icon.createWithResource(context, android.R.drawable.ic_menu_compass),
                "Open in Chaperone",
                pendingOpen
            ).build()
            putExtra(Intent.EXTRA_CHOOSER_CUSTOM_ACTIONS, arrayOf(openAction))
        }

        context.startActivity(chooser)
    }

    /** Saves the rendered 9:16 PNG cleanly into Pictures/Chaperone via MediaStore. */
    fun saveCardToGallery(context: Context, pngFile: File, slug: String): Boolean {
        return try {
            val safeSlug = Signal.slugify(slug).ifBlank { "signal" }
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, "chaperone-$safeSlug-${System.currentTimeMillis()}.png")
                put(MediaStore.Images.Media.MIME_TYPE, "image/png")
                put(MediaStore.Images.Media.RELATIVE_PATH, "${Environment.DIRECTORY_PICTURES}/Chaperone")
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
            val resolver = context.contentResolver
            val inserted = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                ?: return false
            resolver.openOutputStream(inserted)?.use { out ->
                pngFile.inputStream().use { input -> input.copyTo(out) }
            } ?: return false
            values.clear()
            values.put(MediaStore.Images.Media.IS_PENDING, 0)
            resolver.update(inserted, values, null, null)
            true
        } catch (_: Exception) {
            false
        }
    }
}
