"""Property test: Test Parity.

Verifies all platform-skip markers use correct reason string patterns.
Verifies only tests that directly call platform-specific modules have skip
markers.

Validates: Requirements 9.2, 9.3, 9.5
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT / "tests"

VALID_SKIP_PATTERNS = [
    re.compile(r"Requires Windows: \w+"),
    re.compile(r"Requires macOS: [\w/]+"),
]


def test_skip_markers_use_correct_reason_patterns() -> None:
    """All skipif markers have reason strings matching required patterns."""
    for test_file in TESTS_DIR.glob("test_*.py"):
        source = test_file.read_text()
        # Find all skipif reason strings
        reasons = re.findall(r'reason="([^"]+)"', source)
        for reason in reasons:
            if "Requires" in reason:
                assert any(
                    p.match(reason) for p in VALID_SKIP_PATTERNS
                ), f"Invalid skip reason in {test_file.name}: '{reason}'"


def test_only_platform_specific_tests_have_skip_markers() -> None:
    """Files with skip markers must import platform-specific modules."""
    platform_modules = {"winreg", "ctypes", "fcntl", "plistlib"}

    for test_file in TESTS_DIR.glob("test_*.py"):
        source = test_file.read_text()
        has_skip = "skipif" in source and "Requires" in source

        if has_skip:
            # The file should reference at least one platform-specific module
            tree = ast.parse(source)
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split(".")[0])

            # Check if file references platform modules either via import or
            # string reference (e.g., in import statements within test code)
            references_platform = bool(
                imports & platform_modules
                or any(m in source for m in platform_modules)
            )
            assert references_platform, (
                f"{test_file.name} has skip markers but doesn't reference "
                f"platform-specific modules"
            )
