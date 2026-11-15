"""Retirement isolation must remain explicit and must not hide supported failures."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).parent

def setup_project(folder):
    text="raise AssertionError('retired module must not execute')\ndef test_archived_a(): pass\ndef test_archived_b(): pass\n"
    (folder/'test_archived.py').write_text(text)
    entry={'reason':'SYNTHETIC_RETIRED_TEST_ONLY','sourceSha256':hashlib.sha256(text.encode()).hexdigest()}
    (folder/'retired_test_inventory.json').write_text(json.dumps({'test_archived.py':entry}))
    (folder/'conftest.py').write_text((ROOT/'conftest.py').read_text())
    return folder/'test_archived.py'

def test_named_retired_skips_do_not_suppress_a_supported_failure(tmp_path):
    setup_project(tmp_path)
    (tmp_path/'test_supported.py').write_text('def test_supported_failure():\n    assert False, "supported failure must remain visible"\n')
    result=subprocess.run([sys.executable,'-m','pytest','-q',str(tmp_path)],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==1
    assert '1 failed, 2 skipped' in result.stdout
    assert 'supported failure must remain visible' in result.stdout
    assert 'retired module must not execute' not in result.stdout

def test_changed_retired_source_requires_auditable_inventory_review(tmp_path):
    path=setup_project(tmp_path);path.write_text(path.read_text()+'\ndef test_new_guard(): assert False\n')
    result=subprocess.run([sys.executable,'-m','pytest','-q',str(tmp_path)],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==4
    assert 'Retired test source changed' in result.stderr
