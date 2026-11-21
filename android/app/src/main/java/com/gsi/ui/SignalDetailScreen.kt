package com.gsi.ui

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.PredictiveBackHandler
import androidx.compose.animation.AnimatedVisibilityScope
import androidx.compose.animation.ExperimentalSharedTransitionApi
import androidx.compose.animation.SharedTransitionScope
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.Edit
import androidx.compose.material.icons.rounded.OpenInNew
import androidx.compose.material.icons.rounded.Pause
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material.icons.rounded.Share
import androidx.compose.material3.AssistChip
import androidx.compose.material3.ExperimentalMaterial3ExpressiveApi
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FloatingToolbarDefaults
import androidx.compose.material3.HorizontalFloatingToolbar
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gsi.audio.PeekAudioPlayer
import com.gsi.audio.PeekPlaybackState
import com.gsi.data.GsiRepository
import com.gsi.model.Signal
import com.gsi.share.ShareBridge
import com.gsi.ui.components.AudioPulseBar
import com.gsi.ui.theme.ChaperoneAsymmShape
import com.gsi.ui.theme.ChaperoneCompactAsymmShape
import com.gsi.ui.theme.GSITheme
import com.gsi.util.HapticHelper
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Song Room Detail Screen.
 * Harmonizes Material You with the track's cover-derived room atmosphere,
 * supports SharedTransitionLayout hero bounds, PredictiveBackHandler edge-swipe scaling,
 * live Media3 PEEK playback, and an M3 Expressive bottom HorizontalFloatingToolbar.
 */
@OptIn(
    ExperimentalSharedTransitionApi::class,
    ExperimentalMaterial3ExpressiveApi::class,
    ExperimentalLayoutApi::class
)
@Composable
fun SignalDetailScreen(
    signal: Signal,
    isActiveP53: Boolean,
    playbackState: PeekPlaybackState,
    sharedTransitionScope: SharedTransitionScope,
    animatedVisibilityScope: AnimatedVisibilityScope,
    onBack: () -> Unit,
    onEditSignal: (Signal) -> Unit
) {
    val context = LocalContext.current
    var showShareStudio by remember { mutableStateOf(false) }

    var backProgress by remember { mutableFloatStateOf(0f) }
    PredictiveBackHandler { progress ->
        try {
            progress.collect { event ->
                backProgress = event.progress
            }
            onBack()
        } catch (_: CancellationException) {
            backProgress = 0f
        }
    }

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

    GSITheme(roomAccent = signal.primaryColor) {
        with(sharedTransitionScope) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .graphicsLayer {
                        val scale = 1f - (backProgress * 0.08f)
                        scaleX = scale
                        scaleY = scale
                        translationX = backProgress * 36f
                    }
                    .background(MaterialTheme.colorScheme.background)
                    .background(
                        Brush.verticalGradient(
                            colors = listOf(
                                signal.primaryColor.copy(alpha = 0.22f),
                                signal.glowColor.copy(alpha = 0.08f),
                                Color.Transparent
                            )
                        )
                    )
                    .sharedBounds(
                        sharedContentState = rememberSharedContentState(key = "card-${signal.slug}"),
                        animatedVisibilityScope = animatedVisibilityScope
                    )
            ) {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .statusBarsPadding(),
                    contentPadding = PaddingValues(
                        start = 20.dp,
                        end = 20.dp,
                        top = 8.dp,
                        bottom = 128.dp
                    ),
                    verticalArrangement = Arrangement.spacedBy(18.dp)
                ) {
                    // Navigation Header
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            IconButton(
                                onClick = {
                                    HapticHelper.tick(context)
                                    onBack()
                                }
                            ) {
                                Icon(
                                    imageVector = Icons.AutoMirrored.Rounded.ArrowBack,
                                    contentDescription = "Back to Archive"
                                )
                            }

                            Text(
                                text = when {
                                    isActiveP53 -> "RADIO P53 · ACTIVE"
                                    signal.isP53 -> "RADIO P53 · SIGNAL"
                                    signal.pendingSync -> "LOCAL · UNSYNCED"
                                    else -> "CHAPERONE · ROOM"
                                },
                                fontSize = 11.sp,
                                fontWeight = FontWeight.ExtraBold,
                                letterSpacing = 1.2.sp,
                                color = MaterialTheme.colorScheme.primary
                            )

                            IconButton(
                                onClick = {
                                    HapticHelper.tick(context)
                                    showShareStudio = true
                                }
                            ) {
                                Icon(
                                    imageVector = Icons.Rounded.Share,
                                    contentDescription = "Share 9:16 Story Card"
                                )
                            }
                        }
                    }

                    // Cover Artwork + Identity Hero
                    item {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Surface(
                                shape = ChaperoneAsymmShape,
                                border = BorderStroke(1.5.dp, signal.primaryColor.copy(alpha = 0.5f)),
                                shadowElevation = 18.dp,
                                modifier = Modifier
                                    .fillMaxWidth(0.76f)
                                    .aspectRatio(1f)
                                    .sharedElement(
                                        sharedContentState = rememberSharedContentState(key = "cover-${signal.slug}"),
                                        animatedVisibilityScope = animatedVisibilityScope
                                    )
                            ) {
                                val bmp = coverBitmap.value
                                if (bmp != null) {
                                    Image(
                                        bitmap = bmp,
                                        contentDescription = "${signal.album} cover",
                                        contentScale = ContentScale.Crop,
                                        modifier = Modifier.fillMaxSize()
                                    )
                                } else {
                                    Box(
                                        modifier = Modifier
                                            .fillMaxSize()
                                            .background(signal.surfaceColor)
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(18.dp))

                            Text(
                                text = signal.track,
                                style = MaterialTheme.typography.headlineMedium,
                                fontWeight = FontWeight.ExtraBold,
                                color = MaterialTheme.colorScheme.onBackground
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = signal.artist,
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            if (signal.album.isNotBlank()) {
                                Spacer(modifier = Modifier.height(2.dp))
                                Text(
                                    text = listOfNotNull(signal.album, signal.releaseYear).joinToString(" · "),
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.primary
                                )
                            }
                        }
                    }

                    // Live PEEK Waveform & Streaming Links
                    item {
                        Surface(
                            shape = ChaperoneCompactAsymmShape,
                            color = MaterialTheme.colorScheme.surfaceContainer,
                            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                        ) {
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(16.dp),
                                verticalArrangement = Arrangement.spacedBy(12.dp)
                            ) {
                                if (!signal.previewUrl.isNullOrBlank()) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                                    ) {
                                        FilledTonalButton(
                                            onClick = {
                                                HapticHelper.click(context)
                                                PeekAudioPlayer.togglePeek(context, signal)
                                            }
                                        ) {
                                            Icon(
                                                imageVector = if (isThisPlaying) Icons.Rounded.Pause else Icons.Rounded.PlayArrow,
                                                contentDescription = null,
                                                modifier = Modifier.size(18.dp)
                                            )
                                            Spacer(modifier = Modifier.width(6.dp))
                                            Text(if (isThisPlaying) "PEEKING" else "PEEK 30s", fontWeight = FontWeight.Bold)
                                        }
                                        AudioPulseBar(
                                            barColor = signal.primaryColor,
                                            isPlaying = isThisPlaying,
                                            progress = thisProgress,
                                            modifier = Modifier.weight(1f)
                                        )
                                    }
                                }

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    signal.appleUrl?.let { url ->
                                        OutlinedButton(
                                            onClick = {
                                                HapticHelper.tick(context)
                                                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                                            },
                                            modifier = Modifier.weight(1f)
                                        ) {
                                            Text("Apple Music", maxLines = 1)
                                        }
                                    }
                                    signal.spotifyUrl?.let { url ->
                                        OutlinedButton(
                                            onClick = {
                                                HapticHelper.tick(context)
                                                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                                            },
                                            modifier = Modifier.weight(1f)
                                        ) {
                                            Text("Spotify", maxLines = 1)
                                        }
                                    }
                                    OutlinedButton(
                                        onClick = {
                                            HapticHelper.tick(context)
                                            val webUrl = ShareBridge.canonicalSignalUrl(context, signal)
                                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(webUrl)))
                                        }
                                    ) {
                                        Icon(Icons.Rounded.OpenInNew, contentDescription = "Open web room", modifier = Modifier.size(16.dp))
                                    }
                                }
                            }
                        }
                    }

                    // Radio P53 Transmission Note
                    signal.transmissionNote?.takeIf { it.isNotBlank() }?.let { note ->
                        item {
                            Surface(
                                shape = ChaperoneCompactAsymmShape,
                                color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.48f),
                                border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.4f))
                            ) {
                                Column(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(16.dp),
                                    verticalArrangement = Arrangement.spacedBy(6.dp)
                                ) {
                                    Text(
                                        text = "RADIO P53 TRANSMISSION NOTE",
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.ExtraBold,
                                        letterSpacing = 1.sp,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                    Text(
                                        text = "“$note”",
                                        style = MaterialTheme.typography.bodyLarge,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                }
                            }
                        }
                    }

                    // Tags
                    if (signal.tags.isNotEmpty()) {
                        item {
                            FlowRow(
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                verticalArrangement = Arrangement.spacedBy(4.dp)
                            ) {
                                signal.tags.forEach { tag ->
                                    AssistChip(
                                        onClick = {},
                                        label = { Text(tag.uppercase(), fontSize = 11.sp, fontWeight = FontWeight.Bold) }
                                    )
                                }
                            }
                        }
                    }

                    // Chaperone Authored Review Sections
                    if (signal.reviewSections.isNotEmpty()) {
                        items(signal.reviewSections, key = { it.title }) { section ->
                            Surface(
                                shape = ChaperoneAsymmShape,
                                color = MaterialTheme.colorScheme.surfaceContainer,
                                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                            ) {
                                Column(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(18.dp),
                                    verticalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    Text(
                                        text = section.title,
                                        style = MaterialTheme.typography.titleMedium,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                    Text(
                                        text = section.content.replace(Regex("\\*\\*(.*?)\\*\\*"), "$1"),
                                        style = MaterialTheme.typography.bodyLarge,
                                        lineHeight = 24.sp,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                }
                            }
                        }
                    } else {
                        item {
                            Surface(
                                shape = ChaperoneCompactAsymmShape,
                                color = MaterialTheme.colorScheme.surfaceContainer,
                                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                            ) {
                                Column(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(18.dp),
                                    verticalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    Text(
                                        text = "No written listening notes yet",
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.Bold
                                    )
                                    Text(
                                        text = "Tap Edit in the floating toolbar below to write Charge, Sonic Attraction, Lore, or a P53 note right from your phone.",
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                        }
                    }
                }

                // Material 3 Expressive Floating Toolbar anchored in the natural bottom thumb zone
                HorizontalFloatingToolbar(
                    expanded = true,
                    colors = FloatingToolbarDefaults.vibrantFloatingToolbarColors(),
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .navigationBarsPadding()
                        .padding(bottom = 16.dp)
                ) {
                    if (!signal.previewUrl.isNullOrBlank()) {
                        IconButton(
                            onClick = {
                                HapticHelper.click(context)
                                PeekAudioPlayer.togglePeek(context, signal)
                            }
                        ) {
                            Icon(
                                imageVector = if (isThisPlaying) Icons.Rounded.Pause else Icons.Rounded.PlayArrow,
                                contentDescription = if (isThisPlaying) "Pause PEEK" else "Play PEEK"
                            )
                        }
                    }

                    IconButton(
                        onClick = {
                            HapticHelper.click(context)
                            showShareStudio = true
                        }
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.Share,
                            contentDescription = "9:16 Share Card Studio"
                        )
                    }

                    IconButton(
                        onClick = {
                            HapticHelper.tick(context)
                            onEditSignal(signal)
                        }
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.Edit,
                            contentDescription = "Edit notes"
                        )
                    }

                    IconButton(
                        onClick = {
                            HapticHelper.tick(context)
                            val target = signal.appleUrl
                                ?: signal.spotifyUrl
                                ?: ShareBridge.canonicalSignalUrl(context, signal)
                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(target)))
                        }
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.OpenInNew,
                            contentDescription = "Open external link"
                        )
                    }
                }
            }
        }

        if (showShareStudio) {
            ShareCardStudioSheet(
                signal = signal,
                isActiveP53 = isActiveP53,
                onDismiss = { showShareStudio = false }
            )
        }
    }
}
