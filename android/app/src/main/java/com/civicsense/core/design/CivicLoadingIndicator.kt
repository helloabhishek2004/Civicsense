package com.civicsense.core.design

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.civicsense.core.theme.CivicGreen
import com.civicsense.core.theme.CivicGreenContainer
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/**
 * Material 3 Expressive Loading Indicator (Uncontained).
 *
 * Implements the official M3 Expressive shape-morphing motion for short wait states (< 5s).
 * Morphs continuously through 5 characteristic M3 geometric shapes:
 * 1. 4-petal rounded clover / flower
 * 2. Rounded squircle / soft square
 * 3. 4-point rounded star / diamond
 * 4. Rounded pill / oval
 * 5. Circle
 */
@Composable
fun CivicLoadingIndicator(
    modifier: Modifier = Modifier,
    size: Dp = 40.dp,
    color: Color = MaterialTheme.colorScheme.primary,
    progress: Float? = null // When null, runs indeterminate continuous morphing
) {
    val infiniteTransition = rememberInfiniteTransition(label = "m3e_loading_transition")

    // Cycle through shapes: 5 shapes, morph duration 2500ms total
    val animMorphProgress by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 5f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 3200, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "m3e_morph_progress"
    )

    // Continuous smooth rotation
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 4800, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "m3e_rotation"
    )

    // Breathing pulse scale
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 0.94f,
        targetValue = 1.06f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 800, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "m3e_pulse"
    )

    val currentMorphProgress = progress?.times(5f) ?: animMorphProgress
    val currentRotation = progress?.times(180f) ?: rotation
    val currentScale = if (progress != null) 0.6f + (progress * 0.4f) else pulseScale

    Canvas(
        modifier = modifier
            .size(size)
            .scale(currentScale)
            .rotate(currentRotation)
            .semantics {
                progressBarRangeInfo = ProgressBarRangeInfo(
                    current = progress ?: 0f,
                    range = 0f..1f
                )
            }
    ) {
        val centerX = size.toPx() / 2f
        val centerY = size.toPx() / 2f
        val baseRadius = (size.toPx() / 2f) * 0.88f

        val shapeStage = currentMorphProgress % 5f
        val shapeIndex = shapeStage.toInt()
        val stageFraction = shapeStage - shapeIndex

        // Smooth cubic easing between shape stages
        val easedFraction = FastOutSlowInEasing.transform(stageFraction)

        val nextIndex = (shapeIndex + 1) % 5

        val path = Path()
        val numSamples = 72
        val step = (2.0 * PI / numSamples).toFloat()

        for (i in 0 until numSamples) {
            val theta = i * step

            val r1 = calculateRadiusForShape(shapeIndex, theta, baseRadius)
            val r2 = calculateRadiusForShape(nextIndex, theta, baseRadius)

            // Interpolate radius between shapes
            val currentRadius = r1 + (r2 - r1) * easedFraction

            val x = centerX + currentRadius * cos(theta)
            val y = centerY + currentRadius * sin(theta)

            if (i == 0) {
                path.moveTo(x, y)
            } else {
                path.lineTo(x, y)
            }
        }
        path.close()

        drawPath(
            path = path,
            color = color,
            style = Fill
        )
    }
}

/**
 * Calculates radius for the 5 M3 Expressive shapes at angle theta.
 */
private fun calculateRadiusForShape(shapeIndex: Int, theta: Float, baseRadius: Float): Float {
    return when (shapeIndex) {
        // 0: Circle
        0 -> baseRadius * 0.90f

        // 1: 4-petal Rounded Clover / Flower
        1 -> baseRadius * (0.74f + 0.24f * cos(4f * theta))

        // 2: Squircle / Soft Rounded Square
        2 -> baseRadius * (0.84f + 0.14f * cos(4f * theta + PI.toFloat()))

        // 3: 4-point Rounded Star / Diamond
        3 -> baseRadius * (0.66f + 0.32f * cos(4f * theta))

        // 4: Rounded Pill / Capsule
        4 -> baseRadius * (0.78f + 0.20f * cos(2f * theta))

        else -> baseRadius * 0.90f
    }
}

/**
 * Material 3 Expressive Contained Loading Indicator.
 *
 * Places the morphing shape inside an elevated container, as specified in M3 Expressive.
 * Used for pull-to-refresh and high-emphasis loading states such as report submission.
 */
@Composable
fun CivicContainedLoadingIndicator(
    modifier: Modifier = Modifier,
    indicatorSize: Dp = 32.dp,
    containerSize: Dp = 56.dp,
    indicatorColor: Color = CivicGreen,
    containerColor: Color = MaterialTheme.colorScheme.surfaceContainerHigh,
    containerShape: Shape = RoundedCornerShape(18.dp),
    progress: Float? = null
) {
    Surface(
        modifier = modifier
            .size(containerSize)
            .shadow(elevation = 6.dp, shape = containerShape, clip = false),
        shape = containerShape,
        color = containerColor,
        tonalElevation = 4.dp
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier.padding(8.dp)
        ) {
            CivicLoadingIndicator(
                size = indicatorSize,
                color = indicatorColor,
                progress = progress
            )
        }
    }
}
