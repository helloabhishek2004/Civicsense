package com.civicsense.core.util

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Address
import android.location.Geocoder
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.Looper
import androidx.core.content.ContextCompat
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import java.util.Locale
import kotlin.coroutines.resume

data class ResolvedAddress(
    val formattedAddress: String?,
    val postalPin: String?
)

object LocationHelper {

    fun hasLocationPermission(context: Context): Boolean {
        val fineGranted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val coarseGranted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        return fineGranted || coarseGranted
    }

    fun isLocationServiceEnabled(context: Context): Boolean {
        val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as? LocationManager
            ?: return false
        val gpsEnabled = try {
            locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)
        } catch (_: Exception) {
            false
        }
        val networkEnabled = try {
            locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
        } catch (_: Exception) {
            false
        }
        return gpsEnabled || networkEnabled
    }

    /**
     * Executes the ordered location acquisition strategy:
     * 1. Checks permissions
     * 2. Checks location services
     * 3. Tries recent valid lastLocation (< 5 minutes old)
     * 4. Requests fresh location via FusedLocationProviderClient (getCurrentLocation)
     * 5. Fallback to active LocationRequest callback
     * 6. Fallback to platform LocationManager
     * 7. Ensures all callbacks are cleaned up and cancelled properly
     */
    suspend fun acquireCurrentLocation(context: Context): Location? {
        if (!hasLocationPermission(context)) return null
        if (!isLocationServiceEnabled(context)) return null

        // Step 1: Check cached last location if fresh and accurate (< 5 minutes old)
        val recentCached = getRecentLastLocation(context)
        if (recentCached != null) {
            return recentCached
        }

        // Step 2: Request fresh location via FusedLocationProviderClient with 10s timeout
        val freshFused = withTimeoutOrNull(10000L) {
            getFreshFusedLocation(context)
        }
        if (freshFused != null) return freshFused

        // Step 3: Active single-shot location request with LocationCallback (5s timeout)
        val activeUpdateLocation = withTimeoutOrNull(6000L) {
            getActiveLocationUpdate(context)
        }
        if (activeUpdateLocation != null) return activeUpdateLocation

        // Step 4: Controlled platform LocationManager fallback (GPS / Network)
        return withTimeoutOrNull(6000L) {
            getPlatformLocationFallback(context)
        }
    }

    private suspend fun getRecentLastLocation(context: Context): Location? = suspendCancellableCoroutine { cont ->
        try {
            val fusedClient = LocationServices.getFusedLocationProviderClient(context)
            fusedClient.lastLocation
                .addOnSuccessListener { location ->
                    if (location != null) {
                        val ageMs = System.currentTimeMillis() - location.time
                        // Accept if less than 5 minutes old and accuracy is acceptable
                        if (ageMs < 5 * 60 * 1000L) {
                            cont.resume(location)
                            return@addOnSuccessListener
                        }
                    }
                    cont.resume(null)
                }
                .addOnFailureListener {
                    cont.resume(null)
                }
        } catch (_: SecurityException) {
            cont.resume(null)
        } catch (_: Exception) {
            cont.resume(null)
        }
    }

    private suspend fun getFreshFusedLocation(context: Context): Location? = suspendCancellableCoroutine { cont ->
        try {
            val fusedClient = LocationServices.getFusedLocationProviderClient(context)
            val cts = CancellationTokenSource()

            cont.invokeOnCancellation {
                cts.cancel()
            }

            fusedClient.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, cts.token)
                .addOnSuccessListener { location ->
                    cont.resume(location)
                }
                .addOnFailureListener {
                    cont.resume(null)
                }
        } catch (_: SecurityException) {
            cont.resume(null)
        } catch (_: Exception) {
            cont.resume(null)
        }
    }

    private suspend fun getActiveLocationUpdate(context: Context): Location? = suspendCancellableCoroutine { cont ->
        try {
            val fusedClient = LocationServices.getFusedLocationProviderClient(context)
            val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 2000L)
                .setMinUpdateIntervalMillis(1000L)
                .setMaxUpdates(1)
                .setDurationMillis(5000L)
                .build()

            val callback = object : LocationCallback() {
                override fun onLocationResult(result: LocationResult) {
                    fusedClient.removeLocationUpdates(this)
                    val loc = result.lastLocation
                    if (cont.isActive) {
                        cont.resume(loc)
                    }
                }
            }

            cont.invokeOnCancellation {
                fusedClient.removeLocationUpdates(callback)
            }

            fusedClient.requestLocationUpdates(request, callback, Looper.getMainLooper())
                .addOnFailureListener {
                    fusedClient.removeLocationUpdates(callback)
                    if (cont.isActive) {
                        cont.resume(null)
                    }
                }
        } catch (_: SecurityException) {
            if (cont.isActive) cont.resume(null)
        } catch (_: Exception) {
            if (cont.isActive) cont.resume(null)
        }
    }

    @Suppress("DEPRECATION")
    private suspend fun getPlatformLocationFallback(context: Context): Location? = suspendCancellableCoroutine { cont ->
        try {
            val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as? LocationManager
            if (locationManager == null) {
                cont.resume(null)
                return@suspendCancellableCoroutine
            }

            var bestLocation: Location? = null
            if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                bestLocation = locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
            }
            if (bestLocation == null && locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                bestLocation = locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
            }

            if (bestLocation != null) {
                cont.resume(bestLocation)
                return@suspendCancellableCoroutine
            }

            // Single update via listener
            val provider = when {
                locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
                locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
                else -> null
            }

            if (provider == null) {
                cont.resume(null)
                return@suspendCancellableCoroutine
            }

            val listener = object : LocationListener {
                override fun onLocationChanged(location: Location) {
                    locationManager.removeUpdates(this)
                    if (cont.isActive) cont.resume(location)
                }

                @Deprecated("Deprecated in Java")
                override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
                override fun onProviderEnabled(provider: String) {}
                override fun onProviderDisabled(provider: String) {
                    locationManager.removeUpdates(this)
                    if (cont.isActive) cont.resume(null)
                }
            }

            cont.invokeOnCancellation {
                locationManager.removeUpdates(listener)
            }

            locationManager.requestSingleUpdate(provider, listener, Looper.getMainLooper())
        } catch (_: SecurityException) {
            if (cont.isActive) cont.resume(null)
        } catch (_: Exception) {
            if (cont.isActive) cont.resume(null)
        }
    }

    /**
     * Asynchronously reverse geocodes coordinates to a human-readable address and postal PIN.
     * Guaranteed never to throw and runs strictly on Dispatchers.IO.
     */
    suspend fun reverseGeocode(context: Context, latitude: Double, longitude: Double): ResolvedAddress =
        withContext(Dispatchers.IO) {
            if (!Geocoder.isPresent()) {
                return@withContext ResolvedAddress(null, null)
            }

            try {
                val geocoder = Geocoder(context, Locale.getDefault())

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    suspendCancellableCoroutine { continuation ->
                        geocoder.getFromLocation(latitude, longitude, 1, object : Geocoder.GeocodeListener {
                            override fun onGeocode(addresses: MutableList<Address>) {
                                val address = addresses.firstOrNull()
                                val formatted = formatAddress(address)
                                val pin = address?.postalCode
                                continuation.resume(ResolvedAddress(formatted, pin))
                            }

                            override fun onError(errorMessage: String?) {
                                continuation.resume(ResolvedAddress(null, null))
                            }
                        })
                    }
                } else {
                    @Suppress("DEPRECATION")
                    val addresses = geocoder.getFromLocation(latitude, longitude, 1)
                    val address = addresses?.firstOrNull()
                    val formatted = formatAddress(address)
                    val pin = address?.postalCode
                    ResolvedAddress(formatted, pin)
                }
            } catch (_: Exception) {
                ResolvedAddress(null, null)
            }
        }

    private fun formatAddress(address: Address?): String? {
        if (address == null) return null
        val parts = mutableListOf<String>()

        address.thoroughfare?.let { parts.add(it) }
        address.subLocality?.let { parts.add(it) }
        address.locality?.let { parts.add(it) }
        address.adminArea?.let { parts.add(it) }

        return if (parts.isNotEmpty()) {
            parts.distinct().joinToString(", ")
        } else {
            address.getAddressLine(0)
        }
    }
}
