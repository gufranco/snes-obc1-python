from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import snesobc1  # noqa: E402

SOURCE = ROOT / "snesobc1" / "errors.py"

HOME = "snesobc1.errors"


def defined(source: str) -> list[str]:
    return sorted(node.name for node in ast.parse(source).body if isinstance(node, ast.ClassDef))


def exported_refusals() -> dict[str, type]:
    return {
        name: held
        for name in snesobc1.__all__
        if isinstance(held := getattr(snesobc1, name), type) and issubclass(held, BaseException)
    }


def reaching_back(source: str) -> list[str]:
    def inside(name: str) -> bool:
        return name.startswith(".") or name == "snesobc1" or name.startswith("snesobc1.")

    borrowed = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            borrowed += [alias.name for alias in node.names if inside(alias.name)]
        elif isinstance(node, ast.ImportFrom):
            name = "." * node.level + (node.module or "")
            if inside(name):
                borrowed.append(name)
    return borrowed


class OneHomeTest(unittest.TestCase):
    def test_the_module_defines_the_refusals_this_package_makes(self) -> None:
        # Arrange
        source = SOURCE.read_text()

        # Act
        found = defined(source)

        # Assert
        self.assertEqual(found, ["OutOfRange", "UnknownModelError"])

    def test_the_package_publishes_every_one_of_them(self) -> None:
        # Arrange
        source = SOURCE.read_text()

        # Act
        found = sorted(exported_refusals())

        # Assert
        self.assertEqual(found, defined(source))

    def test_and_each_one_it_publishes_lives_there(self) -> None:
        # Arrange
        published = exported_refusals()

        # Act
        homes = {name: held.__module__ for name, held in published.items()}

        # Assert
        self.assertEqual(homes, {"OutOfRange": HOME, "UnknownModelError": HOME})

    def test_each_one_is_an_exception_rather_than_a_signal(self) -> None:
        # Arrange
        published = exported_refusals()

        # Act
        stray = [name for name, held in published.items() if not issubclass(held, Exception)]

        # Assert
        self.assertEqual(stray, [])

    def test_the_chip_raises_the_one_published(self) -> None:
        # Arrange
        part = snesobc1.Chip("obc1")

        # Act
        with self.assertRaises(snesobc1.OutOfRange) as raised:
            part.read(0x0000)

        # Assert
        self.assertEqual(str(raised.exception), "0x0000 is not an address this chip answers")


class NoCycleTest(unittest.TestCase):
    def test_it_imports_nothing_from_this_package(self) -> None:
        # Arrange
        held = SOURCE.read_text()

        # Act
        found = reaching_back(held)

        # Assert
        self.assertEqual(found, [])

    def test_the_reader_of_that_names_an_absolute_import_back(self) -> None:
        # Arrange
        source = "import snesobc1.chip\n"

        # Act
        found = reaching_back(source)

        # Assert
        self.assertEqual(found, ["snesobc1.chip"])

    def test_and_a_relative_one(self) -> None:
        # Arrange
        source = "from . import chip\n"

        # Act
        found = reaching_back(source)

        # Assert
        self.assertEqual(found, ["."])

    def test_and_steps_over_one_from_outside(self) -> None:
        # Arrange
        source = "from __future__ import annotations\nimport snesobc1tools\n"

        # Act
        found = reaching_back(source)

        # Assert
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
