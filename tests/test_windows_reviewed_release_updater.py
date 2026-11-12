"""Offline security contracts for reviewed Windows updater. No actual scheduling."""
import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/"scripts/windows_pdufa_reviewed_release_updater.ps1"
BODY=FILE.read_text(encoding="utf-8")
EXAMPLE=json.loads((ROOT/"automation/windows-release-channel.example.json")
                   .read_text(encoding="utf-8"))

class ReviewedUpdaterSecurityTests(unittest.TestCase):
    def test_distinct_task_not_watchdog_or_worker(self):
        self.assertIn("$taskName='PDUFA-Reviewed-Release-Updater'",BODY)
        self.assertIn("$workerName='PDUFA-Continuous-Development'",BODY)
        self.assertIn("-RepetitionInterval (New-TimeSpan -Minutes 15)",BODY)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn",BODY)
        self.assertIn("Register-ScheduledTask -TaskName $taskName",BODY)
        self.assertNotIn("Stop-ScheduledTask",BODY)
        self.assertNotIn("Stop-Process",BODY)
        self.assertNotIn("Remove-Item -LiteralPath $stop",BODY)

    def test_disabled_channel_sample_cannot_authorize_install(self):
        self.assertEqual(EXAMPLE["schema_version"],1)
        self.assertEqual(EXAMPLE["channel"],"pdufa-reviewed-windows")
        self.assertIs(EXAMPLE["enabled"],False)
        self.assertIsNone(EXAMPLE["release_commit"])
        self.assertIsNone(EXAMPLE["approved_pr"])
        self.assertEqual(EXAMPLE["installer_path"],
                         "scripts/windows_pdufa_level6_unblock.ps1")
        self.assertFalse((ROOT/"automation/windows-release-channel.json").exists())

    def test_only_protected_main_can_authorize(self):
        for required in (
            "refs/remotes/origin/main",
            "+refs/heads/main:",
            "automation/windows-release-channel.json",
            "repos/'+$repo+'/branches/main/protection",
            "required_pull_request_reviews.required_approving_review_count",
            "required_status_checks.contexts",
            "$pr.reviewDecision -ne 'APPROVED'",
            "$pr.state -ne 'MERGED'",
            "$pr.baseRefName -ne 'main'",
            "$pr.mergeCommit.oid -ne $release",
            "gh pr checks $prNumber --repo $repo --required",
            "git -C $root merge-base --is-ancestor $release $mainRef",
        ):
            self.assertIn(required,BODY)

    def test_unmerged_draft_never_installable(self):
        self.assertIn("$pr.isDraft -ne $false",BODY)
        self.assertIn("RELEASE_PR_NOT_INDEPENDENTLY_APPROVED_AND_MERGED_INTO_MAIN",BODY)
        self.assertIn("REQUIRED_RELEASE_CI_NOT_GREEN",BODY)
        self.assertIn("PROTECTED_MAIN_REQUIRED",BODY)

    def test_exact_installer_path_commit_sha_and_download_blob(self):
        for required in (
            "$channel.installer_path -cne $installerRel",
            "$release -notmatch '^[0-9a-f]{40}$'",
            "$blob -notmatch '^[0-9a-f]{40}$'",
            "$sourceBlob -cne $blob",
            "$fetchedBlob -cne $blob",
            "git -C $root hash-object $incoming",
            "git -C $root rev-parse ($release+':'+$installerRel)",
        ):
            self.assertIn(required,BODY)
        self.assertLess(BODY.index("REQUIRED_RELEASE_CI_NOT_GREEN"),
                        BODY.index("Copy-Item -LiteralPath $incoming -Destination $installer"))
        self.assertLess(BODY.index("$fetchedBlob -cne $blob"),
                        BODY.index("Copy-Item -LiteralPath $incoming -Destination $installer"))

    def test_existing_installer_controls_preflight_before_restart(self):
        self.assertIn("-File $installer -Preflight",BODY)
        self.assertIn("-File $installer -Install",BODY)
        self.assertLess(BODY.index("-File $installer -Preflight"),
                        BODY.index("-File $installer -Install"))
        self.assertIn("RequireSuccess 'RELEASE_PREFLIGHT'",BODY)
        self.assertIn("RequireSuccess 'RELEASE_INSTALL_OR_RESTART'",BODY)

    def test_owner_stop_lock_and_no_unauthorized_task_overwrite(self):
        for required in (
            "if(Test-Path -LiteralPath $stop)",
            "AssertOwner $worker",
            "if($old) { AssertUpdater $old }",
            "[IO.FileShare]::None",
            "AssertUpdater $t",
            "$identity",  # removed check below; check current user explicitly
        ):
            if required == "$identity":
                continue
            self.assertIn(required,BODY)
        self.assertIn("[Security.Principal.WindowsIdentity]::GetCurrent()",BODY)

    def test_rollback_protection_and_no_unsafe_worker_termination(self):
        for required in (
            "Copy-Item -LiteralPath $installer -Destination $backup",
            "Copy-Item -LiteralPath $backup -Destination $installer",
            "$now.State -eq 'Ready'",
            "Worker may be active; do not overwrite active installation.",
            "Record 'UPDATE_BLOCKED_OR_FAILED'",
            "Record 'INSTALLED_AND_RESTART_VERIFIED'",
        ):
            self.assertIn(required,BODY)

    def test_no_release_activated_and_no_autonomous_scientific_signoff(self):
        self.assertIn("independent_scientific_acceptance=$false",BODY)
        self.assertIn("automatic_merges=$false",BODY)
        self.assertIn("NO_APPROVED_RELEASE_CHANNEL",BODY)
        self.assertIn("RELEASE_CHANNEL_DISABLED",BODY)
        self.assertIn("APPROVED_RELEASE_ALREADY_INSTALLED",BODY)

    def test_user_setup_only_schedules_and_does_not_run_install(self):
        install=BODY.split("if($Install) {",1)[1].split("\n# -Check.",1)[0]
        self.assertIn("Register-ScheduledTask",install)
        self.assertNotIn("-File $installer -Install",install)
        self.assertNotIn("Start-ScheduledTask",install)
        self.assertIn("UPDATER_INSTALLED",install)

if __name__=="__main__":
    unittest.main()
