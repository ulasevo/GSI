package com.gsi.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gsi.model.Signal
import com.gsi.ui.theme.GsiBorder
import com.gsi.ui.theme.GsiBorderActive
import com.gsi.ui.theme.GsiSurface
import com.gsi.ui.theme.GsiSurfaceElevated
import com.gsi.ui.theme.GsiTextMuted
import com.gsi.ui.theme.GsiTextPrimary
import com.gsi.ui.theme.GsiTextSecondary

/**
 * An individual Signal item from the GSI catalogue.
 * Instantaneous tactile spring on touch, high-contrast typography, and album palette indicator.
 */
@Composable
fun SignalCard(
    signal: Signal,
    coverBitmap: ImageBitmap?,
    isSelected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    val borderColor = if (isSelected) signal.glowColor else GsiBorder
    val borderWidth = if (isSelected) 1.5.dp else 1.dp
    val backgroundColor = if (isSelected) GsiSurfaceElevated else GsiSurface

    TactileCard(
        onClick = onClick,
        cornerRadius = 14.dp,
        backgroundColor = backgroundColor,
        borderColor = borderColor,
        borderWidth = borderWidth,
        modifier = modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // 1. Thumbnail
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .border(0.5.dp, GsiBorderActive, RoundedCornerShape(8.dp)),
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
                            .background(signal.surfaceColor),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = signal.track.take(1).uppercase(),
                            color = signal.glowColor,
                            fontWeight = FontWeight.Bold,
                            fontSize = 18.sp
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.width(14.dp))

            // 2. Track & Artist text
            Column(
                modifier = Modifier.weight(1f)
            ) {
                Text(
                    text = signal.track,
                    style = androidx.compose.material3.MaterialTheme.typography.titleMedium.copy(
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium
                    ),
                    color = GsiTextPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                Spacer(modifier = Modifier.height(2.dp))

                Text(
                    text = signal.artist,
                    style = androidx.compose.material3.MaterialTheme.typography.bodyMedium,
                    color = GsiTextSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                if (signal.tags.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(5.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        signal.tags.take(2).forEach { tag ->
                            Text(
                                text = tag.replaceFirstChar { it.uppercase() },
                                style = androidx.compose.material3.MaterialTheme.typography.labelSmall.copy(
                                    fontSize = 10.sp,
                                    color = if (isSelected) signal.glowColor else GsiTextMuted
                                ),
                                modifier = Modifier
                                    .background(
                                        color = Color.Black.copy(alpha = 0.5f),
                                        shape = RoundedCornerShape(4.dp)
                                    )
                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.width(8.dp))

            // 3. Extracted Palette Indicator Dot
            Box(
                modifier = Modifier
                    .size(9.dp)
                    .background(
                        color = signal.glowColor,
                        shape = CircleShape
                    )
                    .border(
                        width = 0.5.dp,
                        color = Color.White.copy(alpha = 0.3f),
                        shape = CircleShape
                    )
            )
        }
    }
}
