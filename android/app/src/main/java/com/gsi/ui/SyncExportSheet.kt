package com.gsi.ui

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
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
import androidx.compose.material.icons.rounded.CloudDownload
import androidx.compose.material.icons.rounded.CloudUpload
import androidx.compose.material.icons.rounded.FileDownload
import androidx.compose.material.icons.rounded.Wifi
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gsi.data.LanSyncClient
import com.gsi.data.LocalSignalStore
import com.gsi.model.Signal
import com.gsi.ui.theme.ChaperoneCompactAsymmShape
import com.gsi.util.HapticHelper
import com.gsi.widget.P53GlanceWidget
import kotlinx.coroutines.launch

/**
 * Expressive Bottom Sheet for bidirectional LAN Sync (Node.js server)
 * and one-tap portable JSON archive export via Android Storage Access Framework.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SyncExportSheet(
    allSignals: List<Signal>,
    activeP53Slug: String?,
    onArchiveUpdated: () -> Unit,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    val pendingSignals = remember(allSignals) { allSignals.filter { it.pendingSync } }
    var serverUrl by remember { mutableStateOf(LocalSignalStore.getLanBaseUrl(context)) }
    var bearerToken by remember { mutableStateOf(LocalSignalStore.getLanBearerToken(context)) }
    var isBusy by remember { mutableStateOf(false) }
    var statusMessage by remember { mutableStateOf("") }

    val jsonExportLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("application/json")
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        try {
            val json = LocalSignalStore.buildExportJson(context, allSignals, activeP53Slug)
            context.contentResolver.openOutputStream(uri)?.use { out ->
                out.write(json.toByteArray(Charsets.UTF_8))
            }
            HapticHelper.confirmSuccess(context)
            statusMessage = "Exported ${allSignals.size} signals to JSON."
        } catch (e: Exception) {
            statusMessage = e.message ?: "JSON export failed."
        }
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
                .padding(horizontal = 20.dp, vertical = 6.dp)
                .padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Column {
                Text(
                    text = "ON-DEVICE STORAGE · LAN SYNC · JSON EXPORT",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.1.sp,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = "Sync & Export Archive",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )
            }

            // Status summary pill
            Surface(
                shape = ChaperoneCompactAsymmShape,
                color = MaterialTheme.colorScheme.surfaceContainer,
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "${allSignals.size} total signals on device",
                            fontWeight = FontWeight.SemiBold
                        )
                        Text(
                            text = if (pendingSignals.isEmpty()) {
                                "All local notes synced"
                            } else {
                                "${pendingSignals.size} local edit(s) pending LAN push"
                            },
                            style = MaterialTheme.typography.bodySmall,
                            color = if (pendingSignals.isNotEmpty()) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Icon(
                        Icons.Rounded.Wifi,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
            }

            // LAN Host & Token Config
            OutlinedTextField(
                value = serverUrl,
                onValueChange = { serverUrl = it },
                label = { Text("Node.js LAN Server URL") },
                placeholder = { Text("http://192.168.1.100:3000") },
                singleLine = true,
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.fillMaxWidth()
            )

            OutlinedTextField(
                value = bearerToken,
                onValueChange = { bearerToken = it },
                label = { Text("Bearer Token (GSI_LOCAL_AUTH_TOKEN, optional)") },
                singleLine = true,
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.fillMaxWidth()
            )

            // Push & Pull Buttons
            Button(
                onClick = {
                    scope.launch {
                        isBusy = true
                        LocalSignalStore.saveLanConfig(context, serverUrl, bearerToken)
                        statusMessage = "Pushing ${pendingSignals.size} local signal(s)…"
                        val res = LanSyncClient.pushPendingSignals(
                            context = context,
                            baseUrl = serverUrl,
                            bearerToken = bearerToken,
                            pendingSignals = pendingSignals
                        )
                        statusMessage = res.message
                        if (res.success) {
                            HapticHelper.confirmSuccess(context)
                            P53GlanceWidget.refreshAll(context)
                            onArchiveUpdated()
                        }
                        isBusy = false
                    }
                },
                enabled = !isBusy && pendingSignals.isNotEmpty(),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp)
            ) {
                if (isBusy) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                } else {
                    Icon(Icons.Rounded.CloudUpload, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Push ${pendingSignals.size} Local Edit(s) to LAN", fontWeight = FontWeight.Bold)
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                FilledTonalButton(
                    onClick = {
                        scope.launch {
                            isBusy = true
                            LocalSignalStore.saveLanConfig(context, serverUrl, bearerToken)
                            statusMessage = "Pulling latest archive bundle…"
                            val res = LanSyncClient.pullArchiveBundle(context, serverUrl, bearerToken)
                            statusMessage = res.message
                            if (res.success) {
                                HapticHelper.confirmSuccess(context)
                                P53GlanceWidget.refreshAll(context)
                                onArchiveUpdated()
                            }
                            isBusy = false
                        }
                    },
                    enabled = !isBusy,
                    modifier = Modifier
                        .weight(1f)
                        .height(48.dp)
                ) {
                    Icon(Icons.Rounded.CloudDownload, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Pull Archive")
                }

                OutlinedButton(
                    onClick = {
                        scope.launch {
                            isBusy = true
                            LocalSignalStore.saveLanConfig(context, serverUrl, bearerToken)
                            val res = LanSyncClient.pingServer(serverUrl, bearerToken)
                            statusMessage = res.message
                            if (res.success) HapticHelper.tick(context)
                            isBusy = false
                        }
                    },
                    enabled = !isBusy,
                    modifier = Modifier
                        .weight(1f)
                        .height(48.dp)
                ) {
                    Text("Test LAN")
                }
            }

            // Portable JSON Snapshot Export via Storage Access Framework
            OutlinedButton(
                onClick = {
                    HapticHelper.click(context)
                    jsonExportLauncher.launch("chaperone-archive-export.json")
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp)
            ) {
                Icon(Icons.Rounded.FileDownload, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("Export Full Archive as JSON")
            }

            if (statusMessage.isNotBlank()) {
                Text(
                    text = statusMessage,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Medium
                )
            }
        }
    }
}
