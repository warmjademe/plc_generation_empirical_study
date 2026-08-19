param(
    [string]$OutputPath = "\\tsclient\codex\ispsoft_packaging_hits.json"
)

$ErrorActionPreference = "Stop"
$roots = @(
    "$env:ProgramData\Delta Industrial Automation\ISPSoft_New",
    "${env:ProgramFiles(x86)}\Delta Industrial Automation"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
$needles = @(
    "Unzipped.src",
    "ZipFile.tmp",
    ".MPU",
    ".FBU",
    "Import User FBs",
    "Export User FBs"
)

$ascii = [Text.Encoding]::ASCII
$unicode = [Text.Encoding]::Unicode
$hits = @()
$scanned = 0
foreach ($root in $roots) {
    foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue |
             Where-Object { $_.Extension -in @(".dll", ".exe") }) {
        try {
            $bytes = [IO.File]::ReadAllBytes($file.FullName)
            $asciiText = $ascii.GetString($bytes)
            $unicodeText = $unicode.GetString($bytes)
        } catch { continue }
        $scanned += 1
        $matched = @()
        foreach ($needle in $needles) {
            if ($asciiText.Contains($needle) -or $unicodeText.Contains($needle)) {
                $matched += $needle
            }
        }
        if ($matched.Count -gt 0) {
            $hits += [ordered]@{
                path = $file.FullName
                size = $file.Length
                sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
                needles = $matched
            }
        }
    }
}

[ordered]@{
    captured_at = (Get-Date).ToString("o")
    roots = $roots
    scanned_files = $scanned
    hits = $hits
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
