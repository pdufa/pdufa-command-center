"""Reproduce CPython's actual missing-module KeyError during hot reload."""
import ast
import importlib.abc
import importlib.util
from pathlib import Path
import sys
import unittest


MODULE = "post_phase3_workspace"
APP = Path(__file__).resolve().parents[1] / "app.py"


class WorkspaceLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, *, evictions=0, import_error=None, render_error=None):
        self.loads = 0
        self.evictions = evictions
        self.import_error = import_error
        self.render_error = render_error

    def find_spec(self, fullname, path=None, target=None):
        if fullname == MODULE:
            return importlib.util.spec_from_loader(fullname, self)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        self.loads += 1
        if self.import_error is not None:
            raise self.import_error
        def render(*args, **kwargs):
            if self.render_error is not None:
                raise self.render_error
            return args, kwargs
        module.render_post_phase3_workspace = render
        if self.loads <= self.evictions:
            # This is the same global eviction performed by the file watcher.
            # The error is raised by importlib itself after exec_module returns.
            del sys.modules[MODULE]


class StartupImportRaceTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(APP.read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "render_post_phase3_workspace")
        namespace = {"__name__": "startup_import_test"}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(APP), "exec"), namespace)
        self.render = namespace["render_post_phase3_workspace"]
        self.previous = sys.modules.pop(MODULE, None)
        self.loader = WorkspaceLoader()
        sys.meta_path.insert(0, self.loader)

    def tearDown(self):
        sys.meta_path.remove(self.loader)
        sys.modules.pop(MODULE, None)
        if self.previous is not None:
            sys.modules[MODULE] = self.previous

    def test_normal_import_and_render_arguments(self):
        self.assertEqual(self.loader.loads, 0)
        self.assertEqual(self.render("ticker", root="data"), (("ticker",), {"root": "data"}))
        self.assertEqual(self.loader.loads, 1)

    def test_single_hot_reload_eviction_recovers(self):
        self.loader.evictions = 1
        self.assertEqual(self.render(root="data"), ((), {"root": "data"}))
        self.assertEqual(self.loader.loads, 2)

    def test_repeated_eviction_is_bounded(self):
        self.loader.evictions = 3
        with self.assertRaisesRegex(KeyError, MODULE):
            self.render()
        self.assertEqual(self.loader.loads, 2)

    def test_module_code_keyerror_is_not_retried(self):
        self.loader.import_error = KeyError(MODULE)
        with self.assertRaises(KeyError) as caught:
            self.render()
        self.assertIs(caught.exception, self.loader.import_error)
        self.assertEqual(self.loader.loads, 1)

    def test_missing_dependency_is_not_retried(self):
        self.loader.import_error = ModuleNotFoundError("missing_dependency")
        with self.assertRaises(ModuleNotFoundError):
            self.render()
        self.assertEqual(self.loader.loads, 1)

    def test_render_data_keyerror_is_not_retried(self):
        self.loader.render_error = KeyError(MODULE)
        with self.assertRaises(KeyError) as caught:
            self.render()
        self.assertIs(caught.exception, self.loader.render_error)
        self.assertEqual(self.loader.loads, 1)


if __name__ == "__main__":
    unittest.main()
