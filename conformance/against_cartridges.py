import collections
import hashlib
import json
import sys
import zlib
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from snesobc1 import chip

ROOT = Path(__file__).resolve().parent

RECORDED = "cartridges.json"

HEADER_AT = 0x7FC0

TITLE_BYTES = 21

CHIPSET = 0x25

SUFFIXES = (".sfc", ".smc")


def declared() -> tuple[int, ...]:
    return (
        *range(chip.FIRST_REGISTER, chip.PACKED_REGISTER),
        chip.PACKED_REGISTER,
        chip.BASE_REGISTER,
        chip.POINTER_REGISTER,
    )


def digests_of(image: bytes) -> dict[str, str]:
    return {
        "crc32": f"{zlib.crc32(image):08x}",
        "md5": hashlib.md5(image).hexdigest(),
        "sha1": hashlib.sha1(image).hexdigest(),
        "sha256": hashlib.sha256(image).hexdigest(),
    }


class Malformed(Exception): ...


MANIFEST = (
    Path(__file__).resolve().parent.parent / "snes-driver-python" / "cartridges.manifest.json"
)

DIGESTS = ("crc32", "md5", "sha1", "sha256")


def published() -> dict[str, dict[str, Any]]:
    held = json.loads(MANIFEST.read_text())
    assert isinstance(held, dict), f"{MANIFEST} does not hold an object"
    return {str(row["sha256"]): row for row in held["cartridges"]}


def confirmed(image: bytes, named: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    found = digests_of(image)
    row = named.get(found["sha256"])
    if row is None:
        return None
    if any(str(row[one]) != found[one] for one in DIGESTS):
        raise Malformed(f"{row['name']} is named in the manifest with digests it does not have")
    return row


def carries_the_part(image: bytes) -> bool:
    if len(image) < HEADER_AT + 32:
        return False
    return image[HEADER_AT + 22] == CHIPSET and 0x20 <= image[HEADER_AT + 21] <= 0x3F


def reached(image: bytes) -> dict[int, int]:
    here = Path(__file__).resolve().parent.parent / "snes-driver-python"
    for where in (here, here / "mos65xx-python", here / "snes-mapper-python"):
        if str(where) not in sys.path:
            sys.path.insert(0, str(where))
    from snesdriver import conversation, window_for

    window = window_for("obc1", "lorom")
    assert window is not None, "the driver knows no window for this part"

    counted: collections.Counter[int] = collections.Counter()
    seen: set[int] = set()
    for site in conversation.sites(image, window):
        if site in seen:
            continue
        talk = conversation.at(image, site, window)
        seen.update(talk.covered)
        for step in talk.steps:
            if step.address is not None and step.address >= chip.FIRST_REGISTER:
                counted[step.address] += 1
    return dict(counted)


def compare(found: dict[int, int]) -> dict[str, Any]:
    known = set(declared())
    return {
        "confirmed": [f"{at:#06x}" for at in sorted(set(found) & known)],
        "asMemory": [f"{at:#06x}" for at in sorted(set(found) - known)],
        "unreached": [f"{at:#06x}" for at in sorted(known - set(found))],
    }


def recorded(where: Path | str | None = None) -> dict[str, Any]:
    path = Path(where) if where is not None else ROOT / RECORDED
    if not path.is_file():
        return {}
    found: dict[str, Any] = json.loads(path.read_text())
    return found


def main(
    argv: Sequence[str],
    say: Callable[[str], object] = print,
    named: dict[str, dict[str, Any]] | None = None,
) -> int:
    if len(argv) < 2:
        say("usage: against_cartridges.py <directory of cartridges> <output directory>")
        return 2

    source, out = Path(argv[0]), Path(argv[1])
    if not source.is_dir():
        say(f"  no such directory: {source}")
        return 2

    catalogue = published() if named is None else named
    rows = []
    together: collections.Counter[int] = collections.Counter()
    for path in sorted(source.rglob("*")):
        if path.suffix.lower() not in SUFFIXES or not path.is_file():
            continue
        image = path.read_bytes()
        if confirmed(image, catalogue) is None:
            continue
        if not carries_the_part(image):
            continue
        found = reached(image)
        together.update(found)
        rows.append(
            {
                "name": path.name,
                "title": image[HEADER_AT : HEADER_AT + TITLE_BYTES]
                .decode("shift_jis", "replace")
                .strip("\x00 "),
                "bytes": len(image),
                "layout": "lorom",
                "chipset": f"{CHIPSET:#04x}",
                **digests_of(image),
                **{"confirmed": " ".join(compare(found)["confirmed"])},
            }
        )

    if not rows:
        say(f"  no cartridge carrying this part was found under {source}")
        return 2

    written: dict[str, Any] = {
        "note": (
            "Which addresses inside the part's window the cartridges' own driver "
            "routines reach, read out of their code without running any of it. This "
            "is the cartridge saying where the registers are rather than an emulator "
            "saying it. No cartridge byte is recorded here."
        ),
        "producedBy": "https://github.com/gufranco/snes-driver-python",
        "readFrom": sorted(rows, key=lambda row: str(row["name"])),
        "reached": {f"{at:#06x}": count for at, count in sorted(together.items())},
        **compare(dict(together)),
    }
    (out / RECORDED).write_text(json.dumps(written, indent=2) + "\n")

    say(
        f"  {len(rows)} cartridges read; {len(written['confirmed'])} of"
        f" {len(declared())} registers reached, and {len(written['asMemory'])} further"
        " addresses the model treats as memory"
    )
    return 0 if written["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
