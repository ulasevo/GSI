package com.gsi.widget

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.GlanceTheme
import androidx.glance.Image
import androidx.glance.ImageProvider
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.action.actionStartActivity
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.appwidget.updateAll
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Box
import androidx.glance.layout.Column
import androidx.glance.layout.ContentScale
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.size
import androidx.glance.layout.width
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import com.gsi.MainActivity
import com.gsi.data.GsiRepository

/**
 * Jetpack Glance Home Screen Widget displaying the active Radio P53 transmission
 * with cover art, track/artist, and transmission note, deep-linking straight to the Song Room.
 */
class P53GlanceWidget : GlanceAppWidget() {

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val signals = GsiRepository.loadSignals(context)
        val activeSlug = GsiRepository.loadCurrentP53Slug(context)
        val activeSignal = signals.find { it.slug == activeSlug }
            ?: signals.firstOrNull { it.isP53 }
            ?: signals.firstOrNull()

        val coverBitmap = activeSignal?.let {
            GsiRepository.loadCoverAndroidBitmap(context, it.coverFileName, it.localCoverPath, maxEdgePx = 280)
        }

        provideContent {
            GlanceTheme {
                WidgetContent(
                    context = context,
                    track = activeSignal?.track ?: "Radio P53",
                    artist = activeSignal?.artist ?: "Chaperone Archive",
                    note = activeSignal?.transmissionNote,
                    slug = activeSignal?.slug,
                    accentColor = activeSignal?.primaryColor ?: Color(0xFFFF65AD),
                    coverBitmap = coverBitmap
                )
            }
        }
    }

    @Composable
    private fun WidgetContent(
        context: Context,
        track: String,
        artist: String,
        note: String?,
        slug: String?,
        accentColor: Color,
        coverBitmap: android.graphics.Bitmap?
    ) {
        val deepLinkUri = if (!slug.isNullOrBlank()) {
            Uri.parse("chaperone://signal/$slug")
        } else {
            Uri.parse("chaperone://p53/active")
        }
        val launchIntent = Intent(Intent.ACTION_VIEW, deepLinkUri, context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        Box(
            modifier = GlanceModifier
                .fillMaxSize()
                .cornerRadius(24.dp)
                .background(ColorProvider(Color(0xFF14101A)))
                .clickable(actionStartActivity(launchIntent))
                .padding(14.dp)
        ) {
            Row(
                modifier = GlanceModifier.fillMaxSize(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (coverBitmap != null) {
                    Image(
                        provider = ImageProvider(coverBitmap),
                        contentDescription = "$track cover",
                        contentScale = ContentScale.Crop,
                        modifier = GlanceModifier
                            .size(84.dp)
                            .cornerRadius(16.dp)
                    )
                    Spacer(modifier = GlanceModifier.width(12.dp))
                }

                Column(
                    modifier = GlanceModifier.fillMaxWidth()
                ) {
                    Text(
                        text = "RADIO P53 · ACTIVE",
                        style = TextStyle(
                            color = ColorProvider(accentColor),
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold
                        ),
                        maxLines = 1
                    )
                    Spacer(modifier = GlanceModifier.height(3.dp))
                    Text(
                        text = track,
                        style = TextStyle(
                            color = ColorProvider(Color(0xFFF8F5EF)),
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold
                        ),
                        maxLines = 1
                    )
                    Text(
                        text = artist,
                        style = TextStyle(
                            color = ColorProvider(Color(0xFFC4B9CF)),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium
                        ),
                        maxLines = 1
                    )
                    if (!note.isNullOrBlank()) {
                        Spacer(modifier = GlanceModifier.height(5.dp))
                        Text(
                            text = "“$note”",
                            style = TextStyle(
                                color = ColorProvider(Color(0xFFE7DFEE)),
                                fontSize = 11.sp
                            ),
                            maxLines = 2
                        )
                    }
                }
            }
        }
    }

    companion object {
        suspend fun refreshAll(context: Context) {
            try {
                P53GlanceWidget().updateAll(context)
            } catch (_: Exception) {
                // Ignore if no widget instances are currently pinned
            }
        }
    }
}
