package com.civicsense.feature.report

import android.content.Context
import android.net.Uri
import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.civicsense.BuildConfig
import com.civicsense.core.util.CameraHelper
import com.civicsense.core.util.InputValidators
import com.civicsense.core.util.LocationHelper
import com.civicsense.data.model.ImageProcessingStage
import com.civicsense.data.model.ImageProcessingState
import com.civicsense.data.model.ImageQualityFeedback
import com.civicsense.data.model.LocationSource
import com.civicsense.data.model.LocationStatus
import com.civicsense.data.model.Report
import com.civicsense.data.model.ReportCategory
import com.civicsense.data.model.ReportLocation
import com.civicsense.data.model.ReportStatus
import com.civicsense.data.model.SeverityLevel
import com.civicsense.data.model.TimelineStage
import com.civicsense.data.repository.PreferenceRepository
import com.civicsense.data.repository.ReportRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

import com.civicsense.core.edge.CivicImagePreprocessor
import com.civicsense.core.edge.CivicSenseEdgeProcessor
import com.civicsense.core.edge.ImageQualityMetrics
import com.civicsense.core.edge.ProcessedReportPackage
import com.civicsense.core.network.CivicReportUploadClient
import com.civicsense.core.network.UploadResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

enum class ReportStep {
    INTRO,
    IMAGE_CAPTURE,
    IMAGE_PREVIEW,
    DESCRIPTION,
    LOCATION,
    REVIEW,
    SUBMISSION_PROGRESS,
    SUCCESS
}

enum class SubmissionState {
    IDLE,
    SUBMITTING,
    SUCCESS,
    QUEUED_OFFLINE,
    ERROR
}

enum class SubmissionStage(val label: String) {
    PREPARING("Preparing report…"),
    UPLOADING("Uploading evidence…"),
    SAVING("Saving report…"),
    RECEIVED("Report received")
}

data class ReportUiState(
    val currentStep: ReportStep = ReportStep.INTRO,
    val selectedImageUri: Uri? = null,
    val mockImageDrawableRes: Int? = null,
    val hasImage: Boolean = false,
    val imageProcessingState: ImageProcessingState = ImageProcessingState(),
    val imageMetrics: ImageQualityMetrics? = null,
    val edgePackage: ProcessedReportPackage? = null,
    val description: String = "",
    val descriptionError: String? = null,
    val reportLocation: ReportLocation = ReportLocation(),
    val locationStatus: LocationStatus = LocationStatus.NONE,
    val locationErrorMessage: String? = null,
    val selectedCategory: ReportCategory = ReportCategory.NOT_SURE,
    val submissionStage: SubmissionStage = SubmissionStage.PREPARING,
    val isSubmitting: Boolean = false,
    val submissionState: SubmissionState = SubmissionState.IDLE,
    val submissionError: String? = null,
    val createdReport: Report? = null,
    val showDiscardDialog: Boolean = false,
    val tempCameraUri: Uri? = null
)

class ReportViewModel(
    private val reportRepository: ReportRepository = ReportRepository.getInstance(),
    private val edgeProcessor: CivicSenseEdgeProcessor = CivicSenseEdgeProcessor.getInstance(),
    private val uploadClient: CivicReportUploadClient = CivicReportUploadClient(),
    private val preferenceRepository: PreferenceRepository? = null
) : ViewModel() {

    private val _uiState = MutableStateFlow(ReportUiState())
    val uiState: StateFlow<ReportUiState> = _uiState.asStateFlow()

    private var imageProcessingJob: Job? = null
    private var locationJob: Job? = null
    private var reverseGeocodeJob: Job? = null

    fun setStep(step: ReportStep) {
        _uiState.update { it.copy(currentStep = step) }
    }

    /**
     * Prepares a file URI for the camera TakePicture contract.
     */
    fun prepareCameraCaptureUri(context: Context): Uri {
        val uri = CameraHelper.createTempPictureUri(context)
        _uiState.update { it.copy(tempCameraUri = uri) }
        return uri
    }

    /**
     * Called when the camera capture successfully writes to tempCameraUri.
     */
    fun onCameraCaptured(context: Context? = null) {
        val uri = _uiState.value.tempCameraUri ?: return
        _uiState.update {
            it.copy(
                selectedImageUri = uri,
                mockImageDrawableRes = null,
                hasImage = true,
                currentStep = ReportStep.IMAGE_PREVIEW
            )
        }
        if (context != null) {
            startRealImageProcessing(context, uri)
        } else {
            startNonBlockingImageProcessing()
        }
    }

    fun onImageSelected(uri: Uri?, context: Context? = null) {
        if (uri == null) return
        _uiState.update {
            it.copy(
                selectedImageUri = uri,
                mockImageDrawableRes = null,
                hasImage = true,
                currentStep = ReportStep.IMAGE_PREVIEW
            )
        }
        if (context != null) {
            startRealImageProcessing(context, uri)
        } else {
            startNonBlockingImageProcessing()
        }
    }

    fun onSelectMockSampleImage(drawableRes: Int, category: ReportCategory) {
        _uiState.update {
            it.copy(
                selectedImageUri = null,
                mockImageDrawableRes = drawableRes,
                hasImage = true,
                selectedCategory = if (it.selectedCategory == ReportCategory.NOT_SURE) category else it.selectedCategory,
                currentStep = ReportStep.IMAGE_PREVIEW
            )
        }
        startNonBlockingImageProcessing()
    }

    fun removeImage() {
        imageProcessingJob?.cancel()
        _uiState.update {
            it.copy(
                selectedImageUri = null,
                mockImageDrawableRes = null,
                hasImage = false,
                imageProcessingState = ImageProcessingState(),
                imageMetrics = null,
                currentStep = ReportStep.IMAGE_CAPTURE
            )
        }
    }

    private fun startRealImageProcessing(context: Context, uri: Uri) {
        imageProcessingJob?.cancel()
        imageProcessingJob = viewModelScope.launch {
            _uiState.update {
                it.copy(
                    imageProcessingState = ImageProcessingState(
                        stage = ImageProcessingStage.PREPARING,
                        feedback = ImageQualityFeedback.GOOD,
                        isComplete = false
                    )
                )
            }

            val result = withContext(Dispatchers.IO) {
                CivicImagePreprocessor.preprocess(context, uri)
            }

            _uiState.update {
                it.copy(
                    imageProcessingState = it.imageProcessingState.copy(
                        stage = ImageProcessingStage.CHECKING_QUALITY
                    )
                )
            }
            delay(150)

            if (result.isSuccess && result.metrics != null) {
                val feedback = when {
                    result.metrics.brightness != null && result.metrics.brightness < 0.22f -> ImageQualityFeedback.TOO_DARK
                    result.metrics.isBlurry == true -> ImageQualityFeedback.BLURRY
                    else -> ImageQualityFeedback.GOOD
                }
                _uiState.update {
                    it.copy(
                        selectedImageUri = result.previewUri ?: it.selectedImageUri,
                        imageMetrics = result.metrics,
                        imageProcessingState = ImageProcessingState(
                            stage = ImageProcessingStage.READY,
                            feedback = feedback,
                            isComplete = true
                        )
                    )
                }
            } else {
                _uiState.update {
                    it.copy(
                        imageProcessingState = ImageProcessingState(
                            stage = ImageProcessingStage.READY,
                            feedback = ImageQualityFeedback.GOOD,
                            isComplete = true
                        )
                    )
                }
            }
        }
    }

    private fun startNonBlockingImageProcessing() {
        imageProcessingJob?.cancel()
        imageProcessingJob = viewModelScope.launch {
            _uiState.update {
                it.copy(
                    imageProcessingState = ImageProcessingState(
                        stage = ImageProcessingStage.PREPARING,
                        feedback = ImageQualityFeedback.GOOD,
                        isComplete = false
                    )
                )
            }
            delay(900)

            _uiState.update {
                it.copy(
                    imageProcessingState = ImageProcessingState(
                        stage = ImageProcessingStage.CHECKING_QUALITY,
                        feedback = ImageQualityFeedback.GOOD,
                        isComplete = false
                    )
                )
            }
            delay(1000)

            _uiState.update {
                it.copy(
                    imageProcessingState = ImageProcessingState(
                        stage = ImageProcessingStage.ANALYZING,
                        feedback = ImageQualityFeedback.GOOD,
                        isComplete = false
                    )
                )
            }
            delay(900)

            _uiState.update {
                it.copy(
                    imageProcessingState = ImageProcessingState(
                        stage = ImageProcessingStage.READY,
                        feedback = ImageQualityFeedback.GOOD,
                        isComplete = true
                    )
                )
            }
        }
    }

    fun selectCategory(category: ReportCategory) {
        _uiState.update { it.copy(selectedCategory = category) }
    }

    fun updateDescription(text: String) {
        if (text.length <= 300) {
            _uiState.update {
                it.copy(
                    description = text,
                    descriptionError = if (text.trim().length >= 5) null else it.descriptionError
                )
            }
        }
    }

    fun appendQuickPhrase(phrase: String) {
        val current = _uiState.value.description.trim()
        val newText = if (current.isEmpty()) {
            phrase
        } else {
            val separator = if (current.endsWith(".") || current.endsWith("!") || current.endsWith("?")) " " else ". "
            "$current$separator$phrase"
        }
        if (newText.length <= 300) {
            updateDescription(newText)
        }
    }

    fun applySuggestionChip(chipText: String) {
        appendQuickPhrase(chipText)
    }

    fun validateDescriptionAndProceed(): Boolean {
        val trimmed = _uiState.value.description.trim()
        return if (!InputValidators.isValidDescription(trimmed)) {
            _uiState.update {
                it.copy(descriptionError = "Please describe the problem (at least 5 characters)")
            }
            false
        } else {
            _uiState.update {
                it.copy(descriptionError = null, currentStep = ReportStep.LOCATION)
            }
            true
        }
    }

    /**
     * Executes the complete ordered location acquisition strategy:
     * Checks permissions, checks location services, queries recent lastLocation,
     * requests fresh fused location, falls back to active location request / platform manager,
     * immediately records coordinates, then asynchronously reverse geocodes address without blocking.
     */
    fun requestDeviceLocation(context: Context) {
        if (!LocationHelper.hasLocationPermission(context)) {
            _uiState.update {
                it.copy(
                    locationStatus = LocationStatus.PERMISSION_REQUIRED,
                    locationErrorMessage = "Location permission is required to detect your current location."
                )
            }
            return
        }

        if (!LocationHelper.isLocationServiceEnabled(context)) {
            _uiState.update {
                it.copy(
                    locationStatus = LocationStatus.SERVICES_DISABLED,
                    locationErrorMessage = "Location services (GPS) are turned off. Please enable GPS in device settings or enter details manually."
                )
            }
            return
        }

        locationJob?.cancel()
        locationJob = viewModelScope.launch {
            _uiState.update {
                it.copy(
                    locationStatus = LocationStatus.FETCHING,
                    locationErrorMessage = null
                )
            }

            val location = LocationHelper.acquireCurrentLocation(context)
            if (location != null) {
                // Immediately persist coordinates without waiting for reverse geocoding
                val coordsOnlyLocation = _uiState.value.reportLocation.copy(
                    latitude = location.latitude,
                    longitude = location.longitude,
                    source = LocationSource.CURRENT_LOCATION
                )
                _uiState.update {
                    it.copy(
                        reportLocation = coordsOnlyLocation,
                        locationStatus = LocationStatus.COORDINATES_FOUND,
                        locationErrorMessage = null
                    )
                }

                // Asynchronously resolve human-readable address
                _uiState.update { it.copy(locationStatus = LocationStatus.ADDRESS_RESOLVING) }

                val resolved = LocationHelper.reverseGeocode(
                    context = context,
                    latitude = location.latitude,
                    longitude = location.longitude
                )

                val updatedLocation = coordsOnlyLocation.copy(
                    address = resolved.formattedAddress ?: coordsOnlyLocation.address ?: "Coordinates recorded",
                    postalPin = resolved.postalPin ?: coordsOnlyLocation.postalPin
                )

                _uiState.update {
                    it.copy(
                        reportLocation = updatedLocation,
                        locationStatus = LocationStatus.RESOLVED,
                        locationErrorMessage = null
                    )
                }
            } else {
                _uiState.update {
                    it.copy(
                        locationStatus = LocationStatus.FAILED,
                        locationErrorMessage = "Unable to acquire current location. Please verify GPS or select on map / enter manually."
                    )
                }
            }
        }
    }

    /**
     * Updates coordinates immediately when user pans or selects on the map.
     * Triggers debounced reverse geocoding to resolve address without blocking or overriding coordinates.
     */
    fun onMapLocationChanged(latitude: Double, longitude: Double, context: Context) {
        val current = _uiState.value.reportLocation
        val updated = current.copy(
            latitude = latitude,
            longitude = longitude,
            source = LocationSource.MAP_SELECTION
        )
        _uiState.update {
            it.copy(
                reportLocation = updated,
                locationStatus = LocationStatus.COORDINATES_FOUND,
                locationErrorMessage = null
            )
        }

        reverseGeocodeJob?.cancel()
        reverseGeocodeJob = viewModelScope.launch {
            delay(500) // Debounce rapid panning
            _uiState.update { it.copy(locationStatus = LocationStatus.ADDRESS_RESOLVING) }
            val resolved = LocationHelper.reverseGeocode(context, latitude, longitude)
            val finalAddress = resolved.formattedAddress ?: _uiState.value.reportLocation.address ?: "Selected map coordinates"
            val finalPin = resolved.postalPin ?: _uiState.value.reportLocation.postalPin
            _uiState.update {
                it.copy(
                    reportLocation = it.reportLocation.copy(
                        address = finalAddress,
                        postalPin = finalPin
                    ),
                    locationStatus = LocationStatus.RESOLVED
                )
            }
        }
    }

    fun updateManualLocation(address: String, postalPin: String) {
        val current = _uiState.value.reportLocation
        val updated = current.copy(
            address = address.trim().ifEmpty { null },
            postalPin = postalPin.trim().ifEmpty { null },
            source = LocationSource.MANUAL
        )
        _uiState.update {
            it.copy(
                reportLocation = updated,
                locationStatus = LocationStatus.MANUAL,
                locationErrorMessage = null
            )
        }
    }

    fun setLocationPermissionDenied() {
        _uiState.update {
            it.copy(
                locationStatus = LocationStatus.PERMISSION_DENIED,
                locationErrorMessage = "Location permission was denied. You can select the location on the map or enter details manually."
            )
        }
    }

    /**
     * Checks whether the user has modified any meaningful report field.
     */
    fun isDraftDirty(): Boolean {
        val s = _uiState.value
        return s.hasImage ||
                s.description.isNotBlank() ||
                s.selectedCategory != ReportCategory.NOT_SURE ||
                s.reportLocation.hasCoordinates ||
                !s.reportLocation.address.isNullOrBlank()
    }

    fun showDiscardConfirmation() {
        _uiState.update { it.copy(showDiscardDialog = true) }
    }

    fun dismissDiscardConfirmation() {
        _uiState.update { it.copy(showDiscardDialog = false) }
    }

    fun discardDraftAndReset(context: Context? = null) {
        imageProcessingJob?.cancel()
        locationJob?.cancel()
        reverseGeocodeJob?.cancel()
        if (context != null) {
            CameraHelper.clearTempImages(context)
        }
        _uiState.value = ReportUiState()
    }

    fun resetWizard() {
        discardDraftAndReset(null)
    }

    fun submitReport(context: Context? = null) {
        val currentState = _uiState.value
        if (currentState.isSubmitting || currentState.submissionState == SubmissionState.SUBMITTING) {
            return
        }

        val totalSubmitStart = System.currentTimeMillis()
        val clientReportId = java.util.UUID.randomUUID().toString()

        Log.i("CivicSenseSubmit", "SUBMIT_START client_report_id=$clientReportId api_base_url=${BuildConfig.API_BASE_URL}")

        // Client validation check
        val valStart = System.currentTimeMillis()
        val isValid = currentState.description.trim().length >= 5
        val valDuration = System.currentTimeMillis() - valStart
        Log.i("CivicSenseSubmit", "VALIDATION_COMPLETE duration_ms=$valDuration valid=$isValid")

        // Location check
        val locStart = System.currentTimeMillis()
        Log.i("CivicSenseSubmit", "LOCATION_START")
        val hasCoords = currentState.reportLocation.hasCoordinates
        val locDuration = System.currentTimeMillis() - locStart
        Log.i("CivicSenseSubmit", "LOCATION_COMPLETE duration_ms=$locDuration has_coords=$hasCoords address=${currentState.reportLocation.address}")

        _uiState.update {
            it.copy(
                isSubmitting = true,
                submissionState = SubmissionState.SUBMITTING,
                submissionStage = SubmissionStage.PREPARING,
                submissionError = null
            )
        }

        viewModelScope.launch {
            try {
                val timestamp = SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.getDefault()).format(Date())

                if (context != null) {
                    val userProfile = preferenceRepository?.userProfileFlow?.firstOrNull()
                    val citizenId = preferenceRepository?.getOrCreateCitizenId()
                    val citizenName = userProfile?.fullName?.trim()?.ifEmpty { null }
                    val citizenPhone = userProfile?.mobileNumber?.trim()?.ifEmpty { null }
                    val citizenEmail = userProfile?.email?.trim()?.ifEmpty { null }
                    val citizenPostalCode = userProfile?.postalPin?.trim()?.ifEmpty { null }

                    // 1. Real On-Device Edge Preprocessing
                    val processingResult = withContext(Dispatchers.IO) {
                        edgeProcessor.process(
                            context = context,
                            rawDescription = currentState.description,
                            imageUri = currentState.selectedImageUri,
                            location = currentState.reportLocation,
                            category = currentState.selectedCategory.backendCategory,
                            categoryHint = currentState.selectedCategory.shortName,
                            clientReportId = clientReportId,
                            citizenId = citizenId,
                            citizenName = citizenName,
                            citizenPhone = citizenPhone,
                            citizenEmail = citizenEmail,
                            citizenPostalCode = citizenPostalCode
                        )
                    }

                    _uiState.update {
                        it.copy(
                            edgePackage = processingResult.reportPackage,
                            submissionStage = SubmissionStage.UPLOADING
                        )
                    }

                    // 2. Reliable Upload Pipeline with Bounded Exponential Backoff
                    val uploadResult = withContext(Dispatchers.IO) {
                        uploadClient.uploadReport(processingResult.reportPackage)
                    }

                    when (uploadResult) {
                        is UploadResult.Success -> {
                            preferenceRepository?.addSubmittedReportId(uploadResult.serverTrackingId)
                            val newReport = createReportModel(
                                reportId = uploadResult.serverTrackingId,
                                currentState = currentState,
                                timestamp = timestamp,
                                status = ReportStatus.SUBMITTED
                            )
                            reportRepository.addReport(newReport)
                            _uiState.update {
                                it.copy(
                                    submissionState = SubmissionState.SUCCESS,
                                    createdReport = newReport,
                                    currentStep = ReportStep.SUCCESS
                                )
                            }
                        }
                        is UploadResult.OfflineQueued -> {
                            val offlineId = "CS-OFFLINE-${clientReportId.take(5).uppercase()}"
                            preferenceRepository?.addSubmittedReportId(offlineId)
                            val offlineReport = createReportModel(
                                reportId = offlineId,
                                currentState = currentState,
                                timestamp = timestamp,
                                status = ReportStatus.QUEUED_OFFLINE
                            )
                            reportRepository.addReport(offlineReport)
                            _uiState.update {
                                it.copy(
                                    submissionState = SubmissionState.QUEUED_OFFLINE,
                                    createdReport = offlineReport,
                                    currentStep = ReportStep.SUCCESS
                                )
                            }
                        }
                        is UploadResult.Error -> {
                            _uiState.update {
                                it.copy(
                                    submissionState = SubmissionState.ERROR,
                                    submissionError = uploadResult.message
                                )
                            }
                        }
                    }
                } else {
                    // Headless local fallback (for unit tests without Android Context)
                    val randomNum = (10000..99999).random()
                    val newReportId = "CS-DEMO-$randomNum"
                    val newReport = createReportModel(
                        reportId = newReportId,
                        currentState = currentState,
                        timestamp = timestamp,
                        status = ReportStatus.SUBMITTED
                    )
                    reportRepository.addReport(newReport)
                    _uiState.update {
                        it.copy(
                            submissionState = SubmissionState.SUCCESS,
                            createdReport = newReport,
                            currentStep = ReportStep.SUCCESS
                        )
                    }
                }
            } catch (e: Exception) {
                Log.e("CivicSenseSubmit", "SUBMISSION_UNCAUGHT_EXCEPTION error=${e.message}", e)
                _uiState.update {
                    it.copy(
                        submissionState = SubmissionState.ERROR,
                        submissionError = e.message ?: "Failed to submit report. Please try again."
                    )
                }
            } finally {
                val totalDuration = System.currentTimeMillis() - totalSubmitStart
                _uiState.update { it.copy(isSubmitting = false) }
                Log.i("CivicSenseSubmit", "SUBMIT_END total_duration_ms=$totalDuration status=${_uiState.value.submissionState}")
            }
        }
    }

    private fun createReportModel(
        reportId: String,
        currentState: ReportUiState,
        timestamp: String,
        status: ReportStatus = ReportStatus.SUBMITTED
    ): Report {
        val title = if (currentState.description.length > 35) {
            currentState.description.take(35).trim() + "…"
        } else {
            currentState.description.ifBlank { "Citizen Civic Report" }
        }

        val location = currentState.reportLocation
        val initialTimelineDesc = if (status == ReportStatus.QUEUED_OFFLINE) {
            "Report preserved locally on this device. Network connection pending."
        } else {
            "Report received and evidence cryptographically recorded."
        }

        return Report(
            id = reportId,
            title = title,
            description = currentState.description,
            category = currentState.selectedCategory,
            status = status,
            severity = SeverityLevel.MEDIUM,
            dateTime = timestamp,
            address = location.displayAddress,
            postalPin = location.postalPin.orEmpty(),
            latitude = location.latitude,
            longitude = location.longitude,
            imageUri = currentState.selectedImageUri?.toString(),
            mockImageDrawableRes = currentState.mockImageDrawableRes,
            isImageProcessingComplete = true,
            timeline = listOf(
                TimelineStage(
                    status = status,
                    date = timestamp,
                    description = initialTimelineDesc,
                    isCompleted = true,
                    isCurrent = true
                ),
                TimelineStage(
                    status = ReportStatus.UNDER_REVIEW,
                    date = null,
                    description = "Triage team is verifying the issue location and severity.",
                    isCompleted = false,
                    isCurrent = false
                ),
                TimelineStage(
                    status = ReportStatus.CONFIRMED,
                    date = null,
                    description = "Verification by municipal ward engineer.",
                    isCompleted = false,
                    isCurrent = false
                ),
                TimelineStage(
                    status = ReportStatus.ASSIGNED,
                    date = null,
                    description = "Work order issued to municipal maintenance crew.",
                    isCompleted = false,
                    isCurrent = false
                ),
                TimelineStage(
                    status = ReportStatus.IN_PROGRESS,
                    date = null,
                    description = "On-site repair and defect remediation.",
                    isCompleted = false,
                    isCurrent = false
                ),
                TimelineStage(
                    status = ReportStatus.RESOLVED,
                    date = null,
                    description = "Final inspection and defect closure.",
                    isCompleted = false,
                    isCurrent = false
                )
            )
        )
    }
}
