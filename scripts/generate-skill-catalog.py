#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    sys.exit("PyYAML is required; run this script from the Nix development shell")

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SKILLS = ROOT / "skills"
START = "<!-- skill-catalog:start -->"
END = "<!-- skill-catalog:end -->"


def fail(message):
    sys.exit(f"skill catalog: {message}")


def load_skill(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        fail(f"{path.relative_to(ROOT)} has no YAML frontmatter")

    try:
        frontmatter_end = lines.index("---", 1)
    except ValueError:
        fail(f"{path.relative_to(ROOT)} has unterminated YAML frontmatter")

    data = yaml.safe_load("\n".join(lines[1:frontmatter_end]))
    if not isinstance(data, dict):
        fail(f"{path.relative_to(ROOT)} has invalid YAML frontmatter")

    name = data.get("name")
    metadata = data.get("metadata")
    emoji = metadata.get("catalog-emoji") if isinstance(metadata, dict) else None
    summary = metadata.get("catalog-summary") if isinstance(metadata, dict) else None
    if not isinstance(name, str) or not name:
        fail(f"{path.relative_to(ROOT)} has no name")
    if name != path.parent.name:
        fail(f"{path.relative_to(ROOT)} name must match its directory")
    if not isinstance(emoji, str) or not emoji.strip():
        fail(f"{path.relative_to(ROOT)} has no metadata.catalog-emoji")
    if not isinstance(summary, str) or not summary.strip():
        fail(f"{path.relative_to(ROOT)} has no metadata.catalog-summary")

    return name, emoji.strip(), summary.strip(), path.relative_to(ROOT).as_posix()


def markdown_cell(value):
    return " ".join(value.split()).replace("|", "\\|")


def render_catalog():
    skills = sorted(
        (load_skill(path) for path in SKILLS.glob("*/SKILL.md")),
        key=lambda skill: skill[0],
    )
    if not skills:
        fail("no skills found")

    names = [name for name, _, _, _ in skills]
    if len(names) != len(set(names)):
        fail("skill names must be unique")

    rows = [
        "| Preview | Skill | What it does |",
        "| --- | --- | --- |",
    ]
    rows.extend(
        f'| [<img width="160" src="./assets/{name}.webp" alt="{name} illustration"/>](./{path}) | '
        f"{markdown_cell(emoji)} **[{name}](./{path})** | {markdown_cell(summary)} |"
        for name, emoji, summary, path in skills
    )
    return "\n".join(rows), len(skills)


def main():
    parser = argparse.ArgumentParser(description="Generate the README skill catalog")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="fail if the catalog is stale")
    mode.add_argument("--validate", action="store_true", help="validate catalog metadata")
    args = parser.parse_args()

    catalog, count = render_catalog()
    noun = "skill" if count == 1 else "skills"
    if args.validate:
        print(f"Skill catalog metadata is valid ({count} {noun})")
        return

    source = README.read_text(encoding="utf-8")
    if source.count(START) != 1 or source.count(END) != 1:
        fail(f"README.md must contain exactly one {START} / {END} pair")

    before, remainder = source.split(START, 1)
    _, after = remainder.split(END, 1)
    updated = f"{before}{START}\n{catalog}\n{END}{after}"

    if args.check:
        if source != updated:
            fail("README.md is out of date; run 'just fix-catalog'")
        print(f"Skill catalog is up to date ({count} {noun})")
        return

    if source == updated:
        print(f"Skill catalog is already up to date ({count} {noun})")
        return

    README.write_text(updated, encoding="utf-8")
    print(f"Updated README.md skill catalog ({count} {noun})")


if __name__ == "__main__":
    main()
