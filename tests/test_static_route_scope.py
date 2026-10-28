"""Static-route regression check without importing heavy ML dependencies."""

import ast
from pathlib import Path
import unittest


APP_MAIN = Path(__file__).resolve().parents[1] / "app" / "main.py"


class StaticAssetBoundaryTests(unittest.TestCase):
    def test_backend_does_not_mount_repository_as_static_directory(self):
        tree = ast.parse(APP_MAIN.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            name = function.id if isinstance(function, ast.Name) else (
                function.attr if isinstance(function, ast.Attribute) else None
            )
            self.assertNotEqual(name, "StaticFiles", "Do not serve a whole directory as static content")
            if isinstance(function, ast.Attribute) and function.attr == "mount":
                self.fail("Audit directory mounts before reintroducing them to the backend")

    def test_public_logo_route_remains_explicit(self):
        source = APP_MAIN.read_text(encoding="utf-8")
        self.assertIn('@app.get("/static/logo.png", include_in_schema=False)', source)
        self.assertIn('FileResponse(path=logo_path, media_type="image/png")', source)


if __name__ == "__main__":
    unittest.main()
