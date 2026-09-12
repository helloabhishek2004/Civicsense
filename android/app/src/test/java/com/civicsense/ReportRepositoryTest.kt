package com.civicsense

import com.civicsense.data.model.Report
import com.civicsense.data.model.ReportCategory
import com.civicsense.data.model.ReportStatus
import com.civicsense.data.model.SeverityLevel
import com.civicsense.data.repository.ReportFilter
import com.civicsense.data.repository.ReportRepository
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class ReportRepositoryTest {

    private lateinit var repository: ReportRepository

    @Before
    fun setUp() {
        repository = ReportRepository.getInstance()
        repository.resetDemoData()
    }

    @Test
    fun initialSeedReports_containsAtLeastFiveReports() {
        val reports = repository.reports.value
        assertTrue("Seed reports must contain at least 5 reports", reports.size >= 5)
    }

    @Test
    fun initialSeedReports_coversCoreCategories() {
        val reports = repository.reports.value
        val categories = reports.map { it.category }.toSet()

        assertTrue(categories.contains(ReportCategory.ROAD_DAMAGE))
        assertTrue(categories.contains(ReportCategory.GARBAGE))
        assertTrue(categories.contains(ReportCategory.WATER_LEAKAGE))
        assertTrue(categories.contains(ReportCategory.INFRASTRUCTURE))
    }

    @Test
    fun filtering_worksCorrectly() {
        val allReports = repository.getFilteredReports(ReportFilter.ALL)
        val activeReports = repository.getFilteredReports(ReportFilter.ACTIVE)
        val resolvedReports = repository.getFilteredReports(ReportFilter.RESOLVED)

        assertEquals(allReports.size, activeReports.size + resolvedReports.size)
        assertTrue(resolvedReports.all { it.status == ReportStatus.RESOLVED })
        assertTrue(activeReports.all { it.status != ReportStatus.RESOLVED })
    }

    @Test
    fun addReport_prependsAndUpdatesStateFlow() {
        val initialCount = repository.reports.value.size

        val newReport = Report(
            id = "CS-2026-TEST-999",
            title = "Test Pothole Report",
            description = "Test Description for civic verification",
            category = ReportCategory.ROAD_DAMAGE,
            status = ReportStatus.SUBMITTED,
            severity = SeverityLevel.HIGH,
            dateTime = "11 Sep 2026, 12:00 PM",
            address = "Kariavattom",
            postalPin = "695581",
            latitude = 8.5615,
            longitude = 76.8850
        )

        repository.addReport(newReport)

        val updatedReports = repository.reports.value
        assertEquals(initialCount + 1, updatedReports.size)
        assertEquals("CS-2026-TEST-999", updatedReports.first().id)
        assertEquals(newReport, repository.getReportById("CS-2026-TEST-999"))
    }

    @Test
    fun resetDemoData_restoresOriginalSeedCount() {
        val initialCount = repository.reports.value.size

        val dummy = Report(
            id = "CS-DUMMY",
            title = "Dummy",
            description = "Dummy",
            category = ReportCategory.OTHER,
            status = ReportStatus.SUBMITTED,
            severity = SeverityLevel.LOW,
            dateTime = "11 Sep 2026",
            address = "Test",
            postalPin = "695581",
            latitude = 8.0,
            longitude = 76.0
        )
        repository.addReport(dummy)
        assertEquals(initialCount + 1, repository.reports.value.size)

        repository.resetDemoData()
        assertEquals(initialCount, repository.reports.value.size)
    }

    @Test
    fun refreshReports_succeedsAndDeduplicates() = kotlinx.coroutines.test.runTest {
        val result = repository.refreshReports()
        assertTrue(result.isSuccess)
        assertTrue(result is com.civicsense.data.repository.RefreshResult.Success)
        val reports = repository.reports.value
        assertEquals(reports.distinctBy { it.id }.size, reports.size)
    }

    @Test
    fun refreshReports_handlesEmptyDataSourceReturnsNoData() = kotlinx.coroutines.test.runTest {
        repository.setDataSource(object : com.civicsense.data.repository.ReportsDataSource {
            override suspend fun fetchReports(): List<Report> = emptyList()
        })

        val result = repository.refreshReports()
        assertTrue(result is com.civicsense.data.repository.RefreshResult.NoData)
        assertTrue(repository.reports.value.isEmpty())
    }

    @Test
    fun refreshReports_handlesDataSourceErrorGracefully() = kotlinx.coroutines.test.runTest {
        val initialReports = repository.reports.value
        repository.setDataSource(object : com.civicsense.data.repository.ReportsDataSource {
            override suspend fun fetchReports(): List<Report> {
                throw java.io.IOException("Network unavailable")
            }
        })

        val result = repository.refreshReports()
        assertTrue("Error result expected on exception", result is com.civicsense.data.repository.RefreshResult.Error)
        val errorResult = result as com.civicsense.data.repository.RefreshResult.Error
        assertEquals("Network unavailable", errorResult.message)
        assertEquals("Existing reports must be preserved on refresh failure", initialReports, repository.reports.value)
    }

    @Test
    fun refreshReports_overwritesStaleLocalReportWithUpdatedServerStatus() = kotlinx.coroutines.test.runTest {
        val testId = "REP-SYNC-UPDATE-001"
        val localStaleReport = Report(
            id = testId,
            title = "Pothole",
            description = "Pothole on road",
            category = ReportCategory.ROAD_DAMAGE,
            status = ReportStatus.SUBMITTED,
            severity = SeverityLevel.HIGH,
            dateTime = "12 Sep 2026, 10:00 AM"
        )
        repository.addReport(localStaleReport)
        assertEquals(ReportStatus.SUBMITTED, repository.getReportById(testId)?.status)

        val serverUpdatedReport = localStaleReport.copy(
            status = ReportStatus.IN_PROGRESS,
            serverStatus = "IN_PROGRESS"
        )

        repository.setDataSource(object : com.civicsense.data.repository.ReportsDataSource {
            override suspend fun fetchReports(): List<Report> = listOf(serverUpdatedReport)
        })

        repository.refreshReports()

        val updated = repository.getReportById(testId)
        assertNotNull(updated)
        assertEquals(ReportStatus.IN_PROGRESS, updated?.status)
        assertEquals("IN_PROGRESS", updated?.serverStatus)
    }

    @Test
    fun refreshReports_preservesQueuedOfflineReport() = kotlinx.coroutines.test.runTest {
        val offlineId = "CS-OFFLINE-99999"
        val offlineReport = Report(
            id = offlineId,
            title = "Offline issue",
            description = "Report captured without network",
            category = ReportCategory.GARBAGE,
            status = ReportStatus.QUEUED_OFFLINE,
            severity = SeverityLevel.MEDIUM,
            dateTime = "12 Sep 2026, 10:30 AM"
        )
        repository.addReport(offlineReport)

        val serverReport = Report(
            id = "REP-SERVER-12345",
            title = "Server issue",
            description = "Server report",
            category = ReportCategory.WATER_LEAKAGE,
            status = ReportStatus.SUBMITTED,
            severity = SeverityLevel.LOW,
            dateTime = "12 Sep 2026, 09:00 AM"
        )

        repository.setDataSource(object : com.civicsense.data.repository.ReportsDataSource {
            override suspend fun fetchReports(): List<Report> = listOf(serverReport)
        })

        repository.refreshReports()

        assertNotNull("Offline report must survive remote refresh", repository.getReportById(offlineId))
        assertNotNull("Server report must be added", repository.getReportById("REP-SERVER-12345"))
    }

    @Test
    fun filtering_includesClosedReportsInResolvedFilter() {
        val closedReport = Report(
            id = "REP-CLOSED-999",
            title = "Fixed light",
            description = "Streetlight replaced and closed",
            category = ReportCategory.INFRASTRUCTURE,
            status = ReportStatus.CLOSED,
            severity = SeverityLevel.LOW,
            dateTime = "12 Sep 2026, 11:00 AM"
        )
        repository.addReport(closedReport)

        val active = repository.getFilteredReports(ReportFilter.ACTIVE)
        val resolved = repository.getFilteredReports(ReportFilter.RESOLVED)

        assertFalse("Active filter must exclude CLOSED reports", active.any { it.id == "REP-CLOSED-999" })
        assertTrue("Resolved filter must include CLOSED reports", resolved.any { it.id == "REP-CLOSED-999" })
    }

    @Test
    fun fetchReportDetail_updatesCacheWithFreshServerReport() = kotlinx.coroutines.test.runTest {
        val testId = "REP-DETAIL-001"
        val initial = Report(
            id = testId,
            title = "Test Pothole",
            description = "Description",
            category = ReportCategory.ROAD_DAMAGE,
            status = ReportStatus.SUBMITTED,
            severity = SeverityLevel.HIGH,
            dateTime = "12 Sep 2026, 10:00 AM"
        )
        repository.addReport(initial)

        val freshServerVersion = initial.copy(status = ReportStatus.RESOLVED)
        repository.setDataSource(object : com.civicsense.data.repository.ReportsDataSource {
            override suspend fun fetchReports(): List<Report> = listOf(freshServerVersion)
            override suspend fun fetchReport(identifier: String): Report? {
                return if (identifier == testId) freshServerVersion else null
            }
        })

        val fetched = repository.fetchReportDetail(testId)
        assertNotNull(fetched)
        assertEquals(ReportStatus.RESOLVED, fetched?.status)
        assertEquals(ReportStatus.RESOLVED, repository.getReportById(testId)?.status)
    }

    @Test
    fun refreshReports_preservesInstanceWhenDataUnchanged() = kotlinx.coroutines.test.runTest {
        val testReport = Report(
            id = "REP-UNCHANGED-001",
            title = "Test Pothole",
            description = "Description",
            category = ReportCategory.ROAD_DAMAGE,
            status = ReportStatus.SUBMITTED,
            severity = SeverityLevel.HIGH,
            dateTime = "12 Sep 2026, 10:00 AM"
        )
        repository.setDataSource(object : com.civicsense.data.repository.ReportsDataSource {
            override suspend fun fetchReports(): List<Report> = listOf(testReport)
        })

        repository.refreshReports()
        val firstState = repository.reports.value

        // Second refresh with identical data
        repository.refreshReports()
        val secondState = repository.reports.value

        // Verify referential identity: StateFlow was not re-emitted
        assertTrue("StateFlow instance must be preserved when data is identical", firstState === secondState)
    }

    @Test
    fun fetchReportDetail_preservesInstanceWhenDetailUnchanged() = kotlinx.coroutines.test.runTest {
        val testId = "REP-UNCHANGED-002"
        val testReport = Report(
            id = testId,
            title = "Test Pothole",
            description = "Description",
            category = ReportCategory.ROAD_DAMAGE,
            status = ReportStatus.SUBMITTED,
            severity = SeverityLevel.HIGH,
            dateTime = "12 Sep 2026, 10:00 AM"
        )
        repository.setDataSource(object : com.civicsense.data.repository.ReportsDataSource {
            override suspend fun fetchReports(): List<Report> = listOf(testReport)
            override suspend fun fetchReport(identifier: String): Report? = testReport
        })

        repository.refreshReports()
        val firstState = repository.reports.value

        val fetched = repository.fetchReportDetail(testId)
        assertNotNull(fetched)
        val secondState = repository.reports.value

        assertTrue("StateFlow list should remain identical when detail matches cache", firstState === secondState)
    }
}

