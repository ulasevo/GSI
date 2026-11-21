package com.gsi.util

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.provider.Settings

/**
 * Choreographed Pixel linear resonant actuator (LRA) haptics for Chaperone.
 * Respects system haptic feedback settings and cancels cleanly before firing.
 */
object HapticHelper {

    private fun isHapticsEnabled(context: Context): Boolean {
        return try {
            Settings.System.getInt(
                context.contentResolver,
                Settings.System.HAPTIC_FEEDBACK_ENABLED,
                1
            ) != 0
        } catch (_: Exception) {
            true
        }
    }

    private fun getVibrator(context: Context): Vibrator? {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val manager = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager
            manager?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        }
    }

    private fun vibrateEffect(context: Context, effect: VibrationEffect) {
        if (!isHapticsEnabled(context)) return
        try {
            val vibrator = getVibrator(context) ?: return
            if (!vibrator.hasVibrator()) return
            vibrator.cancel()
            vibrator.vibrate(effect)
        } catch (_: Exception) {
            // Gracefully ignore when vibrator service is unavailable
        }
    }

    /** Crisp detent for filter chips, quote selectors, and segmented controls. */
    fun tick(context: Context) {
        val effect = VibrationEffect.startComposition()
            .addPrimitive(VibrationEffect.Composition.PRIMITIVE_TICK, 0.55f)
            .compose()
        vibrateEffect(context, effect)
    }

    /** Clean tactile confirmation for PEEK playback toggle and standard buttons. */
    fun click(context: Context) {
        vibrateEffect(context, VibrationEffect.createPredefined(VibrationEffect.EFFECT_CLICK))
    }

    /** Grounded physical thud when opening a Song Room or settling into a hero card. */
    fun roomOpen(context: Context) {
        val effect = VibrationEffect.startComposition()
            .addPrimitive(VibrationEffect.Composition.PRIMITIVE_THUD, 0.72f)
            .compose()
        vibrateEffect(context, effect)
    }

    /** Rising two-beat signature when saving a signal, copying a 9:16 card, or finishing LAN sync. */
    fun confirmSuccess(context: Context) {
        val effect = VibrationEffect.startComposition()
            .addPrimitive(VibrationEffect.Composition.PRIMITIVE_QUICK_RISE, 0.6f)
            .addPrimitive(VibrationEffect.Composition.PRIMITIVE_TICK, 0.85f, 38)
            .compose()
        vibrateEffect(context, effect)
    }

    /** Deep tactile anchor for destructive/reset or heavy gestures. */
    fun heavyClick(context: Context) {
        vibrateEffect(context, VibrationEffect.createPredefined(VibrationEffect.EFFECT_HEAVY_CLICK))
    }
}
