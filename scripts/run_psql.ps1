param(
    [Parameter(Mandatory=$true)]
    [string]$SqlFile
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $Root ".env"

if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
        $key, $value = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
    }
}

if (-not $env:PSQL_PATH) {
    $env:PSQL_PATH = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
}
if (-not $env:PGHOST) { $env:PGHOST = "localhost" }
if (-not $env:PGPORT) { $env:PGPORT = "5432" }
if (-not $env:PGDATABASE) { $env:PGDATABASE = "uscis_analysis" }
if (-not $env:PGUSER) { $env:PGUSER = "postgres" }

if (-not (Test-Path $env:PSQL_PATH)) {
    throw "psql not found at $env:PSQL_PATH"
}

$ResolvedSqlFile = Resolve-Path $SqlFile
$SqlDir = Split-Path -Parent $ResolvedSqlFile
$SqlName = Split-Path -Leaf $ResolvedSqlFile

Push-Location $SqlDir
try {
    & $env:PSQL_PATH `
        -h $env:PGHOST `
        -p $env:PGPORT `
        -U $env:PGUSER `
        -d $env:PGDATABASE `
        -v ON_ERROR_STOP=1 `
        -f $SqlName
}
finally {
    Pop-Location
}
