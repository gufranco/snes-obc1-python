import importlib
import json
import re
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any, NoReturn, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesobc1 import chip, doctor


class Complaint(Exception):
    pass


def a_finding(
    name: str = "something", ok: bool = True, detail: str = "detail", advice: str | None = None
) -> Any:
    return doctor.Finding(name, ok, detail, advice)


def a_pin(name: str = "snes9x", commit: str = "2971061", source: str = "obc1.cpp") -> Path:
    where = Path(tempfile.mkdtemp()) / "pinned.json"
    where.write_text(json.dumps({"reference": {"name": name, "commit": commit, "source": source}}))
    return where


class FindingTest(unittest.TestCase):
    def test_a_finding_says_what_was_checked(self) -> None:
        self.assertEqual(a_finding(name="the window").name, "the window")

    def test_and_whether_it_was_well(self) -> None:
        self.assertTrue(a_finding(ok=True).ok)
        self.assertFalse(a_finding(ok=False).ok)

    def test_a_healthy_finding_prints_with_a_mark_that_says_so(self) -> None:
        self.assertIn("ok", a_finding(ok=True).line)

    def test_and_an_unhealthy_one_prints_differently(self) -> None:
        self.assertNotIn("ok", a_finding(ok=False).line)

    def test_every_finding_carries_what_it_actually_saw(self) -> None:
        self.assertIn("8192 bytes", a_finding(detail="8192 bytes").line)

    def test_an_unhealthy_finding_says_what_to_do_about_it(self) -> None:
        self.assertIn("go and look", a_finding(ok=False, advice="go and look").report)

    def test_a_healthy_one_carries_no_advice(self) -> None:
        self.assertEqual(a_finding(ok=True, advice="x").report, a_finding(ok=True).line)

    def test_a_finding_prints_as_itself(self) -> None:
        self.assertIn("something", repr(a_finding()))


class ExamineTest(unittest.TestCase):
    def test_the_examination_produces_findings(self) -> None:
        self.assertTrue(doctor.examine())

    def test_it_reports_the_python_it_is_running_on(self) -> None:
        self.assertIn("python", [one.name for one in doctor.examine()])

    def test_and_the_version_of_this_package(self) -> None:
        self.assertIn("snesobc1", [one.name for one in doctor.examine()])

    def test_and_the_chip_itself(self) -> None:
        self.assertIn("obc1", [one.name for one in doctor.examine()])

    def test_every_finding_carries_a_detail(self) -> None:
        for one in doctor.examine():
            self.assertTrue(one.detail, one.name)

    def test_a_chip_that_will_not_build_is_reported_rather_than_hidden(self) -> None:
        def boom() -> Any:
            raise Complaint("the chip exploded")

        self.assertTrue(any(not one.ok for one in doctor.examine(build=boom)))

    def test_and_the_report_carries_what_it_said_and_what_kind(self) -> None:
        def boom() -> Any:
            raise Complaint("the chip exploded")

        text = "\n".join(one.report for one in doctor.examine(build=boom))

        self.assertIn("the chip exploded", text)
        self.assertIn("Complaint", text)

    def test_the_chip_is_reported_with_the_window_it_answers(self) -> None:
        for one in doctor.examine():
            if one.name == "obc1":
                self.assertIn("0x6000", one.detail)

    def test_and_with_the_base_the_reset_derived(self) -> None:
        """Driven rather than described, so a reset that stopped deriving shows here."""
        found = [one for one in doctor.examine() if one.name == "obc1"]

        self.assertIn("resets to base 0x", found[0].detail)

    def test_a_chip_that_builds_and_will_not_reset_is_reported_as_broken(self) -> None:
        class WillNotReset(chip.Chip):
            @override
            def reset(self) -> NoReturn:
                raise Complaint("the line did nothing")

        found = [one for one in doctor.examine(build=WillNotReset) if one.name == "obc1"]

        self.assertFalse(found[0].ok)


class WindowTest(unittest.TestCase):
    """That the window is exercised here rather than assumed to be wired."""

    def test_the_report_says_what_the_window_did(self) -> None:
        self.assertIn("window", [one.name for one in doctor.examine()])

    def test_a_write_through_the_window_lands_where_the_pointer_says(self) -> None:
        for one in doctor.examine():
            if one.name == "window":
                self.assertTrue(one.ok)

    def test_a_chip_that_puts_it_somewhere_else_is_a_failure(self) -> None:
        class Wrong:
            ram = bytearray(chip.RAM_BYTES)

            def write(self, _address: int, _value: int) -> None:
                return None

        found = doctor._window(Wrong)

        self.assertFalse(found.ok)

    def test_a_window_that_throws_is_reported_rather_than_swallowed(self) -> None:
        def boom() -> Any:
            raise Complaint("no window at all")

        found = doctor._window(boom)

        self.assertFalse(found.ok)
        self.assertIn("no window at all", found.detail)

    def test_an_address_outside_the_window_is_refused(self) -> None:
        self.assertIn("refuses", " ".join(one.detail for one in doctor.examine()))

    def test_a_chip_that_answers_outside_its_window_is_a_failure(self) -> None:
        class TooKind:
            @staticmethod
            def read(_address: int) -> int:
                return 0

        found = doctor._outside(TooKind)

        self.assertFalse(found.ok)


class PinTest(unittest.TestCase):
    def test_the_reference_it_is_held_to_is_named(self) -> None:
        found = doctor.examine(pin=a_pin(name="somebody else"))

        self.assertIn("somebody else", " ".join(one.detail for one in found))

    def test_and_the_commit_it_is_pinned_to(self) -> None:
        found = doctor.examine(pin=a_pin(commit="deadbeef"))

        self.assertIn("deadbeef", " ".join(one.detail for one in found))

    def test_and_the_digest_of_the_file_that_says_so(self) -> None:
        import hashlib

        where = a_pin()

        found = doctor.examine(pin=where)

        self.assertIn(
            hashlib.sha256(where.read_bytes()).hexdigest(), " ".join(one.detail for one in found)
        )

    def test_a_pin_that_is_not_here_is_a_failure(self) -> None:
        found = doctor.examine(pin=Path("/nowhere/at/all.json"))

        self.assertTrue(any(one.name == "reference" and not one.ok for one in found))

    def test_a_pin_that_is_here_and_damaged_says_so(self) -> None:
        where = Path(tempfile.mkdtemp()) / "pinned.json"
        where.write_text("{ not json at all")

        found = doctor.examine(pin=where)

        self.assertIn("not readable as JSON", " ".join(one.detail for one in found))

    def test_a_pin_that_names_nothing_is_a_failure(self) -> None:
        where = Path(tempfile.mkdtemp()) / "pinned.json"
        where.write_text(json.dumps({}))

        found = doctor.examine(pin=where)

        self.assertTrue(any(one.name == "reference" and not one.ok for one in found))

    def test_the_pin_it_reads_by_default_is_the_one_in_this_repository(self) -> None:
        self.assertTrue(doctor.PIN.exists())


class DriverTest(unittest.TestCase):
    def test_a_driver_that_is_built_is_reported_as_here(self) -> None:
        where = Path(tempfile.mkdtemp()) / "driver"
        where.write_bytes(b"not really a driver")

        self.assertIn(
            "built and here", " ".join(one.detail for one in doctor.examine(driver=where))
        )

    def test_one_that_is_not_built_says_what_will_skip(self) -> None:
        found = doctor.examine(driver=Path("/nowhere/at/all"))

        self.assertIn("skip", " ".join(one.detail for one in found))

    def test_and_that_is_not_treated_as_a_failure(self) -> None:
        for one in doctor.examine(driver=Path("/nowhere/at/all")):
            if one.name == "reference driver":
                self.assertTrue(one.ok)


class ReportTest(unittest.TestCase):
    def test_the_report_has_a_line_for_every_finding(self) -> None:
        found = doctor.examine()

        self.assertGreaterEqual(len(doctor.report(found)), len(found))

    def test_it_opens_with_something_that_says_what_it_is(self) -> None:
        self.assertIn("snesobc1", doctor.report(doctor.examine())[0])

    def test_an_unhealthy_run_says_how_many_did_not_pass(self) -> None:
        self.assertIn("1", " ".join(doctor.report([a_finding(ok=False)])))

    def test_a_healthy_run_says_there_is_nothing_to_report(self) -> None:
        self.assertIn("nothing to report", " ".join(doctor.report([a_finding(ok=True)])))


class EntryTest(unittest.TestCase):
    def test_a_healthy_run_reports_success(self) -> None:
        self.assertEqual(
            doctor.main([], examine=lambda **_: [a_finding(ok=True)], say=lambda _: None), 0
        )

    def test_an_unhealthy_one_reports_failure(self) -> None:
        self.assertEqual(
            doctor.main([], examine=lambda **_: [a_finding(ok=False)], say=lambda _: None), 1
        )

    def test_the_report_is_printed_rather_than_kept(self) -> None:
        said: list[str] = []

        doctor.main([], examine=lambda **_: [a_finding(ok=True)], say=said.append)

        self.assertTrue(said)

    def test_a_real_run_says_something_about_this_machine(self) -> None:
        said: list[str] = []

        doctor.main([], say=said.append)

        self.assertIn("snesobc1", " ".join(said))


class PathTest(unittest.TestCase):
    """That the doctor puts the repository on the path when nothing else has.

    Run as a file it has no package to be relative to, so it inserts the
    repository itself. Under the test suite the path is already set, so the line
    never runs and nothing would report it broken.
    """

    def test_the_repository_is_put_on_the_path_when_it_is_not_already_there(self) -> None:
        held = [one for one in sys.path if one != str(doctor.ROOT)]

        with unittest.mock.patch.object(sys, "path", held):
            importlib.reload(doctor)

            self.assertIn(str(doctor.ROOT), held)

    def test_the_version_is_read_out_of_the_file_rather_than_imported(self) -> None:
        found = re.search(
            r'VERSION[^"\']*"([^"]+)"', (doctor.ROOT / "snesobc1" / "version.py").read_text()
        )
        assert found is not None

        self.assertEqual(doctor.VERSION, found.group(1))

    def test_a_version_file_naming_nothing_reads_as_unknown(self) -> None:
        where = Path(tempfile.mkdtemp()) / "version.py"
        where.write_text("NOTHING = 1\n")

        self.assertEqual(doctor._version(where), "unknown")


if __name__ == "__main__":
    unittest.main()
