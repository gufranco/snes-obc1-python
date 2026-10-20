import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

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


def _named(*images: bytes) -> dict[str, dict[str, Any]]:
    return {
        against.digests_of(one)["sha256"]: {
            "name": f"made-up-{at}.sfc",
            **against.digests_of(one),
        }
        for at, one in enumerate(images)
    }


def _reaching(*addresses: int) -> bytes:
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
    def test_a_store_on_a_taken_branch_keeps_the_width_set_before_the_branch(self) -> None:
        # Arrange
        body = bytes(
            (0x8F, 0xF0, 0x7F, 0x00, 0xC2, 0x20, 0xF0, 0x01, 0x60, 0x8F, 0xF3, 0x7F, 0x00, 0x60)
        )

        # Act
        found = against.reached(_a_cartridge(body))

        # Assert
        self.assertEqual(sorted(found), [0x7FF0, 0x7FF3, 0x7FF4])

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

    def test_a_sixteen_bit_store_reaches_the_byte_after_its_address_too(self) -> None:
        # Arrange
        wide = _reaching(0x7FF0)[:-1] + bytes((0xC2, 0x20)) + _reaching(0x7FF3)

        # Act
        found = against.reached(_a_cartridge(wide))

        # Assert
        self.assertEqual(found, {0x7FF0: 1, 0x7FF3: 1, 0x7FF4: 1})

    def test_an_eight_bit_store_reaches_only_its_own_byte(self) -> None:
        # Arrange
        narrow = _reaching(0x7FF0)[:-1] + bytes((0xE2, 0x20)) + _reaching(0x7FF3)

        # Act
        found = against.reached(_a_cartridge(narrow))

        # Assert
        self.assertEqual(found, {0x7FF0: 1, 0x7FF3: 1})

    def test_how_often_each_address_was_reached_is_counted(self) -> None:
        found = against.reached(_a_cartridge(_reaching(0x7FF0) + _reaching(0x7FF0)))

        self.assertEqual(found[0x7FF0], 2)


def _labels(known: int = 0, executed: int = 0, traced: int = 0, assumed: int = 0) -> dict[str, int]:
    return {"known": known, "executed": executed, "traced": traced, "assumed": assumed}


class WidthLabelTest(unittest.TestCase):
    def test_an_access_whose_width_the_code_does_not_set_is_one_byte_and_assumed(self) -> None:
        # Arrange
        image = _a_cartridge(_reaching(0x7FF3))

        # Act
        found = against.read(image)

        # Assert
        self.assertEqual(
            (found.counted, dict(found.labels), found.assumed),
            ({0x7FF3: 1}, _labels(assumed=1), [0x200]),
        )

    def test_an_access_after_the_code_sets_its_width_is_known(self) -> None:
        # Arrange
        image = _a_cartridge(_reaching(0x7FF0)[:-1] + bytes((0xE2, 0x20)) + _reaching(0x7FF3))

        # Act
        found = against.read(image)

        # Assert
        self.assertEqual(
            (dict(found.labels), found.assumed), (_labels(known=1, assumed=1), [0x200])
        )

    def test_a_width_a_trace_saw_settles_the_assumption(self) -> None:
        # Arrange
        image = _a_cartridge(_reaching(0x7FF3))

        # Act
        found = against.read(image, traced={0x200: 2})

        # Assert
        self.assertEqual(
            (found.counted, dict(found.labels), found.assumed),
            ({0x7FF3: 1, 0x7FF4: 1}, _labels(traced=1), []),
        )

    def test_a_width_a_run_used_is_labelled_executed(self) -> None:
        # Arrange
        step = against.driver().conversation.Step("write", 2, 0x7FF3, 0x00, ran=True)

        # Act
        found = against.label_of(step)

        # Assert
        self.assertEqual(found, "executed")

    def test_the_labels_are_the_four_the_driver_marks(self) -> None:
        # Arrange
        driver = against.driver().conversation

        # Act
        found = against.MARKS

        # Assert
        self.assertEqual(
            found,
            {
                "known": "",
                "executed": driver.RAN,
                "traced": driver.TRACED,
                "assumed": driver.UNKNOWN,
            },
        )


class ByAddressTest(unittest.TestCase):
    def test_each_address_names_the_labels_of_the_accesses_that_reached_it(self) -> None:
        # Arrange
        image = _a_cartridge(_reaching(0x7FF0)[:-1] + bytes((0xC2, 0x20)) + _reaching(0x7FF3))

        # Act
        found = against.read(image, traced={0x200: 1})

        # Assert
        self.assertEqual(
            found.by_address,
            {0x7FF0: {"traced"}, 0x7FF3: {"known"}, 0x7FF4: {"known"}},
        )


class TracedCorpusTest(unittest.TestCase):
    def test_a_site_traced_at_one_width_gives_that_width(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "traced.json"
        sites = [
            {"offset": "0x000200", "widths": [2], "disputed": False},
            {"offset": "0x000300", "widths": [1, 2], "disputed": False},
            {"offset": "0x000400", "widths": [1], "disputed": True},
        ]
        path.write_text(json.dumps({"cartridges": {"ab" * 32: {"sites": sites}}}))

        # Act
        found = [against.traced_widths("ab" * 32, path), against.traced_widths("cd" * 32, path)]

        # Assert
        self.assertEqual(found, [{0x200: 2}, {}])

    def test_the_driver_beside_this_one_carries_a_traced_corpus(self) -> None:
        # Arrange
        named = against.published()

        # Act
        found = {digest: against.traced_widths(digest) for digest in named}

        # Assert
        self.assertEqual(len([one for one in found.values() if one]) >= 2, True)


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
    def test_the_recorded_reading_confirms_all_seven(self) -> None:
        # Arrange
        expected = 7

        # Act
        found = against.recorded()

        # Assert
        self.assertEqual(len(found["confirmed"]), expected)

    def test_the_seventh_is_reached_only_through_a_traced_width(self) -> None:
        # Arrange
        found = against.recorded()

        # Act
        labels = found["labelsByAddress"]["0x7ff4"]

        # Assert
        self.assertEqual(labels, ["traced"])

    def test_it_reaches_a_few_addresses_the_model_treats_as_memory(self) -> None:
        # Arrange
        expected = ["0x7ff7", "0x7ffd", "0x7fff"]

        # Act
        found = against.recorded()

        # Assert
        self.assertEqual(found["asMemory"], expected)

    def test_both_releases_were_read(self) -> None:
        found = against.recorded()

        self.assertEqual(len(found["readFrom"]), 2)

    def test_and_they_agree_on_every_register_the_american_one_reaches(self) -> None:
        found = against.recorded()

        by_name = {one["name"]: set(one["confirmed"].split()) for one in found["readFrom"]}
        american = next(one for name, one in by_name.items() if "(USA)" in name)
        european = next(one for name, one in by_name.items() if "(Europe)" in name)

        self.assertEqual(american - european, set())

    def test_every_cartridge_it_names_carries_four_digests(self) -> None:
        found = against.recorded()

        for one in found["readFrom"]:
            self.assertEqual(
                [key for key in ("crc32", "md5", "sha1", "sha256") if key in one],
                ["crc32", "md5", "sha1", "sha256"],
            )

    def test_every_access_it_counted_carries_one_of_the_four_labels(self) -> None:
        # Arrange
        found = against.recorded()

        # Act
        labels = found["accesses"]

        # Assert
        self.assertEqual(sorted(labels), ["assumed", "executed", "known", "traced"])

    def test_each_cartridge_names_the_sites_that_rest_on_an_assumed_width(self) -> None:
        # Arrange
        found = against.recorded()

        # Act
        named = [len(one["assumedAt"]) > 0 for one in found["readFrom"]]

        # Assert
        self.assertEqual(named, [True, True])

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
            image = _a_cartridge(_reaching(0x7FF0, 0x7FF6))
            (Path(where) / "one.sfc").write_bytes(image)

            code = against.main([where, where], say=said.append, named=_named(image))

            self.assertEqual((code, (Path(where) / "cartridges.json").is_file()), (0, True))

    def test_a_cartridge_reaching_no_register_at_all_reports_failure(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            image = _a_cartridge(_reaching(0x6100))
            (Path(where) / "one.sfc").write_bytes(image)

            code = against.main([where, where], say=said.append, named=_named(image))

        self.assertEqual(code, 1)

    def test_a_file_that_is_not_a_cartridge_at_all_is_skipped(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            image = _a_cartridge(_reaching(0x7FF0))
            (Path(where) / "notes.txt").write_bytes(b"not a cartridge")
            (Path(where) / "one.sfc").write_bytes(image)

            code = against.main([where, where], say=said.append, named=_named(image))

        self.assertEqual(code, 0)

    def test_a_file_that_is_not_a_cartridge_for_this_part_is_skipped(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            held = bytearray(_a_cartridge(_reaching(0x7FF0)))
            held[0x7FD6] = 0x03
            image = _a_cartridge(_reaching(0x7FF0))
            (Path(where) / "other.sfc").write_bytes(bytes(held))
            (Path(where) / "one.sfc").write_bytes(image)

            code = against.main([where, where], say=said.append, named=_named(image, bytes(held)))

            self.assertEqual(
                (code, len(json.loads((Path(where) / "cartridges.json").read_text())["readFrom"])),
                (0, 1),
            )


class ManifestTest(unittest.TestCase):
    def test_a_cartridge_the_manifest_names_comes_back_with_its_row(self) -> None:
        image = _a_cartridge()

        found = against.confirmed(image, _named(image))

        self.assertEqual((found or {}).get("name"), "made-up-0.sfc")

    def test_a_cartridge_the_manifest_does_not_name_is_refused(self) -> None:
        self.assertIsNone(against.confirmed(_a_cartridge(), _named(_a_cartridge(b"\x01"))))

    def test_a_row_that_disagrees_with_itself_is_reported(self) -> None:
        image = _a_cartridge()
        catalogue = _named(image)
        next(iter(catalogue.values()))["crc32"] = "00000000"

        with self.assertRaises(against.Malformed):
            against.confirmed(image, catalogue)

    def test_the_manifest_beside_this_one_names_the_cartridges_it_reads(self) -> None:
        self.assertGreater(len(against.published()), 0)

    def test_a_cartridge_the_manifest_does_not_name_is_skipped(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "one.sfc").write_bytes(_a_cartridge(_reaching(0x7FF0)))

            code = against.main(
                [where, where], say=said.append, named=_named(_a_cartridge(b"\x01"))
            )

        self.assertEqual((code, any("no cartridge" in one for one in said)), (2, True))


if __name__ == "__main__":
    unittest.main()
