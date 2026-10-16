import hashlib
import json
import platform
import re
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, override


def _version(where: Path | None = None) -> str:
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


ROOT = Path(__file__).resolve().parent.parent


def _reachable(root: Path = ROOT, path: list[str] | None = None) -> bool:
    where = sys.path if path is None else path
    if str(root) in where:
        return False
    where.insert(0, str(root))
    return True


_reachable()

from snesobc1 import environment  # noqa: E402

VERSION = _version()

from snesobc1 import chip  # noqa: E402
from snesobc1.errors import OutOfRange  # noqa: E402

PIN = ROOT / "conformance" / "pinned.json"

DRIVER = ROOT / "conformance" / "ref" / "driver"

OLDEST_PYTHON = (3, 12)

WRITTEN = 0xA5

POINTED_AT = 0x02


class Finding:
    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _python() -> "Finding":
    return Finding(
        "python",
        sys.version_info[:2] >= OLDEST_PYTHON,
        f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _package() -> "Finding":
    return Finding("snesobc1", True, f"version {VERSION}")


def _chip(build: Callable[[], Any]) -> "Finding":
    try:
        one = build()
        one.reset()
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
        f" {len(one.ram)} bytes behind it, resets to base {one.base:#06x}",
    )


def _window(build: Callable[[], Any]) -> "Finding":
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


def _outside(build: Callable[[], Any]) -> "Finding":
    try:
        build().read(chip.WINDOW_END)
    except OutOfRange:
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


def _reference(where: Path | str) -> "Finding":
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


def _driver(where: Path | str) -> "Finding":
    found = Path(where).exists()
    return Finding(
        "reference driver",
        True,
        "built and here"
        if found
        else "not built, so the exhaustive check will skip rather than run",
    )


def _default_build() -> Any:
    return chip.Chip()


def examine(
    build: Callable[[], Any] = _default_build,
    pin: Path | str = PIN,
    driver: Path | str = DRIVER,
) -> list["Finding"]:
    return [
        _python(),
        _package(),
        _chip(build),
        _window(build),
        _outside(build),
        _reference(pin),
        _driver(driver),
    ]


def report(found: list["Finding"]) -> list[str]:
    unwell = [one for one in found if not one.ok]
    lines = [f"snesobc1 {VERSION} on {platform.python_version()}, {platform.system()}", ""]
    lines.append("  the machine")
    lines.extend(environment.lines(ROOT))
    lines.append("")
    lines.append("  this package")
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(
    argv: Sequence[str] = (),
    examine: Callable[..., list["Finding"]] = examine,
    say: Callable[[str], None] = print,
) -> int:
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
