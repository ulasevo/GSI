package com.gsi.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.unit.dp
import kotlin.math.abs
import kotlin.math.sin

/**
 * Reactive audio waveform visualizer driven by genuine Media3 PEEK playback state.
 * Smoothly settles into a calm resting profile when paused/idle and highlights elapsed progress.
 */
@Composable
fun AudioPulseBar(
    modifier: Modifier = Modifier,
    barColor: Color = Color(0xFFFFB703),
    barCount: Int = 36,
    isPlaying: Boolean = false,
    progress: Float = 0f
) {
    val infiniteTransition = rememberInfiniteTransition(label = "peekWave")
    val phase by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 6.28318f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1900, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "peekPhase"
    )

    val energy by animateFloatAsState(
        targetValue = if (isPlaying) 1f else 0f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessMediumLow
        ),
        label = "peekEnergy"
    )

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height(28.dp)
    ) {
        val width = size.width
        val height = size.height
        val midY = height / 2f
        val spacing = width / barCount

        for (i in 0 until barCount) {
            val fraction = i.toFloat() / barCount.toFloat()
            val x = i * spacing + (spacing / 2f)
            val normalizedX = fraction * 4.5f * Math.PI.toFloat()

            val restingShape = 0.14f + 0.14f * abs(sin(normalizedX * 0.7f))
            val activeWave = abs(sin(normalizedX + phase) * 0.62f + sin(normalizedX * 1.6f - phase * 0.85f) * 0.38f)
            val combinedRatio = restingShape + (activeWave * 0.34f * energy)
            val amplitude = (height * combinedRatio).coerceAtMost(height * 0.46f)

            val isElapsed = progress > 0f && fraction <= progress
            val alpha = when {
                isPlaying && isElapsed -> 0.95f
                isPlaying -> 0.42f + (amplitude / height) * 0.45f
                isElapsed -> 0.72f
                else -> 0.30f
            }

            drawLine(
                color = barColor.copy(alpha = alpha),
                start = Offset(x, midY - amplitude),
                end = Offset(x, midY + amplitude),
                strokeWidth = 2.4.dp.toPx(),
                cap = StrokeCap.Round
            )
        }
    }
}
