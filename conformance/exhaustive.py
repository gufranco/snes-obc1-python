"""Settle the chip against its own reference, in every state it has.

This chip is small enough that there is no need to sample it. Its state is a
base, one of two, and a pointer, one of a hundred and twenty eight, with a shift
the pointer already decides. Every combination is reachable in a few writes, so
every combination is visited.

For each of them the walk writes through each of the five window addresses and
reads each one back, then dumps all eight kilobytes and compares them byte for
byte against the reference. That covers both halves of the remapping: where a
value lands, and what a read of the same address hands back afterwards.

The reset is walked separately, because it is the part most likely to be modelled
wrong. It looks like it recovers the base and pointer from memory, and it does
not: it sets every byte first and then reads the bytes it just wrote, so it
always comes up the same way. The walk leaves memory in a chosen state, resets,
and confirms both sides ignore what was there.

Usage:
    python3 conformance/exhaustive.py [--driver PATH]
"""

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesobc1 import chip

USAGE = "usage: exhaustive.py [--driver PATH]"

DEFAULT_DRIVER = str(Path(__file__).resolve().parent / "ref" / "driver")

DRIVER_TIMEOUT = 600

WINDOW_REGISTERS = (0x7FF0, 0x7FF1, 0x7FF2, 0x7FF3, 0x7FF4)

BASE_VALUES = (0x00, 0x01)

POINTERS = range(0x80)

WRITTEN = (0x00, 0x55, 0xAA, 0xFF)

RECOVERED_POINTERS = (0x00, 0x01, 0x42, 0x7F, 0xFF)

BARE = ("reset", "dump", "state")


class Usage(Exception):
    pass


class Options:
    def __init__(self, driver: Path | str = DEFAULT_DRIVER) -> None:
        self.driver = driver


def walk() -> list[tuple[str, int, int]]:
    """Every base and pointer the chip has, with each window address exercised."""
    steps = [("reset", 0, 0)]
    for base in BASE_VALUES:
        steps.append(("w", chip.BASE_REGISTER, base))
        for pointer in POINTERS:
            steps.append(("w", chip.POINTER_REGISTER, pointer))
            for index, register in enumerate(WINDOW_REGISTERS):
                steps.append(("w", register, WRITTEN[index % len(WRITTEN)]))
                steps.append(("r", register, 0))
            steps.append(("state", 0, 0))
    steps.append(("dump", 0, 0))
    return steps


def resetting() -> list[tuple[str, int, int]]:
    """The reset, which ignores whatever the cartridge held."""
    steps = []
    for base in BASE_VALUES:
        for pointer in RECOVERED_POINTERS:
            steps.append(("poke", chip.BASE_REGISTER - chip.WINDOW_START, base))
            steps.append(("poke", chip.POINTER_REGISTER - chip.WINDOW_START, pointer))
            steps.append(("reset", 0, 0))
            steps.append(("state", 0, 0))
            steps.append(("r", chip.WINDOW_START, 0))
    return steps


def render(steps: Sequence[tuple[str, int, int]]) -> str:
    """The steps as the driver reads them, one to a line."""
    lines = []
    for verb, first, second in steps:
        if verb in BARE:
            lines.append(verb)
        elif verb == "r":
            lines.append(f"r {first}")
        else:
            lines.append(f"{verb} {first} {second}")
    return "\n".join(lines) + "\n"


def replay(steps: Sequence[tuple[str, int, int]]) -> list[str]:
    """The same steps through the model, producing the same shape of transcript."""
    found = chip.Chip()
    transcript = []
    for verb, first, second in steps:
        if verb == "reset":
            found.reset()
        elif verb == "poke":
            found.ram[first] = second & 0xFF
        elif verb == "w":
            found.write(first, second)
        elif verb == "r":
            transcript.append(f"{found.read(first):02X}")
        elif verb == "state":
            transcript.append(f"{found.base:04X} {found.address:04X} {found.shift:04X}")
        else:
            transcript.append("".join(f"{value:02X}" for value in found.ram))
    return transcript


def ask(steps: Sequence[tuple[str, int, int]], driver: Path | str) -> list[str]:
    """The same steps through the reference, whose answers decide."""
    done = subprocess.run(
        [driver],
        input=render(steps),
        capture_output=True,
        text=True,
        check=False,
        timeout=DRIVER_TIMEOUT,
    )
    if done.returncode:
        raise Usage(f"the reference driver failed: {done.stderr.strip()}")
    return done.stdout.splitlines()


def differences(
    expected: Sequence[str], actual: Sequence[str]
) -> list[tuple[int, str | None, str | None]]:
    """Where the two transcripts stop agreeing, by line."""
    found = []
    for index in range(max(len(expected), len(actual))):
        theirs = expected[index] if index < len(expected) else None
        ours = actual[index] if index < len(actual) else None
        if theirs != ours:
            found.append((index, theirs, ours))
    return found


def options(argv: Sequence[str]) -> "Options":
    chosen = Options()
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item != "--driver":
            raise Usage(USAGE)
        if not rest:
            raise Usage(USAGE)
        chosen.driver = rest.pop(0)
    return chosen


def run(argv: Sequence[str]) -> int:
    chosen = options(argv)
    if not Path(chosen.driver).exists():
        print(f"no reference driver at {chosen.driver}; build it first")
        return 2

    failed = 0
    checked = 0
    for name, steps in (("every state", walk()), ("the reset", resetting())):
        found = differences(ask(steps, chosen.driver), replay(steps))
        checked += len(steps)
        if not found:
            print(f"  {name}: {len(steps):,} steps agreed")
            continue
        failed += 1
        index, theirs, ours = found[0]
        print(f"  {name}: {len(found)} disagreements, first at line {index}")
        print(f"    reference {theirs}")
        print(f"    model     {ours}")

    print(f"{checked:,} steps, {failed} walks disagreed")
    return 1 if failed else 0


def main(argv: Sequence[str]) -> int:
    try:
        return run(argv)
    except Usage as error:
        print(error)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
