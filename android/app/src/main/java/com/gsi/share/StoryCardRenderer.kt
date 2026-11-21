package com.gsi.share

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RadialGradient
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Shader
import android.graphics.Typeface
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import com.gsi.data.GsiRepository
import com.gsi.model.Signal
import java.io.File
import java.io.FileOutputStream
import kotlin.math.roundToInt

enum class StorySurfaceMode {
    PAPER,
    DARK
}

data class StoryCardConfig(
    val mode: StorySurfaceMode = StorySurfaceMode.DARK,
    val quoteText: String = "",
    val quoteLabel: String = "",
    val isActiveP53: Boolean = false
)

/**
 * Offscreen 1080x1920 (9:16) editorial Story Card renderer matching Chaperone's web studio.
 * Writes PNG output into `cacheDir/shared_cards/` scoped for FileProvider sharing and clipboard copy.
 */
object StoryCardRenderer {

    private const val WIDTH = 1080
    private const val HEIGHT = 1920
    private const val SHARED_CARDS_DIR = "shared_cards"

    fun renderBitmap(
        context: Context,
        signal: Signal,
        config: StoryCardConfig
    ): Bitmap {
        val bitmap = Bitmap.createBitmap(WIDTH, HEIGHT, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)

        val primaryColor = parseColor(signal.primaryHex, 0xFFFF65AD.toInt())
        val surfaceColor = parseColor(signal.surfaceHex, 0xFF16111C.toInt())
        val glowColor = parseColor(signal.glowHex, primaryColor)
        val cyanAccent = 0xFF35C9E9.toInt()
        val p53Accent = 0xFFFF58A6.toInt()
        val isPaper = config.mode == StorySurfaceMode.PAPER

        // Palette tokens
        val outerTop = blend(if (isPaper) 0xFF14101A.toInt() else 0xFF0A080E.toInt(), surfaceColor, 0.45f)
        val outerBottom = blend(0xFF07050A.toInt(), primaryColor, 0.14f)
        val sleeveTop = if (isPaper) blend(0xFFF6F0E4.toInt(), primaryColor, 0.04f) else blend(0xFF1B1622.toInt(), surfaceColor, 0.55f)
        val sleeveMid = if (isPaper) blend(0xFFF1E9DA.toInt(), primaryColor, 0.06f) else blend(0xFF14111B.toInt(), primaryColor, 0.12f)
        val sleeveBottom = if (isPaper) blend(0xFFE7DEC9.toInt(), surfaceColor, 0.06f) else blend(0xFF0E0B14.toInt(), cyanAccent, 0.08f)
        val inkPrimary = if (isPaper) 0xFF18121E.toInt() else 0xFFF8F5EF.toInt()
        val inkMuted = if (isPaper) 0xFF54495E.toInt() else 0xFFB8B0C2.toInt()
        val accentRule = if (isPaper) blend(primaryColor, 0xFF18121E.toInt(), 0.25f) else blend(primaryColor, 0xFFFFFFFF.toInt(), 0.2f)
        val noteBg = if (isPaper) 0xCCFFFDF8.toInt() else 0x1AFFFFFF

        // 1. Outer ambient backdrop
        val bgPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            shader = LinearGradient(0f, 0f, WIDTH.toFloat(), HEIGHT.toFloat(), outerTop, outerBottom, Shader.TileMode.CLAMP)
        }
        canvas.drawRect(0f, 0f, WIDTH.toFloat(), HEIGHT.toFloat(), bgPaint)

        val glowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            shader = RadialGradient(
                540f, 680f, 860f,
                withAlpha(glowColor, if (isPaper) 72 else 110),
                Color.TRANSPARENT,
                Shader.TileMode.CLAMP
            )
        }
        canvas.drawRect(0f, 0f, WIDTH.toFloat(), HEIGHT.toFloat(), glowPaint)

        // 2. Asymmetric sleeve frame + chromatic registration plates
        val sleeve = RectF(54f, 76f, 54f + 972f, 76f + 1768f)
        val radii = floatArrayOf(18f, 18f, 44f, 44f, 18f, 18f, 44f, 44f)

        fun drawAsymmRect(rect: RectF, color: Int, dx: Float = 0f, dy: Float = 0f) {
            val shifted = RectF(rect.left + dx, rect.top + dy, rect.right + dx, rect.bottom + dy)
            val path = Path().apply { addRoundRect(shifted, radii, Path.Direction.CW) }
            canvas.drawPath(path, Paint(Paint.ANTI_ALIAS_FLAG).apply { this.color = color })
        }

        drawAsymmRect(sleeve, 0x7006040A, 12f, 18f)
        drawAsymmRect(sleeve, withAlpha(cyanAccent, 138), 10f, 10f)
        drawAsymmRect(sleeve, withAlpha(if (signal.isP53) p53Accent else primaryColor, 152), -8f, -8f)

        val sleeveClip = Path().apply { addRoundRect(sleeve, radii, Path.Direction.CW) }
        canvas.save()
        canvas.clipPath(sleeveClip)

        // Sleeve gradient
        val sleevePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            shader = LinearGradient(
                sleeve.left, sleeve.top, sleeve.right, sleeve.bottom,
                intArrayOf(sleeveTop, sleeveMid, sleeveBottom),
                floatArrayOf(0f, 0.55f, 1f),
                Shader.TileMode.CLAMP
            )
        }
        canvas.drawRect(sleeve, sleevePaint)

        // Subtle laid-paper / studio horizontal grain
        val grainPaint = Paint().apply {
            color = if (isPaper) 0x082D2018 else 0x08FFFFFF
            strokeWidth = 1f
        }
        var gy = sleeve.top + 18f
        while (gy < sleeve.bottom) {
            canvas.drawLine(sleeve.left, gy, sleeve.right, gy, grainPaint)
            gy += 18f
        }

        // 3. Left Spine Strip (P53 protein specimen strip or tonal signal spine)
        val spineW = if (signal.isP53) 124f else 36f
        val spineRect = RectF(sleeve.left, sleeve.top, sleeve.left + spineW, sleeve.bottom)
        if (signal.isP53) {
            val protein = GsiRepository.loadCoverAndroidBitmap(context, "P53_cover.jpg", maxEdgePx = 800)
                ?: GsiRepository.loadCoverAndroidBitmap(context, "P53_cover-runtime.webp", maxEdgePx = 800)
            if (protein != null) {
                val sliceCount = 4
                val sliceH = (sleeve.height() / sliceCount).roundToInt()
                val offsets = floatArrayOf(0.12f, 0.36f, 0.58f, 0.24f)
                val cropH = (protein.height * 0.9f).roundToInt().coerceAtLeast(1)
                val cropW = (cropH * (spineW / sliceH)).roundToInt().coerceIn(1, protein.width)
                for (i in 0 until sliceCount) {
                    val sx = ((protein.width - cropW) * offsets[i]).roundToInt().coerceAtLeast(0)
                    val sy = (protein.height * 0.05f).roundToInt()
                    val src = Rect(sx, sy, (sx + cropW).coerceAtMost(protein.width), (sy + cropH).coerceAtMost(protein.height))
                    val dst = RectF(sleeve.left, sleeve.top + i * sliceH, sleeve.left + spineW, sleeve.top + (i + 1) * sliceH)
                    canvas.drawBitmap(protein, src, dst, Paint(Paint.FILTER_BITMAP_FLAG))
                }
                canvas.drawRect(spineRect, Paint().apply { color = withAlpha(primaryColor, 36) })
            } else {
                val fallbackSpine = Paint().apply {
                    shader = LinearGradient(
                        spineRect.left, spineRect.top, spineRect.left, spineRect.bottom,
                        intArrayOf(p53Accent, primaryColor, cyanAccent),
                        null,
                        Shader.TileMode.CLAMP
                    )
                }
                canvas.drawRect(spineRect, fallbackSpine)
            }
            // Registration trim beside spine
            val foldX = sleeve.left + spineW
            canvas.drawRect(foldX, sleeve.top, foldX + 3f, sleeve.bottom, Paint().apply { color = withAlpha(cyanAccent, 200) })
            canvas.drawRect(foldX + 4f, sleeve.top, foldX + 7f, sleeve.bottom, Paint().apply { color = withAlpha(p53Accent, 215) })
        } else {
            val spinePaint = Paint().apply {
                shader = LinearGradient(
                    spineRect.left, spineRect.top, spineRect.left, spineRect.bottom,
                    intArrayOf(primaryColor, glowColor, cyanAccent),
                    null,
                    Shader.TileMode.CLAMP
                )
            }
            canvas.drawRect(spineRect, spinePaint)
        }

        val contentX = sleeve.left + spineW + 52f
        val contentRight = sleeve.right - 52f
        val contentW = (contentRight - contentX).roundToInt()

        // 4. Header Row
        canvas.drawRect(contentX, 141f, contentX + 6f, 166f, Paint().apply { color = cyanAccent })
        canvas.drawRect(contentX + 10f, 141f, contentX + 16f, 166f, Paint().apply { color = if (signal.isP53) p53Accent else primaryColor })

        val headerTitlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = inkPrimary
            textSize = 31f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        canvas.drawText(if (signal.isP53) "Radio P53" else "Chaperone", contentX + 28f, 165f, headerTitlePaint)

        val statusLabel = when {
            signal.isP53 && config.isActiveP53 -> "Active"
            signal.isP53 -> "Transmission"
            else -> "Archive Signal"
        }
        val statusPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = inkMuted
            textSize = 23f
            textAlign = Paint.Align.RIGHT
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        canvas.drawText(statusLabel, contentRight, 163f, statusPaint)

        canvas.drawRect(contentX, 192f, contentRight, 194f, Paint().apply { color = withAlpha(inkPrimary, 42) })
        canvas.drawRect(contentX, 191f, contentX + 114f, 195f, Paint().apply { color = accentRule })

        // 5. Track, Artist, Album Typography above Cover
        var y = 224f
        val trackSize = when {
            signal.track.length <= 18 -> 72f
            signal.track.length <= 32 -> 60f
            else -> 50f
        }
        y = drawWrappedText(
            canvas = canvas,
            text = signal.track,
            x = contentX,
            y = y,
            maxWidth = contentW,
            textSize = trackSize,
            color = inkPrimary,
            bold = true,
            maxLines = 2
        ) + 8f

        y = drawWrappedText(
            canvas = canvas,
            text = signal.artist,
            x = contentX,
            y = y,
            maxWidth = contentW,
            textSize = 38f,
            color = inkPrimary,
            bold = true,
            maxLines = 2
        ) + 6f

        if (signal.album.isNotBlank()) {
            y = drawWrappedText(
                canvas = canvas,
                text = signal.album,
                x = contentX,
                y = y,
                maxWidth = contentW,
                textSize = 28f,
                color = inkMuted,
                bold = false,
                maxLines = 2
            )
        }

        // 6. Asymmetric Album Cover Window
        val quote = config.quoteText.trim()
        val coverY = y + 26f
        val coverMaxBottom = if (quote.isNotEmpty()) 1046f else 1380f
        val coverSize = (coverMaxBottom - coverY).coerceIn(if (quote.isNotEmpty()) 400f else 520f, if (quote.isNotEmpty()) 560f else 700f)
        val coverX = contentX + (contentW - coverSize) / 2f
        val coverRect = RectF(coverX, coverY, coverX + coverSize, coverY + coverSize)
        val coverRadii = floatArrayOf(12f, 12f, 36f, 36f, 12f, 12f, 36f, 36f)

        // Offset registration plates behind cover
        canvas.drawPath(
            Path().apply { addRoundRect(RectF(coverX + 9f, coverY + 9f, coverX + coverSize + 9f, coverY + coverSize + 9f), coverRadii, Path.Direction.CW) },
            Paint(Paint.ANTI_ALIAS_FLAG).apply { color = withAlpha(cyanAccent, 122) }
        )
        canvas.drawPath(
            Path().apply { addRoundRect(RectF(coverX - 7f, coverY - 7f, coverX + coverSize - 7f, coverY + coverSize - 7f), coverRadii, Path.Direction.CW) },
            Paint(Paint.ANTI_ALIAS_FLAG).apply { color = withAlpha(if (signal.isP53) p53Accent else primaryColor, 138) }
        )

        val coverBmp = GsiRepository.loadCoverAndroidBitmap(context, signal.coverFileName, signal.localCoverPath, maxEdgePx = 900)
        canvas.save()
        val coverPath = Path().apply { addRoundRect(coverRect, coverRadii, Path.Direction.CW) }
        canvas.clipPath(coverPath)
        if (coverBmp != null) {
            val crop = minOf(coverBmp.width, coverBmp.height)
            val src = Rect(
                (coverBmp.width - crop) / 2,
                (coverBmp.height - crop) / 2,
                (coverBmp.width + crop) / 2,
                (coverBmp.height + crop) / 2
            )
            canvas.drawBitmap(coverBmp, src, coverRect, Paint(Paint.FILTER_BITMAP_FLAG))
        } else {
            canvas.drawRect(coverRect, Paint().apply { color = surfaceColor })
        }
        canvas.restore()

        canvas.drawPath(
            coverPath,
            Paint(Paint.ANTI_ALIAS_FLAG).apply {
                style = Paint.Style.STROKE
                strokeWidth = 2f
                color = withAlpha(inkPrimary, 48)
            }
        )

        // 7. Selected Quote / Excerpt Card below Cover
        if (quote.isNotEmpty()) {
            val noteTop = coverY + coverSize + 36f
            val isLong = quote.length > 165
            val noteSize = if (isLong) 36f else 41f
            val hasLabel = config.quoteLabel.isNotBlank()
            val labelOffset = if (hasLabel) 46f else 18f
            val textW = (contentW - 60).coerceAtLeast(240)

            val noteTextPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
                color = inkPrimary
                textSize = noteSize
                typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
            }
            val layout = StaticLayout.Builder.obtain(quote, 0, quote.length, noteTextPaint, textW)
                .setAlignment(Layout.Alignment.ALIGN_NORMAL)
                .setLineSpacing(10f, 1f)
                .setMaxLines(if (isLong) 6 else 5)
                .setEllipsize(android.text.TextUtils.TruncateAt.END)
                .build()

            val boxH = (labelOffset + layout.height + 34f).coerceAtMost(1540f - noteTop)
            val noteRect = RectF(contentX, noteTop, contentRight, noteTop + boxH)
            canvas.drawRoundRect(noteRect, 14f, 14f, Paint(Paint.ANTI_ALIAS_FLAG).apply { color = noteBg })
            canvas.drawRoundRect(
                noteRect, 14f, 14f,
                Paint(Paint.ANTI_ALIAS_FLAG).apply {
                    style = Paint.Style.STROKE
                    strokeWidth = 1.5f
                    color = withAlpha(inkPrimary, 34)
                }
            )
            // Vertical accent indicator bar
            canvas.drawRoundRect(
                RectF(contentX + 14f, noteTop + 16f, contentX + 20f, noteTop + boxH - 16f),
                3f, 3f,
                Paint(Paint.ANTI_ALIAS_FLAG).apply { color = accentRule }
            )

            if (hasLabel) {
                val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                    color = accentRule
                    textSize = 21f
                    letterSpacing = 0.08f
                    typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
                }
                canvas.drawText(config.quoteLabel.uppercase(), contentX + 34f, noteTop + 38f, labelPaint)
            }

            canvas.save()
            canvas.translate(contentX + 34f, noteTop + labelOffset + 8f)
            layout.draw(canvas)
            canvas.restore()
        }

        // 8. Quiet breathing room + directional cue + authentic Chaperone footer
        val centerX = contentX + contentW / 2f
        val cuePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = withAlpha(inkPrimary, 86)
            strokeWidth = 2.2f
            style = Paint.Style.STROKE
            strokeCap = Paint.Cap.ROUND
            strokeJoin = Paint.Join.ROUND
        }
        val cuePath = Path().apply {
            moveTo(centerX - 11f, 1720f)
            lineTo(centerX, 1709f)
            lineTo(centerX + 11f, 1720f)
        }
        canvas.drawPath(cuePath, cuePaint)

        canvas.drawRect(contentX, 1744f, contentRight, 1746f, Paint().apply { color = withAlpha(inkPrimary, 46) })

        val footerLeft = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = inkMuted
            textSize = 23f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        canvas.drawText(if (signal.isP53) "Radio P53" else "Genome Stability Inducer", contentX, 1790f, footerLeft)

        val footerRight = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = inkPrimary
            textSize = 24f
            textAlign = Paint.Align.RIGHT
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        canvas.drawText("Chaperone", contentRight, 1790f, footerRight)

        canvas.restore()

        // Outer sleeve hairline border
        canvas.drawPath(
            sleeveClip,
            Paint(Paint.ANTI_ALIAS_FLAG).apply {
                style = Paint.Style.STROKE
                strokeWidth = 2f
                color = withAlpha(inkPrimary, 42)
            }
        )

        return bitmap
    }

    fun renderToCacheFile(context: Context, signal: Signal, config: StoryCardConfig): File {
        val dir = File(context.cacheDir, SHARED_CARDS_DIR).apply { if (!exists()) mkdirs() }
        val safeSlug = Signal.slugify(signal.slug).ifBlank { "signal" }
        val outFile = File(dir, "chaperone-$safeSlug-story.png")
        val bmp = renderBitmap(context, signal, config)
        FileOutputStream(outFile).use { fos ->
            bmp.compress(Bitmap.CompressFormat.PNG, 100, fos)
        }
        bmp.recycle()
        return outFile
    }

    private fun drawWrappedText(
        canvas: Canvas,
        text: String,
        x: Float,
        y: Float,
        maxWidth: Int,
        textSize: Float,
        color: Int,
        bold: Boolean,
        maxLines: Int
    ): Float {
        val tp = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            this.color = color
            this.textSize = textSize
            this.typeface = Typeface.create(Typeface.SANS_SERIF, if (bold) Typeface.BOLD else Typeface.NORMAL)
        }
        val layout = StaticLayout.Builder.obtain(text, 0, text.length, tp, maxWidth.coerceAtLeast(100))
            .setAlignment(Layout.Alignment.ALIGN_NORMAL)
            .setMaxLines(maxLines)
            .setEllipsize(android.text.TextUtils.TruncateAt.END)
            .build()
        canvas.save()
        canvas.translate(x, y)
        layout.draw(canvas)
        canvas.restore()
        return y + layout.height
    }

    private fun parseColor(hex: String, fallback: Int): Int {
        return try {
            val clean = hex.trim().removePrefix("#")
            Color.parseColor("#$clean")
        } catch (_: Exception) {
            fallback
        }
    }

    private fun withAlpha(color: Int, alpha: Int): Int {
        return Color.argb(alpha.coerceIn(0, 255), Color.red(color), Color.green(color), Color.blue(color))
    }

    private fun blend(a: Int, b: Int, ratio: Float): Int {
        val t = ratio.coerceIn(0f, 1f)
        val r = (Color.red(a) + (Color.red(b) - Color.red(a)) * t).roundToInt()
        val g = (Color.green(a) + (Color.green(b) - Color.green(a)) * t).roundToInt()
        val bl = (Color.blue(a) + (Color.blue(b) - Color.blue(a)) * t).roundToInt()
        return Color.rgb(r, g, bl)
    }
}
