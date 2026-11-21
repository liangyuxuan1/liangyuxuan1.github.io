#!/usr/bin/env python3

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_DIR = ROOT / "content" / "publication"


TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z0-9_]+):(?:\s.*)?$")
INLINE_FIELD_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=\s*([{\"])(.*?)([}\"])\s*,?\s*$")


def parse_bib_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = INLINE_FIELD_RE.match(line)
        if not match:
            continue
        key = match.group(1).lower()
        value = match.group(3).strip()
        if value:
            fields[key] = value
    return fields


def yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_publication_value(fields: dict[str, str]) -> str | None:
    venue = fields.get("journal") or fields.get("booktitle")
    if not venue:
        return None

    detail = ""
    volume = fields.get("volume", "").strip()
    number = fields.get("number", "").strip()
    pages = fields.get("pages", "").strip()

    if volume:
        detail = volume
        if number:
            detail += f"({number})"
    elif number:
        detail = f"no. {number}"

    if pages:
        if detail:
            detail += f": {pages}"
        else:
            detail = pages

    publication = f"*{venue}*"
    if detail:
        publication += f", {detail}"
    return publication


def split_front_matter_blocks(front_matter: str) -> list[tuple[str | None, list[str]]]:
    blocks: list[tuple[str | None, list[str]]] = []
    current_key: str | None = None
    current_lines: list[str] = []

    for line in front_matter.splitlines():
        key_match = TOP_LEVEL_KEY_RE.match(line)
        is_top_level = bool(key_match) and not line.startswith(" ")
        if is_top_level:
            if current_lines:
                blocks.append((current_key, current_lines))
            current_key = key_match.group(1)
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        blocks.append((current_key, current_lines))

    return blocks


def update_front_matter(
    front_matter: str, fields: dict[str, str], *, has_featured_image: bool = False
) -> str:
    publication_value = build_publication_value(fields)
    volume = fields.get("volume", "").strip()
    number = fields.get("number", "").strip()
    pages = fields.get("pages", "").strip()

    blocks = split_front_matter_blocks(front_matter)
    filtered: list[tuple[str | None, list[str]]] = []
    inserted = False

    for key, lines in blocks:
        if key == "featured" and has_featured_image:
            continue
        if key in {"publication", "volume", "number", "pages"}:
            continue

        filtered.append((key, lines))

        if key == "publication_types":
            if publication_value is not None:
                filtered.append(("publication", [f"publication: {yaml_quote(publication_value)}"]))
            if volume:
                filtered.append(("volume", [f"volume: {yaml_quote(volume)}"]))
            if number:
                filtered.append(("number", [f"number: {yaml_quote(number)}"]))
            if pages:
                filtered.append(("pages", [f"pages: {yaml_quote(pages)}"]))
            inserted = True

    if not inserted:
        if publication_value is not None:
            filtered.append(("publication", [f"publication: {yaml_quote(publication_value)}"]))
        if volume:
            filtered.append(("volume", [f"volume: {yaml_quote(volume)}"]))
        if number:
            filtered.append(("number", [f"number: {yaml_quote(number)}"]))
        if pages:
            filtered.append(("pages", [f"pages: {yaml_quote(pages)}"]))

    # Academic --overwrite removes manually added front matter. Restore the
    # homepage selection from image assets, which survive the import.
    if has_featured_image:
        filtered.append(("featured", ["featured: true"]))

    return "\n".join("\n".join(lines) for _, lines in filtered) + "\n"


def process_publication_dir(pub_dir: Path) -> bool:
    index_path = pub_dir / "index.md"
    bib_path = pub_dir / "cite.bib"
    if not index_path.exists() or not bib_path.exists():
        return False

    fields = parse_bib_fields(bib_path.read_text(encoding="utf-8"))
    text = index_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False

    try:
        _, front_matter, body = text.split("---\n", 2)
    except ValueError:
        return False

    has_featured_image = any(
        path.is_file()
        and path.stem.lower() == "featured"
        and path.suffix.lower() in {".jpg", ".jpeg", ".png"}
        for path in pub_dir.iterdir()
    )
    new_front_matter = update_front_matter(
        front_matter, fields, has_featured_image=has_featured_image
    )
    new_text = f"---\n{new_front_matter}---\n{body}"

    if new_text != text:
        index_path.write_text(new_text, encoding="utf-8")
        return True

    return False


def main() -> None:
    changed = 0
    for pub_dir in sorted(PUBLICATION_DIR.iterdir()):
        if not pub_dir.is_dir():
            continue
        if process_publication_dir(pub_dir):
            changed += 1
    print(f"Updated {changed} publication index file(s).")


if __name__ == "__main__":
    main()
