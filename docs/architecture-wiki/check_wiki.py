"""Read-only checks for the architecture wiki."""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MARKDOWN_FILES = sorted(ROOT.rglob("*.md"))

OBSERVED_FILES = {
    ROOT / "system-map.md",
    ROOT / "module-inventory.md",
    ROOT / "data-model-input.md",
    ROOT / "crack-detection.md",
    ROOT / "fracture-analysis.md",
    ROOT / "results-io-workflows.md",
    ROOT / "scientific-context.md",
    ROOT / "coupling-map.md",
}

STALE_PATTERNS = {
    "InputData lifecycle": "Use 'Implicit InputData workflow'.",
    "CrackDetectionIntercept": "Use 'CrackDetectionLineIntercept'.",
    "Bueckner/Chen": "Use 'Bueckner-Chen'.",
}

FUTURE_LANGUAGE_PATTERNS = (
    "Future direction:",
    "proposed future",
    "should refactor",
    "should extract",
    "should introduce",
)


def normalize_heading(value: str) -> str:
    value = value.strip().strip("`")
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def markdown_heading_text(line: str) -> str | None:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    if not match:
        return None
    return match.group(2).strip()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_note_index() -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = defaultdict(list)
    for path in MARKDOWN_FILES:
        rel = path.relative_to(ROOT).with_suffix("").as_posix()
        index[rel].append(path)
        index[path.stem].append(path)
    return index


def resolve_note(current: Path, target: str, index: dict[str, list[Path]]) -> Path | None:
    candidates: list[Path] = []
    if target:
        candidates.append((ROOT / target).with_suffix(".md"))
        candidates.append((current.parent / target).with_suffix(".md"))
        candidates.extend(index.get(target, []))
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return None


def collect_headings(path: Path) -> set[str]:
    headings: set[str] = set()
    for line in read_text(path).splitlines():
        heading = markdown_heading_text(line)
        if heading:
            headings.add(normalize_heading(heading))
    return headings


def check_ascii(errors: list[str]) -> None:
    for path in MARKDOWN_FILES + [ROOT / "check_wiki.py"]:
        text = read_text(path)
        bad = sorted({char for char in text if ord(char) > 127})
        if bad:
            codes = ", ".join(f"U+{ord(char):04X}" for char in bad)
            errors.append(f"{path.relative_to(ROOT)} contains non-ASCII characters: {codes}")


def check_wiki_links(errors: list[str]) -> None:
    index = build_note_index()
    heading_cache: dict[Path, set[str]] = {}
    pattern = re.compile(r"\[\[([^\]]+)\]\]")

    for path in MARKDOWN_FILES:
        text = read_text(path)
        for raw_link in pattern.findall(text):
            link = raw_link.split("|", 1)[0].strip()
            note, _, anchor = link.partition("#")
            target = resolve_note(path, note, index)
            if target is None:
                errors.append(f"{path.relative_to(ROOT)} has unresolved wiki link [[{raw_link}]]")
                continue
            if anchor:
                target = target.resolve()
                heading_cache.setdefault(target, collect_headings(target))
                normalized_anchor = normalize_heading(anchor)
                if normalized_anchor not in heading_cache[target]:
                    errors.append(
                        f"{path.relative_to(ROOT)} links to missing heading [[{raw_link}]]"
                    )


def check_duplicate_glossary_headings(errors: list[str]) -> None:
    glossary = ROOT / "glossary.md"
    headings = [
        normalize_heading(line[5:])
        for line in read_text(glossary).splitlines()
        if line.startswith("#### ")
    ]
    duplicates = [heading for heading, count in Counter(headings).items() if count > 1]
    for heading in sorted(duplicates):
        errors.append(f"glossary.md has duplicate glossary heading: {heading}")


def check_stale_terms(errors: list[str]) -> None:
    for path in MARKDOWN_FILES:
        text = read_text(path)
        for pattern, replacement in STALE_PATTERNS.items():
            if pattern in text:
                errors.append(
                    f"{path.relative_to(ROOT)} contains stale term '{pattern}'. {replacement}"
                )


def check_observed_future_language(errors: list[str]) -> None:
    for path in sorted(OBSERVED_FILES):
        text = read_text(path)
        for pattern in FUTURE_LANGUAGE_PATTERNS:
            if pattern.lower() in text.lower():
                errors.append(
                    f"{path.relative_to(ROOT)} contains future-design phrase '{pattern}'"
                )


def check_role_lines(errors: list[str]) -> None:
    for path in MARKDOWN_FILES:
        if path.name == "README.md" and path.parent == ROOT:
            continue
        lines = read_text(path).splitlines()
        if not any(line.startswith("Role: ") for line in lines[:8]):
            errors.append(f"{path.relative_to(ROOT)} is missing a top-level Role line")


def main() -> int:
    errors: list[str] = []
    check_ascii(errors)
    check_wiki_links(errors)
    check_duplicate_glossary_headings(errors)
    check_stale_terms(errors)
    check_observed_future_language(errors)
    check_role_lines(errors)

    if errors:
        print("Architecture wiki checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Architecture wiki checks passed for {len(MARKDOWN_FILES)} Markdown files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
