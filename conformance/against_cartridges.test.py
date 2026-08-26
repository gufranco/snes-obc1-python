"""Reading the register set out of the one cartridge, and holding the model to it."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import against_cartridges as against


def _a_cartridge(body: bytes = b"", title: bytes = b"METAL COMBAT") -> bytes:
    held = bytearray(b"\xea" * 0x200000)
    held[0x200 : 0x200 + len(body)] = body
    held[0x7FC0 : 0x7FC0 + len(title)] = title
    held[0x7FC0 + len(title) : 0x7FD5] = b"\x00" * (0x7FD5 - 0x7FC0 - len(title))
    held[0x7FD5] = 0x30
    held[0x7FD6] = 0x25
    held[0x7FD7] = 0x0B
    return bytes(held)


def _reaching(*addresses: int) -> bytes:
    """A routine that stores to each address in turn and returns."""
    body = bytearray()
    for address in addresses:
        body += bytes((0x8F, address & 0xFF, address >> 8, 0x00))
    body += bytes((0x60,))
    return bytes(body)


class DeclaredTest(unittest.TestCase):
    def test_the_package_names_the_registers_it_models(self) -> None:
        self.assertEqual(
            sorted(against.declared()), [0x7FF0, 0x7FF1, 0x7FF2, 0x7FF3, 0x7FF4, 0x7FF5, 0x7FF6]
        )


class CarriesTest(unittest.TestCase):
    def test_a_cartridge_declaring_this_chipset_carries_the_part(self) -> None:
        self.assertTrue(against.carries_the_part(_a_cartridge()))

    def test_a_file_too_short_to_hold_a_header_does_not(self) -> None:
        self.assertFalse(against.carries_the_part(b"\x00" * 16))

    def test_a_cartridge_declaring_another_chipset_does_not(self) -> None:
        held = bytearray(_a_cartridge())
        held[0x7FD6] = 0x03

        self.assertFalse(against.carries_the_part(bytes(held)))


class ReadTest(unittest.TestCase):
    def test_an_address_a_routine_reaches_comes_back(self) -> None:
        found = against.reached(_a_cartridge(_reaching(0x7FF0)))

        self.assertIn(0x7FF0, found)

    def test_an_address_no_routine_reaches_does_not(self) -> None:
        found = against.reached(_a_cartridge(_reaching(0x7FF0)))

        self.assertNotIn(0x7FF3, found)

    def test_only_addresses_inside_the_window_are_reported(self) -> None:
        found = against.reached(_a_cartridge(_reaching(0x7FF0, 0x2100)))

        self.assertEqual(sorted(found), [0x7FF0])

    def test_a_cartridge_whose_code_reaches_nothing_yields_nothing(self) -> None:
        found = against.reached(_a_cartridge())

        self.assertEqual(found, {})

    def test_how_often_each_address_was_reached_is_counted(self) -> None:
        found = against.reached(_a_cartridge(_reaching(0x7FF0) + _reaching(0x7FF0)))

        self.assertEqual(found[0x7FF0], 2)


class AgreementTest(unittest.TestCase):
    def test_a_cartridge_reaching_only_declared_registers_agrees(self) -> None:
        found = against.compare({0x7FF0: 4, 0x7FF6: 1})

        self.assertEqual(found["asMemory"], [])

    def test_an_address_the_model_treats_as_memory_is_reported_apart(self) -> None:
        found = against.compare({0x7FF0: 4, 0x7FFF: 2})

        self.assertEqual(found["asMemory"], ["0x7fff"])

    def test_a_register_no_routine_reaches_is_reported_apart(self) -> None:
        found = against.compare({0x7FF0: 4})

        self.assertIn("0x7ff4", found["unreached"])

    def test_the_registers_both_agree_on_are_named(self) -> None:
        found = against.compare({0x7FF0: 4, 0x7FF6: 1})

        self.assertEqual(found["confirmed"], ["0x7ff0", "0x7ff6"])


class RecordedTest(unittest.TestCase):
    def test_the_recorded_reading_confirms_six_of_the_seven(self) -> None:
        found = against.recorded()

        self.assertEqual(len(found["confirmed"]), 6)

    def test_it_reaches_a_couple_of_addresses_the_model_treats_as_memory(self) -> None:
        found = against.recorded()

        self.assertEqual(found["asMemory"], ["0x7ff7", "0x7fff"])

    def test_both_releases_were_read(self) -> None:
        found = against.recorded()

        self.assertEqual(len(found["readFrom"]), 2)

    def test_and_they_agree_on_every_register_the_american_one_reaches(self) -> None:
        found = against.recorded()

        american, european = (set(one["confirmed"].split()) for one in found["readFrom"][::-1])

        self.assertEqual(american - european, set())

    def test_every_cartridge_it_names_carries_four_digests(self) -> None:
        found = against.recorded()

        for one in found["readFrom"]:
            self.assertEqual(
                [key for key in ("crc32", "md5", "sha1", "sha256") if key in one],
                ["crc32", "md5", "sha1", "sha256"],
            )

    def test_a_reading_that_is_not_there_reads_as_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            self.assertEqual(against.recorded(Path(where) / "absent.json"), {})


class MainTest(unittest.TestCase):
    def test_with_no_arguments_it_says_how_to_use_it(self) -> None:
        said: list[str] = []

        code = against.main([], say=said.append)

        self.assertEqual((code, "usage" in said[0]), (2, True))

    def test_a_directory_that_is_not_one_is_refused(self) -> None:
        said: list[str] = []

        code = against.main(["/nowhere-at-all", "/tmp"], say=said.append)

        self.assertEqual((code, any("no such" in one for one in said)), (2, True))

    def test_a_directory_holding_no_cartridge_reports_that(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            code = against.main([where, where], say=said.append)

        self.assertEqual((code, any("no cartridge" in one for one in said)), (2, True))

    def test_a_cartridge_it_can_read_is_recorded(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "one.sfc").write_bytes(_a_cartridge(_reaching(0x7FF0, 0x7FF6)))

            code = against.main([where, where], say=said.append)

            self.assertEqual((code, (Path(where) / "cartridges.json").is_file()), (0, True))

    def test_a_cartridge_reaching_no_register_at_all_reports_failure(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "one.sfc").write_bytes(_a_cartridge(_reaching(0x6100)))

            code = against.main([where, where], say=said.append)

        self.assertEqual(code, 1)

    def test_a_file_that_is_not_a_cartridge_at_all_is_skipped(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "notes.txt").write_bytes(b"not a cartridge")
            (Path(where) / "one.sfc").write_bytes(_a_cartridge(_reaching(0x7FF0)))

            code = against.main([where, where], say=said.append)

        self.assertEqual(code, 0)

    def test_a_file_that_is_not_a_cartridge_for_this_part_is_skipped(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            held = bytearray(_a_cartridge(_reaching(0x7FF0)))
            held[0x7FD6] = 0x03
            (Path(where) / "other.sfc").write_bytes(bytes(held))
            (Path(where) / "one.sfc").write_bytes(_a_cartridge(_reaching(0x7FF0)))

            code = against.main([where, where], say=said.append)

            self.assertEqual(
                (code, len(json.loads((Path(where) / "cartridges.json").read_text())["readFrom"])),
                (0, 1),
            )


if __name__ == "__main__":
    unittest.main()
