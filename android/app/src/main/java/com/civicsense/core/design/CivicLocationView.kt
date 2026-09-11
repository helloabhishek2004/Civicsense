package com.civicsense.core.design

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.LocationOff
import androidx.compose.material.icons.filled.MyLocation
import androidx.compose.material.icons.filled.Place
import androidx.compose.material.icons.outlined.Warning
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.civicsense.BuildConfig
import com.civicsense.core.theme.CivicGreen
import com.civicsense.core.theme.civicColors
import com.civicsense.data.model.LocationStatus
import com.civicsense.data.model.ReportLocation
import com.google.android.gms.maps.CameraUpdateFactory
import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLng
import com.google.maps.android.compose.GoogleMap
import com.google.maps.android.compose.MapProperties
import com.google.maps.android.compose.MapUiSettings
import com.google.maps.android.compose.rememberCameraPositionState

@Composable
fun CivicMapLocationPicker(
    reportLocation: ReportLocation,
    onMapLocationSelected: (Double, Double) -> Unit,
    onUseCurrentLocation: () -> Unit,
    isLocating: Boolean = false,
    modifier: Modifier = Modifier
) {
    val isApiKeyConfigured = remember {
        BuildConfig.MAPS_API_KEY.isNotBlank() &&
                !BuildConfig.MAPS_API_KEY.startsWith("YOUR_")
    }

    if (!isApiKeyConfigured) {
        // Honest, transparent fallback when Google Maps API key is not configured
        Card(
            modifier = modifier
                .fillMaxWidth()
                .padding(vertical = 4.dp),
            shape = MaterialTheme.shapes.medium,
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)
            )
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(36.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Info,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    Column {
                        Text(
                            text = "Interactive Map Preview",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = "Add MAPS_API_KEY to local.properties to enable map panning.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    text = "GPS acquisition and manual address entry remain 100% active below.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        return
    }

    // Default coordinates: Fallback to center of India if none specified yet
    val initialLat = reportLocation.latitude ?: 20.5937
    val initialLng = reportLocation.longitude ?: 78.9629
    val initialZoom = if (reportLocation.hasCoordinates) 16f else 5f

    val cameraPositionState = rememberCameraPositionState {
        position = CameraPosition.fromLatLngZoom(LatLng(initialLat, initialLng), initialZoom)
    }

    // Animate camera when external location is acquired (e.g. Current Location button clicked)
    LaunchedEffect(reportLocation.latitude, reportLocation.longitude) {
        if (reportLocation.hasCoordinates) {
            val targetLat = reportLocation.latitude!!
            val targetLng = reportLocation.longitude!!
            val currentTarget = cameraPositionState.position.target
            val latDiff = kotlin.math.abs(currentTarget.latitude - targetLat)
            val lngDiff = kotlin.math.abs(currentTarget.longitude - targetLng)
            if (latDiff > 0.0001 || lngDiff > 0.0001) {
                cameraPositionState.animate(
                    CameraUpdateFactory.newLatLngZoom(LatLng(targetLat, targetLng), 16.5f),
                    durationMs = 800
                )
            }
        }
    }

    // When the user pans/moves the map and it becomes idle, update coordinates with fixed center pin
    LaunchedEffect(cameraPositionState.isMoving) {
        if (!cameraPositionState.isMoving) {
            val target = cameraPositionState.position.target
            val currentLat = reportLocation.latitude ?: 0.0
            val currentLng = reportLocation.longitude ?: 0.0
            val latDiff = kotlin.math.abs(currentLat - target.latitude)
            val lngDiff = kotlin.math.abs(currentLng - target.longitude)
            // Fire if moved noticeably
            if (latDiff > 0.00005 || lngDiff > 0.00005) {
                onMapLocationSelected(target.latitude, target.longitude)
            }
        }
    }

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(240.dp)
            .clip(MaterialTheme.shapes.large)
            .border(
                width = 1.dp,
                color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f),
                shape = MaterialTheme.shapes.large
            )
    ) {
        GoogleMap(
            modifier = Modifier.fillMaxSize(),
            cameraPositionState = cameraPositionState,
            properties = MapProperties(
                isMyLocationEnabled = false
            ),
            uiSettings = MapUiSettings(
                zoomControlsEnabled = false,
                compassEnabled = true,
                myLocationButtonEnabled = false,
                mapToolbarEnabled = false
            )
        )

        // Center Pin Anchor Shadow (represents physical ground contact point)
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(Color.Black.copy(alpha = 0.35f))
                .align(Alignment.Center)
        )

        // Fixed Center Pin Marker (tip rests precisely on center)
        Icon(
            imageVector = Icons.Default.Place,
            contentDescription = "Selected Map Location",
            tint = CivicGreen,
            modifier = Modifier
                .size(40.dp)
                .align(Alignment.Center)
                .offset(y = (-18).dp)
                .shadow(elevation = 4.dp, shape = CircleShape)
        )

        // Floating "My Location" Button inside map
        FloatingActionButton(
            onClick = onUseCurrentLocation,
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(12.dp)
                .size(44.dp),
            containerColor = MaterialTheme.colorScheme.surface,
            contentColor = CivicGreen,
            shape = CircleShape
        ) {
            if (isLocating) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    strokeWidth = 2.dp,
                    color = CivicGreen
                )
            } else {
                Icon(
                    imageVector = Icons.Default.MyLocation,
                    contentDescription = "Center on my location",
                    modifier = Modifier.size(22.dp)
                )
            }
        }

        // Instructional banner overlay at top of map
        Box(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(top = 10.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.9f))
                .padding(horizontal = 12.dp, vertical = 5.dp)
        ) {
            Text(
                text = "Pan map to place pin on issue",
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

@Composable
fun CivicLocationCard(
    reportLocation: ReportLocation,
    status: LocationStatus,
    onUseCurrentLocation: () -> Unit,
    onEditManually: () -> Unit,
    modifier: Modifier = Modifier
) {
    OutlinedCard(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        colors = CardDefaults.outlinedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            // Header Row with Icon and Status Badge
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(36.dp)
                            .clip(CircleShape)
                            .background(CivicGreen.copy(alpha = 0.15f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Place,
                            contentDescription = null,
                            tint = CivicGreen,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = "Location Details",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }

                // Status Badge
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(12.dp))
                        .background(
                            when (status) {
                                LocationStatus.RESOLVED, LocationStatus.COORDINATES_FOUND -> MaterialTheme.civicColors.successContainer
                                LocationStatus.FETCHING, LocationStatus.ADDRESS_RESOLVING -> MaterialTheme.colorScheme.surfaceVariant
                                LocationStatus.PERMISSION_REQUIRED, LocationStatus.PERMISSION_DENIED -> MaterialTheme.colorScheme.errorContainer
                                LocationStatus.SERVICES_DISABLED, LocationStatus.FAILED -> MaterialTheme.civicColors.warningContainer
                                LocationStatus.MANUAL -> MaterialTheme.colorScheme.primaryContainer
                                LocationStatus.NONE -> MaterialTheme.colorScheme.surfaceVariant
                            }
                        )
                        .padding(horizontal = 10.dp, vertical = 4.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        when (status) {
                            LocationStatus.FETCHING -> {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(12.dp),
                                    strokeWidth = 1.5.dp,
                                    color = CivicGreen
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = "Finding location…",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            LocationStatus.COORDINATES_FOUND -> {
                                Icon(
                                    imageVector = Icons.Default.Check,
                                    contentDescription = null,
                                    tint = MaterialTheme.civicColors.success,
                                    modifier = Modifier.size(14.dp)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = "Coordinates set",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.civicColors.onSuccessContainer
                                )
                            }
                            LocationStatus.ADDRESS_RESOLVING -> {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(12.dp),
                                    strokeWidth = 1.5.dp,
                                    color = CivicGreen
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = "Resolving address…",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            LocationStatus.RESOLVED -> {
                                Icon(
                                    imageVector = Icons.Default.Check,
                                    contentDescription = null,
                                    tint = MaterialTheme.civicColors.success,
                                    modifier = Modifier.size(14.dp)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = "Verified",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.civicColors.onSuccessContainer
                                )
                            }
                            LocationStatus.SERVICES_DISABLED -> {
                                Icon(
                                    imageVector = Icons.Default.LocationOff,
                                    contentDescription = null,
                                    tint = MaterialTheme.civicColors.warning,
                                    modifier = Modifier.size(14.dp)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = "GPS off",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.civicColors.onWarningContainer
                                )
                            }
                            LocationStatus.PERMISSION_REQUIRED, LocationStatus.PERMISSION_DENIED -> {
                                Icon(
                                    imageVector = Icons.Outlined.Warning,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.error,
                                    modifier = Modifier.size(14.dp)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = "Permission needed",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onErrorContainer
                                )
                            }
                            LocationStatus.FAILED -> {
                                Icon(
                                    imageVector = Icons.Outlined.Warning,
                                    contentDescription = null,
                                    tint = MaterialTheme.civicColors.warning,
                                    modifier = Modifier.size(14.dp)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = "Unavailable",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.civicColors.onWarningContainer
                                )
                            }
                            LocationStatus.MANUAL -> {
                                Icon(
                                    imageVector = Icons.Default.Edit,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(14.dp)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = "Manual entry",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onPrimaryContainer
                                )
                            }
                            LocationStatus.NONE -> {
                                Text(
                                    text = "Pending",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Address display
            Text(
                text = "Address / Locality",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = reportLocation.address?.ifBlank { null }
                    ?: if (reportLocation.hasCoordinates) "Coordinates detected (Address unlisted)" else "No location specified yet",
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )

            Spacer(modifier = Modifier.height(10.dp))

            // Coordinates and PIN Code
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Coordinates",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = if (reportLocation.hasCoordinates) {
                            String.format(java.util.Locale.US, "%.4f° N, %.4f° E", reportLocation.latitude, reportLocation.longitude)
                        } else {
                            "Not captured"
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Postal PIN",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = reportLocation.postalPin?.ifBlank { null } ?: "Not specified",
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.Medium,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Source indicator
            Text(
                text = "Source: ${reportLocation.source.displayName}",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.primary
            )

            Spacer(modifier = Modifier.height(18.dp))

            // Action Buttons Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                CivicTonalButton(
                    text = "Use current location",
                    onClick = onUseCurrentLocation,
                    leadingIcon = Icons.Default.MyLocation,
                    isLoading = status == LocationStatus.FETCHING || status == LocationStatus.ADDRESS_RESOLVING,
                    modifier = Modifier.weight(1f)
                )
                CivicOutlinedButton(
                    text = "Edit manually",
                    onClick = onEditManually,
                    leadingIcon = Icons.Default.Edit,
                    modifier = Modifier.weight(1f)
                )
            }
        }
    }
}
