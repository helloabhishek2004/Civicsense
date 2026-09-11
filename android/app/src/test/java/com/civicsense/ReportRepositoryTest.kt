package com.civicsense

import com.civicsense.data.model.Report
import com.civicsense.data.model.ReportCategory
import com.civicsense.data.model.ReportStatus
import com.civicsense.data.model.SeverityLevel
import com.civicsense.data.repository.ReportFilter
import com.civicsense.data.repository.ReportRepository
import org.junit.Assert.assertEquals
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
}
