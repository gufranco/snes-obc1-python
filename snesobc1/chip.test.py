import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesobc1 import chip


def fresh(**options):
    return chip.Obc1(**options)


class MemoryTest(unittest.TestCase):
    def test_the_chip_carries_eight_kilobytes(self):
        self.assertEqual(len(fresh().ram), chip.RAM_BYTES)

    def test_a_reset_leaves_every_byte_set_rather_than_cleared(self):
        self.assertEqual(set(fresh().ram), {0xFF})

    def test_an_ordinary_address_reads_straight_out_of_that_memory(self):
        found = fresh()
        found.ram[0x0000] = 0x42

        self.assertEqual(found.read(0x6000), 0x42)

    def test_and_writes_straight_into_it(self):
        found = fresh()

        found.write(0x6000, 0x42)

        self.assertEqual(found.ram[0x0000], 0x42)

    def test_an_address_outside_the_window_is_not_this_chip(self):
        with self.assertRaises(chip.OutOfRange):
            fresh().read(0x5FFF)

    def test_neither_is_one_past_the_end(self):
        with self.assertRaises(chip.OutOfRange):
            fresh().read(0x8000)


class BaseTest(unittest.TestCase):
    def test_the_base_follows_the_low_bit_of_its_register(self):
        found = fresh()

        found.write(0x7FF5, 0x01)

        self.assertEqual(found.base, chip.BASE_LOW)

    def test_a_clear_bit_selects_the_other_base(self):
        found = fresh()

        found.write(0x7FF5, 0x00)

        self.assertEqual(found.base, chip.BASE_HIGH)

    def test_only_the_low_bit_of_that_register_matters(self):
        found = fresh()

        found.write(0x7FF5, 0xFE)

        self.assertEqual(found.base, chip.BASE_HIGH)

    def test_a_reset_ignores_what_the_memory_held_because_it_wipes_it_first(self):
        found = fresh()
        found.ram[0x1FF5] = 0x00

        found.reset()

        self.assertEqual(found.base, chip.BASE_LOW)

    def test_adopting_a_saved_image_does_read_the_base_out_of_it(self):
        saved = bytearray([0xFF] * chip.RAM_BYTES)
        saved[0x1FF5] = 0x00

        self.assertEqual(chip.Obc1(ram=saved).base, chip.BASE_HIGH)


class PointerTest(unittest.TestCase):
    def test_the_pointer_register_keeps_seven_bits(self):
        found = fresh()

        found.write(0x7FF6, 0xFF)

        self.assertEqual(found.address, 0x7F)

    def test_and_takes_its_shift_from_the_low_two(self):
        found = fresh()

        found.write(0x7FF6, 0x03)

        self.assertEqual(found.shift, 6)

    def test_a_pointer_of_zero_shifts_by_nothing(self):
        found = fresh()

        found.write(0x7FF6, 0x00)

        self.assertEqual(found.shift, 0)

    def test_a_reset_always_comes_up_the_same_way(self):
        found = fresh()
        found.ram[0x1FF6] = 0x05

        found.reset()

        self.assertEqual((found.address, found.shift), (0x7F, 6))

    def test_adopting_a_saved_image_does_read_the_pointer_out_of_it(self):
        saved = bytearray([0xFF] * chip.RAM_BYTES)
        saved[0x1FF6] = 0x05

        found = chip.Obc1(ram=saved)

        self.assertEqual((found.address, found.shift), (0x05, 2))


class RemapTest(unittest.TestCase):
    def test_the_first_four_registers_reach_four_consecutive_bytes(self):
        found = fresh()
        found.write(0x7FF5, 0x00)
        found.write(0x7FF6, 0x02)

        for offset in range(4):
            found.write(0x7FF0 + offset, 0x10 + offset)

        at = chip.BASE_HIGH + (0x02 << 2)
        self.assertEqual(list(found.ram[at : at + 4]), [0x10, 0x11, 0x12, 0x13])

    def test_and_read_the_same_four_back(self):
        found = fresh()
        found.write(0x7FF6, 0x02)
        at = found.base + (0x02 << 2)
        found.ram[at : at + 4] = bytes([0x20, 0x21, 0x22, 0x23])

        self.assertEqual(
            [found.read(0x7FF0 + offset) for offset in range(4)], [0x20, 0x21, 0x22, 0x23]
        )

    def test_moving_the_pointer_moves_the_four_bytes_they_reach(self):
        found = fresh()
        found.write(0x7FF6, 0x00)
        found.write(0x7FF0, 0xAA)
        found.write(0x7FF6, 0x01)
        found.write(0x7FF0, 0xBB)

        self.assertEqual(found.ram[found.base], 0xAA)
        self.assertEqual(found.ram[found.base + 4], 0xBB)


class PackedTest(unittest.TestCase):
    def test_the_fifth_register_reaches_a_byte_a_quarter_as_far_along(self):
        found = fresh()
        found.write(0x7FF6, 0x08)
        found.ram[found.base + (0x08 >> 2) + 0x200] = 0x5A

        self.assertEqual(found.read(0x7FF4), 0x5A)

    def test_a_write_there_changes_only_its_own_two_bits(self):
        found = fresh()
        found.write(0x7FF6, 0x00)
        at = found.base + 0x200
        found.ram[at] = 0xFF

        found.write(0x7FF4, 0x00)

        self.assertEqual(found.ram[at], 0xFC)

    def test_the_shift_decides_which_two_bits_it_changes(self):
        found = fresh()
        found.write(0x7FF6, 0x03)
        at = found.base + 0x200
        found.ram[at] = 0xFF

        found.write(0x7FF4, 0x00)

        self.assertEqual(found.ram[at], 0x3F)

    def test_only_the_low_two_bits_of_the_value_are_kept(self):
        found = fresh()
        found.write(0x7FF6, 0x00)
        at = found.base + 0x200
        found.ram[at] = 0x00

        found.write(0x7FF4, 0xFF)

        self.assertEqual(found.ram[at], 0x03)

    def test_four_pointers_sharing_a_byte_each_keep_their_own_corner(self):
        found = fresh()
        at = None
        for pointer in range(4):
            found.write(0x7FF6, pointer)
            at = found.base + 0x200
            found.ram[at] = 0x00
        for pointer in range(4):
            found.write(0x7FF6, pointer)
            found.write(0x7FF4, pointer)

        self.assertEqual(found.ram[at], 0b11_10_01_00)


class ShadowTest(unittest.TestCase):
    def test_a_write_to_a_register_is_also_kept_where_it_landed(self):
        found = fresh()

        found.write(0x7FF5, 0x01)

        self.assertEqual(found.ram[0x1FF5], 0x01)

    def test_which_is_how_a_saved_image_recovers_the_state(self):
        found = fresh()
        found.write(0x7FF6, 0x09)

        self.assertEqual(chip.Obc1(ram=found.ram).address, 0x09)


class ReadingTest(unittest.TestCase):
    def test_a_chip_prints_as_its_base_and_its_pointer(self):
        self.assertIn("pointer", repr(fresh()))


if __name__ == "__main__":
    unittest.main()
