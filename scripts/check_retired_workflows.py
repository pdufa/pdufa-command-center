#!/usr/bin/env python3
"""Default-branch policy entry point; use the full transitive retirement audit.

Policy-enforcement commands and tests are not retired scoring jobs. The shared
engine checks actual runtime dependencies, writer guards and immutable archives.
"""
from pathlib import Path
import subprocess,sys
if __name__=='__main__':
    raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).with_name('audit_raas_retirement.py')),'--check']))
