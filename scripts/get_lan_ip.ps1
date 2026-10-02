<#
.SYNOPSIS
    Detects the active LAN IPv4 address for CivicSense.

.DESCRIPTION
    Scans active network adapters, prioritizes Wi-Fi or active Ethernet interfaces,
    and provides the IP or full backend API URL. Can also update local.properties.

.PARAMETER Port
    Backend port number. Default: 8000.

.PARAMETER Format
    Output format: 'ip', 'url', or 'json'. Default: 'url'.

.PARAMETER UpdateFiles
    If specified, updates android/local.properties with the detected API_BASE_URL.
#>

param(
    [int]$Port = 8000,
    [ValidateSet('ip', 'url', 'json')]
    [string]$Format = 'url',
    [switch]$UpdateFiles
)

# 1. Query IPv4 addresses on active, connected adapters
$ipList = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {
    $_.IPAddress -notmatch '^127\.' -and
    $_.IPAddress -notmatch '^169\.254\.' -and
    $_.InterfaceAlias -notmatch 'vEthernet' -and
    $_.InterfaceAlias -notmatch 'Virtual' -and
    $_.InterfaceAlias -notmatch 'Loopback'
}

# 2. Prioritize Wi-Fi adapter, then Ethernet
$chosen = $ipList | Where-Object { $_.InterfaceAlias -match 'Wi-Fi' } | Select-Object -First 1
if (-not $chosen) {
    $chosen = $ipList | Where-Object { $_.InterfaceAlias -match 'Ethernet' } | Select-Object -First 1
}
if (-not $chosen) {
    $chosen = $ipList | Select-Object -First 1
}

$detectedIp = if ($chosen) { $chosen.IPAddress } else { "127.0.0.1" }
$apiUrl = "http://${detectedIp}:${Port}"

# 3. Optional: update android/local.properties
if ($UpdateFiles) {
    $projectRoot = Split-Path -Parent $PSScriptRoot
    $localPropsPath = Join-Path $projectRoot "android\local.properties"
    if (Test-Path $localPropsPath) {
        $content = Get-Content $localPropsPath -Raw
        if ($content -match "API_BASE_URL=.*") {
            $newContent = $content -replace "API_BASE_URL=.*", "API_BASE_URL=$apiUrl"
            Set-Content -Path $localPropsPath -Value $newContent -NoNewline
        } else {
            Add-Content -Path $localPropsPath -Value "`nAPI_BASE_URL=$apiUrl"
        }
        Write-Host "Updated $localPropsPath with API_BASE_URL=$apiUrl" -ForegroundColor Green
    }
}

# 4. Output according to requested format
switch ($Format) {
    'ip'   { $detectedIp }
    'url'  { $apiUrl }
    'json' {
        @{
            ip = $detectedIp
            port = $Port
            url = $apiUrl
            interface = if ($chosen) { $chosen.InterfaceAlias } else { "unknown" }
        } | ConvertTo-Json -Compress
    }
}
