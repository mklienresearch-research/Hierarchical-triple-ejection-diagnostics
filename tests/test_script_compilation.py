"""Every committed Python file under src/, scripts/, tests/, workflows/ must compile."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_all_python_files_compile():
    failures = []
    checked = 0
    for top in ("src", "scripts", "tests", "workflows"):
        for path in sorted((ROOT / top).rglob("*.py")):
            checked += 1
            try:
                compile(path.read_bytes(), str(path), "exec")
            except SyntaxError as exc:
                failures.append(f"{path}: {exc}")
    assert checked > 10, "expected to find the package, tests, and workflows"
    assert failures == [], failures
