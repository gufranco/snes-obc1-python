import hashlib
import importlib
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any, NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesobc1
from snesobc1 import doctor

RAM_BYTES = 0x2000

NOWHERE = Path("/nowhere/at/all")


class Complaint(Exception):
    pass


def a_pin(name: str = "snes9x", commit: str = "2971061", source: str = "obc1.cpp") -> Path:
    where = Path(tempfile.mkdtemp()) / "pinned.json"
    where.write_text(json.dumps({"reference": {"name": name, "commit": commit, "source": source}}))
    return where


def a_file(body: str, name: str = "pinned.json") -> Path:
    where = Path(tempfile.mkdtemp()) / name
    where.write_text(body)
    return where


def a_chip() -> Any:
    return snesobc1.Chip("obc1")


def boom() -> NoReturn:
    raise Complaint("the chip exploded")


class WillNotReset:
    def reset(self) -> NoReturn:
        raise Complaint("the line did nothing")


class WritesNowhere:
    ram = bytearray(RAM_BYTES)
    base = 0

    def write(self, _address: int, _value: int) -> None:
        return None


class TooKind:
    @staticmethod
    def read(_address: int) -> int:
        return 0


class RefusesWrongly:
    @staticmethod
    def read(_address: int) -> int:
        raise Complaint("not the refusal the package publishes")


class ExamineTest(unittest.TestCase):
    def test_the_examination_names_every_check_it_made(self) -> None:
        # Arrange
        driver = NOWHERE

        # Act
        found = doctor.examine(driver=driver)

        # Assert
        self.assertEqual(
            [one.name for one in found],
            [
                "python",
                "snesobc1",
                "obc1",
                "window",
                "outside the window",
                "reference",
                "reference driver",
            ],
        )

    def test_every_finding_carries_a_detail(self) -> None:
        # Arrange
        driver = NOWHERE

        # Act
        bare = [one.name for one in doctor.examine(driver=driver) if not one.detail]

        # Assert
        self.assertEqual(bare, [])

    def test_the_python_it_runs_on_passes(self) -> None:
        # Arrange
        expected = True

        # Act
        found = doctor.check_python()

        # Assert
        self.assertEqual(found.ok, expected)

    def test_the_package_reports_the_version_it_read(self) -> None:
        # Arrange
        expected = f"version {doctor.VERSION}"

        # Act
        found = doctor.check_package()

        # Assert
        self.assertEqual(found.detail, expected)

    def test_the_chip_is_reported_with_its_window_its_memory_and_its_base(self) -> None:
        # Arrange
        build = a_chip

        # Act
        found = doctor.check_chip(build)

        # Assert
        self.assertEqual(
            (found.ok, found.detail),
            (True, "answers 0x6000 to 0x7fff, 8192 bytes behind it, resets to base 0x1800"),
        )

    def test_a_chip_that_will_not_build_is_reported_with_what_it_said(self) -> None:
        # Arrange
        build = boom

        # Act
        found = doctor.check_chip(build)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "Complaint: the chip exploded"))

    def test_a_chip_that_builds_and_will_not_reset_is_reported_as_broken(self) -> None:
        # Arrange
        build = WillNotReset

        # Act
        found = doctor.check_chip(build)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "Complaint: the line did nothing"))


class WindowTest(unittest.TestCase):
    def test_a_write_through_the_window_lands_where_the_pointer_says(self) -> None:
        # Arrange
        build = a_chip

        # Act
        found = doctor.check_window(build)

        # Assert
        self.assertEqual(
            (found.ok, found.detail),
            (True, "a write through 0x7ff0 with the pointer at 2 landed 0xa5"),
        )

    def test_a_chip_that_puts_it_somewhere_else_is_a_failure(self) -> None:
        # Arrange
        build = WritesNowhere

        # Act
        found = doctor.check_window(build)

        # Assert
        self.assertEqual(
            (found.ok, found.detail),
            (False, "a write through 0x7ff0 with the pointer at 2 landed 0x00"),
        )

    def test_a_window_that_throws_is_reported_rather_than_swallowed(self) -> None:
        # Arrange
        build = boom

        # Act
        found = doctor.check_window(build)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "Complaint: the chip exploded"))

    def test_an_address_outside_the_window_is_refused(self) -> None:
        # Arrange
        build = a_chip

        # Act
        found = doctor.check_outside(build)

        # Assert
        self.assertEqual((found.ok, found.detail), (True, "refuses 0x8000"))

    def test_a_chip_that_answers_outside_its_window_is_a_failure(self) -> None:
        # Arrange
        build = TooKind

        # Act
        found = doctor.check_outside(build)

        # Assert
        self.assertEqual(
            (found.ok, found.detail), (False, "answered 0x8000, which is not an address it drives")
        )

    def test_a_chip_that_refuses_with_the_wrong_error_is_a_failure(self) -> None:
        # Arrange
        build = RefusesWrongly

        # Act
        found = doctor.check_outside(build)

        # Assert
        self.assertEqual(
            (found.ok, found.detail), (False, "Complaint: not the refusal the package publishes")
        )


class PinTest(unittest.TestCase):
    def test_the_reference_is_named_with_its_commit_its_file_and_the_digest_of_the_pin(
        self,
    ) -> None:
        # Arrange
        where = a_pin(name="somebody else", commit="deadbeef")
        digest = hashlib.sha256(where.read_bytes()).hexdigest()

        # Act
        found = doctor.check_reference(where)

        # Assert
        self.assertEqual(
            (found.ok, found.detail),
            (True, f"somebody else at deadbeef, obc1.cpp, sha256 {digest}"),
        )

    def test_a_pin_missing_a_field_says_which(self) -> None:
        # Arrange
        where = a_file(json.dumps({"reference": {"name": "snes9x"}}))

        # Act
        found = doctor.check_reference(where)

        # Assert
        self.assertIn("snes9x at no commit, no file", found.detail)

    def test_a_pin_that_is_not_here_is_a_failure(self) -> None:
        # Arrange
        where = NOWHERE / "pinned.json"

        # Act
        found = doctor.check_reference(where)

        # Assert
        self.assertEqual((found.ok, found.detail.startswith("could not be read: ")), (False, True))

    def test_a_pin_that_is_here_and_damaged_says_so(self) -> None:
        # Arrange
        where = a_file("{ not json at all")

        # Act
        found = doctor.check_reference(where)

        # Assert
        self.assertEqual(
            (found.ok, found.detail.startswith("is not readable as JSON: ")), (False, True)
        )

    def test_a_pin_that_names_nothing_is_a_failure(self) -> None:
        # Arrange
        where = a_file(json.dumps({}))

        # Act
        found = doctor.check_reference(where)

        # Assert
        self.assertEqual(
            (found.ok, found.detail.startswith("names no implementation, sha256 ")), (False, True)
        )

    def test_the_pin_it_reads_by_default_is_the_one_in_this_repository(self) -> None:
        # Arrange
        expected = doctor.ROOT / "conformance" / "pinned.json"

        # Act
        found = doctor.PIN

        # Assert
        self.assertEqual((found, found.is_file()), (expected, True))


class DriverTest(unittest.TestCase):
    def test_a_driver_that_is_built_is_reported_as_here(self) -> None:
        # Arrange
        where = a_file("not really a driver", "driver")

        # Act
        found = doctor.check_driver(where)

        # Assert
        self.assertEqual((found.ok, found.detail), (True, "built and here"))

    def test_one_that_is_not_built_says_what_will_skip_and_is_not_a_failure(self) -> None:
        # Arrange
        where = NOWHERE

        # Act
        found = doctor.check_driver(where)

        # Assert
        self.assertEqual(
            (found.ok, found.detail),
            (True, "not built, so the exhaustive check will skip rather than run"),
        )


class PathTest(unittest.TestCase):
    def test_the_repository_is_put_on_the_path_when_it_is_not_already_there(self) -> None:
        # Arrange
        held = [one for one in sys.path if one != str(doctor.ROOT)]

        # Act
        with unittest.mock.patch.object(sys, "path", held):
            importlib.reload(doctor)

        # Assert
        self.assertIn(str(doctor.ROOT), held)

    def test_the_version_is_read_out_of_the_file_rather_than_imported(self) -> None:
        # Arrange
        where = a_file('VERSION = "9.8.7"\n', "version.py")

        # Act
        found = doctor.installed_version(where)

        # Assert
        self.assertEqual(found, "9.8.7")

    def test_and_by_default_out_of_the_one_beside_the_doctor(self) -> None:
        # Arrange
        held = (doctor.ROOT / "snesobc1" / "version.py").read_text()

        # Act
        found = doctor.installed_version()

        # Assert
        self.assertIn(f'"{found}"', held)

    def test_a_version_file_naming_nothing_reads_as_unknown(self) -> None:
        # Arrange
        where = a_file("NOTHING = 1\n", "version.py")

        # Act
        found = doctor.installed_version(where)

        # Assert
        self.assertEqual(found, "unknown")

    def test_a_root_that_is_not_on_the_path_is_put_there(self) -> None:
        # Arrange
        path: list[str] = []

        # Act
        added = doctor.reachable(Path("/somewhere"), path)

        # Assert
        self.assertEqual((added, path), (True, ["/somewhere"]))

    def test_a_root_already_on_the_path_is_left_alone(self) -> None:
        # Arrange
        path = ["/somewhere"]

        # Act
        added = doctor.reachable(Path("/somewhere"), path)

        # Assert
        self.assertEqual((added, path), (False, ["/somewhere"]))


if __name__ == "__main__":
    unittest.main()
