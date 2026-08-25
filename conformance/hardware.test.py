"""Hold this model's constants to hardware.json, and to their standing.

No manufacturer document names the OBC1, so all but one of these rest on a
reference implementation and say so. The exception is worth the file on its own:
the offset from a base address to the packed attributes is exactly the size of
the OAM low table Nintendo documents, because feeding OAM is the whole of what
this chip does.
"""

import json
import sys
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesobc1 import chip

HERE = Path(__file__).resolve().parent

SPRITES = 128
"""Sprites in an OAM table, from Nintendo's figure by way of snes-graphics-python."""

LOW_ENTRY_BYTES = 4
"""Bytes each one takes in the low table, from the same figure."""


def declared(name: str) -> dict[str, Any]:
    held = json.loads((HERE / name).read_text())
    assert isinstance(held, dict), f"{name} does not hold an object"
    return held


class DocumentTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.declared = declared("hardware.json")
        self.facts: dict[str, Any] = self.declared["facts"]

    def test_the_absence_of_a_document_is_recorded_along_with_the_search(self) -> None:
        missing = self.declared["authority"]["whatIsMissing"]

        self.assertIn("nothing was found", missing)

    def test_every_fact_says_whether_it_is_verified(self) -> None:
        missing = [name for name, fact in self.facts.items() if "verified" not in fact]

        self.assertEqual(missing, [])

    def test_every_unverified_fact_names_its_evidence_and_what_would_settle_it(self) -> None:
        missing = [
            name
            for name, fact in self.facts.items()
            if not fact["verified"] and not (fact.get("evidence") and fact.get("howToSettleIt"))
        ]

        self.assertEqual(missing, [])

    def test_exactly_one_fact_rests_on_a_document(self) -> None:
        verified = [name for name, fact in self.facts.items() if fact["verified"]]

        self.assertEqual(verified, ["packedOffset"])

    def test_what_nothing_settles_is_recorded_rather_than_filled_in(self) -> None:
        stated = self.declared["notStated"]

        self.assertGreaterEqual(len(stated), 4)


class ConstantTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.facts: dict[str, Any] = declared("hardware.json")["facts"]

    def test_the_packed_offset_is_the_size_of_an_oam_low_table(self) -> None:
        packed = self.facts["packedOffset"]

        self.assertEqual(packed["value"], SPRITES * LOW_ENTRY_BYTES)

    def test_and_it_is_the_offset_this_model_uses(self) -> None:
        packed = self.facts["packedOffset"]

        self.assertEqual(packed["value"], chip.PACKED_OFFSET)

    def test_the_window_spans_the_addresses_declared(self) -> None:
        found = (self.facts["windowStart"]["value"], self.facts["windowEnd"]["value"])

        self.assertEqual(found, (chip.WINDOW_START, chip.WINDOW_END))

    def test_and_the_memory_is_exactly_as_wide_as_the_window(self) -> None:
        span = self.facts["windowEnd"]["value"] - self.facts["windowStart"]["value"]

        self.assertEqual(span, chip.RAM_BYTES)

    def test_both_base_addresses_are_the_ones_declared(self) -> None:
        found = self.facts["baseAddresses"]["value"]

        self.assertEqual(sorted(found), sorted((chip.BASE_LOW, chip.BASE_HIGH)))

    def test_and_they_sit_two_low_tables_apart(self) -> None:
        low, high = sorted(self.facts["baseAddresses"]["value"])

        self.assertEqual(high - low, 2 * SPRITES * LOW_ENTRY_BYTES)

    def test_every_declared_register_is_where_this_model_puts_it(self) -> None:
        registers = self.facts["registers"]["value"]

        found = [
            (name, int(registers[name], 16), mine)
            for name, mine in (
                ("first", chip.FIRST_REGISTER),
                ("packed", chip.PACKED_REGISTER),
                ("base", chip.BASE_REGISTER),
                ("pointer", chip.POINTER_REGISTER),
            )
            if int(registers[name], 16) != mine
        ]

        self.assertEqual(found, [])

    def test_the_registers_sit_at_the_top_of_the_window(self) -> None:
        registers = [int(value, 16) for value in self.facts["registers"]["value"].values()]

        self.assertTrue(all(chip.WINDOW_START <= value < chip.WINDOW_END for value in registers))

    def test_an_unwritten_byte_reads_as_the_value_declared(self) -> None:
        unwritten = self.facts["unwrittenByte"]

        self.assertEqual(unwritten["value"], chip.UNWRITTEN)

    def test_and_a_fresh_chip_is_full_of_it(self) -> None:
        fresh = chip.Chip()

        self.assertEqual(fresh.read(chip.WINDOW_START), chip.UNWRITTEN)


class DivergenceTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.entries: list[dict[str, Any]] = declared("divergences.json")["divergences"]

    def test_each_entry_says_which_source_the_package_follows(self) -> None:
        allowed = {"document", "reference", "neither"}

        self.assertEqual({entry["packageFollows"] for entry in self.entries} - allowed, set())

    def test_each_entry_says_what_would_settle_or_reopen_it(self) -> None:
        missing = [
            entry["id"]
            for entry in self.entries
            if not (entry.get("wouldSettleIt") or entry.get("wouldReopenIt"))
        ]

        self.assertEqual(missing, [])

    def test_the_absence_of_a_document_is_recorded_as_serious(self) -> None:
        entry = next(item for item in self.entries if item["id"] == "no-document-names-this-part")

        self.assertEqual(entry["severity"], "high")

    def test_one_cartridge_not_being_a_corpus_is_recorded(self) -> None:
        entry = next(item for item in self.entries if item["id"] == "one-cartridge-is-not-a-corpus")

        self.assertIn("could not be wrong the same way", entry["reasoning"])

    def test_the_one_documented_constant_is_recorded_as_closed(self) -> None:
        entry = next(
            item for item in self.entries if item["id"] == "the-packed-offset-comes-from-a-document"
        )

        self.assertEqual(entry["status"], "closed")


if __name__ == "__main__":
    unittest.main(verbosity=1)
