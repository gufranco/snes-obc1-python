import json
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesobc1

HERE = Path(__file__).resolve().parent

SPRITES = 128

LOW_ENTRY_BYTES = 4

SPRITE_MARK = 0x5A

POINTED_AT = 0x05

MODEL = "obc1"


def declared(name: str) -> dict[str, Any]:
    held = json.loads((HERE / name).read_text())
    assert isinstance(held, dict), f"{name} does not hold an object"
    return held


def facts() -> dict[str, Any]:
    found: dict[str, Any] = declared("hardware.json")["facts"]
    return found


def value(name: str) -> Any:
    return facts()[name]["value"]


def register(name: str) -> int:
    return int(value("registers")[name], 16)


def fresh() -> Any:
    return snesobc1.Chip(MODEL)


def readings(part: Any, addresses: range) -> list[int]:
    return [part.read(at) for at in addresses]


def base_after(written: int) -> int:
    part = fresh()
    part.write(register("base"), written)
    return int(part.base)


class DocumentTest(unittest.TestCase):
    def test_the_absence_of_a_document_is_recorded_along_with_the_search(self) -> None:
        # Arrange
        record = declared("hardware.json")

        # Act
        missing = record["authority"]["whatIsMissing"]

        # Assert
        self.assertIn("nothing was found", missing)

    def test_every_fact_says_whether_it_is_verified(self) -> None:
        # Arrange
        held = facts()

        # Act
        missing = [name for name, fact in held.items() if "verified" not in fact]

        # Assert
        self.assertEqual(missing, [])

    def test_every_unverified_fact_names_its_evidence_and_what_would_settle_it(self) -> None:
        # Arrange
        held = facts()

        # Act
        missing = [
            name
            for name, fact in held.items()
            if not fact["verified"] and not (fact.get("evidence") and fact.get("howToSettleIt"))
        ]

        # Assert
        self.assertEqual(missing, [])

    def test_exactly_one_fact_rests_on_a_document(self) -> None:
        # Arrange
        held = facts()

        # Act
        verified = [name for name, fact in held.items() if fact["verified"]]

        # Assert
        self.assertEqual(verified, ["packedOffset"])

    def test_what_nothing_settles_is_recorded_rather_than_filled_in(self) -> None:
        # Arrange
        record = declared("hardware.json")

        # Act
        stated = record["notStated"]

        # Assert
        self.assertGreaterEqual(len(stated), 4)


class PackedOffsetTest(unittest.TestCase):
    def test_the_packed_offset_is_the_size_of_an_oam_low_table(self) -> None:
        # Arrange
        expected = SPRITES * LOW_ENTRY_BYTES

        # Act
        found = facts()["packedOffset"]["value"]

        # Assert
        self.assertEqual(found, expected)

    def test_the_packed_bits_land_the_printed_offset_past_the_sprite_bytes(self) -> None:
        # Arrange
        held = facts()
        registers = {name: int(at, 16) for name, at in held["registers"]["value"].items()}
        part = fresh()
        part.write(registers["pointer"], 0)
        part.write(registers["first"], SPRITE_MARK)
        memory = range(held["windowStart"]["value"], registers["first"])
        sprite = next(at for at in memory if part.read(at) == SPRITE_MARK)
        before = readings(part, memory)

        # Act
        part.write(registers["packed"], 0)

        # Assert
        after = readings(part, memory)
        moved = [
            at - sprite for at, was, now in zip(memory, before, after, strict=True) if was != now
        ]
        self.assertEqual(moved, [held["packedOffset"]["value"]])


class WindowTest(unittest.TestCase):
    def test_the_first_address_of_the_window_answers(self) -> None:
        # Arrange
        part = fresh()

        # Act
        found = part.read(value("windowStart"))

        # Assert
        self.assertEqual(found, value("unwrittenByte"))

    def test_and_the_one_below_it_does_not(self) -> None:
        # Arrange
        part = fresh()

        # Act
        with self.assertRaises(snesobc1.OutOfRange) as raised:
            part.read(value("windowStart") - 1)

        # Assert
        self.assertIn(f"{value('windowStart') - 1:#06x}", str(raised.exception))

    def test_the_last_address_of_the_window_answers(self) -> None:
        # Arrange
        part = fresh()

        # Act
        found = part.read(value("windowEnd") - 1)

        # Assert
        self.assertEqual(found, value("unwrittenByte"))

    def test_and_the_end_itself_does_not(self) -> None:
        # Arrange
        part = fresh()

        # Act
        with self.assertRaises(snesobc1.OutOfRange) as raised:
            part.read(value("windowEnd"))

        # Assert
        self.assertIn(f"{value('windowEnd'):#06x}", str(raised.exception))

    def test_the_memory_holds_as_many_bytes_as_declared(self) -> None:
        # Arrange
        part = fresh()

        # Act
        found = len(part.ram)

        # Assert
        self.assertEqual(found, value("ramBytes"))

    def test_and_that_is_exactly_as_wide_as_the_window(self) -> None:
        # Arrange
        start, end = value("windowStart"), value("windowEnd")

        # Act
        span = end - start

        # Assert
        self.assertEqual(span, value("ramBytes"))

    def test_a_fresh_chip_is_full_of_the_unwritten_byte(self) -> None:
        # Arrange
        model = MODEL

        # Act
        part = snesobc1.Chip(model)

        # Assert
        self.assertEqual(set(part.ram), {value("unwrittenByte")})


class RegisterTest(unittest.TestCase):
    def test_the_base_register_selects_between_the_two_bases_declared(self) -> None:
        # Arrange
        written = (0x00, 0x01)

        # Act
        found = sorted(base_after(one) for one in written)

        # Assert
        self.assertEqual(found, sorted(value("baseAddresses")))

    def test_and_those_sit_two_low_tables_apart(self) -> None:
        # Arrange
        low, high = sorted(value("baseAddresses"))

        # Act
        apart = high - low

        # Assert
        self.assertEqual(apart, 2 * SPRITES * LOW_ENTRY_BYTES)

    def test_the_pointer_register_is_where_the_record_puts_it(self) -> None:
        # Arrange
        part = fresh()

        # Act
        part.write(register("pointer"), POINTED_AT)

        # Assert
        self.assertEqual(part.address, POINTED_AT)

    def test_the_first_window_register_is_where_the_record_puts_it(self) -> None:
        # Arrange
        part = fresh()
        part.write(register("pointer"), 0)

        # Act
        part.write(register("first"), SPRITE_MARK)

        # Assert
        self.assertEqual(part.ram[part.base], SPRITE_MARK)

    def test_the_registers_sit_at_the_top_of_the_window(self) -> None:
        # Arrange
        window = range(value("windowStart"), value("windowEnd"))

        # Act
        outside = [name for name in value("registers") if register(name) not in window]

        # Assert
        self.assertEqual(outside, [])


class DivergenceTest(unittest.TestCase):
    def entries(self) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = declared("divergences.json")["divergences"]
        return found

    def test_each_entry_says_which_source_the_package_follows(self) -> None:
        # Arrange
        allowed = {"document", "reference", "neither"}

        # Act
        followed = {entry["packageFollows"] for entry in self.entries()}

        # Assert
        self.assertEqual(followed - allowed, set())

    def test_each_entry_says_what_would_settle_or_reopen_it(self) -> None:
        # Arrange
        entries = self.entries()

        # Act
        missing = [
            entry["id"]
            for entry in entries
            if not (entry.get("wouldSettleIt") or entry.get("wouldReopenIt"))
        ]

        # Assert
        self.assertEqual(missing, [])

    def test_the_absence_of_a_document_is_recorded_as_serious(self) -> None:
        # Arrange
        entries = self.entries()

        # Act
        entry = next(item for item in entries if item["id"] == "no-document-names-this-part")

        # Assert
        self.assertEqual(entry["severity"], "high")

    def test_one_cartridge_not_being_a_corpus_is_recorded(self) -> None:
        # Arrange
        entries = self.entries()

        # Act
        entry = next(item for item in entries if item["id"] == "one-cartridge-is-not-a-corpus")

        # Assert
        self.assertIn("could not be wrong the same way", entry["reasoning"])

    def test_the_one_documented_constant_is_recorded_as_closed(self) -> None:
        # Arrange
        entries = self.entries()

        # Act
        entry = next(
            item for item in entries if item["id"] == "the-packed-offset-comes-from-a-document"
        )

        # Assert
        self.assertEqual(entry["status"], "closed")


if __name__ == "__main__":
    unittest.main(verbosity=1)
