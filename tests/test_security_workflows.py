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

    def test_codeql_is_least_privilege_without_stored_checkout_token(self):
        content = (WORKFLOWS / "codeql.yml").read_text(encoding="utf-8")
        self.assertIn("persist-credentials: false", content)
        self.assertIn("timeout-minutes: 20", content)
        self.assertIn("security-events: write", content)
        self.assertIn("contents: read", content)
        self.assertNotIn("      packages: read", content)
        self.assertNotIn("      actions: read", content)

    def test_dependabot_reviews_pinned_actions_and_python_requirements(self):
        config = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        self.assertIn('package-ecosystem: "github-actions"', config)
        self.assertIn('package-ecosystem: "pip"', config)
        self.assertIn('interval: "weekly"', config)
        self.assertEqual(config.count("open-pull-requests-limit: 5"), 2)
        requirements = (ROOT / "requirements-ci.txt").read_text(encoding="utf-8")
        self.assertIn("CairoSVG==2.8.2", requirements)
        workflow = (WORKFLOWS / "profile-refresh.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("pip install --disable-pip-version-check -r requirements-ci.txt"), 3)
        self.assertNotIn("pip install --disable-pip-version-check 'CairoSVG==", workflow)

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
