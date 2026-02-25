<#
.SYNOPSIS
    Deploy 3D Print Farm ke server via Portainer API
    Tidak perlu SSH - cukup username/password Portainer

.USAGE
    .\deploy.ps1              - Deploy kode terbaru ke server
    .\deploy.ps1 -Logs        - Lihat logs backend secara live
    .\deploy.ps1 -Restart     - Restart semua container
    .\deploy.ps1 -Status      - Cek status container
    .\deploy.ps1 -Setup       - Setup awal (pertama kali saja)
    .\deploy.ps1 -SetupGHCR   - Daftarkan GHCR registry ke Portainer (wajib sekali)
#>
param(
    [switch]$Logs,
    [switch]$Restart,
    [switch]$Status,
    [switch]$Setup,
    [switch]$SetupGHCR
)

# ============================================================
#  KONFIGURASI - EDIT BAGIAN INI
# ============================================================
$PORTAINER_URL   = "https://192.168.4.67:9443"
$STACK_ID        = 44
$STACK_NAME      = "3d-print-farm"
$CONFIG_FILE     = "$PSScriptRoot\.deploy-config.json"
$GITHUB_USERNAME = "kevinwiliamleo-dev"
$GHCR_URL        = "ghcr.io"
# ============================================================

# Warna output
function Write-Step  { param($msg) Write-Host "[...] $msg" -ForegroundColor Cyan }
function Write-OK    { param($msg) Write-Host "[ OK] $msg" -ForegroundColor Green }
function Write-Fail  { param($msg) Write-Host "[ERR] $msg" -ForegroundColor Red }
function Write-Warn  { param($msg) Write-Host "[!  ] $msg" -ForegroundColor Yellow }
function Write-Title { param($msg) Write-Host "`n=== $msg ===" -ForegroundColor White }

# Bypass SSL untuk self-signed cert Portainer
if (-not ([System.Management.Automation.PSTypeName]'TrustAllCerts').Type) {
    Add-Type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCerts : ICertificatePolicy {
    public bool CheckValidationResult(ServicePoint sp, X509Certificate cert, WebRequest req, int problem) { return true; }
}
"@
}
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCerts
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

# ============================================================
# LOAD / SIMPAN KONFIGURASI
# ============================================================
function Get-Config {
    if (Test-Path $CONFIG_FILE) {
        # Convert to hashtable so we can add new properties freely
        $obj = Get-Content $CONFIG_FILE | ConvertFrom-Json
        $ht = @{}
        $obj.PSObject.Properties | ForEach-Object { $ht[$_.Name] = $_.Value }
        return $ht
    }
    return @{}
}

function Save-Config { param($config) $config | ConvertTo-Json | Set-Content $CONFIG_FILE }

function Get-GithubPAT {
    $config = Get-Config
    if ($config.github_pat) { return $config.github_pat }
    Write-Warn "GitHub PAT belum tersimpan"
    $pat = Read-Host "Masukkan GitHub PAT (untuk akses GHCR)"
    $config.github_pat = $pat
    $config.github_username = $GITHUB_USERNAME
    Save-Config $config
    return $pat
}

function Get-PortainerToken {
    $config = Get-Config
    if ($config.token) {
        # Test apakah token masih valid
        try {
            $r = Invoke-RestMethod -Uri "$PORTAINER_URL/api/users/me" -Headers @{Authorization="Bearer $($config.token)"} -Method GET
            return $config.token
        } catch { }
    }

    # Token tidak ada / expired - coba auto-login pakai password tersimpan dulu
    $savedUsername = if ($config.username) { $config.username } else { "root" }
    $savedPassword = if ($config.portainer_password) { $config.portainer_password } else { $null }

    if ($savedPassword) {
        Write-Host "[...] Token expired, auto-login dengan credentials tersimpan..."
        try {
            $body = @{ username = $savedUsername; password = $savedPassword } | ConvertTo-Json
            $r = Invoke-RestMethod -Uri "$PORTAINER_URL/api/auth" -Method POST -Body $body -ContentType "application/json"
            $token = $r.jwt
            $config.token = $token
            Save-Config $config
            Write-OK "Auto-login berhasil"
            return $token
        } catch {
            Write-Warn "Auto-login gagal, minta manual login..."
        }
    }

    # Fallback: minta input manual
    Write-Warn "Perlu login ke Portainer"
    $username = Read-Host "Username Portainer"
    $password = Read-Host "Password Portainer" -AsSecureString
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
    )

    try {
        $body = @{ username = $username; password = $plainPassword } | ConvertTo-Json
        $r = Invoke-RestMethod -Uri "$PORTAINER_URL/api/auth" -Method POST -Body $body -ContentType "application/json"
        $token = $r.jwt

        # Simpan token + password untuk auto-login berikutnya
        $config.token = $token
        $config.username = $username
        $config.portainer_password = $plainPassword
        Save-Config $config

        Write-OK "Login berhasil - token & password disimpan (auto-login aktif)"
        return $token
    } catch {
        Write-Fail "Login gagal: $_"
        exit 1
    }
}

# ============================================================
# PORTAINER API HELPERS
# ============================================================
function Invoke-PortainerAPI {
    param($Path, $Method = "GET", $Body = $null)
    $token = Get-PortainerToken
    $headers = @{ Authorization = "Bearer $token" }
    $params = @{
        Uri     = "$PORTAINER_URL$Path"
        Method  = $Method
        Headers = $headers
    }
    if ($Body) {
        $params.Body = $Body | ConvertTo-Json -Depth 10
        $params.ContentType = "application/json"
    }
    return Invoke-RestMethod @params
}

function Get-StackInfo {
    # Coba pakai ID langsung dulu
    try {
        return Invoke-PortainerAPI -Path "/api/stacks/$STACK_ID"
    } catch {
        # Kalau gagal (misal ID berubah setelah recreate), cari by nama
        $stacks = Invoke-PortainerAPI -Path "/api/stacks"
        $found = $stacks | Where-Object { $_.Name -eq $STACK_NAME } | Select-Object -First 1
        if ($found) {
            # Update STACK_ID otomatis
            $script:STACK_ID = $found.Id
            return $found
        }
        throw "Stack '$STACK_NAME' tidak ditemukan di Portainer"
    }
}

function Get-EndpointId {
    $stack = Get-StackInfo
    return $stack.EndpointId
}

function Get-Containers {
    param($endpointId, $stackName)
    $all = Invoke-PortainerAPI -Path "/api/endpoints/$endpointId/docker/containers/json?all=1"
    # Gabungkan: container dengan project label ATAU nama mengandung "3d-farm"
    $byLabel = $all | Where-Object { $_.Labels.'com.docker.compose.project' -eq $stackName }
    $byName  = $all | Where-Object { $_.Names[0] -match "3d-farm" }
    # Merge dan deduplicate berdasarkan container Id
    $combined = @($byLabel) + @($byName) | Sort-Object Id -Unique
    return $combined
}

# ============================================================
# FITUR: STATUS
# ============================================================
function Show-Status {
    Write-Title "Status Container: $STACK_NAME"
    try {
        $endpointId = Get-EndpointId
        $containers = Get-Containers $endpointId $STACK_NAME
        if (-not $containers) {
            Write-Warn "Tidak ada container ditemukan untuk stack '$STACK_NAME'"
            return
        }
        foreach ($c in $containers) {
            $name = $c.Names[0] -replace '^/', ''
            $status = $c.Status
            $color = if ($c.State -eq "running") { "Green" } else { "Red" }
            Write-Host ("  {0,-35} {1}" -f $name, $status) -ForegroundColor $color
        }
    } catch {
        Write-Fail "Gagal ambil status: $_"
    }
}

# ============================================================
# FITUR: LOGS
# ============================================================
function Show-Logs {
    Write-Title "Logs Backend (Ctrl+C untuk stop)"
    try {
        $endpointId = Get-EndpointId
        $containers = Get-Containers $endpointId $STACK_NAME
        $backend = $containers | Where-Object { $_.Names[0] -match "backend" } | Select-Object -First 1
        if (-not $backend) {
            Write-Fail "Container backend tidak ditemukan"
            return
        }
        $containerId = $backend.Id
        Write-OK "Streaming logs dari: $($backend.Names[0])..."
        Write-Host "(Tekan Ctrl+C untuk stop)`n" -ForegroundColor Gray
        # Buka log URL di browser sebagai alternatif
        $logsUrl = "$PORTAINER_URL/#!/$($endpointId.ToString())/docker/containers/$containerId/logs"
        Start-Process $logsUrl
        Write-OK "Log dibuka di browser Portainer"
    } catch {
        Write-Fail "Gagal ambil logs: $_"
    }
}

# ============================================================
# FITUR: RESTART
# ============================================================
function Restart-Stack {
    Write-Title "Restart Container Stack"
    try {
        $endpointId = Get-EndpointId
        $containers = Get-Containers $endpointId $STACK_NAME
        foreach ($c in $containers) {
            $name = $c.Names[0] -replace '^/', ''
            Write-Step "Restart: $name"
            Invoke-PortainerAPI -Path "/api/endpoints/$endpointId/docker/containers/$($c.Id)/restart" -Method POST
            Write-OK "Restarted: $name"
        }
    } catch {
        Write-Fail "Gagal restart: $_"
    }
}

# ============================================================
# FITUR: DEPLOY UTAMA
# ============================================================
function Deploy-ToServer {
    Write-Title "DEPLOY ke $PORTAINER_URL"
    
    # [1] Cek git status
    Write-Step "[1/4] Cek perubahan file..."
    $gitStatus = git -C "$PSScriptRoot" status --porcelain 2>&1
    if (-not $gitStatus) {
        Write-Warn "Tidak ada perubahan file baru"
        $confirm = Read-Host "Tetap deploy? (y/n)"
        if ($confirm -ne "y") { return }
    } else {
        $changedFiles = ($gitStatus -split "`n").Count
        Write-OK "$changedFiles file berubah"
    }

    # [2] Git commit + push
    Write-Step "[2/4] Push ke GitHub..."
    git -C "$PSScriptRoot" add -A 2>&1 | Out-Null
    $commitMsg = "deploy: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    $commitResult = git -C "$PSScriptRoot" commit -m $commitMsg 2>&1
    if ($LASTEXITCODE -ne 0 -and $commitResult -match "nothing to commit") {
        Write-Warn "Tidak ada commit baru"
    } else {
        Write-OK "Commit: $commitMsg"
    }
    
    $pushResult = git -C "$PSScriptRoot" push 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Git push gagal: $pushResult"
        Write-Warn "Lanjut restart container saja..."
    } else {
        Write-OK "Push ke GitHub berhasil"
        Write-Host "  GitHub Actions akan build image baru (~3-5 menit)" -ForegroundColor Gray
        Write-Host "  Cek: https://github.com/kevinwiliamleo-dev/3d-print-farm-management/actions" -ForegroundColor Gray
    }

    # [3] Cek stack info di Portainer
    Write-Step "[3/4] Cek stack di Portainer..."
    try {
        $stack = Get-StackInfo
        $isGitBased = ($stack.GitConfig -ne $null)
        Write-OK "Stack ditemukan: $($stack.Name) (Git: $isGitBased)"

        if ($isGitBased) {
            # Trigger git redeploy via Portainer API
            Write-Step "Trigger Portainer Git redeploy..."
            $body = @{ pullImage = $true; RepositoryReferenceName = $stack.GitConfig.ReferenceName }
            try {
                Invoke-PortainerAPI -Path "/api/stacks/$STACK_ID/git/redeploy" -Method PUT -Body $body
                Write-OK "Portainer sedang redeploy dari Git!"
            } catch {
                Write-Warn "Git redeploy gagal - coba restart container saja"
                Restart-Stack
            }
        } else {
            # Stack pakai file (bukan Git) - update stack via API + pull image baru dari GHCR
            Write-Step "Memperbarui stack via Portainer API (pull image baru)..."
            
            $composeFile = Join-Path $PSScriptRoot "docker-compose.yml"
            if (-not (Test-Path $composeFile)) {
                Write-Fail "docker-compose.yml tidak ditemukan di: $composeFile"
                Restart-Stack
                return
            }

            $composeContent = Get-Content $composeFile -Raw
            # Normalise line endings to LF (Docker API needs LF not CRLF)
            $composeContent = $composeContent -replace "`r`n", "`n"

            $updateBody = @{
                StackFileContent = $composeContent
                Env              = @()
                Prune            = $true
                pullImage        = $true
            } | ConvertTo-Json -Depth 5
            # Fix line endings in JSON too
            $updateBody = $updateBody -replace "`r`n", "`n"

            try {
                $token = Get-PortainerToken
                $endpoint = $stack.EndpointId
                $r = Invoke-RestMethod `
                    -Uri "$PORTAINER_URL/api/stacks/$STACK_ID`?endpointId=$endpoint" `
                    -Method PUT `
                    -Headers @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" } `
                    -Body $updateBody
                Write-OK "Stack berhasil diperbarui! Image baru ditarik dari GHCR."
                Write-Warn "NOTE: Jika GitHub Actions belum selesai build, image yang dipull mungkin yang lama."
                Write-Host "  Cek GitHub Actions: https://github.com/kevinwiliamleo-dev/3d-print-farm-management/actions" -ForegroundColor Gray
            } catch {
                $errMsg = $_.ToString()
                if ($errMsg -match "500" -or $errMsg -match "pull") {
                    Write-Warn "Pull image gagal (mungkin GitHub Actions belum selesai build)."
                    Write-Warn "Menunggu 60 detik lalu coba lagi..."
                    Start-Sleep -Seconds 60
                    try {
                        $r = Invoke-RestMethod `
                            -Uri "$PORTAINER_URL/api/stacks/$STACK_ID`?endpointId=$endpoint" `
                            -Method PUT `
                            -Headers @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" } `
                            -Body $updateBody
                        Write-OK "Stack berhasil diperbarui setelah retry!"
                    } catch {
                        Write-Warn "Pull image masih gagal. Container di-restart dengan image yang ada."
                        Write-Host "  Kemungkinan sebab:" -ForegroundColor Yellow
                        Write-Host "    1. GitHub Actions masih build (tunggu 3-5 menit, lalu jalankan deploy.bat lagi)" -ForegroundColor Gray
                        Write-Host "    2. GHCR private - perlu setup registry di Portainer" -ForegroundColor Gray
                        Write-Host "  Cek status build: https://github.com/kevinwiliamleo-dev/3d-print-farm-management/actions" -ForegroundColor Cyan
                        Restart-Stack
                    }
                } else {
                    Write-Warn "Update stack gagal ($errMsg). Restart container saja..."
                    Restart-Stack
                }
            }
        }
    } catch {
        Write-Fail "Tidak bisa akses Portainer API: $_"
        exit 1
    }

    # [4] Verifikasi
    Write-Step "[4/4] Verifikasi..."
    Start-Sleep -Seconds 3
    Show-Status

    Write-Host ""
    Write-OK "======================================"
    Write-OK "  DEPLOY SELESAI!"
    Write-OK "  Buka: http://192.168.4.67:3051"
    Write-OK "======================================"
}

# ============================================================
# FITUR: SETUP GHCR REGISTRY DI PORTAINER
# ============================================================
function Setup-GHCRRegistry {
    Write-Title "Setup GHCR Registry di Portainer"
    $pat = Get-GithubPAT
    
    # Cek apakah registry GHCR sudah ada
    try {
        $registries = Invoke-PortainerAPI -Path "/api/registries"
        $existing = $registries | Where-Object { $_.URL -eq $GHCR_URL } | Select-Object -First 1
        
        if ($existing) {
            Write-OK "Registry GHCR sudah ada (ID: $($existing.Id))"
            # Update credentials jika perlu
            $body = @{
                Name        = "GHCR"
                Type        = 3
                URL         = $GHCR_URL
                Username    = $GITHUB_USERNAME
                Password    = $pat
                Authentication = $true
            }
            Invoke-PortainerAPI -Path "/api/registries/$($existing.Id)" -Method PUT -Body $body | Out-Null
            Write-OK "Credentials GHCR diperbarui"
        } else {
            # Tambah registry baru
            $body = @{
                Name        = "GHCR"
                Type        = 3
                URL         = $GHCR_URL
                Username    = $GITHUB_USERNAME
                Password    = $pat
                Authentication = $true
            }
            Invoke-PortainerAPI -Path "/api/registries" -Method POST -Body $body | Out-Null
            Write-OK "Registry GHCR berhasil ditambahkan ke Portainer!"
        }
    } catch {
        Write-Fail "Gagal setup GHCR registry: $_"
    }
}

# ============================================================
# FITUR: SETUP AWAL
# ============================================================
function Show-Setup {
    Write-Title "PANDUAN SETUP AWAL"
    Write-Host @"

Untuk deploy otomatis, ikuti langkah berikut di Portainer:

LANGKAH 1: Buka Portainer
  https://192.168.4.67:9443

LANGKAH 2: Hubungkan Stack ke Git
  1. Buka stack '3d-print-farm' (ID: 44)
  2. Klik tombol [Detach this stack from Git / Edit stack]
  3. Kalau ada opsi 'Git Repository' pilih itu
  4. Masukkan:
     - Repository URL: https://github.com/kevinwiliamleo-dev/3d-print-farm-management
     - Reference: refs/heads/development
     - Compose path: docker-compose.dev.yml
  5. Centang 'Auto update' (opsional)
  6. Klik [Save]

LANGKAH 3: Setup Volume di Server
  Di server (192.168.4.67), jalankan SATU KALI:
    git clone https://github.com/kevinwiliamleo-dev/3d-print-farm-management /opt/3d-print-farm

LANGKAH 4: Simpan kredensial Portainer
  Jalankan: .\deploy.ps1
  Masukkan username & password Portainer saat diminta.
  Token akan disimpan otomatis.

SETELAH SETUP:
  Cukup jalankan: .\deploy.bat
  Script ini akan otomatis: git push + redeploy server

"@ -ForegroundColor Cyan
}

# ============================================================
# MAIN
# ============================================================
if ($Setup)   { Show-Setup;         exit 0 }
if ($Status)  { Show-Status;        exit 0 }
if ($Logs)    { Show-Logs;          exit 0 }
if ($Restart) { Restart-Stack;      exit 0 }
if ($SetupGHCR) { Setup-GHCRRegistry; exit 0 }

Deploy-ToServer
