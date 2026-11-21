package com.gsi.ui.components

import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.gsi.ui.theme.ChaperoneAsymmShape
import com.gsi.util.HapticHelper

/**
 * Tactile expressive surface card with asymmetric Chaperone corners,
 * springy press/release scale, and choreographed Pixel LRA haptics.
 */
@Composable
fun TactileCard(
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
    shape: Shape = ChaperoneAsymmShape,
    backgroundColor: Color = MaterialTheme.colorScheme.surfaceContainer,
    borderColor: Color = MaterialTheme.colorScheme.outlineVariant,
    borderWidth: Dp = 1.dp,
    content: @Composable () -> Unit
) {
    val context = LocalContext.current
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.96f else 1f,
        animationSpec = spring(
            stiffness = if (pressed) Spring.StiffnessMedium else Spring.StiffnessMediumLow,
            dampingRatio = if (pressed) Spring.DampingRatioNoBouncy else Spring.DampingRatioMediumBouncy
        ),
        label = "tactileCardScale"
    )

    Surface(
        shape = shape,
        color = backgroundColor,
        border = BorderStroke(borderWidth, borderColor),
        modifier = modifier
            .scale(scale)
            .clickable(interactionSource = interaction, indication = null) {
                HapticHelper.roomOpen(context)
                onClick()
            }
    ) {
        Box {
            content()
        }
    }
}
