package com.civicsense.feature.reports

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.PullToRefreshDefaults
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import android.util.Log
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.repeatOnLifecycle
import com.civicsense.core.design.CivicEmptyState
import com.civicsense.core.design.CivicFilterChip
import com.civicsense.core.design.CivicReportCard
import com.civicsense.data.model.Report
import com.civicsense.data.model.ReportStatus
import com.civicsense.data.repository.RefreshResult
import com.civicsense.data.repository.ReportFilter
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

private const val MY_REPORTS_POLL_INTERVAL_MS = 10_000L

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MyReportsScreen(
    reports: List<Report>,
    onReportClick: (String) -> Unit,
    onStartReport: () -> Unit,
    modifier: Modifier = Modifier,
    onRefresh: (suspend () -> RefreshResult)? = null
) {
    var selectedFilter by rememberSaveable { mutableStateOf(ReportFilter.ALL) }
    val scope = rememberCoroutineScope()
    var isRefreshing by rememberSaveable { mutableStateOf(false) }
    val pullToRefreshState = rememberPullToRefreshState()
    val snackbarHostState = remember { SnackbarHostState() }
    val lifecycleOwner = LocalLifecycleOwner.current

    val filteredReports = when (selectedFilter) {
        ReportFilter.ALL -> reports
        ReportFilter.ACTIVE -> reports.filter { it.status != ReportStatus.RESOLVED && it.status != ReportStatus.CLOSED }
        ReportFilter.RESOLVED -> reports.filter { it.status == ReportStatus.RESOLVED || it.status == ReportStatus.CLOSED }
    }

    // Initial refresh on first composition if list is empty
    LaunchedEffect(Unit) {
        if (reports.isEmpty()) {
            isRefreshing = true
            try {
                onRefresh?.invoke()
            } catch (_: Throwable) {
            } finally {
                isRefreshing = false
            }
        }
    }

    // Lifecycle-aware, visibility-aware silent polling while RESUMED
    LaunchedEffect(lifecycleOwner) {
        if (onRefresh == null) return@LaunchedEffect
        lifecycleOwner.repeatOnLifecycle(Lifecycle.State.RESUMED) {
            while (isActive) {
                delay(MY_REPORTS_POLL_INTERVAL_MS)
                try {
                    onRefresh.invoke()
                } catch (e: Exception) {
                    Log.d("CivicSenseSync", "Silent my-reports polling skipped on error: ${e.message}")
                }
            }
        }
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "My Reports",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        }
    ) { innerPadding ->
        PullToRefreshBox(
            isRefreshing = isRefreshing,
            onRefresh = {
                if (isRefreshing) return@PullToRefreshBox
                scope.launch {
                    isRefreshing = true
                    try {
                        when (val result = onRefresh?.invoke()) {
                            is RefreshResult.Error -> {
                                snackbarHostState.showSnackbar(
                                    message = result.message.ifBlank { "Could not refresh reports. Please try again." },
                                    duration = SnackbarDuration.Short
                                )
                            }
                            else -> Unit
                        }
                    } catch (t: Throwable) {
                        snackbarHostState.showSnackbar(
                            message = t.localizedMessage ?: "Failed to refresh",
                            duration = SnackbarDuration.Short
                        )
                    } finally {
                        isRefreshing = false
                    }
                }
            },
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
            state = pullToRefreshState,
            indicator = {
                PullToRefreshDefaults.Indicator(
                    state = pullToRefreshState,
                    isRefreshing = isRefreshing,
                    modifier = Modifier.align(Alignment.TopCenter),
                    containerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        ) {
            Column(
                modifier = Modifier.fillMaxSize()
            ) {
                // Filter Chips Row
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 20.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    CivicFilterChip(
                        label = "All (${reports.size})",
                        selected = selectedFilter == ReportFilter.ALL,
                        onClick = { selectedFilter = ReportFilter.ALL }
                    )
                    CivicFilterChip(
                        label = "Active (${reports.count { it.status != ReportStatus.RESOLVED && it.status != ReportStatus.CLOSED }})",
                        selected = selectedFilter == ReportFilter.ACTIVE,
                        onClick = { selectedFilter = ReportFilter.ACTIVE }
                    )
                    CivicFilterChip(
                        label = "Resolved (${reports.count { it.status == ReportStatus.RESOLVED || it.status == ReportStatus.CLOSED }})",
                        selected = selectedFilter == ReportFilter.RESOLVED,
                        onClick = { selectedFilter = ReportFilter.RESOLVED }
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                if (filteredReports.isEmpty()) {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.Center,
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        item {
                            CivicEmptyState(
                                title = "No reports yet",
                                description = if (selectedFilter == ReportFilter.ALL) {
                                    "When you report a civic issue, it will appear here with live tracking updates."
                                } else {
                                    "There are currently no reports in the ${selectedFilter.label.lowercase()} state."
                                },
                                actionText = "Report an issue",
                                onActionClick = onStartReport
                            )
                        }
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 20.dp)
                    ) {
                        items(filteredReports, key = { it.id }) { report ->
                            CivicReportCard(
                                report = report,
                                onClick = { onReportClick(report.id) },
                                modifier = Modifier.padding(vertical = 6.dp)
                            )
                        }
                        item {
                            Spacer(modifier = Modifier.height(24.dp))
                        }
                    }
                }
            }
        }
    }
}
