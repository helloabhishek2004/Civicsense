package com.civicsense

import com.civicsense.data.model.ReportCategory
import com.civicsense.data.repository.ReportRepository
import com.civicsense.feature.report.ReportStep
import com.civicsense.feature.report.ReportViewModel
import com.civicsense.feature.report.SubmissionState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ReportViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var repository: ReportRepository
    private lateinit var viewModel: ReportViewModel

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        repository = ReportRepository.getInstance()
        repository.resetDemoData()
        viewModel = ReportViewModel(repository)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun initialState_isIntroWithNoDirtyDraft() {
        val state = viewModel.uiState.value
        assertEquals(ReportStep.INTRO, state.currentStep)
        assertFalse(state.hasImage)
        assertEquals("", state.description)
        assertEquals(ReportCategory.NOT_SURE, state.selectedCategory)
        assertNull(state.createdReport)
        assertFalse("Initial clean state should not be dirty", viewModel.isDraftDirty())
    }

    @Test
    fun draftDirtyState_detectsChangesAccurately() {
        assertFalse(viewModel.isDraftDirty())

        // Description change
        viewModel.updateDescription("Hazardous broken footpath")
        assertTrue(viewModel.isDraftDirty())
        viewModel.updateDescription("")
        assertFalse(viewModel.isDraftDirty())

        // Category change
        viewModel.selectCategory(ReportCategory.ROAD_DAMAGE)
        assertTrue(viewModel.isDraftDirty())
        viewModel.selectCategory(ReportCategory.NOT_SURE)
        assertFalse(viewModel.isDraftDirty())

        // Location manual update
        viewModel.updateManualLocation("Kariavattom", "695581")
        assertTrue(viewModel.isDraftDirty())
    }

    @Test
    fun discardDialog_managesConfirmationLifecycle() {
        assertFalse(viewModel.uiState.value.showDiscardDialog)

        viewModel.showDiscardConfirmation()
        assertTrue(viewModel.uiState.value.showDiscardDialog)

        viewModel.dismissDiscardConfirmation()
        assertFalse(viewModel.uiState.value.showDiscardDialog)

        // Dirty draft discarded
        viewModel.updateDescription("Draft to be discarded")
        viewModel.discardDraftAndReset()
        val resetState = viewModel.uiState.value
        assertEquals("", resetState.description)
        assertFalse(viewModel.isDraftDirty())
    }

    @Test
    fun stepTransitions_workCorrectly() {
        viewModel.setStep(ReportStep.IMAGE_CAPTURE)
        assertEquals(ReportStep.IMAGE_CAPTURE, viewModel.uiState.value.currentStep)

        viewModel.setStep(ReportStep.DESCRIPTION)
        assertEquals(ReportStep.DESCRIPTION, viewModel.uiState.value.currentStep)
    }

    @Test
    fun descriptionValidation_requiresMinimumLength() {
        viewModel.updateDescription("hi")
        val result = viewModel.validateDescriptionAndProceed()
        assertFalse(result)
        assertNotNull(viewModel.uiState.value.descriptionError)

        viewModel.updateDescription("Large pothole causing vehicle damage near bus stop")
        val success = viewModel.validateDescriptionAndProceed()
        assertTrue(success)
        assertNull(viewModel.uiState.value.descriptionError)
        assertEquals(ReportStep.LOCATION, viewModel.uiState.value.currentStep)
    }

    @Test
    fun appendQuickPhrase_insertsAndAppendsIntelligently() {
        // Appending to blank description
        viewModel.appendQuickPhrase("Large pothole on the road")
        assertEquals("Large pothole on the road", viewModel.uiState.value.description)

        // Appending additional phrase
        viewModel.appendQuickPhrase("Road is damaged and difficult to use")
        assertEquals(
            "Large pothole on the road. Road is damaged and difficult to use",
            viewModel.uiState.value.description
        )
    }

    @Test
    fun applySuggestionChip_delegatesToQuickPhrase() {
        viewModel.applySuggestionChip("Garbage has been dumped here")
        assertEquals("Garbage has been dumped here", viewModel.uiState.value.description)
    }

    @Test
    fun updateManualLocation_setsManualSourceAndStatus() {
        viewModel.updateManualLocation("Near Central Library", "695001")
        val loc = viewModel.uiState.value.reportLocation
        assertEquals("Near Central Library", loc.address)
        assertEquals("695001", loc.postalPin)
        assertEquals(com.civicsense.data.model.LocationSource.MANUAL, loc.source)
        assertEquals(com.civicsense.data.model.LocationStatus.MANUAL, viewModel.uiState.value.locationStatus)
    }

    @Test
    fun onSelectMockSampleImage_updatesStateAndStartsProcessing() = runTest {
        viewModel.onSelectMockSampleImage(R.drawable.img_pothole_sample, ReportCategory.ROAD_DAMAGE)

        val state = viewModel.uiState.value
        assertTrue(state.hasImage)
        assertEquals(ReportCategory.ROAD_DAMAGE, state.selectedCategory)
        assertEquals(ReportStep.IMAGE_PREVIEW, state.currentStep)

        // Advance coroutine virtual time to complete simulated image processing
        testDispatcher.scheduler.advanceUntilIdle()

        val processedState = viewModel.uiState.value
        assertTrue(processedState.imageProcessingState.isComplete)
    }

    @Test
    fun submitReport_createsAndAddsReportWithDemoIdFormat() = runTest {
        viewModel.updateDescription("Active water pipe burst gushing onto road")
        viewModel.onSelectMockSampleImage(R.drawable.img_water_sample, ReportCategory.WATER_LEAKAGE)
        viewModel.updateManualLocation("Sreekaryam Junction", "695017")

        viewModel.submitReport()

        // Advance coroutines through all submission stages
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.value
        assertEquals(ReportStep.SUCCESS, state.currentStep)
        assertNotNull(state.createdReport)

        val created = state.createdReport!!
        assertTrue("Report ID must follow CS-DEMO-XXXXX format, was: ${created.id}", created.id.startsWith("CS-DEMO-"))
        assertEquals(ReportCategory.WATER_LEAKAGE, created.category)
        assertEquals("Sreekaryam Junction", created.address)
        assertEquals("695017", created.postalPin)

        val repoReport = repository.getReportById(created.id)
        assertNotNull("Submitted report must be in repository", repoReport)
        assertEquals(created, repoReport)
        assertEquals(SubmissionState.SUCCESS, state.submissionState)
        assertFalse(state.isSubmitting)
    }

    @Test
    fun submitReport_duplicateCallIsIgnored() = runTest {
        viewModel.updateDescription("Garbage piling up on pavement")
        viewModel.updateManualLocation("Palayam", "695034")

        val initialCount = repository.reports.value.size

        // First call submits
        viewModel.submitReport()
        // Immediate second call should be ignored (duplicate prevention)
        viewModel.submitReport()

        testDispatcher.scheduler.advanceUntilIdle()

        val newCount = repository.reports.value.size
        assertEquals("Duplicate submit should not create multiple reports", initialCount + 1, newCount)
        assertEquals(SubmissionState.SUCCESS, viewModel.uiState.value.submissionState)
    }

    @Test
    fun resetWizard_restoresBlankState() {
        viewModel.updateDescription("Some issue")
        viewModel.setStep(ReportStep.REVIEW)

        viewModel.resetWizard()

        val state = viewModel.uiState.value
        assertEquals(ReportStep.INTRO, state.currentStep)
        assertEquals("", state.description)
        assertNull(state.createdReport)
        assertEquals(SubmissionState.IDLE, state.submissionState)
    }
}
