package com.gsi.ui

import androidx.activity.compose.PredictiveBackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material.icons.rounded.CloudUpload
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gsi.data.GsiRepository
import com.gsi.data.LanSyncClient
import com.gsi.data.LocalSignalStore
import com.gsi.model.ReviewSection
import com.gsi.model.Signal
import com.gsi.ui.theme.ChaperoneCompactAsymmShape
import com.gsi.util.HapticHelper
import com.gsi.widget.P53GlanceWidget
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

/**
 * Native Live Authoring & Share-to-Chaperone capture screen.
 * Supports pasting or receiving an Apple Music / Spotify link, fetching track metadata & cover art,
 * selecting archive tags & Radio P53 transmission settings, and writing any of Chaperone's 7 sections.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun AuthorSignalScreen(
    existingSignal: Signal? = null,
    initialSharedLink: String? = null,
    onSaved: (Signal) -> Unit,
    onCancel: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var backProgress by remember { mutableFloatStateOf(0f) }
    PredictiveBackHandler { progress ->
        try {
            progress.collect { event ->
                backProgress = event.progress
            }
            onCancel()
        } catch (_: CancellationException) {
            backProgress = 0f
        }
    }

    var sourceLink by remember {
        mutableStateOf(
            initialSharedLink
                ?: existingSignal?.appleUrl
                ?: existingSignal?.spotifyUrl
                ?: ""
        )
    }
    var track by remember { mutableStateOf(existingSignal?.track ?: "") }
    var artist by remember { mutableStateOf(existingSignal?.artist ?: "") }
    var album by remember { mutableStateOf(existingSignal?.album ?: "") }
    var appleUrl by remember { mutableStateOf(existingSignal?.appleUrl ?: "") }
    var spotifyUrl by remember { mutableStateOf(existingSignal?.spotifyUrl ?: "") }
    var previewUrl by remember { mutableStateOf(existingSignal?.previewUrl ?: "") }
    var releaseYear by remember { mutableStateOf(existingSignal?.releaseYear ?: "") }
    var pendingCoverUrl by remember { mutableStateOf("") }
    var localCoverPath by remember { mutableStateOf(existingSignal?.localCoverPath) }
    var accentHex by remember { mutableStateOf(existingSignal?.primaryHex ?: "#FF65AD") }

    val selectedTags = remember {
        mutableStateMapOf<String, Boolean>().apply {
            Signal.ARCHIVE_TAGS.forEach { tag ->
                put(tag, existingSignal?.tags?.any { it.equals(tag, ignoreCase = true) } == true)
            }
        }
    }

    var isP53 by remember { mutableStateOf(existingSignal?.isP53 == true) }
    var makeActiveP53 by remember { mutableStateOf(existingSignal?.makeActiveP53 == true) }
    var transmissionNote by remember { mutableStateOf(existingSignal?.transmissionNote ?: "") }

    val sectionTexts = remember {
        mutableStateMapOf<String, String>().apply {
            Signal.CHAPERONE_SECTIONS.forEach { title ->
                val existing = existingSignal?.reviewSections?.firstOrNull {
                    it.title.equals(title, ignoreCase = true)
                }?.content ?: ""
                put(title, existing)
            }
        }
    }
    var activeSectionTab by remember { mutableStateOf(Signal.CHAPERONE_SECTIONS.first()) }

    var isLookingUp by remember { mutableStateOf(false) }
    var isSaving by remember { mutableStateOf(false) }
    var statusMessage by remember { mutableStateOf("") }

    fun triggerMetadataLookup(urlToFetch: String) {
        if (urlToFetch.isBlank()) return
        scope.launch {
            isLookingUp = true
            statusMessage = "Looking up track metadata…"
            val res = LanSyncClient.lookupLink(context, urlToFetch)
            res.onSuccess { meta ->
                if (meta.track.isNotBlank()) track = meta.track
                if (meta.artist.isNotBlank()) artist = meta.artist
                if (meta.album.isNotBlank()) album = meta.album
                if (meta.appleUrl.isNotBlank()) appleUrl = meta.appleUrl
                if (meta.spotifyUrl.isNotBlank()) spotifyUrl = meta.spotifyUrl
                if (meta.previewUrl.isNotBlank()) previewUrl = meta.previewUrl
                if (meta.releaseYear.isNotBlank()) releaseYear = meta.releaseYear
                if (meta.coverUrl.isNotBlank()) pendingCoverUrl = meta.coverUrl
                HapticHelper.confirmSuccess(context)
                statusMessage = "Loaded ${meta.track} — ${meta.artist}"
            }.onFailure { err ->
                statusMessage = err.message ?: "Couldn't resolve metadata; you can fill fields manually."
            }
            isLookingUp = false
        }
    }

    LaunchedEffect(initialSharedLink) {
        if (!initialSharedLink.isNullOrBlank() && existingSignal == null) {
            triggerMetadataLookup(initialSharedLink)
        }
    }

    Surface(
        color = MaterialTheme.colorScheme.background,
        modifier = Modifier
            .fillMaxSize()
            .graphicsLayer {
                val scale = 1f - (backProgress * 0.06f)
                scaleX = scale
                scaleY = scale
                translationX = backProgress * 28f
            }
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
                .imePadding()
        ) {
            // Top Bar
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                IconButton(onClick = {
                    HapticHelper.tick(context)
                    onCancel()
                }) {
                    Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = "Close editor")
                }

                Column(modifier = Modifier.weight(1f).padding(horizontal = 8.dp)) {
                    Text(
                        text = if (existingSignal != null) "EDIT SIGNAL" else "LIVE AUTHORING",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.2.sp,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Text(
                        text = if (existingSignal != null) existingSignal.track else "Capture to Chaperone",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                }

                Button(
                    onClick = {
                        val cleanTrack = track.trim()
                        val cleanArtist = artist.trim()
                        if (cleanTrack.isBlank() || cleanArtist.isBlank()) {
                            statusMessage = "Track title and artist are required."
                            return@Button
                        }
                        scope.launch {
                            isSaving = true
                            val slug = existingSignal?.slug ?: Signal.slugify("$cleanArtist-$cleanTrack")
                            var savedCover = localCoverPath
                            if (pendingCoverUrl.isNotBlank()) {
                                savedCover = LanSyncClient.downloadCoverToLocal(context, slug, pendingCoverUrl) ?: savedCover
                            }
                            val tags = selectedTags.filterValues { it }.keys.toMutableList()
                            if (isP53 && !tags.contains("p53")) tags.add("p53")
                            val sections = Signal.CHAPERONE_SECTIONS.mapNotNull { secTitle ->
                                val body = sectionTexts[secTitle]?.trim().orEmpty()
                                if (body.isNotEmpty()) ReviewSection(secTitle, body) else null
                            }

                            val signal = Signal(
                                id = existingSignal?.id ?: "local-$slug",
                                slug = slug,
                                artist = cleanArtist,
                                track = cleanTrack,
                                album = album.trim(),
                                tags = tags,
                                coverFileName = existingSignal?.coverFileName ?: "$slug.jpg",
                                primaryHex = accentHex.ifBlank { "#FF65AD" },
                                surfaceHex = existingSignal?.surfaceHex ?: "#16121C",
                                glowHex = existingSignal?.glowHex ?: accentHex.ifBlank { "#FF65AD" },
                                transmissionNote = transmissionNote.trim().takeIf { it.isNotEmpty() },
                                spotifyUrl = spotifyUrl.trim().takeIf { it.isNotEmpty() },
                                appleUrl = appleUrl.trim().takeIf { it.isNotEmpty() },
                                previewUrl = previewUrl.trim().takeIf { it.isNotEmpty() },
                                releaseYear = releaseYear.trim().takeIf { it.isNotEmpty() },
                                websitePath = existingSignal?.websitePath,
                                isP53 = isP53,
                                reviewSections = sections,
                                localCoverPath = savedCover,
                                isLocalOnly = existingSignal == null || existingSignal.isLocalOnly,
                                pendingSync = true,
                                makeActiveP53 = isP53 && makeActiveP53,
                                updatedAt = System.currentTimeMillis()
                            )

                            LocalSignalStore.upsertSignal(context, signal)
                            GsiRepository.invalidateCache()
                            P53GlanceWidget.refreshAll(context)
                            HapticHelper.confirmSuccess(context)
                            isSaving = false
                            onSaved(signal)
                        }
                    },
                    enabled = !isSaving
                ) {
                    if (isSaving) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                    } else {
                        Icon(Icons.Rounded.Check, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Save")
                    }
                }
            }

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp, vertical = 8.dp)
                    .padding(bottom = 32.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // 1. Link Lookup Card
                Surface(
                    shape = ChaperoneCompactAsymmShape,
                    color = MaterialTheme.colorScheme.surfaceContainer,
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                ) {
                    Column(
                        modifier = Modifier.padding(14.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Text(
                            text = "APPLE MUSIC OR SPOTIFY LINK",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 1.sp,
                            color = MaterialTheme.colorScheme.primary
                        )
                        OutlinedTextField(
                            value = sourceLink,
                            onValueChange = { sourceLink = it },
                            placeholder = { Text("https://music.apple.com/… or open.spotify.com/…") },
                            singleLine = true,
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        )
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            FilledTonalButton(
                                onClick = {
                                    HapticHelper.click(context)
                                    triggerMetadataLookup(sourceLink)
                                },
                                enabled = sourceLink.isNotBlank() && !isLookingUp
                            ) {
                                if (isLookingUp) {
                                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("Fetching…")
                                } else {
                                    Icon(Icons.Rounded.AutoAwesome, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Auto-Fill Track & Cover")
                                }
                            }
                            if (previewUrl.isNotBlank()) {
                                Text(
                                    text = "30s PEEK ready",
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.primary,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }
                        if (statusMessage.isNotBlank()) {
                            Text(
                                text = statusMessage,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }

                // 2. Core Track Metadata
                OutlinedTextField(
                    value = track,
                    onValueChange = { track = it },
                    label = { Text("Track Title") },
                    singleLine = true,
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = artist,
                    onValueChange = { artist = it },
                    label = { Text("Artist") },
                    singleLine = true,
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = album,
                    onValueChange = { album = it },
                    label = { Text("Album") },
                    singleLine = true,
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.fillMaxWidth()
                )

                // 3. Archive Filter Tags
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = "ARCHIVE TAGS",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Signal.ARCHIVE_TAGS.forEach { tag ->
                            val isSelected = selectedTags[tag] == true
                            FilterChip(
                                selected = isSelected,
                                onClick = {
                                    HapticHelper.tick(context)
                                    val next = !isSelected
                                    selectedTags[tag] = next
                                    if (tag == "p53") isP53 = next
                                },
                                label = { Text(tag.uppercase()) }
                            )
                        }
                    }
                }

                // 4. Radio P53 Transmission Controls
                Surface(
                    shape = ChaperoneCompactAsymmShape,
                    color = MaterialTheme.colorScheme.surfaceContainer,
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                ) {
                    Column(
                        modifier = Modifier.padding(14.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text("Radio P53 Transmission", fontWeight = FontWeight.Bold)
                                Text(
                                    "Include this signal in Radio P53 & Home Widget",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            Switch(
                                checked = isP53,
                                onCheckedChange = {
                                    HapticHelper.tick(context)
                                    isP53 = it
                                    selectedTags["p53"] = it
                                }
                            )
                        }

                        if (isP53) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text("Set as Active P53 Signal", style = MaterialTheme.typography.bodyMedium)
                                Switch(
                                    checked = makeActiveP53,
                                    onCheckedChange = {
                                        HapticHelper.tick(context)
                                        makeActiveP53 = it
                                    }
                                )
                            }

                            OutlinedTextField(
                                value = transmissionNote,
                                onValueChange = { transmissionNote = it },
                                label = { Text("Transmission Note (featured on P53 & 9:16 card)") },
                                minLines = 2,
                                maxLines = 4,
                                shape = RoundedCornerShape(12.dp),
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }
                }

                // 5. Chaperone 7-Section Writing Studio
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = "LISTENING NOTES (7 CHAPERONE SECTIONS)",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp,
                        color = MaterialTheme.colorScheme.primary
                    )

                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Signal.CHAPERONE_SECTIONS.forEach { sec ->
                            val hasContent = !sectionTexts[sec].isNullOrBlank()
                            FilterChip(
                                selected = activeSectionTab == sec,
                                onClick = {
                                    HapticHelper.tick(context)
                                    activeSectionTab = sec
                                },
                                label = {
                                    Text(if (hasContent) "$sec •" else sec)
                                }
                            )
                        }
                    }

                    OutlinedTextField(
                        value = sectionTexts[activeSectionTab] ?: "",
                        onValueChange = { sectionTexts[activeSectionTab] = it },
                        label = { Text(activeSectionTab) },
                        placeholder = { Text("Write what belongs in $activeSectionTab…") },
                        minLines = 5,
                        maxLines = 12,
                        shape = RoundedCornerShape(16.dp),
                        modifier = Modifier.fillMaxWidth()
                    )
                }

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        Icons.Rounded.CloudUpload,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(16.dp)
                    )
                    Text(
                        text = "Saved immediately to on-device archive. Push to your computer anytime via Sync & Export.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}
