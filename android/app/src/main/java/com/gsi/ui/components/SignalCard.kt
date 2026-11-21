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
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
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
import com.gsi.data.GsiRepository
import com.gsi.model.Signal
import com.gsi.ui.theme.ChaperoneAsymmShape
import com.gsi.ui.theme.ChaperoneCompactAsymmShape
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Archive Wall Signal Card featuring Chaperone's asymmetric 28dp/8dp framing,
 * cover-derived tonal border, and SharedTransitionLayout hero hooks.
 */
@OptIn(ExperimentalSharedTransitionApi::class)
@Composable
fun SignalCard(
    signal: Signal,
    sharedTransitionScope: SharedTransitionScope,
    animatedVisibilityScope: AnimatedVisibilityScope,
    onClick: () -> Unit,
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

    with(sharedTransitionScope) {
        TactileCard(
            onClick = onClick,
            shape = ChaperoneAsymmShape,
            backgroundColor = MaterialTheme.colorScheme.surfaceContainer,
            borderColor = signal.primaryColor.copy(alpha = 0.34f),
            borderWidth = 1.dp,
            modifier = modifier
                .fillMaxWidth()
                .sharedBounds(
                    sharedContentState = rememberSharedContentState(key = "card-${signal.slug}"),
                    animatedVisibilityScope = animatedVisibilityScope
                )
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(1f)
                        .clip(ChaperoneCompactAsymmShape)
                        .background(
                            Brush.linearGradient(
                                listOf(
                                    signal.surfaceColor,
                                    signal.primaryColor.copy(alpha = 0.32f)
                                )
                            )
                        )
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
                            modifier = Modifier.fillMaxSize()
                        )
                    }

                    // Subtle accent indicator dot for Radio P53 or unsynced local note
                    if (signal.isP53 || signal.pendingSync) {
                        Row(
                            modifier = Modifier
                                .align(Alignment.TopEnd)
                                .padding(10.dp),
                            horizontalArrangement = Arrangement.spacedBy(5.dp)
                        ) {
                            if (signal.isP53) {
                                Box(
                                    modifier = Modifier
                                        .size(9.dp)
                                        .clip(CircleShape)
                                        .background(Color(0xFFFF58A6))
                                )
                            }
                            if (signal.pendingSync) {
                                Box(
                                    modifier = Modifier
                                        .size(9.dp)
                                        .clip(CircleShape)
                                        .background(Color(0xFF35C9E9))
                                )
                            }
                        }
                    }
                }

                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 11.dp)
                ) {
                    Text(
                        text = signal.track,
                        color = MaterialTheme.colorScheme.onSurface,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = signal.artist,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 13.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    if (signal.album.isNotBlank()) {
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = signal.album,
                            color = signal.primaryColor.copy(alpha = 0.85f),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                }
            }
        }
    }
}
