"""Tests de la vérification des versions (scripts/verifier-version.py) et des
hooks Git qui refusent un tag vX.Y.Z incohérent (.githooks/)."""

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "verifier-version.py"
_spec = importlib.util.spec_from_file_location("verifier_version", SCRIPT)
vv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vv)
VERSION = json.loads((ROOT / "app-names.json").read_text(encoding="utf-8"))["version"]
FILES = sorted({path for path, _ in vv.FIELDS}) + ["CHANGELOG.md"]


class Verification(unittest.TestCase):
    def test_depot_coherent(self):
        self.assertEqual(vv.check(), [])

    def test_version_differente_signalee(self):
        errors = vv.check("9.9.9")
        self.assertEqual(len(errors), len(vv.FIELDS) + 1, errors)  # chaque champ, et le CHANGELOG
        self.assertIn("app-names.json (version) : %s au lieu de 9.9.9" % VERSION, errors)
        self.assertIn("pas de section « ## 9.9.9 — … » dans CHANGELOG.md", errors)

    def test_format_de_version(self):
        self.assertEqual(vv.check("1.2"), ["version attendue sous la forme X.Y.Z : 1.2"])

    def test_notes_de_version(self):
        title, body = vv.changelog_section("0.3.1")
        self.assertTrue(title.startswith("0.3.1 — "), title)
        self.assertTrue(any(line.startswith("- ") for line in body))
        self.assertFalse(any(line.startswith("## ") for line in body))
        self.assertIsNone(vv.changelog_section("0.0.0"))


def git(repo, *args, check=True):
    env = dict(
        os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t"
    )
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=env, check=check)


@unittest.skipUnless(shutil.which("git"), "git absent")
class HooksGit(unittest.TestCase):
    """Dépôt temporaire avec les fichiers versionnés, les hooks et le script."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        for f in FILES + ["scripts/verifier-version.py"]:
            (self.repo / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / f, self.repo / f)
        shutil.copytree(ROOT / ".githooks", self.repo / ".githooks")
        git(self.repo, "init", "-q")
        git(self.repo, "config", "core.hooksPath", ".githooks")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "init")

    def tearDown(self):
        self.tmp.cleanup()

    def test_tag_coherent_accepte(self):
        r = git(self.repo, "tag", "-a", "v" + VERSION, "-m", "ok", check=False)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_tag_incoherent_refuse(self):
        r = git(self.repo, "tag", "v9.9.9", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Tag v9.9.9 refusé", r.stderr)
        self.assertEqual(git(self.repo, "tag").stdout, "")  # tag non créé

    def test_autres_tags_ignores(self):
        self.assertEqual(git(self.repo, "tag", "essai", check=False).returncode, 0)

    def test_tag_d_avant_la_version_dans_app_names_ignore(self):
        names = json.loads((self.repo / "app-names.json").read_text(encoding="utf-8"))
        del names["version"]
        (self.repo / "app-names.json").write_text(json.dumps(names), encoding="utf-8")
        git(self.repo, "commit", "-qam", "ancien")
        self.assertEqual(git(self.repo, "tag", "v0.1.0", check=False).returncode, 0)

    def test_push_d_un_tag_incoherent_refuse(self):
        remote = self.repo / "distant.git"
        git(self.repo, "init", "-q", "--bare", str(remote))
        # tag créé sans les hooks (comme sur un autre poste), puis poussé avec
        git(self.repo, "-c", "core.hooksPath=/dev/null", "tag", "v9.9.9")
        r = git(self.repo, "push", str(remote), "v9.9.9", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Tag v9.9.9 refusé", r.stderr)


if __name__ == "__main__":
    unittest.main()
