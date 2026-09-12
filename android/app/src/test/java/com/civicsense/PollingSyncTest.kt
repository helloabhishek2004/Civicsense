package com.civicsense

import com.civicsense.data.model.Report
import com.civicsense.data.model.ReportCategory
import com.civicsense.data.model.ReportStatus
import com.civicsense.data.model.SeverityLevel
import com.civicsense.data.repository.ReportsDataSource
import com.civicsense.data.repository.ReportRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class PollingSyncTest {

    private lateinit var repository: ReportRepository

    @Before
    fun setUp() {
        repository = ReportRepository.getInstance()
        repository.resetDemoData()
    }

    @Test
    fun silentPolling_preservesQueuedOfflineReportsDuringBackgroundSync() = runTest {
        val offlineReport = Report(
            id = "CS-OFFLINE-SYNC-01",
            title = "Pothole saved offline",
            description = "Network was unavailable at submission",
            category = ReportCategory.ROAD_DAMAGE,
            status = ReportStatus.QUEUED_OFFLINE,
            severity = SeverityLevel.HIGH,
            dateTime = "12 Sep 2026, 09:00 AM"
        )
        repository.addReport(offlineReport)

        val serverReport = Report(
            id = "REP-202609-SERVER01",
            title = "Water Leakage",
            description = "Main line leaking",
            category = ReportCategory.WATER_LEAKAGE,
            status = ReportStatus.SUBMITTED,
            severity = SeverityLevel.MEDIUM,
            dateTime = "12 Sep 2026, 10:00 AM"
        )

        repository.setDataSource(object : ReportsDataSource {
            override suspend fun fetchReports(): List<Report> = listOf(serverReport)
        })

        // Execute silent background refresh
        val result = repository.refreshReports()
        assertTrue(result.isSuccess)

        // Verify offline report is retained in repository
        val offlineInRepo = repository.getReportById("CS-OFFLINE-SYNC-01")
        assertNotNull("QUEUED_OFFLINE report must be preserved across background syncs", offlineInRepo)
        assertEquals(ReportStatus.QUEUED_OFFLINE, offlineInRepo?.status)

        // Verify server report is added
        val serverInRepo = repository.getReportById("REP-202609-SERVER01")
        assertNotNull("Remote server report must be ingested", serverInRepo)
    }

    @Test
    fun silentPolling_updatesReportStatusWhenOfficerAdvancesLifecycle() = runTest {
        val testId = "REP-SYNC-LIFECYCLE"
        val submittedReport = Report(
            id = testId,
            title = "Damaged streetlight",
            description = "Light not functioning",
            category = ReportCategory.INFRASTRUCTURE,
            status = ReportStatus.SUBMITTED,
            severity = SeverityLevel.LOW,
            dateTime = "12 Sep 2026, 08:30 AM"
        )
        repository.addReport(submittedReport)

        // Server advances status to IN_PROGRESS
        val updatedReport = submittedReport.copy(
            status = ReportStatus.IN_PROGRESS,
            dateTime = "12 Sep 2026, 11:45 AM"
        )

        repository.setDataSource(object : ReportsDataSource {
            override suspend fun fetchReports(): List<Report> = listOf(updatedReport)
            override suspend fun fetchReport(identifier: String): Report? {
                return if (identifier == testId) updatedReport else null
            }
        })

        // Single detail fetch (as triggered by ReportDetailScreen silent polling)
        val fetchedDetail = repository.fetchReportDetail(testId)
        assertNotNull(fetchedDetail)
        assertEquals(ReportStatus.IN_PROGRESS, fetchedDetail?.status)
        assertEquals(ReportStatus.IN_PROGRESS, repository.getReportById(testId)?.status)
    }

    @Test
    fun silentPolling_concurrentRequestsDoNotOverlapOrCorruptCache() = runTest {
        val serverReport = Report(
            id = "REP-CONCURRENT-001",
            title = "Garbage dump",
            description = "Trash near market",
            category = ReportCategory.GARBAGE,
            status = ReportStatus.SUBMITTED,
            severity = SeverityLevel.MEDIUM,
            dateTime = "12 Sep 2026, 12:00 PM"
        )

        repository.setDataSource(object : ReportsDataSource {
            override suspend fun fetchReports(): List<Report> {
                kotlinx.coroutines.delay(50)
                return listOf(serverReport)
            }
        })

        // Launch 5 concurrent refresh invocations simulating rapid triggers
        val deferreds = (1..5).map {
            async { repository.refreshReports() }
        }
        val results = deferreds.awaitAll()

        // All should return cleanly without throwing or crashing
        assertTrue(results.all { it.isSuccess })
        assertEquals(1, repository.reports.value.filter { it.id == "REP-CONCURRENT-001" }.size)
    }
}
