"""Security regression tests for GitHub workflow supply-chain controls."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class WorkflowSecurityTests(unittest.TestCase):
    def test_all_external_actions_use_immutable_commit_shas(self):
        found = 0
        for path in sorted(WORKFLOWS.glob("*.yml")):
            content = path.read_text(encoding="utf-8")
            for match in re.finditer(r"(?m)^\s*-?\s*uses:\s*([^\s#]+)", content):
                action = match.group(1)
                if action.startswith("./"):
                    continue
                found += 1
                self.assertRegex(
                    action,
                    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*@[a-fA-F0-9]{40}$",
                    f"{path.name}: action reference must use a full immutable commit SHA: {action}",
                )
        self.assertGreaterEqual(found, 5)

    def test_codeql_has_manual_review_branch_scan(self):
        content = (WORKFLOWS / "codeql.yml").read_text(encoding="utf-8")
        self.assertIn("  workflow_dispatch:", content)
        self.assertIn("language: python", content)
        self.assertIn("language: actions", content)
        self.assertIn("security-events: write", content)
        self.assertIn("contents: read", content)
        self.assertNotIn("pull_request_target:", content)

    def test_publication_never_pushes_main_directly(self):
        content = (WORKFLOWS / "profile-refresh.yml").read_text(encoding="utf-8")
        self.assertIn('git push -u origin "${review_branch}"', content)
        self.assertIn("gh pr create --base main", content)
        self.assertNotIn("git push origin HEAD:main", content)
        self.assertIn("codeql.yml on that same branch", content)


if __name__ == "__main__":
    unittest.main()
