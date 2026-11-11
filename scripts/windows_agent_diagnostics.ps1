# Read-only readiness check for the Windows PDUFA local coding agent.
$ErrorActionPreference = 'Continue'
Write-Host "PDUFA Windows local agent readiness check"
Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,@{N='RAM_GB';E={[math]::Round($_.TotalVisibleMemorySize/1MB,1)}} | Format-List
Get-CimInstance Win32_Processor | Select-Object -First 1 Name | Format-List
Get-CimInstance Win32_VideoController | Select-Object Name,@{N='VRAM_GB';E={[math]::Round($_.AdapterRAM/1GB,1)}} | Format-Table
Get-PSDrive C | Select-Object Name,@{N='Free_GB';E={[math]::Round($_.Free/1GB,1)}} | Format-Table
foreach ($cmd in @('git','python','ollama','gh')) {
  $found = Get-Command $cmd -ErrorAction SilentlyContinue
  Write-Host "$cmd installed: $([bool]$found)"
}
try {
  $models = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3
  Write-Host "Ollama reachable: yes"
  $models.models | Select-Object name,size | Format-Table
} catch { Write-Host "Ollama reachable: no" }
Write-Host "No files, credentials, predictions, or production systems were modified."
