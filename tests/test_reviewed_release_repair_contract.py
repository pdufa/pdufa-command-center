"""Release/STOP safety regressions; Windows cases execute only pure helpers.

The installer and updater top-level code is never invoked by these tests. On
Windows, helper definitions are extracted into a temporary PowerShell process
with temporary files, without Task Scheduler, a network request, or a worker.
"""
from pathlib import Path
import base64
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/windows_pdufa_level6_unblock.ps1"
UPDATER = ROOT / "scripts/windows_pdufa_reviewed_release_updater.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("pwsh")


def function_definition(source: str, name: str) -> str:
    match = re.search(r"(?ms)^function " + re.escape(name) + r"\b.*?^}", source)
    if match is None:
        raise AssertionError("Missing PowerShell helper: " + name)
    return match.group(0)


def powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


class ReviewedReleaseRepairContractTests(unittest.TestCase):
    def test_reviewed_installer_checks_authority_instead_of_trusting_receipt(self):
        text = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("[string]$ReviewedReleaseCommit", text)
        self.assertIn("if($reviewedMode)", text)
        # A locally edited authorization JSON cannot substitute for these
        # independent GitHub/repository checks in reviewed-release mode.
        for check in (
            "branches/main/protection",
            "required_approving_review_count",
            "reviewDecision",
            "mergeCommit",
            "--required",
            "merge-base --is-ancestor",
        ):
            self.assertIn(check, text)
        reviewed = text.index("if($reviewedMode)")
        self.assertGreater(text.index("branches/main/protection"), reviewed)
        draft_gate = text.index("if(-not $reviewedMode)")
        self.assertLess(draft_gate, text.index("LEVEL6_PR_NO_LONGER_APPROVED_DRAFT"))
        self.assertLess(text.index("LEVEL6_PR_NO_LONGER_APPROVED_DRAFT"), reviewed)

    def test_updater_passes_exact_authorized_release_to_both_installer_modes(self):
        text = UPDATER.read_text(encoding="utf-8")
        invocations = [line for line in text.splitlines()
                       if "-File $installer" in line and
                       ("-Preflight" in line or "-Install" in line)]
        self.assertEqual(len(invocations), 2)
        for invocation in invocations:
            self.assertIn("-ReviewedReleaseCommit $release", invocation)

    def test_entire_source_bundle_is_verified_before_any_worker_drain(self):
        text = INSTALLER.read_text(encoding="utf-8")
        stage_hash = text.index("Downloaded source hash mismatch")
        self.assertLess(stage_hash, text.index("Disable-ScheduledTask"))
        self.assertLess(stage_hash, text.index("[IO.File]::Open($stopToken,[IO.FileMode]::CreateNew"))
        self.assertIn("scripts/pdufa_runtime_status.py", text)
        self.assertIn("tests/test_pdufa_runtime_status.py", text)

    def test_latest_poll_status_cannot_replace_successful_installation_receipt(self):
        text = UPDATER.read_text(encoding="utf-8")
        self.assertIn("installed-release-receipt.json", text)
        record = function_definition(text, "Record")
        self.assertIn("$statusPath", record)
        self.assertNotIn("$installedReceiptPath", record)
        installed = function_definition(text, "WriteInstalledReceipt")
        self.assertIn("$installedReceiptPath", installed)
        self.assertNotIn("$statusPath", installed)

    def test_stop_cleanup_requires_own_unique_marker(self):
        text = INSTALLER.read_text(encoding="utf-8")
        cleanup = function_definition(text, "RemoveOwnedUpgradeStop")
        self.assertIn("$content -ceq $Marker", cleanup)
        self.assertIn("Owner STOP changed", cleanup)
        self.assertIn("[guid]::NewGuid()", text)
        self.assertNotRegex(text, r"Remove-Item\s+-LiteralPath\s+\$stopToken")

    def test_fresh_heartbeat_requires_exact_loaded_release_and_source_files(self):
        for script in (INSTALLER, UPDATER):
            text = script.read_text(encoding="utf-8")
            self.assertIn("runtime_version.release_commit -ceq", text)
            self.assertIn("runtime_version.files_match_authorization -eq $true", text)
            self.assertIn("runtime_version.disk_changed_since_start", text)
            self.assertIn("runtime_version.startup_files", text)
            self.assertIn("$h.mode -notin @('ENGINEERING_STARTING','ENGINEERING_STARTUP_BLOCKED')", text)

    def test_installer_lock_covers_staging_activation_and_final_receipt(self):
        text = INSTALLER.read_text(encoding="utf-8")
        acquisition = text.index("$installationLock=AcquireInstallerLock")
        self.assertLess(acquisition, text.index("New-Item -ItemType Directory -Path $stage,$backup"))
        self.assertLess(acquisition, text.index("Disable-ScheduledTask"))
        disposal = text.rindex("$installationLock.Dispose()")
        self.assertGreater(disposal, text.index("Start-ScheduledTask"))
        self.assertGreater(disposal, text.rindex("installed-release-receipt.json"))
        self.assertRegex(text[text.rindex("} finally {"):],
                         r"(?s)^} finally \{\s+if\(\$installationLock\) \{ \$installationLock.Dispose\(\) \}\s+}\s*$")


@unittest.skipUnless(POWERSHELL, "PowerShell unavailable; native Windows CI runs helper behavior")
class NativeWindowsReleaseHelpersTests(unittest.TestCase):
    def run_powershell(self, body: str) -> None:
        command = "$ErrorActionPreference='Stop'\n" + body
        encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
        result = subprocess.run(
            [POWERSHELL, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)

    def test_duplicate_install_lock_rejects_until_first_holder_releases(self):
        helper = function_definition(INSTALLER.read_text(encoding="utf-8"),
                                     "AcquireInstallerLock")
        with tempfile.TemporaryDirectory(prefix="pdufa-install-lock-fixture-") as temp:
            self.run_powershell(helper + "\n" + f"""
$path={powershell_quote(str(Path(temp) / 'reviewed-install.lock'))}
$first=$null
$second=$null
$third=$null
try {{
  $first=AcquireInstallerLock $path
  $rejected=$false
  try {{ $second=AcquireInstallerLock $path }} catch {{ $rejected=$true }}
  if(-not $rejected) {{ throw 'Concurrent installer acquired the same exclusive lock.' }}
  $first.Dispose()
  $first=$null
  $third=AcquireInstallerLock $path
  if($null -eq $third -or -not $third.CanWrite) {{ throw 'Released lock cannot be reacquired.' }}
}} finally {{
  if($first) {{ $first.Dispose() }}
  if($second) {{ $second.Dispose() }}
  if($third) {{ $third.Dispose() }}
}}
""")

    def test_reviewed_release_acceptance_and_fail_closed_authority(self):
        helper = function_definition(INSTALLER.read_text(encoding="utf-8"), "RequireSuccess")
        # Select only the reviewed-mode authority block through the native AST.
        # All GitHub/Git commands below are functions backed by in-memory JSON;
        # no scheduler, worker, download, or full installer code is executed.
        fixture = r"""
$tokens=$null
$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile(__INSTALLER__,[ref]$tokens,[ref]$errors)
if($errors.Count -ne 0) { throw 'Installer must parse before authority tests.' }
$blocks=@($ast.FindAll({ param($node)
  $node -is [System.Management.Automation.Language.IfStatementAst] -and
  $node.Clauses[0].Item1.Extent.Text.Trim().Trim('()'.ToCharArray()).Trim() -eq '$reviewedMode'
},$true) | Where-Object { $_.Clauses[0].Item2.Extent.Text -match 'PROTECTED_MAIN_FETCH' })
if($blocks.Count -ne 1) { throw 'Cannot isolate reviewed release authority.' }
$body=$blocks[0].Clauses[0].Item2.Extent.Text
$authority=[ScriptBlock]::Create($body.Substring(1,$body.Length-2))

function git {
  $global:LASTEXITCODE=0
  if($args -contains 'fetch') { return }
  if($args -contains 'show') { return ($global:channelFixture | ConvertTo-Json -Depth 6) }
  if($args -contains 'hash-object') { return ('b'*40) }
  if($args -contains 'merge-base') { return }
  if($args -contains 'rev-parse') {
    if($args[-1] -like '*:scripts/windows_pdufa_level6_unblock.ps1') { return ('b'*40) }
    return ('c'*40)
  }
  throw ('Unexpected Git command in isolated authority: '+($args -join ' '))
}
function gh {
  $global:LASTEXITCODE=0
  if($args[0] -eq 'api') { return ($global:protectionFixture | ConvertTo-Json -Depth 6) }
  if($args[0] -eq 'pr' -and $args[1] -eq 'view') { return ($global:prFixture | ConvertTo-Json -Depth 6) }
  if($args[0] -eq 'pr' -and $args[1] -eq 'checks') {
    if($global:scenario -eq 'FAILED_CI') { $global:LASTEXITCODE=1 }
    return
  }
  throw ('Unexpected GitHub command in isolated authority: '+($args -join ' '))
}
foreach($case in @('APPROVED','DRAFT','UNAPPROVED','WRONG_BASE','WRONG_COMMIT','FAILED_CI','NO_PROTECTION','WRONG_CHANNEL','PR_STRING','PR_FRACTION','PR_BOOLEAN')) {
  $global:scenario=$case
  $global:channelFixture=@{schema_version=1;channel='pdufa-reviewed-windows';enabled=$true;
    release_commit=('a'*40);installer_path='scripts/windows_pdufa_level6_unblock.ps1';
    installer_git_blob_sha1=('b'*40);approved_pr=123}
  $global:prFixture=@{number=123;state='MERGED';isDraft=$false;mergedAt='2026-11-13T00:00:00Z';
    baseRefName='main';reviewDecision='APPROVED';mergeCommit=@{oid=('a'*40)}}
  $global:protectionFixture=@{required_pull_request_reviews=@{required_approving_review_count=1};
    required_status_checks=@{contexts=@('required-ci')}}
  switch($case) {
    'DRAFT' { $global:prFixture.isDraft=$true }
    'UNAPPROVED' { $global:prFixture.reviewDecision='REVIEW_REQUIRED' }
    'WRONG_BASE' { $global:prFixture.baseRefName='unreviewed-feature' }
    'WRONG_COMMIT' { $global:prFixture.mergeCommit.oid=('d'*40) }
    'NO_PROTECTION' { $global:protectionFixture.required_pull_request_reviews=$null }
    'WRONG_CHANNEL' { $global:channelFixture.release_commit=('d'*40) }
    'PR_STRING' { $global:channelFixture.approved_pr='123' }
    'PR_FRACTION' { $global:channelFixture.approved_pr=123.5 }
    'PR_BOOLEAN' { $global:channelFixture.approved_pr=$true }
  }
  $ReviewedReleaseCommit=('a'*40)
  $root='unused-fixture-root'
  $allowed=@{'scripts/pdufa_runtime_status.py'=('e'*40)}
  $authorization=$null
  $rejected=$false
  $rejection=$null
  try { . $authority } catch { $rejected=$true; $rejection=$_ }
  if($case -eq 'APPROVED') {
    if($rejected -or $authorization.release_commit -cne ('a'*40) -or
       $revision -cne ('a'*40)) {
      throw ('Approved merged fixture did not authorize the exact commit: '+$rejection)
    }
  } elseif(-not $rejected -or $null -ne $authorization) {
    throw ('Invalid release fixture was authorized: '+$case)
  }
}
"""
        self.run_powershell(helper + "\n" + fixture.replace(
            "__INSTALLER__", powershell_quote(str(INSTALLER))))

    def test_owned_stop_removed_but_user_replacement_preserved(self):
        helper = function_definition(INSTALLER.read_text(encoding="utf-8"),
                                     "RemoveOwnedUpgradeStop")
        with tempfile.TemporaryDirectory(prefix="pdufa-stop-fixture-") as temp:
            stop = powershell_quote(str(Path(temp) / "STOP"))
            self.run_powershell(helper + "\n" + f"""
$path={stop}
$marker='GRACEFUL_IDLE_UPGRADE:fixture-unique-owner'
[IO.File]::WriteAllText($path,$marker)
RemoveOwnedUpgradeStop $path $marker
if(Test-Path -LiteralPath $path) {{ throw 'Owned marker was not removed.' }}
RemoveOwnedUpgradeStop $path $marker
[IO.File]::WriteAllText($path,'OWNER REQUEST: leave worker stopped')
$blocked=$false
try {{ RemoveOwnedUpgradeStop $path $marker }} catch {{ $blocked=$true }}
if(-not $blocked) {{ throw 'Owner replacement did not block activation.' }}
if([IO.File]::ReadAllText($path) -cne 'OWNER REQUEST: leave worker stopped') {{
  throw 'Owner replacement was modified.'
}}
""")

    def test_new_owner_stop_after_atomic_capture_is_never_deleted(self):
        helper = function_definition(INSTALLER.read_text(encoding="utf-8"),
                                     "RemoveOwnedUpgradeStop")
        for original in ("UPGRADE:fixture-unique-owner", "OWNER EARLIER STOP"):
            with self.subTest(captured_contents=original), tempfile.TemporaryDirectory(
                    prefix="pdufa-stop-race-fixture-") as temp:
                self.run_powershell(helper + "\n" + f"""
$global:StopRacePath={powershell_quote(str(Path(temp) / 'STOP'))}
$marker='UPGRADE:fixture-unique-owner'
$initial={powershell_quote(original)}
[IO.File]::WriteAllText($global:StopRacePath,$initial)
# Intercept only inspection, after the real atomic rename. A new owner STOP
# appears at the original path before cleanup decides whether to delete.
function Get-Content {{
  [CmdletBinding()]
  param([string]$LiteralPath,[switch]$Raw)
  if($LiteralPath -ceq $global:StopRacePath) {{ throw 'STOP was inspected before capture.' }}
  [IO.File]::WriteAllText($global:StopRacePath,'OWNER NEW STOP')
  return [IO.File]::ReadAllText($LiteralPath)
}}
$blocked=$false
try {{ RemoveOwnedUpgradeStop $global:StopRacePath $marker }} catch {{ $blocked=$true }}
if(-not $blocked) {{ throw 'Owner STOP created after capture must block activation.' }}
if([IO.File]::ReadAllText($global:StopRacePath) -cne 'OWNER NEW STOP') {{
  throw 'A new owner STOP was deleted or overwritten.'
}}
$captured=@(Get-ChildItem -LiteralPath {powershell_quote(temp)} -Filter '*.captured')
if($initial -ceq $marker) {{
  if($captured.Count -ne 0) {{ throw 'Owned captured marker was not cleaned up.' }}
}} elseif($captured.Count -ne 1 -or [IO.File]::ReadAllText($captured[0].FullName) -cne $initial) {{
  throw 'An earlier owner STOP was not preserved alongside its replacement.'
}}
""")

    def test_failed_poll_does_not_erase_durable_success(self):
        text = UPDATER.read_text(encoding="utf-8")
        helpers = function_definition(text, "Record") + "\n" + function_definition(
            text, "WriteInstalledReceipt")
        with tempfile.TemporaryDirectory(prefix="pdufa-receipt-fixture-") as temp:
            self.run_powershell(helpers + "\n" + f"""
$data={powershell_quote(temp)}
$statusPath=Join-Path $data 'reviewed-release-updater-status.json'
$installedReceiptPath=Join-Path $data 'installed-release-receipt.json'
$receipt=@{{schema_version=1;release_commit=('a'*40);state='INSTALLED_AND_RESTART_VERIFIED'}}
WriteInstalledReceipt $receipt
$before=[IO.File]::ReadAllText($installedReceiptPath)
Record 'UPDATE_BLOCKED_OR_FAILED' 'Synthetic offline failed poll' ('b'*40)
Record 'RELEASE_CHANNEL_DISABLED' 'Synthetic offline disabled channel'
if([IO.File]::ReadAllText($installedReceiptPath) -cne $before) {{
  throw 'A later poll erased the successful installation receipt.'
}}
if((Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json).state -ne 'RELEASE_CHANNEL_DISABLED') {{
  throw 'Latest poll status was not updated independently.'
}}
""")


if __name__ == "__main__":
    unittest.main()
