$ErrorActionPreference = "SilentlyContinue"

$Ports = @(8000, 5173)

foreach ($Port in $Ports) {
    $Connections = Get-NetTCPConnection -LocalPort $Port -State Listen
    foreach ($Connection in $Connections) {
        $ProcessId = $Connection.OwningProcess
        if ($ProcessId) {
            $Process = Get-Process -Id $ProcessId
            if ($Process) {
                Write-Host "Stopping port $Port: $($Process.ProcessName)($ProcessId)" -ForegroundColor Yellow
                Stop-Process -Id $ProcessId -Force
            }
        }
    }
}

Write-Host "NewWorld services stopped." -ForegroundColor Green
pause
