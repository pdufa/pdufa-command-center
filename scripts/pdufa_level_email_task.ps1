# PDUFA Level Acceptance Email: separate read-only scheduled notifier.
# On install prompts for Gmail app password and encrypts it using Windows DPAPI.
# NEVER logs the password, modifies the PDUFA development worker, or mails drafts.
[CmdletBinding()]
param([switch]$Install,[switch]$Check,[switch]$Status,[switch]$Uninstall)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if(@(@($Install,$Check,$Status,$Uninstall)|Where-Object {$_}).Count -ne 1){
  throw 'Choose -Install, -Check, -Status, or -Uninstall.'
}
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$data=Join-Path $env:USERPROFILE 'PDUFA-Agent-Continuous'
$cfg=Join-Path $data 'level-email-config.json'
$passwordPath=Join-Path $data 'level-email-password.dpapi'
$sequence=Join-Path $data 'sequential_level_status.json'
$taskName='PDUFA-Level-Completion-Email'
$pythonScript=Join-Path $PSScriptRoot 'pdufa_level_accepted_email.py'
$branch='automation/level-acceptance-email-20261112'
$blob='d10b8e3ccda71f685a200e673804508adb9bf804'
$actor=[Security.Principal.WindowsIdentity]::GetCurrent()
function AssertSameUser($task){
  if($null -eq $task){return}
  $name=[string]$task.Principal.UserId
  if([string]::IsNullOrWhiteSpace($name)){throw 'Task principal missing'}
  try{
    if($name -match '^S-1-[0-9]+(?:-[0-9]+)+$'){
      $sid=([Security.Principal.SecurityIdentifier]::new($name)).Value
    }else{
      $sid=([Security.Principal.NTAccount]::new($name)).Translate(
        [Security.Principal.SecurityIdentifier]).Value
    }
  }catch{throw 'Cannot verify scheduled task ownership'}
  if($sid -ne $actor.User.Value){throw 'Existing email task belongs to a different Windows user'}
  if(@($task.Actions).Count -ne 1 -or
    $task.Actions[0].Arguments -notmatch 'pdufa_level_email_task\.ps1' -or
    $task.Actions[0].Arguments -notmatch '(?<!\S)-Check(?!\S)'){
    throw 'Unexpected existing task: no modification permitted'
  }
}
function Require([string]$label){
  if($LASTEXITCODE -ne 0){throw ($label+'_FAILED')}
}
function ValidateEmail([string]$value){
  if($value -notmatch '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,30}$' -or $value.Length -gt 254){
    throw 'A single valid mailbox is required'
  }
  return $value
}
function InvokeNotifier([switch]$ReadOnly){
  if(-not(Test-Path $pythonScript -PathType Leaf)){throw 'Email notifier code is not installed'}
  if($ReadOnly){
    & py -3.13 -B $pythonScript --status
    Require 'EMAIL_STATUS'
    return
  }
  if(-not(Test-Path $cfg -PathType Leaf) -or
     -not(Test-Path $passwordPath -PathType Leaf)){
    throw 'GMAIL_APP_PASSWORD_NOT_CONFIGURED'
  }
  $record=Get-Content $cfg -Raw | ConvertFrom-Json
  $user=ValidateEmail ([string]$record.gmail_user)
  $recipient=ValidateEmail ([string]$record.alert_email)
  # Same-user DPAPI. Never write decrypted secret to the disk.
  $secure=(Get-Content $passwordPath -Raw).Trim() | ConvertTo-SecureString
  $ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try{
    $env:PDUFA_GMAIL_USER=$user
    $env:PDUFA_ALERT_EMAIL=$recipient
    $env:PDUFA_GMAIL_APP_PASSWORD=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    & py -3.13 -B $pythonScript --once
    Require 'EMAIL_DELIVERY_CHECK'
  }finally{
    Remove-Item Env:PDUFA_GMAIL_APP_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:PDUFA_GMAIL_USER -ErrorAction SilentlyContinue
    Remove-Item Env:PDUFA_ALERT_EMAIL -ErrorAction SilentlyContinue
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
  }
}
$task=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
AssertSameUser $task
if($Status){
  Write-Host ('PDUFA level email task: '+$(if($task){$task.State}else{'NOT INSTALLED'}))
  Write-Host ('Local encrypted Gmail configuration: '+(
    (Test-Path $cfg -PathType Leaf) -and (Test-Path $passwordPath -PathType Leaf)))
  if(Test-Path $pythonScript -PathType Leaf){
    InvokeNotifier -ReadOnly
  }
  exit 0
}
if($Uninstall){
  if($task){Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop}
  Write-Host 'Level completion email schedule removed; encrypted credentials retained.'
  exit 0
}
if($Check){
  # The sequencing worker remains independent, safe and unaffected.
  if(-not(Test-Path $sequence -PathType Leaf)){
    Write-Host 'STRICT_LEVEL_WORKER_NOT_INSTALLED: no email attempted.'
    exit 2
  }
  InvokeNotifier
  exit 0
}
# Install: check existing worker, exact reviewed Git blob, and local email settings.
if(-not(Test-Path $sequence -PathType Leaf)){
  throw 'Strict Level Completion worker has no recorded sequence state.'
}
New-Item -ItemType Directory -Path $data -Force | Out-Null
$origin=(& git -C $root remote get-url origin | Out-String).Trim()
Require 'GIT_REMOTE'
if($origin -notmatch '^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)pdufa/pdufa-command-center(?:\.git)?/?$'){
  throw 'Unexpected repository origin'
}
& git -C $root fetch --no-tags origin $branch
Require 'FETCH_EMAIL_DRAFT'
$revision=(& git -C $root rev-parse ('FETCH_HEAD^{commit}') | Out-String).Trim()
Require 'FETCHED_REVISION'
$actual=(& git -C $root rev-parse ($revision+':scripts/pdufa_level_accepted_email.py') | Out-String).Trim()
Require 'REVIEWED_BLOB'
if($actual -ne $blob){throw 'Email notifier changed since review; do not install'}
$url='https://raw.githubusercontent.com/pdufa/pdufa-command-center/'+$revision+'/scripts/pdufa_level_accepted_email.py'
$tmp=Join-Path $data ('email-'+[guid]::NewGuid().ToString('N')+'.tmp')
Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $tmp
$hash=(& git -C $root hash-object $tmp | Out-String).Trim()
Require 'NOTIFIER_HASH'
if($hash -ne $blob){
  Remove-Item $tmp -Force -ErrorAction SilentlyContinue
  throw 'Email notifier content hash mismatch'
}
$existingHash=''
if(Test-Path $pythonScript -PathType Leaf){
  $existingHash=(& git -C $root hash-object $pythonScript | Out-String).Trim()
  Require 'EXISTING_NOTIFIER_HASH'
}
if($existingHash -and $existingHash -ne $blob){
  Remove-Item $tmp -Force -ErrorAction SilentlyContinue
  throw 'A different notifier already exists; manual review required.'
}
Copy-Item $tmp $pythonScript -Force
Remove-Item $tmp -Force -ErrorAction SilentlyContinue
& py -3.13 -B $pythonScript --self-test
Require 'EMAIL_SELF_TEST'
$tests=Join-Path $root 'tests/test_pdufa_level_accepted_email.py'
if(-not(Test-Path $tests -PathType Leaf)){
  Write-Host 'Offline tests are in GitHub draft PR. Self-test passed locally.'
}
if(-not(Test-Path $cfg -PathType Leaf) -or -not(Test-Path $passwordPath -PathType Leaf)){
  $sender=ValidateEmail (Read-Host 'Gmail sender address for PDUFA alerts')
  $recipient=ValidateEmail (Read-Host 'Email address to receive level-completion alerts')
  $secure=Read-Host -AsSecureString 'Gmail APP password (not your normal Gmail password)'
  if($secure.Length -lt 8){throw 'Gmail app password missing'}
  $secure | ConvertFrom-SecureString | Set-Content -LiteralPath $passwordPath -Encoding UTF8
  @{gmail_user=$sender;alert_email=$recipient} | ConvertTo-Json |
    Set-Content -LiteralPath $cfg -Encoding UTF8
}
if(-not $task){
  $taskScript=(Resolve-Path -LiteralPath $PSCommandPath).Path
  $action=New-ScheduledTaskAction -Execute (Join-Path $PSHOME 'powershell.exe') -Argument (
    '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -Check' -f $taskScript
  ) -WorkingDirectory $root
  $trigger=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 2)
  $logon=New-ScheduledTaskTrigger -AtLogOn -User $actor.Name
  $principal=New-ScheduledTaskPrincipal -UserId $actor.Name -LogonType Interactive -RunLevel Limited
  $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::FromMinutes(2)) -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($trigger,$logon) -Principal $principal -Settings $settings -Description 'Email only after external PDUFA level acceptance; no model predictions or trades' -ErrorAction Stop | Out-Null
}
Write-Host 'LEVEL_ACCEPTANCE_EMAIL_SCHEDULED: checks for independently accepted levels every 2 minutes.'
Write-Host 'No email will be sent for Stage 4 until all external review gates are accepted.'
& $PSCommandPath -Check
if($LASTEXITCODE -ne 0){Write-Warning 'Notification delivery not verified; check local Gmail app-password configuration.'}
