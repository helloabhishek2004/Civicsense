package com.civicsense.feature.reports

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Place
import androidx.compose.material.icons.outlined.CalendarToday
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.civicsense.R
import android.util.Log
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.repeatOnLifecycle
import com.civicsense.core.design.CivicCategoryChip
import com.civicsense.core.design.CivicStatusChip
import com.civicsense.core.design.CivicTimeline
import com.civicsense.core.design.CivicTopAppBar
import com.civicsense.core.theme.CivicGreen
import com.civicsense.data.model.Report
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

private const val REPORT_DETAIL_POLL_INTERVAL_MS = 6_000L

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportDetailScreen(
    report: Report?,
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier,
    onRefreshDetail: (suspend () -> Report?)? = null
) {
    var activeReport by remember(report) { mutableStateOf(report) }
    var isRefreshing by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val pullToRefreshState = rememberPullToRefreshState()
    val lifecycleOwner = LocalLifecycleOwner.current

    // Initial detail refresh on first mount
    LaunchedEffect(report?.id) {
        if (onRefreshDetail != null) {
            isRefreshing = true
            try {
                val fresh = onRefreshDetail()
                if (fresh != null) {
                    activeReport = fresh
                }
            } catch (_: Throwable) {
            } finally {
                isRefreshing = false
            }
        }
    }

    // Lifecycle-aware, visibility-aware silent polling while RESUMED
    LaunchedEffect(lifecycleOwner, report?.id) {
        val reportId = report?.id
        if (reportId.isNullOrBlank() || onRefreshDetail == null) return@LaunchedEffect
        lifecycleOwner.repeatOnLifecycle(Lifecycle.State.RESUMED) {
            while (isActive) {
                delay(REPORT_DETAIL_POLL_INTERVAL_MS)
                try {
                    val fresh = onRefreshDetail()
                    if (fresh != null && fresh != activeReport) {
                        activeReport = fresh
                    }
                } catch (e: Exception) {
                    Log.d("CivicSenseSync", "Silent detail polling skipped on error: ${e.message}")
                }
            }
        }
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            CivicTopAppBar(
                title = "Report details",
                canNavigateBack = true,
                onNavigateBack = onNavigateBack
            )
        }
    ) { innerPadding ->
        val currentReport = activeReport
        if (currentReport == null) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
                contentAlignment = Alignment.Center
            ) {
                if (isRefreshing) {
                    CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                } else {
                    Text(
                        text = "Report not found",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        } else {
            PullToRefreshBox(
                isRefreshing = isRefreshing,
                onRefresh = {
                    if (isRefreshing || onRefreshDetail == null) return@PullToRefreshBox
                    scope.launch {
                        isRefreshing = true
                        try {
                            val fresh = onRefreshDetail()
                            if (fresh != null) {
                                activeReport = fresh
                            }
                        } catch (_: Throwable) {
                        } finally {
                            isRefreshing = false
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
                state = pullToRefreshState
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 20.dp)
                        .verticalScroll(rememberScrollState())
                ) {
                    // Large Image Card
                    OutlinedCard(
                        modifier = Modifier
                            .fillMaxWidth()
                            .aspectRatio(16f / 10f),
                        shape = MaterialTheme.shapes.large
                    ) {
                        Box(modifier = Modifier.fillMaxSize()) {
                            if (currentReport.imageUri != null) {
                                AsyncImage(
                                    model = currentReport.imageUri,
                                    contentDescription = currentReport.title,
                                    modifier = Modifier.fillMaxSize(),
                                    contentScale = ContentScale.Crop
                                )
                            } else if (currentReport.mockImageDrawableRes != null) {
                                Image(
                                    painter = painterResource(id = currentReport.mockImageDrawableRes),
                                    contentDescription = currentReport.title,
                                    modifier = Modifier.fillMaxSize(),
                                    contentScale = ContentScale.Crop
                                )
                            } else {
                                Icon(
                                    painter = painterResource(id = R.drawable.ic_civicsense_path_logo),
                                    contentDescription = null,
                                    modifier = Modifier
                                        .size(64.dp)
                                        .align(Alignment.Center),
                                    tint = MaterialTheme.colorScheme.primary
                                )
                            }
                        }
                    }

                Spacer(modifier = Modifier.height(20.dp))

                // Metadata Row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = currentReport.id,
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                    CivicStatusChip(status = currentReport.status)
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Title
                Text(
                    text = currentReport.title,
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onBackground
                )

                Spacer(modifier = Modifier.height(10.dp))

                // Date & Location Info Row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Outlined.CalendarToday,
                        contentDescription = null,
                        modifier = Modifier.size(15.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = currentReport.dateTime,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Spacer(modifier = Modifier.height(6.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Place,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                        tint = CivicGreen
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    val pinText = if (currentReport.postalPin.isNotBlank()) " (PIN: ${currentReport.postalPin})" else ""
                    Text(
                        text = "${currentReport.address}$pinText",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Category & Severity
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    CivicCategoryChip(category = currentReport.category)
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(6.dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant)
                            .padding(horizontal = 8.dp, vertical = 3.dp)
                    ) {
                        Text(
                            text = "Severity: ${currentReport.severity.displayName}",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Spacer(modifier = Modifier.height(20.dp))

                // Description Card
                OutlinedCard(
                    modifier = Modifier.fillMaxWidth(),
                    shape = MaterialTheme.shapes.medium
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Citizen Description",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = currentReport.description,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface,
                            lineHeight = MaterialTheme.typography.bodyLarge.lineHeight
                        )
                    }
                }

                Spacer(modifier = Modifier.height(28.dp))

                // Status Timeline Section
                Text(
                    text = "Resolution Timeline",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onBackground
                )

                Spacer(modifier = Modifier.height(16.dp))

                CivicTimeline(stages = currentReport.timeline)

                Spacer(modifier = Modifier.height(32.dp))
            }
        }
    }
}
}
