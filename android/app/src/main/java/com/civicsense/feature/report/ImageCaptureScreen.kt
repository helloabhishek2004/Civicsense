package com.civicsense.feature.report

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.outlined.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import coil.compose.AsyncImage
import com.civicsense.R
import com.civicsense.core.design.CivicOutlinedButton
import com.civicsense.core.design.CivicPrimaryButton
import com.civicsense.core.design.CivicProcessingChip
import com.civicsense.core.design.CivicReportProgressBar
import com.civicsense.core.design.CivicTopAppBar
import com.civicsense.core.theme.civicColors
import com.civicsense.data.model.ReportCategory

@Composable
fun ImageCaptureScreen(
    uiState: ReportUiState,
    onPrepareCameraUri: () -> Uri,
    onCameraSuccess: () -> Unit,
    onImageSelected: (Uri?) -> Unit,
    onSelectMockSample: (Int, ReportCategory) -> Unit,
    onRemoveImage: () -> Unit,
    onContinue: () -> Unit,
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    var showCameraPermissionRationale by remember { mutableStateOf(false) }

    val takePictureLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success: Boolean ->
        if (success) {
            onCameraSuccess()
        }
    }

    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            val destinationUri = onPrepareCameraUri()
            takePictureLauncher.launch(destinationUri)
        } else {
            showCameraPermissionRationale = true
        }
    }

    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null) {
            onImageSelected(uri)
        }
    }

    fun launchCamera() {
        val hasPermission = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED

        if (hasPermission) {
            val destinationUri = onPrepareCameraUri()
            takePictureLauncher.launch(destinationUri)
        } else {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    if (showCameraPermissionRationale) {
        AlertDialog(
            onDismissRequest = { showCameraPermissionRationale = false },
            title = { Text("Camera Permission Required") },
            text = {
                Text("Camera permission allows you to take immediate photos of civic issues. You can still select existing photos from your gallery if you prefer.")
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showCameraPermissionRationale = false
                        cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
                    }
                ) {
                    Text("Retry")
                }
            },
            dismissButton = {
                TextButton(
                    onClick = {
                        showCameraPermissionRationale = false
                        galleryLauncher.launch("image/*")
                    }
                ) {
                    Text("Use Gallery Instead")
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
                    title = if (uiState.hasImage) "Check your photo" else "Capture issue",
                    canNavigateBack = true,
                    onNavigateBack = onNavigateBack,
                    actions = {
                        if (uiState.hasImage) {
                            CivicProcessingChip(
                                state = uiState.imageProcessingState,
                                modifier = Modifier.padding(end = 16.dp)
                            )
                        }
                    }
                )
                CivicReportProgressBar(
                    stepIndex = 1,
                    stageName = "Evidence"
                )
            }
        },
        bottomBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp)
            ) {
                if (uiState.hasImage) {
                    CivicPrimaryButton(
                        text = "Continue",
                        onClick = onContinue
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        CivicOutlinedButton(
                            text = "Change photo",
                            leadingIcon = Icons.Default.Refresh,
                            onClick = { launchCamera() },
                            modifier = Modifier.weight(1f)
                        )
                        CivicOutlinedButton(
                            text = "Remove photo",
                            leadingIcon = Icons.Default.Delete,
                            onClick = onRemoveImage,
                            modifier = Modifier.weight(1f)
                        )
                    }
                } else {
                    CivicPrimaryButton(
                        text = "Take photo with Camera",
                        leadingIcon = Icons.Default.CameraAlt,
                        onClick = { launchCamera() }
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    CivicOutlinedButton(
                        text = "Choose from gallery",
                        leadingIcon = Icons.Default.PhotoLibrary,
                        onClick = { galleryLauncher.launch("image/*") }
                    )
                }
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
            if (uiState.hasImage) {
                // Large Image Preview Card
                OutlinedCard(
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(4f / 3f),
                    shape = MaterialTheme.shapes.large,
                    colors = CardDefaults.outlinedCardColors(
                        containerColor = MaterialTheme.colorScheme.surface
                    )
                ) {
                    Box(modifier = Modifier.fillMaxSize()) {
                        if (uiState.selectedImageUri != null) {
                            AsyncImage(
                                model = uiState.selectedImageUri,
                                contentDescription = "Captured evidence",
                                modifier = Modifier.fillMaxSize(),
                                contentScale = ContentScale.Crop
                            )
                        } else if (uiState.mockImageDrawableRes != null) {
                            Image(
                                painter = painterResource(id = uiState.mockImageDrawableRes),
                                contentDescription = "Captured evidence",
                                modifier = Modifier.fillMaxSize(),
                                contentScale = ContentScale.Crop
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Quality Guidance Card
                Card(
                    shape = MaterialTheme.shapes.medium,
                    colors = CardDefaults.cardColors(
                        containerColor = if (uiState.imageProcessingState.feedback.isWarning) {
                            MaterialTheme.civicColors.warningContainer
                        } else {
                            MaterialTheme.civicColors.successContainer
                        }
                    ),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(14.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = if (uiState.imageProcessingState.feedback.isWarning) {
                                Icons.Outlined.Warning
                            } else {
                                Icons.Default.CheckCircle
                            },
                            contentDescription = null,
                            tint = if (uiState.imageProcessingState.feedback.isWarning) {
                                MaterialTheme.civicColors.onWarningContainer
                            } else {
                                MaterialTheme.civicColors.onSuccessContainer
                            },
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "Photo Quality Guidance",
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.Bold,
                                color = if (uiState.imageProcessingState.feedback.isWarning) {
                                    MaterialTheme.civicColors.onWarningContainer
                                } else {
                                    MaterialTheme.civicColors.onSuccessContainer
                                }
                            )
                            Text(
                                text = uiState.imageProcessingState.feedback.message,
                                style = MaterialTheme.typography.bodySmall,
                                color = if (uiState.imageProcessingState.feedback.isWarning) {
                                    MaterialTheme.civicColors.onWarningContainer
                                } else {
                                    MaterialTheme.civicColors.onSuccessContainer
                                }
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(20.dp))

                Text(
                    text = "A sharp, well-lit photo allows civic authorities to evaluate the problem accurately.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            } else {
                // No image chosen yet
                Text(
                    text = "Capture issue evidence",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onBackground
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Take a live photo of the defect or select one from your gallery. Clear photos help dispatch maintenance crews faster.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(24.dp))

                Text(
                    text = "Or choose a sample civic problem for testing:",
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(modifier = Modifier.height(12.dp))

                SampleImageOption(
                    title = "Road damage (Pothole)",
                    subtitle = "Crater defect on road surface",
                    drawableRes = R.drawable.img_pothole_sample,
                    onClick = { onSelectMockSample(R.drawable.img_pothole_sample, ReportCategory.ROAD_DAMAGE) }
                )
                Spacer(modifier = Modifier.height(10.dp))

                SampleImageOption(
                    title = "Garbage accumulation",
                    subtitle = "Waste overflow near public path",
                    drawableRes = R.drawable.img_garbage_sample,
                    onClick = { onSelectMockSample(R.drawable.img_garbage_sample, ReportCategory.GARBAGE) }
                )
                Spacer(modifier = Modifier.height(10.dp))

                SampleImageOption(
                    title = "Water leakage",
                    subtitle = "Pipeline break with pooling water",
                    drawableRes = R.drawable.img_water_sample,
                    onClick = { onSelectMockSample(R.drawable.img_water_sample, ReportCategory.WATER_LEAKAGE) }
                )
                Spacer(modifier = Modifier.height(10.dp))

                SampleImageOption(
                    title = "Damaged infrastructure",
                    subtitle = "Broken footpath and lighting",
                    drawableRes = R.drawable.img_infrastructure_sample,
                    onClick = { onSelectMockSample(R.drawable.img_infrastructure_sample, ReportCategory.INFRASTRUCTURE) }
                )
            }

            Spacer(modifier = Modifier.height(32.dp))
        }
    }
}

@Composable
private fun SampleImageOption(
    title: String,
    subtitle: String,
    drawableRes: Int,
    onClick: () -> Unit
) {
    OutlinedCard(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = MaterialTheme.shapes.medium,
        colors = CardDefaults.outlinedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Image(
                painter = painterResource(id = drawableRes),
                contentDescription = title,
                modifier = Modifier
                    .size(52.dp)
                    .clip(RoundedCornerShape(8.dp)),
                contentScale = ContentScale.Crop
            )
            Spacer(modifier = Modifier.width(14.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
