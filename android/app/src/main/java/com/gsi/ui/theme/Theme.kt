package com.gsi.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.ExperimentalMaterial3ExpressiveApi
import androidx.compose.material3.MaterialExpressiveTheme
import androidx.compose.material3.MotionScheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp

/**
 * Chaperone's asymmetric signature geometry harmonized with Material 3 Expressive.
 * Top-end & bottom-start carry 28dp while opposing corners hold tight 8dp anchoring.
 */
val ChaperoneAsymmShape = RoundedCornerShape(
    topStart = 8.dp,
    topEnd = 28.dp,
    bottomEnd = 8.dp,
    bottomStart = 28.dp
)

val ChaperoneCompactAsymmShape = RoundedCornerShape(
    topStart = 6.dp,
    topEnd = 18.dp,
    bottomEnd = 6.dp,
    bottomStart = 18.dp
)

val GsiShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = ChaperoneCompactAsymmShape,
    large = ChaperoneAsymmShape,
    extraLarge = RoundedCornerShape(topStart = 14.dp, topEnd = 32.dp, bottomEnd = 14.dp, bottomStart = 32.dp)
)

private val GsiFallbackDarkColorScheme = darkColorScheme(
    primary = GsiP53Amber,
    onPrimary = GsiVoid,
    secondary = GsiSignalCyan,
    onSecondary = GsiVoid,
    tertiary = GsiBeaconGreen,
    background = GsiVoid,
    onBackground = GsiTextPrimary,
    surface = GsiSurface,
    onSurface = GsiTextPrimary,
    surfaceVariant = GsiSurfaceElevated,
    onSurfaceVariant = GsiTextSecondary,
    outline = GsiBorder
)

private val GsiFallbackLightColorScheme = lightColorScheme(
    primary = Color(0xFF9C327A),
    onPrimary = Color(0xFFFFFAF8),
    secondary = Color(0xFF006B7D),
    onSecondary = Color(0xFFFFFFFF),
    background = Color(0xFFF6F1E8),
    onBackground = Color(0xFF19131F),
    surface = Color(0xFFFAF6EE),
    onSurface = Color(0xFF19131F),
    surfaceVariant = Color(0xFFEDE5D8),
    onSurfaceVariant = Color(0xFF53485C),
    outline = Color(0xFFD2C7B7)
)

/**
 * Harmonizes a Material You wallpaper ColorScheme with a Song Room's cover-derived accent,
 * preserving system legibility while giving each song its own tonal room atmosphere.
 */
private fun harmonizeWithRoomAccent(
    base: ColorScheme,
    roomAccent: Color?,
    darkTheme: Boolean
): ColorScheme {
    if (roomAccent == null) return base
    val harmonizedPrimary = lerp(base.primary, roomAccent, 0.62f)
    val onHarmonizedPrimary = if (harmonizedPrimary.luminance() > 0.45f) Color(0xFF120E16) else Color(0xFFFBF8F4)
    val containerBlend = if (darkTheme) 0.22f else 0.16f
    val surfaceBlend = if (darkTheme) 0.08f else 0.05f
    return base.copy(
        primary = harmonizedPrimary,
        onPrimary = onHarmonizedPrimary,
        primaryContainer = lerp(base.primaryContainer, roomAccent, containerBlend),
        surfaceContainer = lerp(base.surfaceContainer, roomAccent, surfaceBlend),
        surfaceContainerHigh = lerp(base.surfaceContainerHigh, roomAccent, surfaceBlend * 1.3f),
        outlineVariant = lerp(base.outlineVariant, roomAccent, 0.28f)
    )
}

@OptIn(ExperimentalMaterial3ExpressiveApi::class)
@Composable
fun GSITheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    roomAccent: Color? = null,
    content: @Composable () -> Unit
) {
    val context = LocalContext.current
    val dynamicScheme = try {
        if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
    } catch (_: Exception) {
        if (darkTheme) GsiFallbackDarkColorScheme else GsiFallbackLightColorScheme
    }

    val colorScheme = harmonizeWithRoomAccent(
        base = dynamicScheme,
        roomAccent = roomAccent,
        darkTheme = darkTheme
    )

    MaterialExpressiveTheme(
        colorScheme = colorScheme,
        motionScheme = MotionScheme.expressive(),
        shapes = GsiShapes,
        typography = Typography,
        content = content
    )
}
