package com.gsi.audio

import android.content.Context
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import com.gsi.model.Signal
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class PeekPlaybackState(
    val activeSlug: String? = null,
    val activeTrack: String = "",
    val activeArtist: String = "",
    val accentHex: String = "#FF65AD",
    val isPlaying: Boolean = false,
    val isBuffering: Boolean = false,
    val progress: Float = 0f,
    val error: String? = null
)

/**
 * Native Media3 ExoPlayer controller for Chaperone's 30-second PEEK signal previews.
 * Handles Android audio focus, noisy-audio pause, and reactive progress state for AudioPulseBar.
 */
object PeekAudioPlayer {

    private var player: ExoPlayer? = null
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private var progressJob: Job? = null

    private val _state = MutableStateFlow(PeekPlaybackState())
    val state: StateFlow<PeekPlaybackState> = _state.asStateFlow()

    private fun ensurePlayer(context: Context): ExoPlayer {
        player?.let { return it }
        val audioAttrs = AudioAttributes.Builder()
            .setUsage(C.USAGE_MEDIA)
            .setContentType(C.AUDIO_CONTENT_TYPE_MUSIC)
            .build()

        val exo = ExoPlayer.Builder(context.applicationContext)
            .setAudioAttributes(audioAttrs, /* handleAudioFocus = */ true)
            .setHandleAudioBecomingNoisy(true)
            .build()

        exo.addListener(object : Player.Listener {
            override fun onIsPlayingChanged(isPlaying: Boolean) {
                _state.update { it.copy(isPlaying = isPlaying, error = null) }
                if (isPlaying) startProgressTicker() else stopProgressTicker()
            }

            override fun onPlaybackStateChanged(playbackState: Int) {
                when (playbackState) {
                    Player.STATE_BUFFERING -> _state.update { it.copy(isBuffering = true) }
                    Player.STATE_READY -> _state.update { it.copy(isBuffering = false) }
                    Player.STATE_ENDED -> {
                        stopProgressTicker()
                        exo.seekTo(0)
                        exo.pause()
                        _state.update { it.copy(isPlaying = false, isBuffering = false, progress = 0f) }
                    }
                    Player.STATE_IDLE -> {
                        stopProgressTicker()
                        _state.update { it.copy(isPlaying = false, isBuffering = false) }
                    }
                }
            }

            override fun onPlayerError(error: PlaybackException) {
                stopProgressTicker()
                _state.update {
                    it.copy(
                        isPlaying = false,
                        isBuffering = false,
                        error = "Preview unavailable"
                    )
                }
            }
        })

        player = exo
        return exo
    }

    fun togglePeek(context: Context, signal: Signal) {
        val url = signal.previewUrl?.takeIf { it.startsWith("https://") }
        if (url == null) {
            _state.update {
                it.copy(
                    activeSlug = signal.slug,
                    activeTrack = signal.track,
                    activeArtist = signal.artist,
                    accentHex = signal.primaryHex,
                    isPlaying = false,
                    isBuffering = false,
                    error = "No 30s preview available"
                )
            }
            return
        }

        val exo = ensurePlayer(context)
        val current = _state.value
        if (current.activeSlug == signal.slug && exo.mediaItemCount > 0) {
            if (exo.isPlaying) {
                exo.pause()
            } else {
                exo.play()
            }
            return
        }

        _state.value = PeekPlaybackState(
            activeSlug = signal.slug,
            activeTrack = signal.track,
            activeArtist = signal.artist,
            accentHex = signal.primaryHex,
            isPlaying = false,
            isBuffering = true,
            progress = 0f,
            error = null
        )

        exo.stop()
        exo.setMediaItem(MediaItem.fromUri(url))
        exo.prepare()
        exo.playWhenReady = true
    }

    fun togglePlayPause() {
        val exo = player ?: return
        if (exo.isPlaying) exo.pause() else exo.play()
    }

    fun pauseIfPlaying() {
        player?.let { if (it.isPlaying) it.pause() }
    }

    fun stopAndClear() {
        stopProgressTicker()
        player?.stop()
        _state.value = PeekPlaybackState()
    }

    fun release() {
        stopProgressTicker()
        player?.release()
        player = null
        _state.value = PeekPlaybackState()
    }

    private fun startProgressTicker() {
        if (progressJob?.isActive == true) return
        progressJob = scope.launch {
            while (true) {
                val exo = player
                if (exo != null && exo.duration > 0L) {
                    val ratio = (exo.currentPosition.toFloat() / exo.duration.toFloat()).coerceIn(0f, 1f)
                    _state.update { it.copy(progress = ratio) }
                }
                delay(120)
            }
        }
    }

    private fun stopProgressTicker() {
        progressJob?.cancel()
        progressJob = null
    }
}
