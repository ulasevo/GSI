package com.gsi.ui

import android.graphics.Bitmap
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.ContentCopy
import androidx.compose.material.icons.rounded.Download
import androidx.compose.material.icons.rounded.Link
import androidx.compose.material.icons.rounded.Share
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gsi.model.Signal
import com.gsi.share.ShareBridge
import com.gsi.share.StoryCardConfig
import com.gsi.share.StoryCardRenderer
import com.gsi.share.StorySurfaceMode
import com.gsi.ui.theme.ChaperoneCompactAsymmShape
import com.gsi.util.HapticHelper
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private data class QuoteOption(
    val label: String,
    val text: String
)

/**
 * Interactive 9:16 Story Card Studio Bottom Sheet for Android.
 * Features live 9:16 preview, Archival Paper vs. Dark Room surface toggle,
 * section quote picker + custom note editor, direct Image-to-Clipboard copy,
 * and native Pixel Sharesheet / Quick Share handoff.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShareCardStudioSheet(
    signal: Signal,
    isActiveP53: Boolean,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    val quoteOptions = remember(signal) {
        buildList {
            signal.transmissionNote?.takeIf { it.isNotBlank() }?.let {
                add(QuoteOption("Transmission Note", it))
            }
            signal.reviewSections.forEach { sec ->
                val clean = sec.content.replace(Regex("\\*\\*(.*?)\\*\\*"), "$1").trim()
                if (clean.isNotEmpty()) {
                    val snippet = if (clean.length > 210) clean.take(207).trimEnd() + "…" else clean
                    add(QuoteOption(sec.title, snippet))
                }
            }
            add(QuoteOption("No quote", ""))
        }
    }

    var surfaceMode by remember(signal.slug) {
        mutableStateOf(if (signal.isP53) StorySurfaceMode.PAPER else StorySurfaceMode.DARK)
    }
    var selectedChipIndex by remember(signal.slug) { mutableStateOf(0) }
    var quoteLabel by remember(signal.slug) {
        mutableStateOf(quoteOptions.firstOrNull()?.takeIf { it.text.isNotEmpty() }?.label ?: "")
    }
    var quoteText by remember(signal.slug) {
        mutableStateOf(quoteOptions.firstOrNull()?.text ?: "")
    }
    var previewBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var isRendering by remember { mutableStateOf(true) }
    var statusMessage by remember { mutableStateOf("") }

    val currentConfig = StoryCardConfig(
        mode = surfaceMode,
        quoteText = quoteText,
        quoteLabel = if (quoteLabel == "Transmission Note") "" else quoteLabel,
        isActiveP53 = isActiveP53
    )

    LaunchedEffect(signal.slug, surfaceMode, quoteText, quoteLabel) {
        isRendering = true
        val bmp = withContext(Dispatchers.Default) {
            StoryCardRenderer.renderBitmap(context, signal, currentConfig)
        }
        previewBitmap = bmp
        isRendering = false
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = MaterialTheme.colorScheme.surfaceContainerLow
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .navigationBarsPadding()
                .padding(horizontal = 20.dp, vertical = 4.dp)
                .padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Column {
                Text(
                    text = if (signal.isP53) "RADIO P53 · 9:16 STUDIO" else "CHAPERONE · 9:16 STUDIO",
                    color = signal.primaryColor,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.2.sp
                )
                Text(
                    text = "Share Story Card",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }

            // Live 9:16 Card Preview
            Box(
                modifier = Modifier.fillMaxWidth(),
                contentAlignment = Alignment.Center
            ) {
                Surface(
                    shape = ChaperoneCompactAsymmShape,
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    shadowElevation = 10.dp,
                    modifier = Modifier
                        .width(196.dp)
                        .aspectRatio(9f / 16f)
                ) {
                    val bmp = previewBitmap
                    if (bmp != null) {
                        Image(
                            bitmap = bmp.asImageBitmap(),
                            contentDescription = "9:16 story card preview for ${signal.track}",
                            contentScale = ContentScale.Fit,
                            modifier = Modifier.clip(ChaperoneCompactAsymmShape)
                        )
                    } else {
                        Box(contentAlignment = Alignment.Center) {
                            CircularProgressIndicator(modifier = Modifier.size(28.dp))
                        }
                    }
                }
            }

            // Surface Mode Segmented Control
            SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
                SegmentedButton(
                    selected = surfaceMode == StorySurfaceMode.DARK,
                    onClick = {
                        HapticHelper.tick(context)
                        surfaceMode = StorySurfaceMode.DARK
                    },
                    shape = SegmentedButtonDefaults.itemShape(index = 0, count = 2)
                ) {
                    Text("Dark Room")
                }
                SegmentedButton(
                    selected = surfaceMode == StorySurfaceMode.PAPER,
                    onClick = {
                        HapticHelper.tick(context)
                        surfaceMode = StorySurfaceMode.PAPER
                    },
                    shape = SegmentedButtonDefaults.itemShape(index = 1, count = 2)
                ) {
                    Text("Archival Paper")
                }
            }

            // Excerpt Source Chips
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    text = "EXCERPT ON CARD",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    quoteOptions.forEachIndexed { idx, opt ->
                        FilterChip(
                            selected = selectedChipIndex == idx,
                            onClick = {
                                HapticHelper.tick(context)
                                selectedChipIndex = idx
                                quoteText = opt.text
                                quoteLabel = if (opt.text.isNotEmpty()) opt.label else ""
                            },
                            label = { Text(opt.label) }
                        )
                    }
                }
                OutlinedTextField(
                    value = quoteText,
                    onValueChange = { quoteText = it.take(300) },
                    label = { Text("Custom line or excerpt") },
                    minLines = 2,
                    maxLines = 4,
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.fillMaxWidth()
                )
            }

            // Primary Native Handoff Buttons (48dp+ touch targets)
            Button(
                onClick = {
                    scope.launch {
                        HapticHelper.click(context)
                        statusMessage = "Preparing Quick Share…"
                        val file = withContext(Dispatchers.IO) {
                            StoryCardRenderer.renderToCacheFile(context, signal, currentConfig)
                        }
                        ShareBridge.launchRichShareSheet(context, signal, file)
                        statusMessage = "Opened Android Sharesheet / Quick Share"
                    }
                },
                enabled = !isRendering,
                colors = ButtonDefaults.buttonColors(containerColor = signal.primaryColor),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp)
            ) {
                Icon(Icons.Rounded.Share, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("Quick Share / Sharesheet", fontWeight = FontWeight.Bold)
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                FilledTonalButton(
                    onClick = {
                        scope.launch {
                            val file = withContext(Dispatchers.IO) {
                                StoryCardRenderer.renderToCacheFile(context, signal, currentConfig)
                            }
                            val copied = ShareBridge.copyCardImageToClipboard(context, file)
                            if (copied) {
                                HapticHelper.confirmSuccess(context)
                                statusMessage = "9:16 PNG copied to clipboard — ready to paste!"
                            } else {
                                statusMessage = "Couldn't copy image to clipboard."
                            }
                        }
                    },
                    enabled = !isRendering,
                    modifier = Modifier
                        .weight(1f)
                        .height(48.dp)
                ) {
                    Icon(Icons.Rounded.ContentCopy, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Copy Image", maxLines = 1)
                }

                OutlinedButton(
                    onClick = {
                        scope.launch {
                            val file = withContext(Dispatchers.IO) {
                                StoryCardRenderer.renderToCacheFile(context, signal, currentConfig)
                            }
                            val saved = withContext(Dispatchers.IO) {
                                ShareBridge.saveCardToGallery(context, file, signal.slug)
                            }
                            if (saved) {
                                HapticHelper.confirmSuccess(context)
                                statusMessage = "Saved to Pictures/Chaperone"
                            } else {
                                statusMessage = "Couldn't save card to Gallery."
                            }
                        }
                    },
                    enabled = !isRendering,
                    modifier = Modifier
                        .weight(1f)
                        .height(48.dp)
                ) {
                    Icon(Icons.Rounded.Download, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Save PNG", maxLines = 1)
                }
            }

            OutlinedButton(
                onClick = {
                    val ok = ShareBridge.copyCanonicalLink(context, signal)
                    if (ok) {
                        HapticHelper.tick(context)
                        statusMessage = "Canonical Chaperone link copied"
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(46.dp)
            ) {
                Icon(Icons.Rounded.Link, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text("Copy Canonical Link")
            }

            if (statusMessage.isNotBlank()) {
                Text(
                    text = statusMessage,
                    color = MaterialTheme.colorScheme.primary,
                    style = MaterialTheme.typography.bodySmall,
                    fontWeight = FontWeight.Medium
                )
            }
        }
    }
}
