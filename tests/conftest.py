"""Explicit retirement inventory, not blanket error suppression.

Never import the retired survey collector to make its archived tests collect.
Each retained test is reported as a named skip; supported tests still execute.
"""
import ast
import json
import hashlib
from pathlib import Path
import pytest

MANIFEST = Path(__file__).with_name('retired_test_inventory.json')

class RetiredModule(pytest.Module):
    def collect(self):
        source = ast.parse(self.path.read_text(encoding='utf-8'))
        reason = json.loads(MANIFEST.read_text())[self.path.name]['reason']
        for node in source.body:
            candidates = node.body if isinstance(node, ast.ClassDef) else [node]
            for function in candidates:
                if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)) and function.name.startswith('test_'):
                    name = (node.name + '::' if isinstance(node, ast.ClassDef) else '') + function.name
                    item = pytest.Function.from_parent(self, name=name, callobj=lambda: None)
                    item.add_marker(pytest.mark.skip(reason=reason))
                    yield item

def pytest_pycollect_makemodule(module_path, parent):
    retired = json.loads(MANIFEST.read_text())
    if module_path.name in retired and retired[module_path.name].get("collectionMode") != "SKIP_NAMED_TESTS":
        return RetiredModule.from_parent(parent, path=module_path)

def pytest_addoption(parser):
    parser.addoption('--disposition-report', help='Write per-test executed/skipped outcomes for the collection audit')

_RESULTS = {}

def pytest_runtest_logreport(report):
    if report.when == 'call' or report.failed or (report.when == 'setup' and report.skipped):
        _RESULTS[report.nodeid] = report.outcome

def pytest_sessionfinish(session, exitstatus):
    path = session.config.getoption('--disposition-report')
    if path:
        Path(path).write_text(json.dumps({'exitStatus': int(exitstatus), 'tests': _RESULTS}, indent=2)+'\n')


def pytest_sessionstart(session):
    for name, entry in json.loads(MANIFEST.read_text()).items():
        path = MANIFEST.parent / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sourceSha256"]:
            raise pytest.UsageError("Retired test source changed; review the explicit retirement inventory: " + name)


def pytest_collection_modifyitems(items):
    retired = json.loads(MANIFEST.read_text())
    for item in items:
        entry = retired.get(item.path.name, {})
        if entry.get("collectionMode") == "SKIP_NAMED_TESTS" and item.originalname in entry["nodes"]:
            item.add_marker(pytest.mark.skip(reason=entry["reason"]))

def pytest_terminal_summary(terminalreporter):
    entries=json.loads(MANIFEST.read_text())
    terminalreporter.write_sep('-', 'Explicit retirement inventory (not passing active coverage)')
    for name,entry in sorted(entries.items()):
        scope='named tests: '+', '.join(entry['nodes']) if entry.get('collectionMode')=='SKIP_NAMED_TESTS' else 'retained module; no retired import executed'
        terminalreporter.write_line(name+': '+scope)
