#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class SkillReleaseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("GIT_", "GITHUB_")) and key != "GH_TOKEN"
        }
        self.env.update(
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_AUTHOR_NAME="Release Test",
            GIT_AUTHOR_EMAIL="release-test@example.org",
            GIT_COMMITTER_NAME="Release Test",
            GIT_COMMITTER_EMAIL="release-test@example.org",
        )
        self.run_command("git", "init", "--initial-branch=main")
        self.run_command("git", "config", "core.hooksPath", os.devnull)
        self.run_command("git", "config", "commit.gpgsign", "false")
        self.run_command("git", "config", "tag.gpgsign", "false")
        self.run_command("git", "remote", "add", "origin", "https://github.com/ccamel/agent-self-help.git")
        self.skills = sorted(path.parent.name for path in (ROOT / "skills").glob("*/pyproject.toml"))
        for name in self.skills:
            target = self.repo / "skills" / name
            target.mkdir(parents=True)
            for filename in ("SKILL.md", "pyproject.toml"):
                shutil.copyfile(ROOT / "skills" / name / filename, target / filename)
        self.commit("feat: introduce self-directed practices")

    def run_command(self, *args, cwd=None):
        result = subprocess.run(
            args, cwd=cwd or self.repo, env=self.env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        return result.stdout.strip()

    def commit(self, message):
        self.run_command("git", "add", ".")
        self.run_command("git", "commit", "-m", message)

    def release(self, name, preview=False):
        options = ["--noop"] if preview else []
        return self.run_command(
            sys.executable, "-m", "semantic_release", *options,
            "version", "--no-push", "--no-vcs-release",
            cwd=self.repo / "skills" / name,
        )

    def signing_script(self, step_id="signing"):
        workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
        return next(
            step["run"] for step in workflow["jobs"]["release"]["steps"]
            if step.get("id") == step_id
        )

    def test_release_commits_and_tags_are_gpg_signed(self):
        with tempfile.TemporaryDirectory() as temporary:
            source_home = Path(temporary) / "source-gnupg"
            source_home.mkdir(mode=0o700)
            self.env["RUNNER_TEMP"] = temporary
            self.env["GNUPGHOME"] = str(Path(temporary) / "release-gnupg")
            passphrase = "release-test-passphrase"
            try:
                self.run_command(
                    "gpg", "--homedir", str(source_home), "--batch",
                    "--pinentry-mode", "loopback", "--passphrase", passphrase,
                    "--quick-generate-key", "Release Test <release-test@example.org>",
                    "ed25519", "sign", "1d",
                )
                public_keys = self.run_command(
                    "gpg", "--homedir", str(source_home), "--with-colons", "--list-keys",
                )
                fingerprint = next(
                    line.split(":")[9] for line in public_keys.splitlines()
                    if line.startswith("fpr:")
                )
                self.env["GPG_FINGERPRINT"] = fingerprint
                self.env["GPG_PRIVATE_KEY"] = self.run_command(
                    "gpg", "--homedir", str(source_home), "--batch",
                    "--pinentry-mode", "loopback", "--passphrase", passphrase,
                    "--armor", "--export-secret-keys", fingerprint,
                )
                self.env["GPG_PASSPHRASE"] = "wrong-passphrase"
                result = subprocess.run(
                    ["bash", "-euo", "pipefail", "-c", self.signing_script()],
                    cwd=self.repo, env=self.env, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
                )
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.run_command("bash", "-euo", "pipefail", "-c", self.signing_script("signing-cleanup"))

                self.env["GPG_PASSPHRASE"] = passphrase
                self.run_command("bash", "-euo", "pipefail", "-c", self.signing_script())
                for name in self.skills:
                    self.release(name)
                    tag = f"{name}-v0.1.0"
                    self.run_command("git", "verify-commit", f"{tag}^{{commit}}")
                    self.run_command("git", "verify-tag", tag)
            finally:
                self.run_command("bash", "-euo", "pipefail", "-c", self.signing_script("signing-cleanup"))
                self.run_command("gpgconf", "--homedir", str(source_home), "--kill", "gpg-agent")
            self.assertFalse(Path(self.env["GNUPGHOME"]).exists())
            self.assertFalse((Path(temporary) / "release-gpg").exists())

    def test_missing_or_invalid_signing_key_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.env["RUNNER_TEMP"] = temporary
            self.env["GNUPGHOME"] = str(Path(temporary) / "release-gnupg")
            for key in ("", "not a private key"):
                with self.subTest(key=key):
                    self.env["GPG_PRIVATE_KEY"] = key
                    try:
                        result = subprocess.run(
                            ["bash", "-euo", "pipefail", "-c", self.signing_script()],
                            cwd=self.repo, env=self.env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
                        )
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                    finally:
                        self.run_command("bash", "-euo", "pipefail", "-c", self.signing_script("signing-cleanup"))

    def test_independent_versions_and_safe_preview(self):
        original = {
            name: (self.repo / "skills" / name / "SKILL.md").read_bytes()
            for name in self.skills
        }
        head = self.run_command("git", "rev-parse", "HEAD")
        for name in self.skills:
            self.release(name, preview=True)
            self.assertEqual((self.repo / "skills" / name / "SKILL.md").read_bytes(), original[name])
            self.assertFalse((self.repo / "skills" / name / "CHANGELOG.md").exists())
        self.assertEqual(self.run_command("git", "rev-parse", "HEAD"), head)
        self.assertEqual(self.run_command("git", "tag"), "")

        for name in self.skills:
            self.release(name)
            self.assertIn(f"{name}-v0.1.0", self.run_command("git", "tag").splitlines())
            changelog = (self.repo / "skills" / name / "CHANGELOG.md").read_text()
            self.assertIn("0.1.0", changelog)

        # The file path, not the scope, decides which skill receives the bump.
        first, second = self.skills[:2]
        expected = {name: "0.1.0" for name in self.skills}
        changes = [
            ("README.md", "feat: describe the catalog", None, None),
            (f"skills/{first}/SKILL.md", f"fix({second}): clarify a practice", first, "0.1.1"),
            (f"skills/{first}/references/example.md", "feat: add a practice resource", first, "0.2.0"),
            (f"skills/{second}/SKILL.md", "feat!: change the practice contract", second, "0.2.0"),
            (f"skills/{first}/evals/example.md", "test: cover another encounter", None, None),
        ]
        for filename, message, changed_skill, version in changes:
            with self.subTest(message=message):
                path = self.repo / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a") as stream:
                    stream.write(f"\n{message}\n")
                self.commit(message)
                previous_tags = set(self.run_command("git", "tag").splitlines())
                if changed_skill:
                    expected[changed_skill] = version
                for name in self.skills:
                    self.release(name)
                    content = (self.repo / "skills" / name / "SKILL.md").read_text()
                    metadata = yaml.safe_load(content.split("---", 2)[1])["metadata"]
                    self.assertEqual(metadata["version"], expected[name])
                tags = previous_tags | ({f"{changed_skill}-v{version}"} if changed_skill else set())
                self.assertEqual(set(self.run_command("git", "tag").splitlines()), tags)

        head = self.run_command("git", "rev-parse", "HEAD")
        for name in self.skills:
            self.release(name)
        self.assertEqual(self.run_command("git", "rev-parse", "HEAD"), head)


if __name__ == "__main__":
    unittest.main()
