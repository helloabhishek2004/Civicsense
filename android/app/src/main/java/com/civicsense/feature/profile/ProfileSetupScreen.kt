package com.civicsense.feature.profile

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.outlined.Email
import androidx.compose.material.icons.outlined.LocationOn
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Phone
import androidx.compose.material.icons.outlined.Pin
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.civicsense.core.design.CivicPrimaryButton
import com.civicsense.core.design.CivicTopAppBar
import com.civicsense.core.theme.CivicGreen
import com.civicsense.core.util.InputValidators
import com.civicsense.data.repository.PreferenceRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun ProfileSetupScreen(
    preferenceRepository: PreferenceRepository,
    onProfileCompleted: () -> Unit,
    modifier: Modifier = Modifier
) {
    val scope = rememberCoroutineScope()
    var fullName by remember { mutableStateOf("") }
    var mobileNumber by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var locality by remember { mutableStateOf("") }
    var postalPin by remember { mutableStateOf("") }

    var fullNameError by remember { mutableStateOf<String?>(null) }
    var mobileError by remember { mutableStateOf<String?>(null) }
    var emailError by remember { mutableStateOf<String?>(null) }
    var postalPinError by remember { mutableStateOf<String?>(null) }
    var isCompleting by remember { mutableStateOf(false) }

    fun validate(): Pair<Boolean, String?> {
        var isValid = true
        var normalizedPhone: String? = null

        if (!InputValidators.isValidFullName(fullName)) {
            fullNameError = "Please enter your full name (at least 2 characters)"
            isValid = false
        } else {
            fullNameError = null
        }

        val (isPhoneValid, normPhone) = InputValidators.normalizeIndianMobile(mobileNumber)
        if (!isPhoneValid || normPhone == null) {
            mobileError = "Enter a valid 10-digit Indian mobile number (starts with 6, 7, 8, or 9)"
            isValid = false
        } else {
            mobileError = null
            normalizedPhone = normPhone
        }

        if (!InputValidators.isValidEmail(email)) {
            emailError = "Enter a valid email address (e.g. name@example.com)"
            isValid = false
        } else {
            emailError = null
        }

        if (!InputValidators.isValidPostalPin(postalPin)) {
            postalPinError = "PIN code must contain exactly 6 digits (cannot start with 0)"
            isValid = false
        } else {
            postalPinError = null
        }

        return Pair(isValid, normalizedPhone)
    }

    if (isCompleting) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
                modifier = Modifier.padding(32.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(64.dp)
                        .clip(CircleShape)
                        .background(CivicGreen.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.CheckCircle,
                        contentDescription = null,
                        tint = CivicGreen,
                        modifier = Modifier.size(36.dp)
                    )
                }

                Spacer(modifier = Modifier.height(20.dp))

                Text(
                    text = "Profile ready!",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onBackground
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = "Setting up your CivicSense dashboard…",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(24.dp))

                CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    strokeWidth = 2.5.dp,
                    color = CivicGreen
                )
            }
        }
        return
    }

    Scaffold(
        modifier = modifier
            .fillMaxSize()
            .imePadding(),
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            CivicTopAppBar(
                title = "Profile Setup",
                canNavigateBack = false
            )
        },
        bottomBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp)
            ) {
                CivicPrimaryButton(
                    text = "Continue",
                    isLoading = isCompleting,
                    onClick = {
                        val (isValid, normalizedPhone) = validate()
                        if (isValid && normalizedPhone != null) {
                            isCompleting = true
                            scope.launch {
                                preferenceRepository.saveProfile(
                                    fullName = fullName,
                                    mobileNumber = normalizedPhone,
                                    email = email,
                                    locality = locality,
                                    postalPin = postalPin
                                )
                                delay(700) // 600-800ms completion moment
                                onProfileCompleted()
                            }
                        }
                    }
                )
            }
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 24.dp)
                .verticalScroll(rememberScrollState())
        ) {
            Text(
                text = "Let's set up your profile",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "These details help identify your reports and route them to your local municipal ward.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Full Name (Required)
            OutlinedTextField(
                value = fullName,
                onValueChange = {
                    fullName = it
                    if (fullNameError != null) fullNameError = null
                },
                label = { Text("Full name *") },
                placeholder = { Text("Abhishek S") },
                leadingIcon = {
                    Icon(imageVector = Icons.Outlined.Person, contentDescription = null)
                },
                isError = fullNameError != null,
                supportingText = fullNameError?.let { { Text(it) } },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Mobile Number (Required)
            OutlinedTextField(
                value = mobileNumber,
                onValueChange = {
                    if (it.length <= 15) mobileNumber = it
                    if (mobileError != null) mobileError = null
                },
                label = { Text("Mobile number *") },
                placeholder = { Text("9874563210") },
                leadingIcon = {
                    Icon(imageVector = Icons.Outlined.Phone, contentDescription = null)
                },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                isError = mobileError != null,
                supportingText = mobileError?.let { { Text(it) } }
                    ?: { Text("10-digit Indian mobile number") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Email Address (Optional)
            OutlinedTextField(
                value = email,
                onValueChange = {
                    email = it
                    if (emailError != null) emailError = null
                },
                label = { Text("Email address (Optional)") },
                placeholder = { Text("abhishek@example.com") },
                leadingIcon = {
                    Icon(imageVector = Icons.Outlined.Email, contentDescription = null)
                },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                isError = emailError != null,
                supportingText = emailError?.let { { Text(it) } },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Locality / Area (Optional)
            OutlinedTextField(
                value = locality,
                onValueChange = { locality = it },
                label = { Text("Locality / Area (Optional)") },
                placeholder = { Text("Near the public library, Main Road") },
                leadingIcon = {
                    Icon(imageVector = Icons.Outlined.LocationOn, contentDescription = null)
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Postal PIN Code (Required, 6 digits)
            OutlinedTextField(
                value = postalPin,
                onValueChange = { input ->
                    val digits = input.filter { it.isDigit() }
                    if (digits.length <= 6) postalPin = digits
                    if (postalPinError != null) postalPinError = null
                },
                label = { Text("Postal PIN code *") },
                placeholder = { Text("695xxx") },
                leadingIcon = {
                    Icon(imageVector = Icons.Outlined.Pin, contentDescription = null)
                },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                isError = postalPinError != null,
                supportingText = postalPinError?.let { { Text(it) } }
                    ?: { Text("6-digit postal PIN code") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(20.dp))

            // Privacy Note Card
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)
                ),
                shape = MaterialTheme.shapes.medium,
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        text = "Privacy note",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "CivicSense uses your details strictly for issue validation and communication. Your contact information is never published to public feeds.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(32.dp))
        }
    }
}
