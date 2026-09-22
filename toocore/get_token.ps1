# get_token.ps1 - mint a Supabase JWT for pasting into Swagger's Authorize.
#
# Reads Supabase URL/key + dev creds from the frontend .env.development,
# calls the Supabase password-grant endpoint, prints the access_token and
# copies it to the clipboard. Paste it (raw, no "Bearer ") into /swagger Authorize.
#
# Usage:  powershell -ExecutionPolicy Bypass -File .\get_token.ps1

$ErrorActionPreference = 'Stop'

$envPath = 'A:\tooreact\web_acc\.env.development'
if (-not (Test-Path $envPath)) {
    throw "Env file not found: $envPath"
}

# Parse KEY=VALUE lines (skip blanks/comments) into a hashtable.
$cfg = @{}
foreach ($line in Get-Content $envPath) {
    $t = $line.Trim()
    if ($t -eq '' -or $t.StartsWith('#')) { continue }
    $i = $t.IndexOf('=')
    if ($i -lt 1) { continue }
    $cfg[$t.Substring(0, $i).Trim()] = $t.Substring($i + 1).Trim()
}

$url   = $cfg['VITE_SUPABASE_URL']
$key   = $cfg['VITE_SUPABASE_ANON_KEY']
$email = $cfg['DEV_EMAIL']
$pass  = $cfg['DEV_PASSWORD']

foreach ($pair in @{ VITE_SUPABASE_URL = $url; VITE_SUPABASE_ANON_KEY = $key; DEV_EMAIL = $email; DEV_PASSWORD = $pass }.GetEnumerator()) {
    if ([string]::IsNullOrWhiteSpace($pair.Value)) { throw "Missing $($pair.Key) in $envPath" }
}

$resp = Invoke-RestMethod -Method Post `
    -Uri "$url/auth/v1/token?grant_type=password" `
    -Headers @{ apikey = $key } `
    -ContentType 'application/json' `
    -Body (@{ email = $email; password = $pass } | ConvertTo-Json)

$token = $resp.access_token
if ([string]::IsNullOrWhiteSpace($token)) { throw "No access_token in response." }

$token | Set-Clipboard
Write-Host "Token copied to clipboard (valid ~1h). Paste into /swagger Authorize." -ForegroundColor Green
Write-Host ""
Write-Host $token
