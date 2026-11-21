package com.gsi.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.Pause
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gsi.audio.PeekAudioPlayer
import com.gsi.audio.PeekPlaybackState
import com.gsi.model.Signal
import com.gsi.ui.theme.ChaperoneCompactAsymmShape
import com.gsi.util.HapticHelper

/**
 * Persistent expressive mini player bar showing active 30-second PEEK audition progress.
 */
@Composable
fun PeekMiniPlayerBar(
    playbackState: PeekPlaybackState,
    onOpenActiveSignal: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val visible = playbackState.activeSlug != null && (playbackState.isPlaying || playbackState.isBuffering || playbackState.progress > 0f)
    val accent = Signal.parseHexColor(playbackState.accentHex, MaterialTheme.colorScheme.primary)

    AnimatedVisibility(
        visible = visible,
        enter = slideInVertically { it },
        exit = slideOutVertically { it },
        modifier = modifier
    ) {
        Surface(
            shape = ChaperoneCompactAsymmShape,
            color = MaterialTheme.colorScheme.surfaceContainerHigh,
            border = BorderStroke(1.dp, accent.copy(alpha = 0.45f)),
            shadowElevation = 8.dp,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp)
                .clickable {
                    playbackState.activeSlug?.let { slug ->
                        HapticHelper.roomOpen(context)
                        onOpenActiveSignal(slug)
                    }
                }
        ) {
            Column {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = if (playbackState.isBuffering) "PEEKING · BUFFERING" else "PEEK · 30S SIGNAL",
                            color = accent,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 1.sp
                        )
                        Text(
                            text = playbackState.activeTrack,
                            color = MaterialTheme.colorScheme.onSurface,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            text = playbackState.activeArtist,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 12.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }

                    Spacer(modifier = Modifier.width(8.dp))

                    if (playbackState.isBuffering) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp),
                            strokeWidth = 2.dp,
                            color = accent
                        )
                    } else {
                        IconButton(
                            onClick = {
                                HapticHelper.click(context)
                                PeekAudioPlayer.togglePlayPause()
                            }
                        ) {
                            Icon(
                                imageVector = if (playbackState.isPlaying) Icons.Rounded.Pause else Icons.Rounded.PlayArrow,
                                contentDescription = if (playbackState.isPlaying) "Pause preview" else "Resume preview",
                                tint = accent
                            )
                        }
                    }

                    IconButton(
                        onClick = {
                            HapticHelper.tick(context)
                            PeekAudioPlayer.stopAndClear()
                        }
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.Close,
                            contentDescription = "Stop preview",
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                LinearProgressIndicator(
                    progress = { playbackState.progress },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(3.dp),
                    color = accent,
                    trackColor = Color.Transparent
                )
            }
        }
    }
}
