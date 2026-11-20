"""Run only the 22 Member 2 unit tests and save the complete output.

Run from the repository root:
  PYTHONDONTWRITEBYTECODE=1 python results/member2/final_report_evidence/run_member2_tests.py

The team's other test file (tests/test_demand_forecasting.py, 3 tests) is
deliberately not run here.
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOG = Path(__file__).resolve().parent / "member2_test_execution_log.txt"
TEST_FILES = ["tests/test_eda_features.py", "tests/test_feature_comparison.py"]
command = [sys.executable, "-m", "unittest", "-v", *TEST_FILES]

from importlib.metadata import version
packages = ", ".join(f"{p} {version(p)}" for p in ["numpy", "pandas", "scikit-learn", "scipy", "shapely", "matplotlib"])
started = datetime.now().astimezone()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=env)
finished = datetime.now().astimezone()
output = completed.stdout + completed.stderr

ran = re.search(r"Ran (\d+) tests? in ([\d.]+)s", output)
tests_run = int(ran.group(1)) if ran else None
ok_lines = len(re.findall(r" \.\.\. ok$", output, flags=re.M))
fail_lines = len(re.findall(r" \.\.\. FAIL$", output, flags=re.M))
error_lines = len(re.findall(r" \.\.\. ERROR$", output, flags=re.M))
skip_lines = len(re.findall(r" \.\.\. skipped", output, flags=re.M))
per_file = {f: len(re.findall(rf"\(tests\.{Path(f).stem}\.\S+\) \.\.\. ", output)) for f in TEST_FILES}
overall = "PASSED" if completed.returncode == 0 and re.search(r"^OK", output, flags=re.M) else "FAILED"

header = f"""Member 2 unit-test execution log
================================
Scope: the 22 Member 2 tests only ({', '.join(TEST_FILES)}).
Not run: tests/test_demand_forecasting.py (3 team tests owned by Member 5).
All 22 tests build synthetic panels. tests/test_feature_comparison.py fits small Poisson
models on its synthetic panel inside the test; no real project data, 2025 targets,
saved model, or saved result is read, retrained, or changed (one test only hashes four
teammate files to confirm they are unchanged).

Started:          {started.isoformat(timespec='seconds')}
Finished:         {finished.isoformat(timespec='seconds')}
Python:           {platform.python_version()} ({sys.executable})
Platform:         {platform.platform()}
Packages:         {packages}
Working dir:      repository root
Command:          PYTHONDONTWRITEBYTECODE=1 python -m unittest -v {' '.join(TEST_FILES)}
Exit code:        {completed.returncode}
Tests run:        {tests_run}
Tests per file:   {per_file}
Passed:           {ok_lines}
Failed:           {fail_lines}
Errors:           {error_lines}
Skipped:          {skip_lines}
Overall result:   {overall}

Complete output
---------------
"""
LOG.write_text(header + output)
print(header + output)
sys.exit(completed.returncode)
