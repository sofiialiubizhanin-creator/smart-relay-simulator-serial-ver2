"""Report AC coverage: AC IDs defined in specs/*/requirements.md vs @pytest.mark.ac(...) in tests/e2e.

Usage: python .claude/skills/e2e-test-conventions/scripts/ac_coverage.py [repo_root]
Exit code 1 if any AC is uncovered or a test references an unknown AC.
"""
import re
import sys
from pathlib import Path

AC_DEF = re.compile(r"^\|\s*(AC-[A-Z0-9]+-\d+)\s*\|", re.MULTILINE)
AC_MARK = re.compile(r"""pytest\.mark\.ac\(([^)]*)\)""")
AC_ID = re.compile(r"AC-[A-Z0-9]+-\d+")
TEST_DEF = re.compile(r"^\s*def (test_\w+)", re.MULTILINE)


def main(root: Path) -> int:
    defined = {}
    for req in sorted(root.glob("specs/*/requirements.md")):
        for ac in AC_DEF.findall(req.read_text(encoding="utf-8")):
            defined[ac] = req.parent.name

    covered: dict[str, list[str]] = {}
    for test_file in sorted((root / "tests" / "e2e").glob("test_*.py")):
        text = test_file.read_text(encoding="utf-8")
        marks = list(AC_MARK.finditer(text))
        for m in marks:
            after = TEST_DEF.search(text, m.end())
            name = after.group(1) if after else "?"
            for ac in AC_ID.findall(m.group(1)):
                covered.setdefault(ac, []).append(f"{test_file.name}::{name}")

    ok = True
    print(f"{'AC':<10} {'tests':>5}  first test")
    for ac in sorted(defined, key=lambda a: (a.rsplit('-', 1)[0], int(a.rsplit('-', 1)[1]))):
        tests = sorted(set(covered.get(ac, [])))
        print(f"{ac:<10} {len(tests):>5}  {tests[0] if tests else 'UNCOVERED'}")
        ok &= bool(tests)
    unknown = sorted(set(covered) - set(defined))
    for ac in unknown:
        print(f"UNKNOWN AC referenced by tests: {ac} -> {covered[ac]}")
    return 0 if ok and not unknown else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()))
