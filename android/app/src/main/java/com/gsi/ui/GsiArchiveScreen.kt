package com.gsi.ui

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.togetherWith
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gsi.data.GsiRepository
import com.gsi.model.Signal
import com.gsi.ui.components.P53HeroCard
import com.gsi.ui.components.SignalCard
import com.gsi.ui.theme.GsiBorder
import com.gsi.ui.theme.GsiP53Amber
import com.gsi.ui.theme.GsiSurface
import com.gsi.ui.theme.GsiSurfaceElevated
import com.gsi.ui.theme.GsiTextMuted
import com.gsi.ui.theme.GsiTextPrimary
import com.gsi.ui.theme.GsiTextSecondary
import com.gsi.ui.theme.GsiVoid
import com.gsi.util.HapticHelper
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Authentic GSI Archive Wall & Listening Room.
 * 
 * Preserves GSI's personal language, authentic section names,
 * filter taxonomy, tactile spring haptics, and reactive ambient lighting.
 */
@Composable
fun GsiArchiveScreen() {
    val context = LocalContext.current
    var signals by remember { mutableStateOf<List<Signal>>(emptyList()) }
    var selectedSignal by remember { mutableStateOf<Signal?>(null) }
    var currentTransmission by remember { mutableStateOf<Signal?>(null) }
    var selectedFilter by remember { mutableStateOf("All") }
    var coverBitmaps by remember { mutableStateOf<Map<String, ImageBitmap>>(emptyMap()) }
    val archiveListState = rememberLazyListState()

    BackHandler(enabled = selectedSignal != null) { selectedSignal = null }

    // Real GSI Filter Taxonomy
    val filters = remember {
        listOf("All", "Personal", "Bassline", "Ulaş's Selection", "Dreamy", "Bite", "POP", "Distortion", "P53")
    }

    // Load data and covers from assets
    LaunchedEffect(Unit) {
        withContext(Dispatchers.IO) {
            val loadedSignals = GsiRepository.loadSignals(context)
            val currentSlug = GsiRepository.loadCurrentP53Slug(context)
            val p53 = loadedSignals.find { it.slug == currentSlug }

            val bitmaps = mutableMapOf<String, ImageBitmap>()
            for (sig in loadedSignals) {
                val bmp = GsiRepository.loadCoverBitmap(context, sig.coverFileName)
                if (bmp != null) {
                    bitmaps[sig.coverFileName] = bmp
                }
            }

            withContext(Dispatchers.Main) {
                signals = loadedSignals
                currentTransmission = p53
                coverBitmaps = bitmaps
            }
        }
    }

    // Filtered signals list
    val filteredSignals = remember(signals, selectedFilter) {
        if (selectedFilter == "All") {
            signals
        } else {
            val key = when (selectedFilter) {
                "Ulaş's Selection" -> "ulas"
                else -> selectedFilter.lowercase()
            }
            signals.filter { it.tags.any { tag -> tag.equals(key, ignoreCase = true) } }
        }
    }

    // Dynamic ambient back-glow derived from active track
    val currentGlowColor = currentTransmission?.glowColor ?: GsiP53Amber
    val animatedAmbientColor by animateColorAsState(
        targetValue = currentGlowColor.copy(alpha = 0.16f),
        animationSpec = tween(durationMillis = 800),
        label = "ambientGlowTransition"
    )

    AnimatedContent(
        targetState = selectedSignal,
        transitionSpec = {
            (fadeIn(tween(180)) + scaleIn(
                initialScale = 0.96f,
                animationSpec = spring(
                    stiffness = Spring.StiffnessMediumLow,
                    dampingRatio = Spring.DampingRatioLowBouncy
                )
            )) togetherWith fadeOut(tween(120))
        },
        label = "archive and song"
    ) { openSignal ->
        if (openSignal != null) {
            SignalDetailScreen(
                signal = openSignal,
                cover = coverBitmaps[openSignal.coverFileName],
                onBack = { selectedSignal = null }
            )
        } else {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(GsiVoid)
    ) {
        // Ambient Radial Gradient behind top section
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(460.dp)
                .background(
                    Brush.verticalGradient(
                        colors = listOf(
                            animatedAmbientColor,
                            Color.Transparent
                        )
                    )
                )
        )

        val statusBarPadding = WindowInsets.statusBars.asPaddingValues()

        LazyColumn(
            state = archiveListState,
            modifier = Modifier
                .fillMaxSize()
                .navigationBarsPadding(),
            contentPadding = PaddingValues(
                start = 18.dp,
                end = 18.dp,
                top = statusBarPadding.calculateTopPadding() + 10.dp,
                bottom = 48.dp
            ),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 1. Header: Authentic GSI Identity
            item {
                Column(modifier = Modifier.padding(bottom = 4.dp)) {
                    Text(
                        text = "GSI",
                        style = androidx.compose.material3.MaterialTheme.typography.headlineLarge.copy(
                            fontWeight = FontWeight.Black,
                            fontSize = 32.sp,
                            letterSpacing = (-1.0).sp,
                            color = GsiTextPrimary
                        )
                    )

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = "Music is the one non-negotiable no matter how I am to feel. Nothing is critically acclaimed, everything is personal.",
                        style = androidx.compose.material3.MaterialTheme.typography.bodyMedium.copy(
                            color = GsiTextSecondary,
                            lineHeight = 18.sp,
                            fontSize = 12.sp
                        )
                    )
                }
            }

            // 2. Active Radio P53 Shrine Hero Card
            currentTransmission?.let { activeSig ->
                item {
                    val cover = coverBitmaps[activeSig.coverFileName]
                    P53HeroCard(
                        signal = activeSig,
                        coverBitmap = cover,
                        onCardClick = { selectedSignal = activeSig }
                    )
                }
            }

            // 3. Real GSI Filter Bar
            item {
                Spacer(modifier = Modifier.height(4.dp))
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(vertical = 4.dp)
                ) {
                    items(filters) { filter ->
                        val isFilterActive = (filter == selectedFilter)
                        val filterBg = if (isFilterActive) GsiSurfaceElevated else Color.Transparent
                        val filterBorder = if (isFilterActive) currentGlowColor else GsiBorder
                        val filterTextColor = if (isFilterActive) GsiTextPrimary else GsiTextSecondary

                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(20.dp))
                                .background(filterBg)
                                .border(1.dp, filterBorder, RoundedCornerShape(20.dp))
                                .clickable {
                                    HapticHelper.tick(context)
                                    selectedFilter = filter
                                }
                                .padding(horizontal = 14.dp, vertical = 7.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = filter,
                                style = androidx.compose.material3.MaterialTheme.typography.labelSmall.copy(
                                    color = filterTextColor,
                                    fontWeight = if (isFilterActive) FontWeight.Bold else FontWeight.Normal,
                                    fontSize = 11.sp
                                )
                            )
                        }
                    }
                }
            }

            // 4. Section Title: Clean & Authentic
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = if (selectedFilter == "All") "Archive" else selectedFilter,
                        style = androidx.compose.material3.MaterialTheme.typography.titleMedium.copy(
                            fontWeight = FontWeight.Bold,
                            color = GsiTextPrimary
                        )
                    )
                    Text(
                        text = "${filteredSignals.size} tracks",
                        style = androidx.compose.material3.MaterialTheme.typography.labelSmall.copy(
                            color = GsiTextMuted
                        )
                    )
                }
            }

            // 5. Signals Stream
            items(filteredSignals, key = { it.id }) { sig ->
                val cover = coverBitmaps[sig.coverFileName]
                SignalCard(
                    signal = sig,
                    coverBitmap = cover,
                    isSelected = false,
                    onClick = {
                        selectedSignal = sig
                    }
                )
            }
        }
    }
        }
    }
}
