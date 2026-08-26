"""Read the register set out of the cartridge, rather than out of an emulator.

Every address this package models came from one reference implementation, which
is the weakest thing in the whole repository: nobody has a datasheet, one
cartridge carries the part, and the reference was written by somebody reading
that cartridge. Agreement with it is agreement with one reading.

There is a second reading available, and it is the cartridge itself. Its driver
routine is ordinary 65816 code, and `snes-driver-python` walks it without running
anything, reporting which addresses inside the part's window each routine
touches. Where those addresses land is the cartridge saying where the registers
are.

**What this establishes and what it does not.** It confirms that the addresses
the model treats as registers are addresses the one program that ever drove this
part actually reaches. It says nothing about what any register does; that still
rests on the reference, and the open questions say so. It also cannot say that an
address the model treats as memory is not really a register, because a game is
free to use the memory and does.

**Only long addressing is visible.** The walk follows instructions that carry
their whole address, so a routine that sets the data bank once and then uses
short addressing is invisible to it. That is why a register can go unreached
without anything being wrong: absence here is absence of evidence.

**What is recorded.** Which addresses were reached and how often, with the name,
length and four digests of each cartridge. No cartridge byte is carried here.

Usage:
    python3 conformance/against_cartridges.py <directory of cartridges> <output directory>
"""

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
"""The chipset byte the one cartridge declares."""

SUFFIXES = (".sfc", ".smc")


def declared() -> tuple[int, ...]:
    """Every address this package treats as a register rather than as memory."""
    return (
        *range(chip.FIRST_REGISTER, chip.PACKED_REGISTER),
        chip.PACKED_REGISTER,
        chip.BASE_REGISTER,
        chip.POINTER_REGISTER,
    )


def digests_of(image: bytes) -> dict[str, str]:
    """The four a manifest publishes, so a reader can cross-check any of them."""
    return {
        "crc32": f"{zlib.crc32(image):08x}",
        "md5": hashlib.md5(image).hexdigest(),
        "sha1": hashlib.sha1(image).hexdigest(),
        "sha256": hashlib.sha256(image).hexdigest(),
    }


def carries_the_part(image: bytes) -> bool:
    """Whether the cartridge declares the chipset this part ships under."""
    if len(image) < HEADER_AT + 32:
        return False
    return image[HEADER_AT + 22] == CHIPSET and 0x20 <= image[HEADER_AT + 21] <= 0x3F


def reached(image: bytes) -> dict[int, int]:
    """Every address inside the part's window the cartridge's own code touches."""
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
    """Which registers the cartridge reaches, and what else it reaches.

    An address in the window that the model treats as memory is not a
    disagreement: the part answers with eight kilobytes of memory there and a
    game is free to use it. It is reported so a reader can see that the walk did
    not simply hit everything, and because an address next to the register file
    is worth a second look rather than a shrug.
    """
    known = set(declared())
    return {
        "confirmed": [f"{at:#06x}" for at in sorted(set(found) & known)],
        "asMemory": [f"{at:#06x}" for at in sorted(set(found) - known)],
        "unreached": [f"{at:#06x}" for at in sorted(known - set(found))],
    }


def recorded(where: Path | str | None = None) -> dict[str, Any]:
    """The reading this repository carries, or nothing if it is not there."""
    path = Path(where) if where is not None else ROOT / RECORDED
    if not path.is_file():
        return {}
    found: dict[str, Any] = json.loads(path.read_text())
    return found


def main(argv: Sequence[str], say: Callable[[str], object] = print) -> int:
    if len(argv) < 2:
        say("usage: against_cartridges.py <directory of cartridges> <output directory>")
        return 2

    source, out = Path(argv[0]), Path(argv[1])
    if not source.is_dir():
        say(f"  no such directory: {source}")
        return 2

    rows = []
    together: collections.Counter[int] = collections.Counter()
    for path in sorted(source.rglob("*")):
        if path.suffix.lower() not in SUFFIXES or not path.is_file():
            continue
        image = path.read_bytes()
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
        "readFrom": rows,
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
