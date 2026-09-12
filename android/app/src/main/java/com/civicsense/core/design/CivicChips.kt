package com.civicsense.core.design

import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.civicsense.core.theme.CivicGreen
import com.civicsense.core.theme.CivicGreenContainer
import com.civicsense.core.theme.civicColors
import com.civicsense.data.model.ImageProcessingStage
import com.civicsense.data.model.ImageProcessingState
import com.civicsense.data.model.ReportCategory
import com.civicsense.data.model.ReportStatus

@Composable
fun CivicStatusChip(
    status: ReportStatus,
    modifier: Modifier = Modifier
) {
    val (bgColor, textColor) = when (status) {
        ReportStatus.QUEUED_OFFLINE -> Pair(
            MaterialTheme.colorScheme.surfaceVariant,
            MaterialTheme.colorScheme.onSurfaceVariant
        )
        ReportStatus.SUBMITTED -> Pair(
            MaterialTheme.civicColors.successContainer,
            MaterialTheme.civicColors.onSuccessContainer
        )
        ReportStatus.UNDER_REVIEW -> Pair(
            MaterialTheme.civicColors.warningContainer,
            MaterialTheme.civicColors.onWarningContainer
        )
        ReportStatus.CONFIRMED -> Pair(
            MaterialTheme.colorScheme.tertiaryContainer,
            MaterialTheme.colorScheme.onTertiaryContainer
        )
        ReportStatus.ASSIGNED -> Pair(
            MaterialTheme.colorScheme.primaryContainer,
            MaterialTheme.colorScheme.onPrimaryContainer
        )
        ReportStatus.IN_PROGRESS -> Pair(
            MaterialTheme.civicColors.warningContainer,
            MaterialTheme.civicColors.onWarningContainer
        )
        ReportStatus.RESOLVED -> Pair(
            MaterialTheme.civicColors.successContainer,
            MaterialTheme.civicColors.onSuccessContainer
        )
        ReportStatus.CLOSED -> Pair(
            MaterialTheme.colorScheme.surfaceVariant,
            MaterialTheme.colorScheme.onSurfaceVariant
        )
    }

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(bgColor)
            .padding(horizontal = 8.dp, vertical = 4.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = status.displayName,
            style = MaterialTheme.typography.labelSmall,
            color = textColor
        )
    }
}

@Composable
fun CivicCategoryChip(
    category: ReportCategory,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.6f))
            .padding(horizontal = 8.dp, vertical = 3.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = category.shortName,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onPrimaryContainer
        )
    }
}

@Composable
fun CivicProcessingChip(
    state: ImageProcessingState,
    modifier: Modifier = Modifier
) {
    if (state.stage == ImageProcessingStage.IDLE) return

    val isReady = state.isComplete || state.stage == ImageProcessingStage.READY

    val bgColor = if (isReady) {
        MaterialTheme.civicColors.successContainer
    } else {
        MaterialTheme.colorScheme.surfaceVariant
    }

    val contentColor = if (isReady) {
        MaterialTheme.civicColors.onSuccessContainer
    } else {
        MaterialTheme.colorScheme.onSurfaceVariant
    }

    Box(
        modifier = modifier
            .clip(CircleShape)
            .background(bgColor)
            .border(1.dp, contentColor.copy(alpha = 0.2f), CircleShape)
            .padding(horizontal = 10.dp, vertical = 5.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically
        ) {
            AnimatedContent(
                targetState = isReady,
                label = "processing_icon"
            ) { ready ->
                if (ready) {
                    Icon(
                        imageVector = Icons.Default.Check,
                        contentDescription = "Ready",
                        modifier = Modifier.size(14.dp),
                        tint = contentColor
                    )
                } else {
                    CircularProgressIndicator(
                        modifier = Modifier.size(12.dp),
                        strokeWidth = 1.5.dp,
                        color = contentColor
                    )
                }
            }

            Spacer(modifier = Modifier.width(6.dp))

            Text(
                text = state.stage.label,
                style = MaterialTheme.typography.labelSmall,
                color = contentColor
            )
        }
    }
}

@Composable
fun CivicFilterChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val bgColor = if (selected) CivicGreen else MaterialTheme.colorScheme.surface
    val textColor = if (selected) Color.White else MaterialTheme.colorScheme.onSurface
    val borderColor = if (selected) CivicGreen else MaterialTheme.colorScheme.outline

    Box(
        modifier = modifier
            .clip(CircleShape)
            .background(bgColor)
            .border(1.dp, borderColor, CircleShape)
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 8.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = textColor
        )
    }
}
