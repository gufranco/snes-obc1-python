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

DRIVER = Path(__file__).resolve().parent.parent / "snes-driver-python"

TRACED_CORPUS = DRIVER / "conformance" / "traced.json"

ASSUMED_WIDTH = 1

LAYOUT = "lorom"


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


def touched(address: int, width: int) -> list[int]:
    return [at for at in range(address, address + width) if at >= chip.FIRST_REGISTER]


def driver() -> Any:
    for where in (DRIVER, DRIVER / "mos65xx-python", DRIVER / "snes-mapper-python"):
        if str(where) not in sys.path:
            sys.path.insert(0, str(where))
    import snesdriver

    return snesdriver


def marks() -> dict[str, str]:
    conversation = driver().conversation
    return {
        "known": "",
        "executed": conversation.RAN,
        "traced": conversation.TRACED,
        "assumed": conversation.UNKNOWN,
    }


MARKS = marks()


def label_of(step: Any) -> str:
    if step.width is None:
        return "assumed"
    if step.traced:
        return "traced"
    return "executed" if step.ran else "known"


def traced_widths(digest: str, path: Path = TRACED_CORPUS) -> dict[int, int]:
    held = json.loads(path.read_text())["cartridges"].get(digest)
    if held is None:
        return {}
    return {
        int(site["offset"], 16): int(site["widths"][0])
        for site in held["sites"]
        if len(site["widths"]) == 1 and not site["disputed"]
    }


class Reading:
    __slots__ = ("assumed", "by_address", "counted", "labels")

    def __init__(self) -> None:
        self.counted: dict[int, int] = {}
        self.labels = dict.fromkeys(MARKS, 0)
        self.assumed: list[int] = []
        self.by_address: dict[int, set[str]] = {}


def walks(image: bytes, window: Any, traced: dict[int, int]) -> list[tuple[int, Any]]:
    snesdriver = driver()
    known = snesdriver.widths(image, LAYOUT)
    conversation = snesdriver.conversation
    found: list[tuple[int, Any]] = []
    seen: set[int] = set()
    for site in conversation.sites(image, window):
        if site in seen:
            continue
        for (wide, index), told in conversation.starts(site, None, known, {}):
            arms = conversation.every(
                image, site, window, wide, index=index, known=known, ran=told, traced=traced
            )
            seen.update(arms.covered)
            found.extend((site, talk) for talk in arms.conversations)
    return found


def read(image: bytes, traced: dict[int, int] | None = None) -> Reading:
    window = driver().window_for("obc1", LAYOUT)
    assert window is not None, "the driver knows no window for this part"
    reading = Reading()
    counted: collections.Counter[int] = collections.Counter()
    assumed: set[int] = set()
    for site, talk in walks(image, window, traced or {}):
        for step in talk.steps:
            label = label_of(step)
            reading.labels[label] += 1
            reaches = touched(step.address, step.width or ASSUMED_WIDTH)
            counted.update(reaches)
            for at in reaches:
                reading.by_address.setdefault(at, set()).add(label)
            assumed |= {site} if label == "assumed" else set()
    reading.counted = dict(counted)
    reading.assumed = sorted(assumed)
    return reading


def reached(image: bytes) -> dict[int, int]:
    return read(image).counted


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
    labels: collections.Counter[str] = collections.Counter(dict.fromkeys(MARKS, 0))
    by_address: dict[int, set[str]] = {}
    for path in sorted(source.rglob("*")):
        if path.suffix.lower() not in SUFFIXES or not path.is_file():
            continue
        image = path.read_bytes()
        if confirmed(image, catalogue) is None:
            continue
        if not carries_the_part(image):
            continue
        reading = read(image, traced_widths(digests_of(image)["sha256"]))
        found = reading.counted
        together.update(found)
        labels.update(reading.labels)
        for at, held in reading.by_address.items():
            by_address.setdefault(at, set()).update(held)
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
                "confirmed": " ".join(compare(found)["confirmed"]),
                "accesses": reading.labels,
                "assumedAt": [f"{at:#08x}" for at in reading.assumed],
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
            "saying it. Every access carries one label: known where the code sets its "
            "width, executed where a run of the image used it, traced where a headless "
            "MAME run saw the bus move it at that instruction, and assumed where none "
            "of those says, in which case it is replayed as one byte. assumedAt names "
            "the sites whose walk rests on an assumed width. No cartridge byte is "
            "recorded here."
        ),
        "producedBy": "https://github.com/gufranco/snes-driver-python",
        "readFrom": sorted(rows, key=lambda row: str(row["name"])),
        "reached": {f"{at:#06x}": count for at, count in sorted(together.items())},
        "accesses": dict(labels),
        "labelsByAddress": {f"{at:#06x}": sorted(held) for at, held in sorted(by_address.items())},
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
