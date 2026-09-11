package com.civicsense.feature.report

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.civicsense.core.design.CivicLocationCard
import com.civicsense.core.design.CivicMapLocationPicker
import com.civicsense.core.design.CivicPrimaryButton
import com.civicsense.core.design.CivicProcessingChip
import com.civicsense.core.design.CivicReportProgressBar
import com.civicsense.core.design.CivicTopAppBar
import com.civicsense.core.util.InputValidators
import com.civicsense.core.util.LocationHelper
import com.civicsense.data.model.LocationStatus

@Composable
fun LocationScreen(
    uiState: ReportUiState,
    onUseCurrentLocation: () -> Unit,
    onMapLocationSelected: (Double, Double) -> Unit,
    onManualLocationSaved: (String, String) -> Unit,
    onPermissionDenied: () -> Unit,
    onConfirmLocation: () -> Unit,
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    var showEditDialog by remember { mutableStateOf(false) }
    var editAddress by remember(uiState.reportLocation) { mutableStateOf(uiState.reportLocation.address ?: "") }
    var editPostalPin by remember(uiState.reportLocation) { mutableStateOf(uiState.reportLocation.postalPin ?: "") }
    var manualPinError by remember { mutableStateOf<String?>(null) }

    val locationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val fineGranted = permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true
        val coarseGranted = permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true

        if (fineGranted || coarseGranted) {
            onUseCurrentLocation()
        } else {
            onPermissionDenied()
        }
    }

    fun requestLocationWithPermission() {
        if (LocationHelper.hasLocationPermission(context)) {
            onUseCurrentLocation()
        } else {
            locationPermissionLauncher.launch(
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                )
            )
        }
    }

    if (showEditDialog) {
        AlertDialog(
            onDismissRequest = { showEditDialog = false },
            title = { Text("Edit Location Details") },
            text = {
                Column {
                    Text(
                        text = "Specify the street, landmark, or area for this issue.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(12.dp))

                    OutlinedTextField(
                        value = editAddress,
                        onValueChange = { editAddress = it },
                        label = { Text("Address / Landmark") },
                        placeholder = { Text("Near the public library, Main Road") },
                        modifier = Modifier.fillMaxWidth()
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    OutlinedTextField(
                        value = editPostalPin,
                        onValueChange = { input ->
                            val digits = input.filter { it.isDigit() }
                            if (digits.length <= 6) editPostalPin = digits
                            if (manualPinError != null) manualPinError = null
                        },
                        label = { Text("Postal PIN (6 digits)") },
                        placeholder = { Text("695xxx") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        isError = manualPinError != null,
                        supportingText = manualPinError?.let { { Text(it) } },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        if (editPostalPin.isNotEmpty() && !InputValidators.isValidPostalPin(editPostalPin)) {
                            manualPinError = "PIN code must be exactly 6 digits"
                        } else {
                            manualPinError = null
                            showEditDialog = false
                            onManualLocationSaved(editAddress, editPostalPin)
                        }
                    }
                ) {
                    Text("Save")
                }
            },
            dismissButton = {
                TextButton(onClick = { showEditDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            Column {
                CivicTopAppBar(
                    title = "Issue Location",
                    canNavigateBack = true,
                    onNavigateBack = onNavigateBack,
                    actions = {
                        CivicProcessingChip(
                            state = uiState.imageProcessingState,
                            modifier = Modifier.padding(end = 16.dp)
                        )
                    }
                )
                CivicReportProgressBar(
                    stepIndex = 3,
                    stageName = "Location"
                )
            }
        },
        bottomBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp)
            ) {
                CivicPrimaryButton(
                    text = "Confirm location",
                    onClick = onConfirmLocation
                )
            }
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 20.dp)
                .verticalScroll(rememberScrollState())
        ) {
            Text(
                text = "Where is the problem located?",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = "Accurate location information connects your report to the designated municipal ward team for rapid action.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(16.dp))

            CivicMapLocationPicker(
                reportLocation = uiState.reportLocation,
                onMapLocationSelected = onMapLocationSelected,
                onUseCurrentLocation = { requestLocationWithPermission() },
                isLocating = uiState.locationStatus == LocationStatus.FETCHING || uiState.locationStatus == LocationStatus.ADDRESS_RESOLVING,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(16.dp))

            CivicLocationCard(
                reportLocation = uiState.reportLocation,
                status = uiState.locationStatus,
                onUseCurrentLocation = { requestLocationWithPermission() },
                onEditManually = {
                    editAddress = uiState.reportLocation.address ?: ""
                    editPostalPin = uiState.reportLocation.postalPin ?: ""
                    manualPinError = null
                    showEditDialog = true
                }
            )

            if (uiState.locationErrorMessage != null) {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = uiState.locationErrorMessage,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }

            Spacer(modifier = Modifier.height(20.dp))

            Text(
                text = "Privacy Guarantee: Precise coordinates are utilized exclusively for municipal triage. CivicSense never publishes private home coordinates to public feeds.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(32.dp))
        }
    }
}
