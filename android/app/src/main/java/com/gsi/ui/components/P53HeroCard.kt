package com.gsi.ui.components

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gsi.model.Signal
import com.gsi.ui.theme.GsiBeaconGreen
import com.gsi.ui.theme.GsiBorder
import com.gsi.ui.theme.GsiP53Amber
import com.gsi.ui.theme.GsiSurface
import com.gsi.ui.theme.GsiSurfaceElevated
import com.gsi.ui.theme.GsiTextMuted
import com.gsi.ui.theme.GsiTextPrimary
import com.gsi.ui.theme.GsiTextSecondary
import com.gsi.util.HapticHelper

/**
 * Authentic GSI Radio P53 Shrine.
 * Intimate album shrine featuring real GSI cover art, personal review quotes,
 * outbound streaming links, and a tactile waveform.
 */
@Composable
fun P53HeroCard(
    signal: Signal,
    coverBitmap: ImageBitmap?,
    modifier: Modifier = Modifier,
    onCardClick: () -> Unit = {}
) {
    val context = LocalContext.current
    var isVisualizerActive by remember { mutableStateOf(true) }

    val infiniteTransition = rememberInfiniteTransition(label = "p53Beacon")
    val beaconAlpha by infiniteTransition.animateFloat(
        initialValue = 0.4f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1200, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "beaconAlpha"
    )

    TactileCard(
        onClick = onCardClick,
        cornerRadius = 22.dp,
        backgroundColor = GsiSurface,
        borderColor = signal.glowColor.copy(alpha = 0.35f),
        borderWidth = 1.dp,
        modifier = modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp)
        ) {
            // 1. Header: Radio P53 & Current Transmission
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(7.dp)
                            .background(
                                color = GsiBeaconGreen.copy(alpha = beaconAlpha),
                                shape = CircleShape
                            )
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Current transmission",
                        style = androidx.compose.material3.MaterialTheme.typography.labelSmall.copy(
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = GsiTextSecondary
                        )
                    )
                }

                Text(
                    text = "RADIO P53",
                    style = androidx.compose.material3.MaterialTheme.typography.labelMedium.copy(
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = GsiP53Amber
                    )
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // 2. High Resolution Album Cover
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(1f)
                    .clip(RoundedCornerShape(14.dp)),
                contentAlignment = Alignment.Center
            ) {
                if (coverBitmap != null) {
                    Image(
                        bitmap = coverBitmap,
                        contentDescription = "${signal.track} by ${signal.artist}",
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Crop
                    )
                } else {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(
                                Brush.verticalGradient(
                                    colors = listOf(
                                        signal.primaryColor.copy(alpha = 0.5f),
                                        GsiSurfaceElevated,
                                        Color.Black
                                    )
                                )
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = signal.track.take(1),
                            fontSize = 64.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White.copy(alpha = 0.6f)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(18.dp))

            // 3. Track & Artist
            Text(
                text = signal.track,
                style = androidx.compose.material3.MaterialTheme.typography.headlineMedium.copy(
                    fontWeight = FontWeight.Bold,
                    fontSize = 24.sp
                )
            )

            Spacer(modifier = Modifier.height(4.dp))

            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = signal.artist,
                    style = androidx.compose.material3.MaterialTheme.typography.titleMedium.copy(
                        color = signal.glowColor,
                        fontWeight = FontWeight.SemiBold
                    )
                )
                if (signal.album.isNotBlank()) {
                    Text(
                        text = " — ${signal.album}",
                        style = androidx.compose.material3.MaterialTheme.typography.bodyMedium.copy(
                            color = GsiTextMuted
                        ),
                        maxLines = 1
                    )
                }
            }

            // 4. Authentic Personal Memory / Transmission Note
            if (!signal.transmissionNote.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(14.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(
                            color = GsiSurfaceElevated,
                            shape = RoundedCornerShape(10.dp)
                        )
                        .border(
                            width = 1.dp,
                            color = GsiBorder,
                            shape = RoundedCornerShape(10.dp)
                        )
                        .padding(horizontal = 14.dp, vertical = 10.dp)
                ) {
                    Text(
                        text = "\"${signal.transmissionNote}\"",
                        style = androidx.compose.material3.MaterialTheme.typography.bodyMedium.copy(
                            color = GsiTextPrimary,
                            fontStyle = FontStyle.Italic,
                            lineHeight = 20.sp
                        )
                    )
                }
            }

            // 5. Outbound Streaming Buttons (Spotify & Apple Music)
            if (signal.spotifyUrl != null || signal.appleUrl != null) {
                Spacer(modifier = Modifier.height(14.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    signal.spotifyUrl?.let { url ->
                        OutlinedButton(
                            onClick = {
                                HapticHelper.click(context)
                                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                                context.startActivity(intent)
                            },
                            shape = RoundedCornerShape(8.dp),
                            border = BorderStroke(1.dp, GsiBorder),
                            colors = ButtonDefaults.outlinedButtonColors(
                                containerColor = Color.Transparent,
                                contentColor = GsiTextPrimary
                            ),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text(
                                text = "Spotify ↗",
                                style = androidx.compose.material3.MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = FontWeight.SemiBold,
                                    letterSpacing = 0.5.sp
                                )
                            )
                        }
                    }

                    signal.appleUrl?.let { url ->
                        OutlinedButton(
                            onClick = {
                                HapticHelper.click(context)
                                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                                context.startActivity(intent)
                            },
                            shape = RoundedCornerShape(8.dp),
                            border = BorderStroke(1.dp, GsiBorder),
                            colors = ButtonDefaults.outlinedButtonColors(
                                containerColor = Color.Transparent,
                                contentColor = GsiTextPrimary
                            ),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text(
                                text = "Apple Music ↗",
                                style = androidx.compose.material3.MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = FontWeight.SemiBold,
                                    letterSpacing = 0.5.sp
                                )
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // 6. Kinetic Waveform with Tap to Toggle
            Box(
                modifier = Modifier
                    .fillMaxWidth()
            ) {
                AudioPulseBar(
                    barColor = signal.glowColor,
                    barCount = 36,
                    isPlaying = isVisualizerActive
                )
            }
        }
    }
}
