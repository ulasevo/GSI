package com.gsi.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
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
import kotlin.math.sin

/**
 * A kinetic signal waveform visualizer.
 * Lectures:
 * In Compose, Canvas provides immediate-mode hardware accelerated 2D drawing.
 * rememberInfiniteTransition creates continuous, declarative looping animations
 * without needing Handler, Timer, or manual requestAnimationFrame.
 */
@Composable
fun AudioPulseBar(
    modifier: Modifier = Modifier,
    barColor: Color = Color(0xFFFFB703),
    barCount: Int = 36,
    isPlaying: Boolean = true
) {
    val infiniteTransition = rememberInfiniteTransition(label = "pulseTransition")
    val phase by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 6.28318f, // 2 * PI
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 2400, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "phaseAnimation"
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
            val x = i * spacing + (spacing / 2f)
            val normalizedX = (i.toFloat() / barCount) * 4f * Math.PI.toFloat()
            
            val amplitude = if (isPlaying) {
                val wave1 = sin(normalizedX + phase)
                val wave2 = sin(normalizedX * 1.5f - phase * 0.7f)
                val combined = (wave1 * 0.6f + wave2 * 0.4f)
                (height * 0.15f) + (height * 0.35f * kotlin.math.abs(combined))
            } else {
                height * 0.08f
            }

            drawLine(
                color = barColor.copy(alpha = 0.4f + (amplitude / height) * 0.6f),
                start = Offset(x, midY - amplitude),
                end = Offset(x, midY + amplitude),
                strokeWidth = 2.dp.toPx(),
                cap = StrokeCap.Round
            )
        }
    }
}
