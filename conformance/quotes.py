from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, NamedTuple

ROOT = Path(__file__).resolve().parent.parent

DOCUMENTS = ROOT / "docs" / "manufacturer"

RECORD = ROOT / "conformance" / "hardware.json"

TIMEOUT = 120

Reader = Callable[[Path, int], str]


class Quote(NamedTuple):
    where: str
    needle: str
    document: str
    page: int


def flatten(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKD", text).lower())


def looked_for(entry: dict[str, Any]) -> str:
    return str(entry["section"]) if entry.get("assembled") else str(entry["quote"])


def quoted(node: Any, files: dict[str, str], trail: str) -> list[Quote]:
    found: list[Quote] = []
    if isinstance(node, dict):
        if isinstance(node.get("quote"), str):
            document = files[str(node["document"])]
            found.append(Quote(trail, looked_for(node), document, int(node["filePage"])))
        for key, value in node.items():
            found.extend(quoted(value, files, f"{trail}/{key}" if trail else str(key)))
    elif isinstance(node, list):
        for at, one in enumerate(node):
            found.extend(quoted(one, files, f"{trail}[{at}]"))
    return found


def held(record: dict[str, Any]) -> list[Quote]:
    files = {name: str(entry["file"]) for name, entry in record["documents"].items()}
    rest = {key: value for key, value in record.items() if key != "documents"}
    return quoted(rest, files, "")


def page_text(path: Path, page: int, run: Any = None) -> str:
    runner = subprocess.run if run is None else run
    try:
        done = runner(
            ["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            check=False,
            timeout=TIMEOUT,
        )
    except OSError:
        return ""
    return str(done.stdout) if done.returncode == 0 else ""


def unplaced(quotes: Sequence[Quote], where: Path, read: Reader) -> list[str]:
    return [
        f"{one.where}: not on page {one.page} of {one.document}"
        for one in quotes
        if flatten(one.needle) not in flatten(read(where / one.document, one.page))
    ]


def main(record: Path | None = None, where: Path | None = None, read: Reader | None = None) -> int:
    quotes = held(json.loads((record or RECORD).read_text()))
    folder = where or DOCUMENTS
    absent = sorted({one.document for one in quotes if not (folder / one.document).is_file()})
    if absent:
        print(f"{len(quotes)} quotes, none checked: {', '.join(absent)} is not on this machine")
        return 0
    missing = unplaced(quotes, folder, read or page_text)
    for line in missing:
        print(f"  {line}")
    print(f"{len(quotes)} quotes, {len(quotes) - len(missing)} found on the page they cite")
    return 1 if missing or not quotes else 0


if __name__ == "__main__":
    sys.exit(main())
