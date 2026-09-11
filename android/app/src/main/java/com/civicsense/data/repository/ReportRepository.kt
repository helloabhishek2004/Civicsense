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
            listOf(report) + current
        }
    }

    suspend fun refreshReports(): RefreshResult {
        if (!isRefreshing.compareAndSet(false, true)) {
            // Already refreshing, ignore duplicate trigger cleanly
            return RefreshResult.Success(_reports.value.size)
        }
        return try {
            val fetchedReports = dataSource.fetchReports()
            if (fetchedReports.isEmpty()) {
                _reports.value = emptyList()
                RefreshResult.NoData
            } else {
                _reports.update { current ->
                    val combined = current + fetchedReports
                    combined.distinctBy { it.id }
                }
                RefreshResult.Success(_reports.value.size)
            }
        } catch (e: Exception) {
            RefreshResult.Error(e.message ?: "Failed to refresh civic reports", e)
        } finally {
            isRefreshing.set(false)
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
            ReportFilter.ACTIVE -> current.filter { it.status != ReportStatus.RESOLVED }
            ReportFilter.RESOLVED -> current.filter { it.status == ReportStatus.RESOLVED }
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

