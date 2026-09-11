package com.civicsense.feature.report

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext

@Composable
fun ReportWizardScreen(
    viewModel: ReportViewModel,
    onFinishWizard: () -> Unit,
    onViewCreatedReport: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val uiState by viewModel.uiState.collectAsState()

    fun handleExitAttempt() {
        if (viewModel.isDraftDirty()) {
            viewModel.showDiscardConfirmation()
        } else {
            viewModel.discardDraftAndReset(context)
            onFinishWizard()
        }
    }

    // Discard Confirmation Dialog
    if (uiState.showDiscardDialog) {
        AlertDialog(
            onDismissRequest = { viewModel.dismissDiscardConfirmation() },
            title = { Text("Discard report draft?") },
            text = {
                Text("You have unsaved report details. Are you sure you want to discard this report and return to home?")
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        viewModel.dismissDiscardConfirmation()
                        viewModel.discardDraftAndReset(context)
                        onFinishWizard()
                    }
                ) {
                    Text("Discard", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { viewModel.dismissDiscardConfirmation() }) {
                    Text("Keep editing")
                }
            }
        )
    }

    // Step-by-step Back Navigation Handler
    BackHandler(enabled = uiState.currentStep != ReportStep.SUCCESS && uiState.currentStep != ReportStep.SUBMISSION_PROGRESS) {
        when (uiState.currentStep) {
            ReportStep.INTRO -> handleExitAttempt()
            ReportStep.IMAGE_CAPTURE, ReportStep.IMAGE_PREVIEW -> viewModel.setStep(ReportStep.INTRO)
            ReportStep.DESCRIPTION -> {
                viewModel.setStep(if (uiState.hasImage) ReportStep.IMAGE_PREVIEW else ReportStep.IMAGE_CAPTURE)
            }
            ReportStep.LOCATION -> viewModel.setStep(ReportStep.DESCRIPTION)
            ReportStep.REVIEW -> viewModel.setStep(ReportStep.LOCATION)
            else -> handleExitAttempt()
        }
    }

    AnimatedContent(
        targetState = uiState.currentStep,
        transitionSpec = { fadeIn() togetherWith fadeOut() },
        label = "report_wizard_steps",
        modifier = modifier
    ) { step ->
        when (step) {
            ReportStep.INTRO -> {
                ReportIntroScreen(
                    onStartReport = { viewModel.setStep(ReportStep.IMAGE_CAPTURE) },
                    onNavigateBack = { handleExitAttempt() }
                )
            }
            ReportStep.IMAGE_CAPTURE, ReportStep.IMAGE_PREVIEW -> {
                ImageCaptureScreen(
                    uiState = uiState,
                    onPrepareCameraUri = { viewModel.prepareCameraCaptureUri(context) },
                    onCameraSuccess = { viewModel.onCameraCaptured() },
                    onImageSelected = { uri -> viewModel.onImageSelected(uri) },
                    onSelectMockSample = { res, cat -> viewModel.onSelectMockSampleImage(res, cat) },
                    onRemoveImage = { viewModel.removeImage() },
                    onContinue = { viewModel.setStep(ReportStep.DESCRIPTION) },
                    onNavigateBack = { viewModel.setStep(ReportStep.INTRO) }
                )
            }
            ReportStep.DESCRIPTION -> {
                DescriptionScreen(
                    uiState = uiState,
                    onCategorySelected = { viewModel.selectCategory(it) },
                    onDescriptionChanged = { viewModel.updateDescription(it) },
                    onApplySuggestionTag = { viewModel.applySuggestionChip(it) },
                    onContinue = {
                        viewModel.validateDescriptionAndProceed()
                    },
                    onNavigateBack = {
                        viewModel.setStep(if (uiState.hasImage) ReportStep.IMAGE_PREVIEW else ReportStep.IMAGE_CAPTURE)
                    }
                )
            }
            ReportStep.LOCATION -> {
                LocationScreen(
                    uiState = uiState,
                    onUseCurrentLocation = { viewModel.requestDeviceLocation(context) },
                    onMapLocationSelected = { lat, lng -> viewModel.onMapLocationChanged(lat, lng, context) },
                    onManualLocationSaved = { address, pin -> viewModel.updateManualLocation(address, pin) },
                    onPermissionDenied = { viewModel.setLocationPermissionDenied() },
                    onConfirmLocation = { viewModel.setStep(ReportStep.REVIEW) },
                    onNavigateBack = { viewModel.setStep(ReportStep.DESCRIPTION) }
                )
            }
            ReportStep.REVIEW -> {
                ReviewScreen(
                    uiState = uiState,
                    onEditImage = {
                        viewModel.setStep(if (uiState.hasImage) ReportStep.IMAGE_PREVIEW else ReportStep.IMAGE_CAPTURE)
                    },
                    onEditDescription = { viewModel.setStep(ReportStep.DESCRIPTION) },
                    onEditLocation = { viewModel.setStep(ReportStep.LOCATION) },
                    onSubmitReport = { viewModel.submitReport() },
                    onNavigateBack = { viewModel.setStep(ReportStep.LOCATION) }
                )
            }
            ReportStep.SUBMISSION_PROGRESS -> {
                SubmissionProgressScreen(stage = uiState.submissionStage)
            }
            ReportStep.SUCCESS -> {
                uiState.createdReport?.let { created ->
                    ReportSuccessScreen(
                        report = created,
                        onViewReport = { reportId ->
                            viewModel.resetWizard()
                            onViewCreatedReport(reportId)
                        },
                        onReportAnother = {
                            viewModel.resetWizard()
                            viewModel.setStep(ReportStep.INTRO)
                        },
                        onBackToHome = {
                            viewModel.resetWizard()
                            onFinishWizard()
                        }
                    )
                }
            }
        }
    }
}
