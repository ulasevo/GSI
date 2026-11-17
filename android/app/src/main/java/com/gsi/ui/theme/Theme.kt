package com.gsi.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val GsiDarkColorScheme = darkColorScheme(
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

@Composable
fun GSITheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = GsiDarkColorScheme,
        typography = Typography,
        content = content
    )
}
