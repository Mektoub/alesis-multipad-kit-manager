#!/usr/bin/env python3
"""Cohérence de la version de l'application dans le dépôt.

La version est écrite dans app-names.json (lue par le serveur) et dans les
package.json de desktop/ et editor/web/, avec leurs package-lock.json (tenus à
jour par ./dev.sh release).

  verifier-version.py               les fichiers ont tous la même version
  verifier-version.py X.Y.Z         ils ont tous X.Y.Z, et CHANGELOG.md a une
                                    section « ## X.Y.Z — … »
  verifier-version.py --notes X.Y.Z notes de version : « Version X.Y.Z — titre »,
                                    puis le contenu de la section du CHANGELOG
  --rev REV                         fichiers du commit REV au lieu de l'arbre de
                                    travail (hooks Git)

Code de sortie : 0 si tout concorde, 1 sinon (détail sur la sortie d'erreur).
Bibliothèque standard uniquement : lancé par les hooks Git et la CI.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
# (fichier, chemin de la clé dans le JSON)
FIELDS = [
    ("app-names.json", ("version",)),
    ("desktop/package.json", ("version",)),
    ("desktop/package-lock.json", ("version",)),
    ("desktop/package-lock.json", ("packages", "", "version")),
    ("editor/web/package.json", ("version",)),
    ("editor/web/package-lock.json", ("version",)),
    ("editor/web/package-lock.json", ("packages", "", "version")),
]


def read(path, rev):
    """Contenu de `path` (relatif à la racine), dans le commit `rev` s'il est donné."""
    if rev is None:
        return (ROOT / path).read_text(encoding="utf-8")
    out = subprocess.run(["git", "-C", str(ROOT), "show", "%s:%s" % (rev, path)], capture_output=True, text=True)
    if out.returncode:
        raise FileNotFoundError("%s absent de %s" % (path, rev))
    return out.stdout


def versions(rev=None):
    """[(« fichier (clé) », version ou None)] pour chaque champ de FIELDS."""
    found = []
    for path, keys in FIELDS:
        value = json.loads(read(path, rev))
        for key in keys:
            value = value.get(key) if isinstance(value, dict) else None
        found.append(("%s (%s)" % (path, ".".join(k or '""' for k in keys)), value))
    return found


def changelog_section(version, rev=None):
    """(titre, lignes) de la section « ## <version> — … » du CHANGELOG, ou None."""
    lines = read("CHANGELOG.md", rev).splitlines()
    head = "## " + version
    for i, line in enumerate(lines):
        if line == head or line.startswith(head + " "):
            end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
            return line[3:], lines[i + 1 : end]
    return None


def check(version=None, rev=None):
    """Liste des incohérences (vide si tout concorde)."""
    errors = []
    found = versions(rev)
    expected = version or found[0][1]
    if version is not None and not VERSION_RE.match(version):
        return ["version attendue sous la forme X.Y.Z : %s" % version]
    if not expected:
        return ["pas de version dans app-names.json"]
    errors += ["%s : %s au lieu de %s" % (where, v, expected) for where, v in found if v != expected]
    if version is not None and changelog_section(version, rev) is None:
        errors.append("pas de section « ## %s — … » dans CHANGELOG.md" % version)
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("version", nargs="?", help="version attendue, X.Y.Z")
    ap.add_argument("--rev", help="commit à vérifier (défaut : arbre de travail)")
    ap.add_argument("--notes", action="store_true", help="afficher les notes de version (CHANGELOG)")
    args = ap.parse_args(argv)
    try:
        if args.notes:
            if not args.version:
                ap.error("--notes demande une version")
            section = changelog_section(args.version, args.rev)
            if section is None:
                print("pas de section « ## %s — … » dans CHANGELOG.md" % args.version, file=sys.stderr)
                return 1
            title, body = section
            print("Version %s\n%s" % (title, "\n".join(body).rstrip()))
            return 0
        errors = check(args.version, args.rev)
    except (OSError, ValueError) as exc:
        print("Erreur : %s" % exc, file=sys.stderr)
        return 1
    where = " dans %s" % args.rev if args.rev else ""
    if errors:
        print("Versions incohérentes%s :" % where, file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        return 1
    print("Version %s cohérente%s." % (args.version or versions(args.rev)[0][1], where))
    return 0


if __name__ == "__main__":
    sys.exit(main())
