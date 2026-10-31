"""Exercise the real nightly dispatch shell without network or credentials."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NightlyDispatchShellTests(unittest.TestCase):
    def test_scan_mode_and_pacific_date_reach_one_dispatch(self):
        workflow = (ROOT / '.github/workflows/pdufa-nightly-pacific-start.yml').read_text()
        step = workflow.split('      - name: Dispatch the entire awaited sequence\n', 1)[1]
        step = step.split('\n      - name:', 1)[0]
        shell = textwrap.dedent(step.split('        run: |\n', 1)[1])

        def render(match):
            expression = match.group(1).strip()
            if expression == 'steps.pacific.outputs.night_date_pacific':
                return '2026-10-30'
            if expression.endswith('steps.pacific.outputs.scan_mode'):
                return 'DELTA'
            raise AssertionError('Unrecognized Actions expression: ' + expression)

        shell = re.sub(r'\$\{\{(.*?)\}\}', render, shell)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture = root / 'arguments.jsonl'
            executable = root / 'gh'
            executable.write_text('#!/usr/bin/env python3\n'
                                  'import json, os, sys\n'
                                  'with open(os.environ["DISPATCH_CAPTURE"], "a") as out:\n'
                                  '    out.write(json.dumps(sys.argv[1:]) + "\\n")\n')
            executable.chmod(0o700)
            environment = dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'],
                               DISPATCH_CAPTURE=str(capture), GITHUB_REPOSITORY='pdufa/pdufa-command-center')
            result = subprocess.run(['bash', '-c', shell], env=environment,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            invocations = [json.loads(line) for line in capture.read_text().splitlines()]
            self.assertEqual(len(invocations), 1)
            self.assertEqual(invocations[0], [
                'api', '--method', 'POST',
                'repos/pdufa/pdufa-command-center/actions/workflows/pdufa-overnight-sequential.yml/dispatches',
                '-f', 'ref=main', '-f', 'inputs[scan_mode]=DELTA',
                '-f', 'inputs[night_date_pacific]=2026-10-30',
            ])


if __name__ == '__main__':
    unittest.main()
