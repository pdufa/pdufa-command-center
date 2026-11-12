"""Replicate the exact Windows-installed file set, not the complete GitHub tree.

This catches deployment-only regression failures caused by optional files
present in CI but absent from the Windows install allowlist. No Windows task is
changed; the entire exercise runs in an isolated temporary directory.
"""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
INSTALLER=ROOT/"scripts/windows_pdufa_level6_unblock.ps1"

class WindowsPartialInstallStagingTests(unittest.TestCase):
    def test_installed_snapshot_offline_regressions_and_preflight(self):
        body=INSTALLER.read_text(encoding="utf-8")
        files=re.search(r"\$files=@\((.*?)\n\)",body,re.S)
        pins=re.search(r"\$allowed=@\{(.*?)\n\}",body,re.S)
        self.assertIsNotNone(files)
        self.assertIsNotNone(pins)
        installed=re.findall(r"'([^']+)'",files.group(1))
        allow=dict(re.findall(r"'([^']+)'='([0-9a-f]{40})'",pins.group(1)))
        self.assertEqual(set(installed),set(allow))
        with tempfile.TemporaryDirectory(prefix="pdufa-exact-install-stage-") as temp:
            stage=Path(temp)
            for relpath in installed:
                src=ROOT/relpath
                self.assertTrue(src.is_file(),relpath)
                raw_sha=subprocess.run(["git","hash-object",str(src)],capture_output=True,
                                       text=True,check=True).stdout.strip()
                self.assertEqual(raw_sha,allow[relpath],relpath)
                dest=stage/relpath
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(src,dest)
            # Present on the existing Windows checkout, not copied by installer.
            for relpath in ("AGENTS.md","scripts/audit_raas_retirement.py"):
                src=ROOT/relpath
                self.assertTrue(src.is_file(),relpath)
                dest=stage/relpath
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(src,dest)
            # The one-time bootstrap downloads itself first, outside $files.
            local_installer=stage/"scripts/windows_pdufa_level6_unblock.ps1"
            shutil.copy2(INSTALLER,local_installer)
            self.assertTrue((stage/"scripts/level7_model_validation_readiness.py").exists())
            self.assertTrue((stage/"scripts/level7_source_readiness_inventory.py").exists())
            result=subprocess.run(
                [sys.executable,"-B","-m","unittest","discover","-s",str(stage/"tests"),
                 "-p","test_pdufa_predictive_preflight.py","-v"],
                cwd=stage,text=True,capture_output=True,timeout=90,check=False,
            )
            self.assertEqual(result.returncode,0,
                             "Windows snapshot predictive tests failed:\n"+result.stdout+
                             "\n"+result.stderr)
            report_path=stage/"predictive-actual-snapshot.json"
            check=subprocess.run(
                [sys.executable,"-B",str(stage/"scripts/pdufa_predictive_preflight.py"),
                 "--root",str(stage),"--out",str(report_path)],
                cwd=stage,text=True,capture_output=True,timeout=90,check=False,
            )
            self.assertEqual(check.returncode,0,
                             "Snapshot command failed:\n"+check.stdout+check.stderr)
            report=json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["known_shared_installation_blockers"],0)
            self.assertEqual(report["future_levels_with_missing_approved_domain_implementation"],
                             list(range(8,21)))
            self.assertFalse(report["windows_restart_confirmed"])

if __name__=="__main__":
    unittest.main()
