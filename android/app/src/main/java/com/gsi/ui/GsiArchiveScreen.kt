package com.gsi.ui

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.ExperimentalSharedTransitionApi
import androidx.compose.animation.SharedTransitionLayout
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.CloudSync
import androidx.compose.material.icons.rounded.Search
import androidx.compose.material.icons.rounded.Shuffle
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gsi.audio.PeekAudioPlayer
import com.gsi.data.GsiRepository
import com.gsi.model.Signal
import com.gsi.ui.components.P53HeroCard
import com.gsi.ui.components.PeekMiniPlayerBar
import com.gsi.ui.components.SignalCard
import com.gsi.util.HapticHelper
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

sealed class ChaperoneLaunchAction {
    data object None : ChaperoneLaunchAction()
    data class OpenSignalSlug(val slug: String) : ChaperoneLaunchAction()
    data object OpenActiveP53 : ChaperoneLaunchAction()
    data object OpenRandomSignal : ChaperoneLaunchAction()
    data class OpenCapture(val sharedUrl: String? = null) : ChaperoneLaunchAction()
}

private sealed class ArchiveDestination {
    data object Wall : ArchiveDestination()
    data class Room(val signal: Signal) : ArchiveDestination()
    data class Author(val existing: Signal? = null, val sharedUrl: String? = null) : ArchiveDestination()
}

/**
 * Root Chaperone Android Archive Screen.
 * Orchestrates SharedTransitionLayout hero transitions between the Archive Wall & Song Rooms,
 * persistent filter & scroll state, live Media3 PEEK mini player, Live Authoring,
 * 9:16 Share Card Studio, and LAN Sync & JSON Export.
 */
@OptIn(ExperimentalSharedTransitionApi::class)
@Composable
fun GsiArchiveScreen(
    launchAction: ChaperoneLaunchAction = ChaperoneLaunchAction.None,
    onLaunchActionConsumed: () -> Unit = {}
) {
    val context = LocalContext.current
    val playbackState by PeekAudioPlayer.state.collectAsState()

    var reloadTrigger by remember { mutableIntStateOf(0) }
    var signals by remember { mutableStateOf<List<Signal>>(emptyList()) }
    var activeP53Slug by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(reloadTrigger) {
        val loaded = withContext(Dispatchers.IO) {
            GsiRepository.loadSignals(context) to GsiRepository.loadCurrentP53Slug(context)
        }
        signals = loaded.first
        activeP53Slug = loaded.second
    }

    var destination by remember { mutableStateOf<ArchiveDestination>(ArchiveDestination.Wall) }
    var selectedTag by remember { mutableStateOf<String?>(null) }
    var searchQuery by remember { mutableStateOf("") }
    var showSearch by remember { mutableStateOf(false) }
    var showSyncSheet by remember { mutableStateOf(false) }
    var quickShareSignal by remember { mutableStateOf<Signal?>(null) }

    val gridState = rememberLazyGridState()

    // Handle deep links, App Shortcuts, Glance Widget taps, and ACTION_SEND links
    LaunchedEffect(launchAction, signals, activeP53Slug) {
        if (launchAction == ChaperoneLaunchAction.None) return@LaunchedEffect
        when (launchAction) {
            is ChaperoneLaunchAction.OpenCapture -> {
                destination = ArchiveDestination.Author(existing = null, sharedUrl = launchAction.sharedUrl)
                onLaunchActionConsumed()
            }
            is ChaperoneLaunchAction.OpenSignalSlug -> {
                val match = signals.firstOrNull { it.slug == launchAction.slug }
                if (match != null) {
                    destination = ArchiveDestination.Room(match)
                    onLaunchActionConsumed()
                }
            }
            is ChaperoneLaunchAction.OpenActiveP53 -> {
                val p53 = signals.firstOrNull { it.slug == activeP53Slug } ?: signals.firstOrNull { it.isP53 }
                if (p53 != null) {
                    destination = ArchiveDestination.Room(p53)
                    onLaunchActionConsumed()
                }
            }
            is ChaperoneLaunchAction.OpenRandomSignal -> {
                if (signals.isNotEmpty()) {
                    destination = ArchiveDestination.Room(signals.random())
                    onLaunchActionConsumed()
                }
            }
            ChaperoneLaunchAction.None -> Unit
        }
    }

    val activeP53Signal = remember(signals, activeP53Slug) {
        signals.firstOrNull { it.slug == activeP53Slug } ?: signals.firstOrNull { it.isP53 }
    }
    val pendingSyncCount = remember(signals) { signals.count { it.pendingSync } }

    val filteredSignals = remember(signals, selectedTag, searchQuery) {
        signals.filter { sig ->
            val tagMatch = selectedTag == null ||
                sig.tags.any { it.equals(selectedTag, ignoreCase = true) } ||
                (selectedTag == "p53" && sig.isP53)
            val q = searchQuery.trim().lowercase()
            val queryMatch = q.isEmpty() ||
                sig.track.lowercase().contains(q) ||
                sig.artist.lowercase().contains(q) ||
                sig.album.lowercase().contains(q)
            tagMatch && queryMatch
        }
    }

    SharedTransitionLayout(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        AnimatedContent(
            targetState = destination,
            transitionSpec = {
                fadeIn(animationSpec = tween(220)) togetherWith fadeOut(animationSpec = tween(180))
            },
            label = "chaperoneNav"
        ) { target ->
            when (target) {
                is ArchiveDestination.Wall -> {
                    Box(modifier = Modifier.fillMaxSize()) {
                        LazyVerticalGrid(
                            columns = GridCells.Fixed(2),
                            state = gridState,
                            modifier = Modifier
                                .fillMaxSize()
                                .statusBarsPadding(),
                            contentPadding = PaddingValues(
                                start = 16.dp,
                                end = 16.dp,
                                top = 12.dp,
                                bottom = 148.dp
                            ),
                            horizontalArrangement = Arrangement.spacedBy(12.dp),
                            verticalArrangement = Arrangement.spacedBy(14.dp)
                        ) {
                            // Top Identity Bar
                            item(span = { GridItemSpan(maxLineSpan) }) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column {
                                        Text(
                                            text = "GENOME STABILITY INDUCERS",
                                            fontSize = 10.sp,
                                            fontWeight = FontWeight.ExtraBold,
                                            letterSpacing = 1.4.sp,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                        Text(
                                            text = "Chaperone",
                                            style = MaterialTheme.typography.headlineMedium,
                                            fontWeight = FontWeight.ExtraBold,
                                            color = MaterialTheme.colorScheme.onBackground
                                        )
                                    }

                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        IconButton(
                                            onClick = {
                                                HapticHelper.tick(context)
                                                showSearch = !showSearch
                                                if (!showSearch) searchQuery = ""
                                            }
                                        ) {
                                            Icon(Icons.Rounded.Search, contentDescription = "Search archive")
                                        }

                                        IconButton(
                                            onClick = {
                                                if (signals.isNotEmpty()) {
                                                    HapticHelper.roomOpen(context)
                                                    destination = ArchiveDestination.Room(signals.random())
                                                }
                                            }
                                        ) {
                                            Icon(Icons.Rounded.Shuffle, contentDescription = "Random signal")
                                        }

                                        IconButton(
                                            onClick = {
                                                HapticHelper.tick(context)
                                                showSyncSheet = true
                                            }
                                        ) {
                                            BadgedBox(
                                                badge = {
                                                    if (pendingSyncCount > 0) {
                                                        Badge { Text(pendingSyncCount.toString()) }
                                                    }
                                                }
                                            ) {
                                                Icon(Icons.Rounded.CloudSync, contentDescription = "Sync and Export")
                                            }
                                        }
                                    }
                                }
                            }

                            // Collapsible Search Input
                            if (showSearch) {
                                item(span = { GridItemSpan(maxLineSpan) }) {
                                    OutlinedTextField(
                                        value = searchQuery,
                                        onValueChange = { searchQuery = it },
                                        placeholder = { Text("Filter tracks, artists, albums…") },
                                        singleLine = true,
                                        shape = RoundedCornerShape(16.dp),
                                        modifier = Modifier.fillMaxWidth()
                                    )
                                }
                            }

                            // Active Radio P53 Hero Card
                            if (activeP53Signal != null && selectedTag == null && searchQuery.isBlank()) {
                                item(span = { GridItemSpan(maxLineSpan) }) {
                                    P53HeroCard(
                                        signal = activeP53Signal,
                                        playbackState = playbackState,
                                        sharedTransitionScope = this@SharedTransitionLayout,
                                        animatedVisibilityScope = this@AnimatedContent,
                                        onOpenRoom = { destination = ArchiveDestination.Room(activeP53Signal) },
                                        onTogglePeek = { PeekAudioPlayer.togglePeek(context, activeP53Signal) },
                                        onOpenShareStudio = { quickShareSignal = activeP53Signal }
                                    )
                                }
                            }

                            // Filter Chips Strip
                            item(span = { GridItemSpan(maxLineSpan) }) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .horizontalScroll(rememberScrollState()),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    FilterChip(
                                        selected = selectedTag == null,
                                        onClick = {
                                            HapticHelper.tick(context)
                                            selectedTag = null
                                        },
                                        label = { Text("ALL (${signals.size})") }
                                    )
                                    Signal.ARCHIVE_TAGS.forEach { tag ->
                                        FilterChip(
                                            selected = selectedTag == tag,
                                            onClick = {
                                                HapticHelper.tick(context)
                                                selectedTag = if (selectedTag == tag) null else tag
                                            },
                                            label = { Text(tag.uppercase()) }
                                        )
                                    }
                                }
                            }

                            // Archive Grid Cards
                            items(filteredSignals, key = { it.slug }) { signal ->
                                SignalCard(
                                    signal = signal,
                                    sharedTransitionScope = this@SharedTransitionLayout,
                                    animatedVisibilityScope = this@AnimatedContent,
                                    onClick = { destination = ArchiveDestination.Room(signal) }
                                )
                            }
                        }

                        // Bottom Overlay: Persistent PEEK Mini Player + Capture FAB
                        Column(
                            modifier = Modifier
                                .align(Alignment.BottomCenter)
                                .fillMaxWidth()
                                .navigationBarsPadding(),
                            horizontalAlignment = Alignment.End
                        ) {
                            ExtendedFloatingActionButton(
                                onClick = {
                                    HapticHelper.click(context)
                                    destination = ArchiveDestination.Author()
                                },
                                icon = { Icon(Icons.Rounded.Add, contentDescription = null) },
                                text = { Text("Capture", fontWeight = FontWeight.Bold) },
                                modifier = Modifier.padding(end = 18.dp, bottom = 10.dp)
                            )

                            PeekMiniPlayerBar(
                                playbackState = playbackState,
                                onOpenActiveSignal = { slug ->
                                    signals.firstOrNull { it.slug == slug }?.let {
                                        destination = ArchiveDestination.Room(it)
                                    }
                                }
                            )
                        }
                    }
                }

                is ArchiveDestination.Room -> {
                    val freshSignal = signals.firstOrNull { it.slug == target.signal.slug } ?: target.signal
                    SignalDetailScreen(
                        signal = freshSignal,
                        isActiveP53 = freshSignal.slug == activeP53Slug,
                        playbackState = playbackState,
                        sharedTransitionScope = this@SharedTransitionLayout,
                        animatedVisibilityScope = this@AnimatedContent,
                        onBack = { destination = ArchiveDestination.Wall },
                        onEditSignal = { toEdit ->
                            destination = ArchiveDestination.Author(existing = toEdit)
                        }
                    )
                }

                is ArchiveDestination.Author -> {
                    AuthorSignalScreen(
                        existingSignal = target.existing,
                        initialSharedLink = target.sharedUrl,
                        onSaved = { saved ->
                            reloadTrigger++
                            destination = ArchiveDestination.Room(saved)
                        },
                        onCancel = {
                            destination = if (target.existing != null) {
                                ArchiveDestination.Room(target.existing)
                            } else {
                                ArchiveDestination.Wall
                            }
                        }
                    )
                }
            }
        }
    }

    if (showSyncSheet) {
        SyncExportSheet(
            allSignals = signals,
            activeP53Slug = activeP53Slug,
            onArchiveUpdated = { reloadTrigger++ },
            onDismiss = { showSyncSheet = false }
        )
    }

    quickShareSignal?.let { toShare ->
        ShareCardStudioSheet(
            signal = toShare,
            isActiveP53 = toShare.slug == activeP53Slug,
            onDismiss = { quickShareSignal = null }
        )
    }
}
