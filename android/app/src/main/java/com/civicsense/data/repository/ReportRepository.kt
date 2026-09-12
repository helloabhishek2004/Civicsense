package com.civicsense.data.repository

import com.civicsense.data.mock.MockReports
import com.civicsense.data.model.Report
import com.civicsense.data.model.ReportStatus
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import java.util.concurrent.atomic.AtomicBoolean

enum class ReportFilter(val label: String) {
    ALL("All"),
    ACTIVE("Active"),
    RESOLVED("Resolved")
}

/**
 * Result representing the outcome of a repository refresh operation.
 */
sealed interface RefreshResult {
    data class Success(val count: Int) : RefreshResult
    data object NoData : RefreshResult
    data class Error(val message: String, val cause: Throwable? = null) : RefreshResult

    val isSuccess: Boolean
        get() = this is Success || this is NoData
}

/**
 * Data source contract for retrieving reports.
 * Allows switching seamlessly between in-memory/local storage and remote backend APIs.
 */
interface ReportsDataSource {
    suspend fun fetchReports(): List<Report>
    suspend fun fetchReport(identifier: String): Report? = null
}

/**
 * Default local in-memory data source using mock seeds and cached reports.
 */
class LocalReportsDataSource(
    private val seedSupplier: () -> List<Report> = { MockReports.getInitialSeedReports() }
) : ReportsDataSource {
    override suspend fun fetchReports(): List<Report> {
        return seedSupplier()
    }

    override suspend fun fetchReport(identifier: String): Report? {
        return seedSupplier().find { it.id == identifier }
    }
}

class ReportRepository private constructor(
    private var dataSource: ReportsDataSource = LocalReportsDataSource()
) {

    private val _reports = MutableStateFlow<List<Report>>(MockReports.getInitialSeedReports())
    val reports: StateFlow<List<Report>> = _reports.asStateFlow()

    private val isRefreshing = AtomicBoolean(false)

    fun setDataSource(newDataSource: ReportsDataSource) {
        this.dataSource = newDataSource
    }

    fun getReportById(id: String): Report? {
        return _reports.value.find { it.id == id }
    }

    fun addReport(report: Report) {
        _reports.update { current ->
            val withoutDuplicate = current.filter { it.id != report.id }
            listOf(report) + withoutDuplicate
        }
    }

    suspend fun refreshReports(): RefreshResult {
        if (!isRefreshing.compareAndSet(false, true)) {
            // Already refreshing, ignore duplicate trigger cleanly
            return RefreshResult.Success(_reports.value.size)
        }
        return try {
            val fetchedReports = dataSource.fetchReports()
            _reports.update { current ->
                val queuedOffline = current.filter { it.status == ReportStatus.QUEUED_OFFLINE }
                val serverMap = fetchedReports.associateBy { it.id }
                val offlinePreserved = queuedOffline.filter { it.id !in serverMap }
                val merged = (offlinePreserved + fetchedReports).sortedByDescending { it.dateTime }
                if (current == merged) current else merged
            }
            if (_reports.value.isEmpty()) {
                RefreshResult.NoData
            } else {
                RefreshResult.Success(_reports.value.size)
            }
        } catch (e: Exception) {
            RefreshResult.Error(e.message ?: "Failed to refresh civic reports", e)
        } finally {
            isRefreshing.set(false)
        }
    }

    suspend fun fetchReportDetail(identifier: String): Report? {
        val cached = getReportById(identifier)
        return try {
            val remote = dataSource.fetchReport(identifier)
            if (remote != null) {
                _reports.update { current ->
                    val existing = current.find { it.id == remote.id }
                    if (existing == remote) {
                        current
                    } else {
                        val map = current.associateBy { it.id }.toMutableMap()
                        map[remote.id] = remote
                        map.values.sortedByDescending { it.dateTime }
                    }
                }
                remote
            } else {
                cached
            }
        } catch (_: Exception) {
            cached
        }
    }

    fun resetDemoData() {
        this.dataSource = LocalReportsDataSource()
        _reports.value = MockReports.getInitialSeedReports()
    }

    fun getFilteredReports(filter: ReportFilter): List<Report> {
        val current = _reports.value
        return when (filter) {
            ReportFilter.ALL -> current
            ReportFilter.ACTIVE -> current.filter { it.status != ReportStatus.RESOLVED && it.status != ReportStatus.CLOSED }
            ReportFilter.RESOLVED -> current.filter { it.status == ReportStatus.RESOLVED || it.status == ReportStatus.CLOSED }
        }
    }

    companion object {
        @Volatile
        private var instance: ReportRepository? = null

        fun getInstance(): ReportRepository {
            return instance ?: synchronized(this) {
                instance ?: ReportRepository().also { instance = it }
            }
        }
    }
}

