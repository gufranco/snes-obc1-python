import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesobc1

MODEL = "obc1"

ALIASES = ("obc-1", "obc")

RAM_BYTES = 0x2000

UNWRITTEN = 0xFF

WINDOW_START = 0x6000

WINDOW_END = 0x8000


def the_model() -> Any:
    return snesobc1.MODELS[MODEL]


class CatalogueTest(unittest.TestCase):
    def test_the_package_publishes_one_model(self) -> None:
        # Arrange
        catalogue = snesobc1.MODELS

        # Act
        found = sorted(catalogue)

        # Assert
        self.assertEqual(found, [MODEL])

    def test_and_a_caller_has_to_name_it_rather_than_getting_it_by_default(self) -> None:
        # Arrange
        named = None

        # Act
        with self.assertRaises(snesobc1.UnknownModelError) as raised:
            snesobc1.Chip(named)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "no model was named, and this package will not choose one for you. Name one of: obc1",
        )

    def test_nothing_named_describe_is_published(self) -> None:
        # Arrange
        package = snesobc1

        # Act
        found = hasattr(package, "describe")

        # Assert
        self.assertFalse(found)

    def test_and_no_default_model_is_published_either(self) -> None:
        # Arrange
        package = snesobc1

        # Act
        found = hasattr(package, "DEFAULT_MODEL")

        # Assert
        self.assertFalse(found)

    def test_every_model_carries_a_summary_of_what_it_is(self) -> None:
        # Arrange
        catalogue = snesobc1.MODELS

        # Act
        unsummarised = [name for name, one in catalogue.items() if not one.summary]

        # Assert
        self.assertEqual(unsummarised, [])

    def test_a_model_prints_as_itself_with_where_it_answers(self) -> None:
        # Arrange
        one = the_model()

        # Act
        found = repr(one)

        # Assert
        self.assertEqual(found, f"<Model obc1, answering at {WINDOW_START:#06x}>")


class NameTest(unittest.TestCase):
    def test_a_model_is_found_by_its_own_name(self) -> None:
        # Arrange
        name = MODEL

        # Act
        part = snesobc1.Chip(name)

        # Assert
        self.assertEqual(part.model, MODEL)

    def test_the_model_lists_the_aliases_it_answers_to(self) -> None:
        # Arrange
        one = the_model()

        # Act
        found = one.aliases

        # Assert
        self.assertEqual(found, ALIASES)

    def test_and_every_alias_builds_the_same_chip(self) -> None:
        # Arrange
        aliases = the_model().aliases

        # Act
        found = {snesobc1.Chip(alias).model for alias in aliases}

        # Assert
        self.assertEqual(found, {MODEL})

    def test_case_does_not_matter(self) -> None:
        # Arrange
        name = "OBC1"

        # Act
        part = snesobc1.Chip(name)

        # Assert
        self.assertEqual(part.model, MODEL)

    def test_nor_do_separators_or_surrounding_space(self) -> None:
        # Arrange
        name = "  obc_1 "

        # Act
        part = snesobc1.Chip(name)

        # Assert
        self.assertEqual(part.model, MODEL)

    def test_a_name_no_model_goes_by_is_refused_and_the_refusal_names_the_ones_there_are(
        self,
    ) -> None:
        # Arrange
        name = "nope"

        # Act
        with self.assertRaises(snesobc1.UnknownModelError) as raised:
            snesobc1.Chip(name)

        # Assert
        self.assertEqual(
            str(raised.exception), "no model called 'nope'; this package publishes obc1"
        )


class BuildTest(unittest.TestCase):
    def test_a_model_builds_a_chip_that_refuses_an_address_past_its_window(self) -> None:
        # Arrange
        built = the_model().build()

        # Act
        with self.assertRaises(snesobc1.OutOfRange) as raised:
            built.read(WINDOW_END)

        # Assert
        self.assertEqual(str(raised.exception), "0x8000 is not an address this chip answers")

    def test_and_the_chip_carries_the_name_it_was_built_from(self) -> None:
        # Arrange
        one = the_model()

        # Act
        built = one.build()

        # Assert
        self.assertEqual(built.model, MODEL)

    def test_an_image_handed_in_is_adopted_rather_than_wiped(self) -> None:
        # Arrange
        saved = bytearray([0x00] * RAM_BYTES)

        # Act
        built = the_model().build(saved)

        # Assert
        self.assertEqual(built.read(WINDOW_START), 0x00)

    def test_while_no_image_leaves_the_reset_value_behind(self) -> None:
        # Arrange
        one = the_model()

        # Act
        built = one.build()

        # Assert
        self.assertEqual(built.read(WINDOW_START), UNWRITTEN)


if __name__ == "__main__":
    unittest.main()
