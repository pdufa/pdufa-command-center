#!/usr/bin/env python3
"""Fail closed when permanently retired RAAS code is reachable from live work.

Historical data and unreachable historical implementation are inventoried, not
deleted or silently treated as active dependencies. This audit uses executable
entrypoints and their import graph rather than a repository-wide word ban.
"""
from __future__ import annotations

import argparse
import ast
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SOURCE_EXTENSIONS = ('.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.py')
POLICY_TOOLS = {'audit_raas_retirement.py', 'test_raas_retirement_guard.py'}
RETIRED_NAME = re.compile(r'(?:^|[/_.-])raas(?:$|[/_.-])', re.I)
JS_IMPORT = re.compile(
    r'''(?:\b(?:import|export)\s+(?:[^;\n]*?\s+from\s+)?|\b(?:require|import)\s*\()\s*["']([^"']+)["']''')
JS_DYNAMIC = re.compile(r'\b(?:require|import)\s*\(([^)]+)\)')
RETIRED_CALL = re.compile(r'\b(?:raas[A-Z_][A-Za-z0-9_]*|RAAS_[A-Za-z0-9_]+|[A-Za-z_]*(?:Raas|RAAS)(?:Score|Rating|Grade|Prediction)[A-Za-z0-9_]*)\s*\(')
RETIRED_OUTPUT = re.compile(r'''["']?(?:raasScore|raasRating|raasPredictionConfidence|approvedRaas|raas_score|raas_rating|raas_prediction)["']?\s*[:=]''', re.I)
RETIRED_REQUEST = re.compile(r'''\b(?:fetch|axios\.(?:get|post|put|delete)|requests\.(?:get|post|put|delete))\s*\(\s*["']([^"']*(?:/api/raas[-/]|/api/raas\b)[^"']*)["']''', re.I)
RETIRED_CONTROL = re.compile(r'''["'](?:Open|Run|Calculate|Install|Recalculate|Launch|Start)\s+RAAS\b[^"'\n]*["']''', re.I)


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def code_without_comments(text: str, suffix: str) -> str:
    if suffix == '.py':
        # AST handles Python imports; comments never establish execution.
        return re.sub(r'(?m)^\s*#.*$', '', text)
    return re.sub(r'/\*[\s\S]*?\*/|(?m:^[ \t]*//.*$)', '', text)


def archive_entry(path: Path, root: Path) -> bool:
    name = '/' + relative(path, root).lower() + '/'
    return '/archive/' in name or '/archives/' in name


def _candidate_files(base: Path) -> Iterable[Path]:
    yield base
    for extension in SOURCE_EXTENSIONS + ('.json', '.csv'):
        yield Path(str(base) + extension)
    for extension in SOURCE_EXTENSIONS:
        yield base / ('index' + extension)
    yield base / '__init__.py'


def resolve_js(spec: str, importer: Path, root: Path) -> Path | None:
    if spec.startswith('.'):
        base = importer.parent / spec
    elif spec.startswith('@/'):
        base = root / 'new-platform/frontend' / spec[2:]
    else:
        return None
    for candidate in _candidate_files(base):
        resolved = candidate.resolve()
        if resolved.is_file() and resolved.is_relative_to(root):
            return resolved
    return None


def resolve_python(module: str, level: int, importer: Path, root: Path) -> list[Path]:
    bases = []
    if level:
        base = importer.parent
        for _ in range(level - 1):
            base = base.parent
        bases.append(base / module.replace('.', '/'))
    else:
        bases.extend([root / module.replace('.', '/'),
                      root / 'new-platform/backend' / module.replace('.', '/'),
                      importer.parent / module.replace('.', '/')])
    result = []
    for base in bases:
        for candidate in (base.with_suffix('.py'), base / '__init__.py'):
            resolved = candidate.resolve()
            if resolved.is_file() and resolved.is_relative_to(root):
                result.append(resolved)
                break
    return list(dict.fromkeys(result))


def imports(path: Path, root: Path) -> tuple[list[tuple[str, Path | None]], list[str]]:
    text = path.read_text(encoding='utf-8')
    clean = code_without_comments(text, path.suffix)
    found: list[tuple[str, Path | None]] = []
    dynamic: list[str] = []
    if path.suffix == '.py':
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            return [], ['Unparseable active Python source: ' + str(exc)]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    resolved = resolve_python(alias.name, 0, path, root)
                    found.extend((alias.name, item) for item in resolved or [None])
            elif isinstance(node, ast.ImportFrom):
                spec = '.' * node.level + (node.module or '')
                resolved = resolve_python(node.module or '', node.level, path, root)
                found.extend((spec, item) for item in resolved or [None])
                for alias in node.names:
                    submodule = '.'.join(filter(None, [node.module, alias.name]))
                    for item in resolve_python(submodule, node.level, path, root):
                        found.append((spec + '.' + alias.name, item))
            elif isinstance(node, ast.Call):
                name = (node.func.id if isinstance(node.func, ast.Name) else
                        node.func.attr if isinstance(node.func, ast.Attribute) else '')
                if name in ('__import__', 'import_module'):
                    expression = ast.get_source_segment(text, node) or ''
                    if re.search(r'raas', expression, re.I):
                        dynamic.append(expression)
        return found, dynamic
    for match in JS_IMPORT.finditer(clean):
        spec = match.group(1)
        found.append((spec, resolve_js(spec, path, root)))
    for match in JS_DYNAMIC.finditer(clean):
        expression = match.group(1)
        if re.search(r'raas', expression, re.I):
            dynamic.append(expression)
    return found, dynamic


def frontend_entrypoints(root: Path) -> list[Path]:
    app = root / 'new-platform/frontend/app'
    if not app.exists():
        return []
    entries = sorted(path for path in app.rglob('*') if path.is_file() and
                     re.fullmatch(r'(?:page|route|layout|template|loading|error|global-error|not-found)\.(?:tsx?|jsx?)', path.name))
    frontend = root / 'new-platform/frontend'
    entries += [path for path in frontend.iterdir() if path.is_file() and
                re.fullmatch(r'(?:next\.config|middleware|proxy|instrumentation|instrumentation-client)\.(?:tsx?|jsx?|mjs|cjs)', path.name)]
    return entries


def workflow_scripts(text: str, root: Path) -> list[Path]:
    # Only executable commands, not path filters or archived file references.
    command_parts = []
    in_run = False
    indentation = 0
    for line in text.splitlines():
        run = re.search(r'\brun:\s*(.*)', line)
        if run:
            indentation = len(line) - len(line.lstrip())
            value = run.group(1)
            in_run = value.strip() in ('|', '>', '|-', '>-')
            command_parts.append(value)
        elif in_run:
            if line.strip() and len(line) - len(line.lstrip()) <= indentation:
                in_run = False
            else:
                command_parts.append(line)
    commands = '\n'.join(command_parts)
    paths = []
    for match in re.finditer(r'''(?:\bpython(?:3(?:\.\d+)?)?\s+(?:-u\s+)?|\bnode\s+|\bbash\s+|\bsh\s+)([A-Za-z0-9_./-]+\.(?:py|cjs|mjs|js|sh))''', commands):
        spec = match.group(1)
        for prefix in ('', 'new-platform/frontend/', 'new-platform/backend/'):
            candidate = (root / prefix / spec).resolve()
            if candidate.is_file():
                paths.append(candidate)
                break
    return paths


def audit(root: Path = ROOT, check_policy: bool = True) -> dict:
    root = root.resolve()
    violations: list[dict] = []
    def add(kind: str, path: Path, detail: str, chain=None):
        value = {'kind': kind, 'path': relative(path, root), 'detail': detail}
        if chain:
            value['entrypointChain'] = chain
        if value not in violations:
            violations.append(value)

    if check_policy:
        policy = root / 'AGENTS.md'
        text = policy.read_text(encoding='utf-8') if policy.exists() else ''
        if not (re.search(r'RAAS', text, re.I) and re.search(r'permanent(?:ly)?\s+retir', text, re.I) and
                re.search(r'read.only', text, re.I)):
            add('PERMANENT_POLICY_MISSING', policy, 'Root instructions must permanently retire RAAS and preserve read-only history.')
        copilot = root / '.github/copilot-instructions.md'
        copilot_text = copilot.read_text(encoding='utf-8') if copilot.exists() else ''
        if not (re.search(r'AGENTS\.md', copilot_text, re.I) and
                re.search(r'RAAS', copilot_text, re.I) and
                re.search(r'permanent(?:ly)?\s+retir', copilot_text, re.I) and
                re.search(r'read.only', copilot_text, re.I)):
            add('COPILOT_POLICY_MISSING', copilot, 'Persistent Copilot instructions must bind AGENTS.md, permanent retirement and read-only history.')

    pinned = root / 'archives/raas/read-only-record-manifest.json'
    pinned_count = 0
    if check_policy and not pinned.is_file():
        add('HISTORICAL_MANIFEST_MISSING', pinned, 'The read-only historical record manifest is required; removing it cannot disable preservation checks.')
    if pinned.exists():
        try:
            manifest = json.loads(pinned.read_text(encoding='utf-8'))
            if manifest.get('schemaVersion') != 1 or not isinstance(manifest.get('files'), list):
                raise ValueError('Invalid read-only record manifest')
            seen_pinned = set()
            for record in manifest['files']:
                path = (root / record['path']).resolve()
                if not path.is_relative_to(root) or path in seen_pinned or not re.fullmatch(r'[0-9a-f]{64}', record['sha256']):
                    raise ValueError('Invalid or duplicated pinned historical identity')
                seen_pinned.add(path)
                pinned_count += 1
                if not path.is_file():
                    add('HISTORICAL_RECORD_DELETED', path, 'Pinned read-only historical record is absent.')
                elif hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
                    add('HISTORICAL_RECORD_MODIFIED', path, 'Pinned read-only historical record differs from its preserved baseline.')
        except (OSError, ValueError, KeyError, TypeError):
            add('HISTORICAL_MANIFEST_INVALID', pinned, 'Read-only archive manifest failed validation.')

    roots = frontend_entrypoints(root)
    for main in ('new-platform/backend/app/main.py', 'app.py'):
        path = root / main
        if path.exists() and not (main == 'app.py' and 'retired' in path.read_text(encoding='utf-8').lower()):
            roots.append(path)
    workflows = root / '.github/workflows'
    for workflow in sorted(workflows.glob('*')) if workflows.exists() else []:
        if workflow.suffix not in ('.yml', '.yaml'):
            continue
        text = workflow.read_text(encoding='utf-8')
        if RETIRED_NAME.search(workflow.name) and 'retirement' not in workflow.name:
            add('RETIRED_WORKFLOW_REGISTERED', workflow, 'Retired workflows must remain outside the active GitHub workflow directory.')
        for script in workflow_scripts(text, root):
            if script.name in POLICY_TOOLS:
                continue
            if RETIRED_NAME.search(script.name):
                add('RETIRED_SCHEDULED_COMMAND', workflow, relative(script, root))
            if script.suffix in SOURCE_EXTENSIONS:
                roots.append(script)

    visited: set[Path] = set()
    queue = deque((path, [relative(path, root)]) for path in dict.fromkeys(roots))
    while queue:
        path, chain = queue.popleft()
        if path in visited or path.suffix not in SOURCE_EXTENSIONS:
            continue
        visited.add(path)
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            add('UNREADABLE_ACTIVE_SOURCE', path, 'Active source could not be inspected.', chain)
            continue
        clean = code_without_comments(text, path.suffix)
        if archive_entry(path, root):
            if re.search(r'\bexport\s+(?:async\s+)?(?:function|const|let)\s+(?:POST|PUT|PATCH|DELETE)\b|\b(?:writeFile(?:Sync)?|appendFile(?:Sync)?|unlink(?:Sync)?|rmSync)\s*\(', clean):
                add('HISTORICAL_ARCHIVE_NOT_READ_ONLY', path, 'Archive routes must be read-only and must never mutate saved records.', chain)
        for match in RETIRED_CALL.finditer(clean):
            add('RETIRED_EXECUTABLE_CALL', path, match.group(0), chain)
        for match in RETIRED_OUTPUT.finditer(clean):
            add('RETIRED_ACTIVE_ANALYSIS_OUTPUT', path, match.group(0), chain)
        for match in RETIRED_REQUEST.finditer(clean):
            add('RETIRED_API_REQUEST', path, match.group(1), chain)
        for match in RETIRED_CONTROL.finditer(clean):
            add('RETIRED_ACTIVE_CONTROL', path, match.group(0), chain)
        dependencies, dynamic = imports(path, root)
        for expression in dynamic:
            add('RETIRED_DYNAMIC_IMPORT', path, expression, chain)
        for spec, dependency in dependencies:
            if RETIRED_NAME.search(spec):
                data_file = dependency and dependency.suffix in ('.json', '.csv')
                if not (data_file and archive_entry(path, root)):
                    add('RETIRED_IMPORT_REACHABLE', path, spec, chain + ([relative(dependency, root)] if dependency else []))
            if dependency and dependency.suffix in SOURCE_EXTENSIONS:
                queue.append((dependency, chain + [relative(dependency, root)]))

    config_paths = [root / name for name in ('render.yaml', 'render.yml', 'vercel.json', 'Procfile', 'Dockerfile', 'docker-compose.yml')]
    # Do not traverse installed dependencies, build output or historical archives.
    for directory, children, names in os.walk(root):
        children[:] = [name for name in children if name not in
                       ('node_modules', '.next', '.git', 'archives', 'cache', '__pycache__')]
        if 'package.json' in names:
            config_paths.append(Path(directory) / 'package.json')
    for path in config_paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8')
        if path.name == 'package.json':
            try:
                config = json.loads(text)
                text = json.dumps({k: config.get(k, {}) for k in ('scripts', 'dependencies', 'devDependencies')})
            except ValueError:
                add('INVALID_DEPLOYMENT_CONFIGURATION', path, 'Configuration JSON cannot be parsed.')
        if re.search(r'\braas(?:[-_][\w-]+)?\b', text, re.I):
            add('RETIRED_INSTALL_OR_DEPLOYMENT_REQUIREMENT', path, 'Active install/build/start configuration still references RAAS.')

    installation = list((root / 'new-platform/frontend/app/installation-audit').rglob('*'))
    installation += list((root / 'new-platform/frontend/lib').glob('installation*'))
    for path in installation:
        if not path.is_file() or path.suffix not in SOURCE_EXTENSIONS:
            continue
        text = code_without_comments(path.read_text(encoding='utf-8'), path.suffix)
        task = re.search(r'''\b(?:title|name|label|requirement|component)\s*:\s*["'][^"'\n]*\bRAAS\b[^"'\n]*["']''', text, re.I)
        if task:
            add('RETIRED_INSTALLATION_TASK', path, task.group(0))
        if re.search(r'''["'](?:Implement|Install|Activate|Configure|Validate|Complete|Run|Build)\s+RAAS\b''', text, re.I):
            add('RETIRED_INSTALLATION_TASK', path, 'RAAS remains an actionable installation task.')

    historical_data = []
    unreachable_implementation = []
    for base in ('data', 'reports', 'archives', 'new-platform/frontend/data', 'new-platform/frontend/public', 'new-platform/frontend/lib', 'scripts'):
        folder = root / base
        if not folder.exists():
            continue
        for path in folder.rglob('*'):
            if not path.is_file() or not RETIRED_NAME.search(path.name) or any(part in ('node_modules', '.next', 'cache', '__pycache__') for part in path.parts):
                continue
            if path.suffix in ('.json', '.csv', '.jsonl', '.md') or '/archives/' in '/' + relative(path, root):
                historical_data.append(relative(path, root))
            elif path.suffix in SOURCE_EXTENSIONS and path not in visited and path.name not in POLICY_TOOLS:
                unreachable_implementation.append(relative(path, root))
    return {'schemaVersion': 1, 'policy': 'RAAS_PERMANENTLY_RETIRED',
            'activeDependenciesRemaining': len(violations), 'passed': not violations,
            'activeEntrypointsInspected': len(set(roots)), 'reachableSourceFilesInspected': len(visited),
            'violations': violations, 'historicalReadOnlyRecordFilesRetained': sorted(set(historical_data)),
            'historicalReadOnlyRecordFileCount': len(set(historical_data)),
            'historicalPinnedRecordFileCount': pinned_count,
            'unreachableHistoricalImplementationFiles': sorted(set(unreachable_implementation)),
            'unreachableHistoricalImplementationFileCount': len(set(unreachable_implementation)),
            'scopeNote': 'Static active-execution import/scheduler/config audit; historical records and unreachable historical implementations are retained, never executed by this audit.'}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    report = audit(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 1 if args.check and not report['passed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
