package com.gsi.ui

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gsi.model.Signal
import com.gsi.ui.theme.GsiTextPrimary
import com.gsi.ui.theme.GsiTextSecondary
import com.gsi.ui.theme.GsiVoid

/** Match the small bold-markup subset supported by the website's renderer. */
private fun reviewText(content: String): AnnotatedString = buildAnnotatedString {
    val bold = Regex("\\*\\*(.*?)\\*\\*")
    var start = 0
    bold.findAll(content).forEach { match ->
        append(content.substring(start, match.range.first))
        withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { append(match.groupValues[1]) }
        start = match.range.last + 1
    }
    append(content.substring(start))
}

/** The native listening detail displays the same authored sections as the website. */
@Composable
fun SignalDetailScreen(signal: Signal, cover: ImageBitmap?, onBack: () -> Unit) {
    val context = LocalContext.current
    fun open(url: String) {
        try {
            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(context, "No app is available to open this link.", Toast.LENGTH_SHORT).show()
        } catch (_: SecurityException) {
            Toast.makeText(context, "This link could not be opened.", Toast.LENGTH_SHORT).show()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(signal.surfaceColor, GsiVoid),
                )
            )
            .statusBarsPadding()
            .navigationBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp)
    ) {
        TextButton(onClick = onBack) {
            Text("← Archive", color = GsiTextPrimary)
        }
        Spacer(Modifier.height(8.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .clip(RoundedCornerShape(topStart = 28.dp, topEnd = 8.dp, bottomEnd = 28.dp, bottomStart = 8.dp))
                .background(signal.primaryColor.copy(alpha = 0.32f))
        ) {
            if (cover != null) {
                Image(
                    bitmap = cover,
                    contentDescription = "${signal.album} cover",
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop
                )
            }
        }
        Spacer(Modifier.height(24.dp))
        Text(
            text = signal.track,
            style = MaterialTheme.typography.headlineLarge.copy(
                fontWeight = FontWeight.Black,
                letterSpacing = (-1).sp
            ),
            color = GsiTextPrimary
        )
        Spacer(Modifier.height(6.dp))
        Text(signal.artist, style = MaterialTheme.typography.titleMedium, color = GsiTextPrimary)
        if (signal.album.isNotBlank()) {
            Spacer(Modifier.height(3.dp))
            Text(signal.album, style = MaterialTheme.typography.bodyMedium, color = GsiTextSecondary)
        }
        Spacer(Modifier.height(24.dp))
        Text("Listen", style = MaterialTheme.typography.titleMedium, color = GsiTextPrimary)
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            signal.spotifyUrl?.let { url ->
                OutlinedButton(onClick = { open(url) }, modifier = Modifier.weight(1f)) {
                    Text(if (url.contains("/search/")) "Search Spotify ↗" else "Spotify ↗")
                }
            }
            signal.appleUrl?.let { url ->
                OutlinedButton(onClick = { open(url) }, modifier = Modifier.weight(1f)) { Text("Apple Music ↗") }
            }
        }
        signal.transmissionNote?.takeIf { it.isNotBlank() }?.let { note ->
            Spacer(Modifier.height(24.dp))
            Text("A note", style = MaterialTheme.typography.titleMedium, color = GsiTextPrimary)
            Spacer(Modifier.height(6.dp))
            Text(reviewText(note), style = MaterialTheme.typography.bodyLarge, color = GsiTextSecondary)
        }
        signal.reviewSections.forEach { section ->
            Spacer(Modifier.height(16.dp))
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(topStart = 24.dp, topEnd = 6.dp, bottomEnd = 24.dp, bottomStart = 6.dp),
                colors = CardDefaults.cardColors(containerColor = signal.surfaceColor.copy(alpha = 0.85f))
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(section.title, style = MaterialTheme.typography.titleLarge, color = GsiTextPrimary)
                    Spacer(Modifier.height(10.dp))
                    Text(
                        reviewText(section.content),
                        style = MaterialTheme.typography.bodyLarge.copy(lineHeight = 25.sp),
                        color = GsiTextPrimary
                    )
                }
            }
        }
        signal.websitePath?.let { path ->
            Spacer(Modifier.height(12.dp))
            Button(
                onClick = { open("https://ulasevo.github.io/GSI/$path") },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (path.startsWith("entries/")) "Read the entry on the website ↗" else "Open on the website ↗")
            }
        }
        Spacer(Modifier.height(32.dp))
    }
}
