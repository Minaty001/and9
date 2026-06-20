package com.jarvis.assistant.voice

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.AttributeSet
import android.view.View
import kotlin.math.abs
import kotlin.math.sin

/**
 * WaveformView — live voice amplitude waveform.
 *
 * Shows animated sine-wave bars that pulse with mic input (RMS dB).
 * Mimics Gemini Live / Google Assistant waveform feel.
 */
class WaveformView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    // ── Config ───────────────────────────────────────────────────
    private val BAR_COUNT  = 32
    private val BAR_WIDTH  = 6f
    private val BAR_GAP    = 5f
    private val BASE_HEIGHT = 8f
    private val MAX_HEIGHT  = 120f

    // Colors: cyan → purple gradient feel
    private val colors = listOf(
        Color.parseColor("#00FFFF"),
        Color.parseColor("#7B61FF"),
        Color.parseColor("#00E5FF"),
        Color.parseColor("#B388FF"),
    )

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        strokeCap = Paint.Cap.ROUND
        strokeWidth = BAR_WIDTH
    }

    // ── State ────────────────────────────────────────────────────
    private var amplitudeLevel = 0f       // 0.0 – 1.0
    private var animating = false
    private var phase = 0f
    private val bars = FloatArray(BAR_COUNT) { BASE_HEIGHT }

    // ── Control ──────────────────────────────────────────────────

    fun startAnimating() {
        animating = true
        postInvalidate()
    }

    fun stopAnimating() {
        animating = false
        amplitudeLevel = 0f
        bars.fill(BASE_HEIGHT)
        postInvalidate()
    }

    fun updateAmplitude(rmsDb: Float) {
        // rmsDb range is typically -2..10; normalize to 0..1
        amplitudeLevel = ((rmsDb + 2f) / 12f).coerceIn(0f, 1f)
    }

    // ── Draw ─────────────────────────────────────────────────────

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val w = width.toFloat()
        val h = height.toFloat()
        val cx = w / 2f
        val cy = h / 2f

        val totalWidth = BAR_COUNT * (BAR_WIDTH + BAR_GAP) - BAR_GAP
        var x = cx - totalWidth / 2f + BAR_WIDTH / 2f

        for (i in 0 until BAR_COUNT) {
            val norm   = i.toFloat() / BAR_COUNT.toFloat()
            val wave   = sin(norm * Math.PI * 2.0 + phase).toFloat()
            val target = if (animating) {
                BASE_HEIGHT + (MAX_HEIGHT - BASE_HEIGHT) *
                        amplitudeLevel * abs(wave)
            } else BASE_HEIGHT

            // Smooth lerp
            bars[i] = bars[i] + (target - bars[i]) * 0.3f

            val barH = bars[i]
            val colorIdx = (norm * (colors.size - 1)).toInt().coerceIn(0, colors.size - 1)
            paint.color = colors[colorIdx]
            paint.alpha = if (animating) 230 else 80

            canvas.drawLine(x, cy - barH / 2f, x, cy + barH / 2f, paint)
            x += BAR_WIDTH + BAR_GAP
        }

        if (animating) {
            phase += 0.18f
            postInvalidateDelayed(16) // ~60fps
        }
    }
}
