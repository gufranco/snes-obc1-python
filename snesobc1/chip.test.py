import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesobc1

MODEL = "obc1"

WINDOW_START = 0x6000

WINDOW_END = 0x8000

RAM_BYTES = 0x2000

BASE_LOW = 0x1800

BASE_HIGH = 0x1C00

PACKED_OFFSET = 0x200

FIRST_REGISTER = 0x7FF0

PACKED_REGISTER = 0x7FF4

BASE_REGISTER = 0x7FF5

POINTER_REGISTER = 0x7FF6

UNWRITTEN = 0xFF

BASE_BYTE = BASE_REGISTER - WINDOW_START

POINTER_BYTE = POINTER_REGISTER - WINDOW_START

SPRITE_BYTES = 4


def fresh() -> Any:
    return snesobc1.Chip(MODEL)


def pointed(at: int) -> Any:
    part = fresh()
    part.write(POINTER_REGISTER, at)
    return part


def an_image(held: dict[int, int]) -> bytearray:
    image = bytearray([UNWRITTEN] * RAM_BYTES)
    for offset, value in held.items():
        image[offset] = value
    return image


class MemoryTest(unittest.TestCase):
    def test_the_chip_carries_eight_kilobytes(self) -> None:
        # Arrange
        model = MODEL

        # Act
        part = snesobc1.Chip(model)

        # Assert
        self.assertEqual(len(part.ram), RAM_BYTES)

    def test_a_reset_leaves_every_byte_set_rather_than_cleared(self) -> None:
        # Arrange
        part = fresh()
        part.ram[0] = 0x00

        # Act
        part.reset()

        # Assert
        self.assertEqual(set(part.ram), {UNWRITTEN})

    def test_a_reset_hands_the_chip_back(self) -> None:
        # Arrange
        part = fresh()

        # Act
        found = part.reset()

        # Assert
        self.assertIs(found, part)

    def test_an_ordinary_address_reads_straight_out_of_that_memory(self) -> None:
        # Arrange
        part = fresh()
        part.ram[0x0000] = 0x42

        # Act
        found = part.read(WINDOW_START)

        # Assert
        self.assertEqual(found, 0x42)

    def test_and_writes_straight_into_it(self) -> None:
        # Arrange
        part = fresh()

        # Act
        part.write(WINDOW_START, 0x42)

        # Assert
        self.assertEqual(part.ram[0x0000], 0x42)

    def test_a_value_wider_than_a_byte_keeps_its_low_eight_bits(self) -> None:
        # Arrange
        part = fresh()

        # Act
        part.write(WINDOW_START, 0x1A5)

        # Assert
        self.assertEqual(part.read(WINDOW_START), 0xA5)

    def test_an_address_outside_the_window_is_not_this_chip(self) -> None:
        # Arrange
        part = fresh()

        # Act
        with self.assertRaises(snesobc1.OutOfRange) as raised:
            part.read(WINDOW_START - 1)

        # Assert
        self.assertEqual(str(raised.exception), "0x5fff is not an address this chip answers")

    def test_neither_is_one_past_the_end(self) -> None:
        # Arrange
        part = fresh()

        # Act
        with self.assertRaises(snesobc1.OutOfRange) as raised:
            part.write(WINDOW_END, 0)

        # Assert
        self.assertEqual(str(raised.exception), "0x8000 is not an address this chip answers")


class BaseTest(unittest.TestCase):
    def test_the_base_follows_the_low_bit_of_its_register(self) -> None:
        # Arrange
        part = fresh()

        # Act
        part.write(BASE_REGISTER, 0x01)

        # Assert
        self.assertEqual(part.base, BASE_LOW)

    def test_a_clear_bit_selects_the_other_base(self) -> None:
        # Arrange
        part = fresh()

        # Act
        part.write(BASE_REGISTER, 0x00)

        # Assert
        self.assertEqual(part.base, BASE_HIGH)

    def test_only_the_low_bit_of_that_register_matters(self) -> None:
        # Arrange
        part = fresh()

        # Act
        part.write(BASE_REGISTER, 0xFE)

        # Assert
        self.assertEqual(part.base, BASE_HIGH)

    def test_a_reset_ignores_what_the_memory_held_because_it_wipes_it_first(self) -> None:
        # Arrange
        part = fresh()
        part.ram[BASE_BYTE] = 0x00

        # Act
        part.reset()

        # Assert
        self.assertEqual(part.base, BASE_LOW)

    def test_adopting_a_saved_image_does_read_the_base_out_of_it(self) -> None:
        # Arrange
        saved = an_image({BASE_BYTE: 0x00})

        # Act
        part = snesobc1.Chip(MODEL, ram=saved)

        # Assert
        self.assertEqual(part.base, BASE_HIGH)


class PointerTest(unittest.TestCase):
    def test_the_pointer_register_keeps_seven_bits(self) -> None:
        # Arrange
        part = fresh()

        # Act
        part.write(POINTER_REGISTER, 0xFF)

        # Assert
        self.assertEqual(part.address, 0x7F)

    def test_and_takes_its_shift_from_the_low_two(self) -> None:
        # Arrange
        part = fresh()

        # Act
        part.write(POINTER_REGISTER, 0x03)

        # Assert
        self.assertEqual(part.shift, 6)

    def test_a_pointer_of_zero_shifts_by_nothing(self) -> None:
        # Arrange
        part = fresh()

        # Act
        part.write(POINTER_REGISTER, 0x00)

        # Assert
        self.assertEqual(part.shift, 0)

    def test_a_reset_always_comes_up_the_same_way(self) -> None:
        # Arrange
        part = fresh()
        part.ram[POINTER_BYTE] = 0x05

        # Act
        part.reset()

        # Assert
        self.assertEqual((part.address, part.shift), (0x7F, 6))

    def test_adopting_a_saved_image_does_read_the_pointer_out_of_it(self) -> None:
        # Arrange
        saved = an_image({POINTER_BYTE: 0x05})

        # Act
        part = snesobc1.Chip(MODEL, ram=saved)

        # Assert
        self.assertEqual((part.address, part.shift), (0x05, 2))

    def test_adopt_reads_the_state_out_of_an_image_handed_to_a_running_chip(self) -> None:
        # Arrange
        part = fresh()
        saved = an_image({BASE_BYTE: 0x00, POINTER_BYTE: 0x09})

        # Act
        found = part.adopt(saved)

        # Assert
        self.assertEqual((found, part.base, part.address, part.shift), (part, BASE_HIGH, 9, 2))


class RemapTest(unittest.TestCase):
    def test_the_first_four_registers_reach_four_consecutive_bytes(self) -> None:
        # Arrange
        part = pointed(0x02)
        part.write(BASE_REGISTER, 0x00)
        for offset in range(3):
            part.write(FIRST_REGISTER + offset, 0x10 + offset)

        # Act
        part.write(FIRST_REGISTER + 3, 0x13)

        # Assert
        at = BASE_HIGH + 0x02 * SPRITE_BYTES
        self.assertEqual(list(part.ram[at : at + SPRITE_BYTES]), [0x10, 0x11, 0x12, 0x13])

    def test_and_read_the_same_four_back(self) -> None:
        # Arrange
        part = pointed(0x02)
        at = BASE_LOW + 0x02 * SPRITE_BYTES
        part.ram[at : at + SPRITE_BYTES] = bytes([0x20, 0x21, 0x22, 0x23])

        # Act
        found = [part.read(FIRST_REGISTER + offset) for offset in range(SPRITE_BYTES)]

        # Assert
        self.assertEqual(found, [0x20, 0x21, 0x22, 0x23])

    def test_moving_the_pointer_moves_the_four_bytes_they_reach(self) -> None:
        # Arrange
        part = pointed(0x00)
        part.write(FIRST_REGISTER, 0xAA)
        part.write(POINTER_REGISTER, 0x01)

        # Act
        part.write(FIRST_REGISTER, 0xBB)

        # Assert
        self.assertEqual((part.ram[BASE_LOW], part.ram[BASE_LOW + SPRITE_BYTES]), (0xAA, 0xBB))


class PackedTest(unittest.TestCase):
    def test_the_fifth_register_reaches_a_byte_a_quarter_as_far_along(self) -> None:
        # Arrange
        part = pointed(0x08)
        part.ram[BASE_LOW + (0x08 >> 2) + PACKED_OFFSET] = 0x5A

        # Act
        found = part.read(PACKED_REGISTER)

        # Assert
        self.assertEqual(found, 0x5A)

    def test_a_write_there_changes_only_its_own_two_bits(self) -> None:
        # Arrange
        part = pointed(0x00)

        # Act
        part.write(PACKED_REGISTER, 0x00)

        # Assert
        self.assertEqual(part.ram[BASE_LOW + PACKED_OFFSET], 0xFC)

    def test_the_shift_decides_which_two_bits_it_changes(self) -> None:
        # Arrange
        part = pointed(0x03)

        # Act
        part.write(PACKED_REGISTER, 0x00)

        # Assert
        self.assertEqual(part.ram[BASE_LOW + PACKED_OFFSET], 0x3F)

    def test_only_the_low_two_bits_of_the_value_are_kept(self) -> None:
        # Arrange
        part = pointed(0x00)
        part.ram[BASE_LOW + PACKED_OFFSET] = 0x00

        # Act
        part.write(PACKED_REGISTER, 0xFF)

        # Assert
        self.assertEqual(part.ram[BASE_LOW + PACKED_OFFSET], 0x03)

    def test_four_pointers_sharing_a_byte_each_keep_their_own_corner(self) -> None:
        # Arrange
        part = fresh()
        part.ram[BASE_LOW + PACKED_OFFSET] = 0x00
        for pointer in range(3):
            part.write(POINTER_REGISTER, pointer)
            part.write(PACKED_REGISTER, pointer)
        part.write(POINTER_REGISTER, 3)

        # Act
        part.write(PACKED_REGISTER, 3)

        # Assert
        self.assertEqual(part.ram[BASE_LOW + PACKED_OFFSET], 0b11_10_01_00)


class ShadowTest(unittest.TestCase):
    def test_a_write_to_a_register_is_also_kept_where_it_landed(self) -> None:
        # Arrange
        part = fresh()

        # Act
        part.write(BASE_REGISTER, 0x01)

        # Assert
        self.assertEqual(part.ram[BASE_BYTE], 0x01)

    def test_which_is_how_a_saved_image_recovers_the_state(self) -> None:
        # Arrange
        saved = pointed(0x09).ram

        # Act
        part = snesobc1.Chip(MODEL, ram=saved)

        # Assert
        self.assertEqual(part.address, 0x09)

    def test_the_base_and_the_pointer_read_back_what_was_written_to_them(self) -> None:
        # Arrange
        part = pointed(0x7F)
        part.write(BASE_REGISTER, 0x00)

        # Act
        found = (part.read(BASE_REGISTER), part.read(POINTER_REGISTER))

        # Assert
        self.assertEqual(found, (0x00, 0x7F))


class ReadingTest(unittest.TestCase):
    def test_a_chip_prints_as_its_base_its_pointer_and_its_shift(self) -> None:
        # Arrange
        part = fresh()

        # Act
        found = repr(part)

        # Assert
        self.assertEqual(found, "<OBC1 base 0x1800 pointer 0x7f shift 6>")


if __name__ == "__main__":
    unittest.main()
