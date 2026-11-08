"""Compatibility entry point for the mandatory permanent-retirement policy."""
from pathlib import Path
import subprocess,sys
if __name__=='__main__':
    raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).with_name('audit_raas_retirement.py')),'--check',*sys.argv[1:]]))
