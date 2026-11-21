package com.gsi.ui.components

import androidx.compose.animation.AnimatedVisibilityScope
import androidx.compose.animation.ExperimentalSharedTransitionApi
import androidx.compose.animation.SharedTransitionScope
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Pause
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material.icons.rounded.Share
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gsi.audio.PeekPlaybackState
import com.gsi.data.GsiRepository
import com.gsi.model.Signal
import com.gsi.ui.theme.ChaperoneAsymmShape
import com.gsi.ui.theme.ChaperoneCompactAsymmShape
import com.gsi.util.HapticHelper
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Active Radio P53 Hero Transmission Card.
 * Features live Media3 PEEK audio preview driving AudioPulseBar, quick 9:16 Share trigger,
 * and shared-element transition into the active transmission Song Room.
 */
@OptIn(ExperimentalSharedTransitionApi::class)
@Composable
fun P53HeroCard(
    signal: Signal,
    playbackState: PeekPlaybackState,
    sharedTransitionScope: SharedTransitionScope,
    animatedVisibilityScope: AnimatedVisibilityScope,
    onOpenRoom: () -> Unit,
    onTogglePeek: () -> Unit,
    onOpenShareStudio: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val coverBitmap = produceState<ImageBitmap?>(
        initialValue = null,
        key1 = signal.coverFileName,
        key2 = signal.localCoverPath
    ) {
        value = withContext(Dispatchers.IO) {
            GsiRepository.loadCoverBitmap(context, signal.coverFileName, signal.localCoverPath)
        }
    }

    val isThisPlaying = playbackState.activeSlug == signal.slug && playbackState.isPlaying
    val thisProgress = if (playbackState.activeSlug == signal.slug) playbackState.progress else 0f
    val p53Pink = Color(0xFFFF58A6)

    with(sharedTransitionScope) {
        TactileCard(
            onClick = onOpenRoom,
            shape = ChaperoneAsymmShape,
            backgroundColor = MaterialTheme.colorScheme.surfaceContainerHigh,
            borderColor = signal.primaryColor.copy(alpha = 0.55f),
            borderWidth = 1.2.dp,
            modifier = modifier
                .fillMaxWidth()
                .sharedBounds(
                    sharedContentState = rememberSharedContentState(key = "card-${signal.slug}"),
                    animatedVisibilityScope = animatedVisibilityScope
                )
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        Brush.linearGradient(
                            colors = listOf(
                                signal.primaryColor.copy(alpha = 0.16f),
                                p53Pink.copy(alpha = 0.10f),
                                Color.Transparent
                            )
                        )
                    )
                    .padding(18.dp)
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(7.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(p53Pink)
                            )
                            Text(
                                text = "RADIO P53 · ACTIVE TRANSMISSION",
                                color = p53Pink,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.ExtraBold,
                                letterSpacing = 1.2.sp
                            )
                        }

                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            if (!signal.previewUrl.isNullOrBlank()) {
                                FilledTonalIconButton(
                                    onClick = {
                                        HapticHelper.click(context)
                                        onTogglePeek()
                                    },
                                    colors = IconButtonDefaults.filledTonalIconButtonColors(
                                        containerColor = signal.primaryColor.copy(alpha = 0.2f),
                                        contentColor = signal.primaryColor
                                    ),
                                    modifier = Modifier.size(40.dp)
                                ) {
                                    Icon(
                                        imageVector = if (isThisPlaying) Icons.Rounded.Pause else Icons.Rounded.PlayArrow,
                                        contentDescription = if (isThisPlaying) "Pause PEEK preview" else "Play PEEK preview"
                                    )
                                }
                            }
                            FilledTonalIconButton(
                                onClick = {
                                    HapticHelper.tick(context)
                                    onOpenShareStudio()
                                },
                                modifier = Modifier.size(40.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Rounded.Share,
                                    contentDescription = "Open 9:16 Share Studio"
                                )
                            }
                        }
                    }

                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Box(
                            modifier = Modifier
                                .size(86.dp)
                                .clip(ChaperoneCompactAsymmShape)
                                .background(signal.surfaceColor)
                                .sharedElement(
                                    sharedContentState = rememberSharedContentState(key = "cover-${signal.slug}"),
                                    animatedVisibilityScope = animatedVisibilityScope
                                )
                        ) {
                            coverBitmap.value?.let { bmp ->
                                Image(
                                    bitmap = bmp,
                                    contentDescription = "${signal.album} cover",
                                    contentScale = ContentScale.Crop,
                                    modifier = Modifier.size(86.dp)
                                )
                            }
                        }

                        Spacer(modifier = Modifier.width(14.dp))

                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = signal.track,
                                color = MaterialTheme.colorScheme.onSurface,
                                fontSize = 20.sp,
                                fontWeight = FontWeight.ExtraBold,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = signal.artist,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.SemiBold,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                            if (signal.album.isNotBlank()) {
                                Text(
                                    text = signal.album,
                                    color = signal.primaryColor,
                                    fontSize = 12.sp,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                        }
                    }

                    signal.transmissionNote?.takeIf { it.isNotBlank() }?.let { note ->
                        Text(
                            text = "“$note”",
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.88f),
                            fontSize = 14.sp,
                            lineHeight = 20.sp,
                            maxLines = 3,
                            overflow = TextOverflow.Ellipsis
                        )
                    }

                    AudioPulseBar(
                        barColor = signal.primaryColor,
                        isPlaying = isThisPlaying,
                        progress = thisProgress
                    )
                }
            }
        }
    }
}
