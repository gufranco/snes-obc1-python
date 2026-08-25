import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesobc1 import chip, models
from snesobc1.errors import UnknownModelError


class CatalogueTest(unittest.TestCase):
    def test_the_package_publishes_one_model(self) -> None:
        self.assertEqual(sorted(models.MODELS), ["obc1"])

    def test_and_it_is_the_one_a_caller_gets_by_default(self) -> None:
        self.assertEqual(models.DEFAULT_MODEL, "obc1")

    def test_every_model_carries_a_summary_of_what_it_is(self) -> None:
        unsummarised = [name for name, one in models.MODELS.items() if not one.summary]

        self.assertEqual(unsummarised, [])

    def test_a_model_prints_as_itself_with_where_it_answers(self) -> None:
        one = models.describe("obc1")

        self.assertEqual(repr(one), f"<Model obc1, answering at {chip.WINDOW_START:#06x}>")


class DescribeTest(unittest.TestCase):
    def test_a_model_is_found_by_its_own_name(self) -> None:
        self.assertEqual(models.describe("obc1").name, "obc1")

    def test_and_by_every_alias_it_answers_to(self) -> None:
        for alias in models.describe("obc1").aliases:
            self.assertEqual(models.describe(alias).name, "obc1", alias)

    def test_case_does_not_matter(self) -> None:
        self.assertEqual(models.describe("OBC1").name, "obc1")

    def test_nor_do_separators_or_surrounding_space(self) -> None:
        self.assertEqual(models.describe("  obc_1 ").name, "obc1")

    def test_a_name_no_model_goes_by_is_refused(self) -> None:
        with self.assertRaises(UnknownModelError):
            models.describe("no model goes by this name")

    def test_and_the_refusal_names_the_ones_that_would_have_worked(self) -> None:
        with self.assertRaises(UnknownModelError) as caught:
            models.describe("nope")

        self.assertIn("obc1", str(caught.exception))


class BuildTest(unittest.TestCase):
    def test_a_model_builds_a_chip(self) -> None:
        built = models.describe("obc1").build()

        self.assertIsInstance(built, chip.Chip)

    def test_and_the_chip_carries_the_name_it_was_built_from(self) -> None:
        built = models.describe("obc1").build()

        self.assertEqual(built.model, "obc1")

    def test_an_image_handed_in_is_adopted_rather_than_wiped(self) -> None:
        saved = bytearray([0x00] * chip.RAM_BYTES)

        built = models.describe("obc1").build(saved)

        self.assertEqual(built.ram[0], 0x00)

    def test_while_no_image_leaves_the_reset_value_behind(self) -> None:
        built = models.describe("obc1").build()

        self.assertEqual(built.ram[0], chip.UNWRITTEN)


if __name__ == "__main__":
    unittest.main()
