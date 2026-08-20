"""Look at this machine and say what is actually here, so a report can be believed.

What goes wrong with this package is rarely a defect in it. It is a Python too
old to run it, a reference driver that was never built so the exhaustive check
quietly did nothing, or a disagreement about which reference it is even being
held to. All of those look the same from outside: the bytes land in the wrong
place.

So this looks, and prints what it found in a form that can be pasted into an
issue as it stands.

Two rules shape it, and they are the whole point.

Nothing is hidden. A check that fails says what it saw, and a check that itself
throws is caught and reported as what it threw, named by its type. Swallowing
either would leave a report that says everything is fine on a machine where
something is not, which is worse than no report.

Nothing is inferred. Every line is something looked at on this machine just now,
including a write actually pushed through the window and read back out of memory.
"""

import hashlib
import json
import platform
import sys
from pathlib import Path

from . import chip
from .version import VERSION

ROOT = Path(__file__).resolve().parent.parent

PIN = ROOT / "conformance" / "pinned.json"

DRIVER = ROOT / "conformance" / "ref" / "driver"

OLDEST_PYTHON = (3, 12)

WRITTEN = 0xA5
"""A value with no symmetry, so a byte that landed by accident does not pass for one that landed."""

POINTED_AT = 0x02
"""Where the window is put before the write, chosen so the answer is not offset zero."""


class Finding:
    """One thing that was looked at, and what was there."""

    def __init__(self, name, ok, detail, advice=None):
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self):
        """The one-line form, which is what a reader scans."""
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self):
        """The same, with what to do about it when there is something to do."""
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    def __repr__(self):
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _python():
    return Finding(
        "python",
        sys.version_info[:2] >= OLDEST_PYTHON,
        f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _package():
    return Finding("snesobc1", True, f"version {VERSION}")


def _chip(build):
    """Whether the chip builds, saying exactly what stopped it if not."""
    try:
        one = build()
    except Exception as trouble:
        return Finding(
            "obc1",
            False,
            f"{type(trouble).__name__}: {trouble}",
            "this is the chip failing to build rather than anything to do with a"
            " reference; the line above is what it said",
        )
    return Finding(
        "obc1",
        True,
        f"answers {chip.WINDOW_START:#06x} to {chip.WINDOW_END - 1:#06x},"
        f" {len(one.ram)} bytes behind it, base {one.base:#06x}",
    )


def _window(build):
    """That a write through the window lands where the pointer says it does.

    This is the whole chip in one line, and it is the thing a report is usually
    about. Pointing the window somewhere and writing one byte through it is
    cheap, needs nobody's cartridge, and separates a chip that is wired from one
    that is merely importable.
    """
    try:
        one = build()
        one.write(chip.POINTER_REGISTER, POINTED_AT)
        one.write(chip.FIRST_REGISTER, WRITTEN)
        landed = one.ram[one.base + (POINTED_AT << 2)]
    except Exception as trouble:
        return Finding(
            "window",
            False,
            f"{type(trouble).__name__}: {trouble}",
            "writing through the window failed, which is itself the finding",
        )
    return Finding(
        "window",
        landed == WRITTEN,
        f"a write through {chip.FIRST_REGISTER:#06x} with the pointer at"
        f" {POINTED_AT} landed {landed:#04x}",
        f"it should have landed {WRITTEN:#04x}; the window is pointing somewhere"
        " other than where the pointer says",
    )


def _outside(build):
    """That an address outside the window is refused rather than answered.

    A chip that answers everywhere is the failure that hides: the console reads
    something plausible from an address this part never drove, and nothing
    downstream can tell it apart from a real answer.
    """
    try:
        build().read(chip.WINDOW_END)
    except chip.OutOfRange:
        return Finding("outside the window", True, f"refuses {chip.WINDOW_END:#06x}")
    except Exception as trouble:
        return Finding(
            "outside the window",
            False,
            f"{type(trouble).__name__}: {trouble}",
            "an address past the window should raise OutOfRange; this raised something else",
        )
    return Finding(
        "outside the window",
        False,
        f"answered {chip.WINDOW_END:#06x}, which is not an address it drives",
        "an answer from outside the window cannot be told from a real one",
    )


def _reference(where):
    """Which implementation this is held to, and at which commit.

    Two people comparing against two commits of the same reference will disagree
    and both be right. The digest of the file that pins it is what ends that.
    """
    try:
        raw = Path(where).read_bytes()
    except OSError as trouble:
        return Finding(
            "reference",
            False,
            f"could not be read: {trouble}",
            "the file that pins which implementation this is held to is missing from conformance/",
        )
    digest = hashlib.sha256(raw).hexdigest()
    try:
        held = json.loads(raw)
    except ValueError as trouble:
        return Finding(
            "reference",
            False,
            f"is not readable as JSON: {trouble}, sha256 {digest}",
            "the file is here and damaged, which is worse than absent",
        )
    named = held.get("reference") or {}
    if not named:
        return Finding(
            "reference",
            False,
            f"names no implementation, sha256 {digest}",
            "a pin that names nothing pins nothing",
        )
    return Finding(
        "reference",
        True,
        f"{named.get('name', 'not stated')} at {named.get('commit', 'no commit')},"
        f" {named.get('source', 'no file')}, sha256 {digest}",
    )


def _driver(where):
    """Whether the reference is built, since its absence is silent otherwise.

    The exhaustive check builds somebody else's implementation and asks it every
    address. That build is not needed to use this package, and a machine without
    it is the normal case rather than a broken one. It is reported so that nobody
    reads a run that skipped as a run that passed.
    """
    found = Path(where).exists()
    return Finding(
        "reference driver",
        True,
        "built and here"
        if found
        else "not built, so the exhaustive check will skip rather than run",
    )


def _default_build():
    return chip.Obc1()


def examine(build=_default_build, pin=PIN, driver=DRIVER):
    """Everything worth looking at on this machine, in the order a reader wants it."""
    return [
        _python(),
        _package(),
        _chip(build),
        _window(build),
        _outside(build),
        _reference(pin),
        _driver(driver),
    ]


def report(found):
    """The lines a person pastes into an issue."""
    unwell = [one for one in found if not one.ok]
    lines = [f"snesobc1 {VERSION} on {platform.python_version()}, {platform.system()}", ""]
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(argv=(), examine=examine, say=print):
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
