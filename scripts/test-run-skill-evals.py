#!/usr/bin/env python3

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

RUNNER_PATH = Path(__file__).with_name("run-skill-evals.py")
SPEC = importlib.util.spec_from_file_location("run_skill_evals", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
ROOT = Path(__file__).resolve().parents[1]


class EvalRunnerTests(unittest.TestCase):
    def test_empty_journey_and_unchanged_summaries_fail_contradiction_case(self):
        manifest = json.loads(
            (ROOT / "skills/continuity/evals/evals.json").read_text(encoding="utf-8")
        )
        case = next(case for case in manifest["evals"] if case["id"] == "preserve-contradictions")
        fixture = ROOT / "skills/continuity/evals/fixtures/preserve-contradictions"

        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"
            shutil.copytree(fixture, workspace)
            RUNNER.expand_workspace_placeholders(workspace)
            before = RUNNER.snapshot(workspace)

            (workspace / "agent-home/memory/journey/empty.md").write_text("# Empty\n", encoding="utf-8")
            startup = workspace / "agent-home/startup.md"
            startup.write_text(
                startup.read_text(encoding="utf-8")
                + f"\nRead {workspace.resolve()}/agent-home/memory/present.md.\n",
                encoding="utf-8",
            )
            (workspace / "eval-report.json").write_text(
                json.dumps(
                    {
                        "outcome": "complete",
                        "records_exist": True,
                        "integration_scope": "agent",
                        "recovery": "unverified",
                        "notes": "claimed success",
                    }
                ),
                encoding="utf-8",
            )

            delta = RUNNER.changes(before, RUNNER.snapshot(workspace))
            semantic_checks = {
                "added_file_content",
                "added_file_linked_from",
                "changed",
                "matches",
            }
            results = [
                RUNNER.grade_assertion(workspace, assertion, before, delta)[0]
                for assertion in case["assertions"]
                if assertion["check"] in semantic_checks
            ]

        self.assertTrue(results)
        self.assertFalse(all(results), "empty integration must not satisfy semantic proxies")

    def test_timeout_bytes_are_saved_and_graded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "continuity"
            fixture = skill / "evals/fixtures/timeout"
            fixture.mkdir(parents=True)
            (fixture / "environment.json").write_text("{}\n", encoding="utf-8")
            case = {
                "id": "timeout",
                "prompt": "Do the task.",
                "expected_output": "The run times out cleanly.",
                "assertions": [{"check": "exists", "path": "environment.json"}],
            }
            timeout = subprocess.TimeoutExpired(
                cmd=["agent"],
                timeout=600,
                output=b"partial\xff",
                stderr=b"problem\xff",
            )

            with patch.object(RUNNER.subprocess, "run", side_effect=timeout):
                grade = RUNNER.run_case(
                    skill,
                    case,
                    "without_skill",
                    ["agent"],
                    root / "results",
                    "",
                )

            destination = root / "results/timeout/without_skill"
            self.assertEqual(grade["process_returncode"], 124)
            self.assertEqual((destination / "trace.jsonl").read_text(encoding="utf-8"), "partial�")
            self.assertIn(
                "problem�\nTimed out after 600 seconds",
                (destination / "stderr.log").read_text(encoding="utf-8"),
            )
            self.assertTrue((destination / "grading.json").is_file())


if __name__ == "__main__":
    unittest.main()
