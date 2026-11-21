package com.gsi

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.mutableStateOf
import com.gsi.audio.PeekAudioPlayer
import com.gsi.data.LanSyncClient
import com.gsi.ui.ChaperoneLaunchAction
import com.gsi.ui.GsiArchiveScreen
import com.gsi.ui.theme.GSITheme

class MainActivity : ComponentActivity() {

    private val pendingLaunchAction = mutableStateOf<ChaperoneLaunchAction>(ChaperoneLaunchAction.None)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        handleIncomingIntent(intent)

        setContent {
            GSITheme {
                GsiArchiveScreen(
                    launchAction = pendingLaunchAction.value,
                    onLaunchActionConsumed = {
                        pendingLaunchAction.value = ChaperoneLaunchAction.None
                    }
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIncomingIntent(intent)
    }

    override fun onStop() {
        super.onStop()
        PeekAudioPlayer.pauseIfPlaying()
    }

    override fun onDestroy() {
        if (isFinishing) {
            PeekAudioPlayer.release()
        }
        super.onDestroy()
    }

    private fun handleIncomingIntent(intent: Intent?) {
        if (intent == null) return
        when (intent.action) {
            Intent.ACTION_SEND -> {
                if (intent.type == "text/plain") {
                    val rawText = intent.getStringExtra(Intent.EXTRA_TEXT)
                    val safeMusicUrl = LanSyncClient.extractFirstMusicUrl(rawText)
                    pendingLaunchAction.value = ChaperoneLaunchAction.OpenCapture(sharedUrl = safeMusicUrl)
                }
            }
            Intent.ACTION_VIEW -> {
                val uri = intent.data ?: return
                if (uri.scheme != "chaperone") return
                when (uri.host) {
                    "signal" -> {
                        val slug = uri.lastPathSegment?.trim().orEmpty()
                        if (slug.matches(Regex("^[a-z0-9]+(?:-[a-z0-9]+)*$"))) {
                            pendingLaunchAction.value = ChaperoneLaunchAction.OpenSignalSlug(slug)
                        }
                    }
                    "p53" -> {
                        pendingLaunchAction.value = ChaperoneLaunchAction.OpenActiveP53
                    }
                    "capture" -> {
                        pendingLaunchAction.value = ChaperoneLaunchAction.OpenCapture(sharedUrl = null)
                    }
                    "random" -> {
                        pendingLaunchAction.value = ChaperoneLaunchAction.OpenRandomSignal
                    }
                }
            }
        }
    }
}
