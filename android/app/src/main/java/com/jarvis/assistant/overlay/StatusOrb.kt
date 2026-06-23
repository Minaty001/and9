package com.jarvis.assistant.overlay

import android.animation.ValueAnimator
import android.content.Context
import android.graphics.*
import android.util.AttributeSet
import android.view.View
import android.view.animation.LinearInterpolator
import kotlin.math.min

/**
 * StatusOrb
 *
 * Custom View that draws a premium, animated color orb mapping to the assistant's
 * current execution pipeline stage:
 *   - IDLE (Yellow): Steady glow
 *   - LISTENING (Green): Pulsing circle animation
 *   - THINKING (Blue): Spinning outer ring animation
 *   - EXECUTING (Red): Flashing/pulsing alert animation
 */
class StatusOrb @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    enum class State {
        IDLE,       // Yellow steady glow
        LISTENING,  // Green pulsing
        THINKING,   // Blue spinning ring
        EXECUTING   // Red flashing
    }

    private var currentState = State.IDLE

    // Paints
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val ringPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
    }

    // Colors
    private val colorIdle = Color.parseColor("#F1C40F")      // Yellow
    private val colorListening = Color.parseColor("#2ECC71") // Green
    private val colorThinking = Color.parseColor("#3498DB")  // Blue
    private val colorExecuting = Color.parseColor("#E74C3C") // Red

    // Animators
    private var pulseAnimator: ValueAnimator? = null
    private var spinAnimator: ValueAnimator? = null
    private var flashAnimator: ValueAnimator? = null

    // Animation values
    private var pulseScale = 1.0f
    private var spinAngle = 0.0f
    private var flashAlpha = 255

    init {
        setupAnimators()
        setState(State.IDLE)
    }

    private fun setupAnimators() {
        // Pulse animator for LISTENING (Green)
        pulseAnimator = ValueAnimator.ofFloat(1.0f, 1.25f, 1.0f).apply {
            duration = 1500
            repeatCount = ValueAnimator.INFINITE
            addUpdateListener { animator ->
                pulseScale = animator.animatedValue as Float
                invalidate()
            }
        }

        // Spin animator for THINKING (Blue)
        spinAnimator = ValueAnimator.ofFloat(0f, 360f).apply {
            duration = 1000
            interpolator = LinearInterpolator()
            repeatCount = ValueAnimator.INFINITE
            addUpdateListener { animator ->
                spinAngle = animator.animatedValue as Float
                invalidate()
            }
        }

        // Flash animator for EXECUTING (Red)
        flashAnimator = ValueAnimator.ofInt(255, 70, 255).apply {
            duration = 800
            repeatCount = ValueAnimator.INFINITE
            addUpdateListener { animator ->
                flashAlpha = animator.animatedValue as Int
                invalidate()
            }
        }
    }

    fun setState(state: State) {
        if (currentState == state) return
        currentState = state

        // Stop all animators first
        pulseAnimator?.cancel()
        spinAnimator?.cancel()
        flashAnimator?.cancel()

        // Reset animation values
        pulseScale = 1.0f
        spinAngle = 0.0f
        flashAlpha = 255

        // Start appropriate animator
        when (state) {
            State.LISTENING -> pulseAnimator?.start()
            State.THINKING -> spinAnimator?.start()
            State.EXECUTING -> flashAnimator?.start()
            State.IDLE -> { /* Steady state, no animator needed */ }
        }

        invalidate()
    }

    fun setStage(stage: String) {
        val newState = when (stage.uppercase()) {
            "LISTENING" -> State.LISTENING
            "UNDERSTANDING", "PLANNING" -> State.THINKING
            "EXECUTING" -> State.EXECUTING
            "COMPLETED", "DEGRADED", "ERROR_RECOVERY" -> State.IDLE
            else -> State.IDLE
        }
        setState(newState)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val width = width.toFloat()
        val height = height.toFloat()
        val cx = width / 2f
        val cy = height / 2f
        val radius = min(cx, cy) * 0.65f

        // Apply drop shadow glow effect to the paint
        paint.reset()
        paint.isAntiAlias = true
        paint.style = Paint.Style.FILL

        when (currentState) {
            State.IDLE -> {
                paint.color = colorIdle
                // Add soft yellow outer glow
                paint.setShadowLayer(radius * 0.4f, 0f, 0f, colorIdle)
                canvas.drawCircle(cx, cy, radius, paint)
            }
            State.LISTENING -> {
                paint.color = colorListening
                paint.setShadowLayer(radius * 0.5f * pulseScale, 0f, 0f, colorListening)
                canvas.drawCircle(cx, cy, radius * pulseScale, paint)
            }
            State.THINKING -> {
                paint.color = colorThinking
                paint.setShadowLayer(radius * 0.4f, 0f, 0f, colorThinking)
                canvas.drawCircle(cx, cy, radius * 0.9f, paint)

                // Draw spinning outer ring
                ringPaint.color = colorThinking
                ringPaint.strokeWidth = radius * 0.15f
                val ringBounds = RectF(
                    cx - radius * 1.2f,
                    cy - radius * 1.2f,
                    cx + radius * 1.2f,
                    cy + radius * 1.2f
                )
                canvas.save()
                canvas.rotate(spinAngle, cx, cy)
                // Draw 2 arcs for spinning ring
                canvas.drawArc(ringBounds, 0f, 90f, false, ringPaint)
                canvas.drawArc(ringBounds, 180f, 90f, false, ringPaint)
                canvas.restore()
            }
            State.EXECUTING -> {
                // Apply alpha flash to paint color
                val flashColor = Color.argb(
                    flashAlpha,
                    Color.red(colorExecuting),
                    Color.green(colorExecuting),
                    Color.blue(colorExecuting)
                )
                paint.color = flashColor
                paint.setShadowLayer(radius * 0.5f, 0f, 0f, colorExecuting)
                canvas.drawCircle(cx, cy, radius, paint)
            }
        }
    }
}
