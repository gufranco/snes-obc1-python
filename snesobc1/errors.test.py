from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from snesobc1 import errors  # noqa: E402


def reaching_back(source: str) -> list[str]:
    """Every import in that source that comes from this package rather than outside it.

    Written against text rather than against the one file it guards, so it can be
    handed something that should fail it. A reader nobody has seen report a fault
    reports a clean run whether or not there is one.

    A relative import counts however deep it goes, and an absolute one counts
    when it is the package or a module under it. The dot is required, because a
    package whose name merely begins the same way is somebody else's.
    """

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
    """That every refusal this package makes is defined here and nowhere else.

    Two classes under one name both work, both get tested, and `except` catches
    half the cases it names. Keeping them in one module is what makes that
    impossible rather than unlikely.
    """

    def named(self) -> list[str]:
        return [
            name
            for name, held in vars(errors).items()
            if isinstance(held, type) and issubclass(held, Exception)
        ]

    def test_the_module_defines_the_refusal_this_package_makes(self) -> None:
        self.assertEqual(sorted(self.named()), ["OutOfRange", "UnknownModelError"])

    def test_it_derives_from_exception(self) -> None:
        stray = [name for name in self.named() if not issubclass(getattr(errors, name), Exception)]

        self.assertEqual(stray, [])

    def test_and_it_says_what_it_means(self) -> None:
        """A refusal a caller meets and cannot look up is a refusal they guess at."""
        silent = [
            name for name in self.named() if not (getattr(errors, name).__doc__ or "").strip()
        ]

        self.assertEqual(silent, [])

    def test_the_chip_raises_the_one_defined_here(self) -> None:
        """Rather than a second class of the same name defined beside the chip."""
        from snesobc1 import chip

        with self.assertRaises(errors.OutOfRange):
            chip.Chip().read(0x0000)


class NoCycleTest(unittest.TestCase):
    """That this module imports nothing from the package it belongs to.

    Everything here raises, so everything here imports this. An import running
    the other way closes the cycle and makes the order modules happen to load in
    decide whether the package works.
    """

    def test_it_imports_nothing_from_this_package(self) -> None:
        held = (ROOT / "snesobc1" / "errors.py").read_text()

        self.assertEqual(reaching_back(held), [])

    def test_the_reader_of_that_names_an_absolute_import_back(self) -> None:
        found = reaching_back("import snesobc1.chip\n")

        self.assertEqual(found, ["snesobc1.chip"])

    def test_and_a_relative_one(self) -> None:
        found = reaching_back("from . import chip\n")

        self.assertEqual(found, ["."])

    def test_and_steps_over_one_from_outside(self) -> None:
        """The standard library and a package whose name merely starts the same."""
        found = reaching_back("from __future__ import annotations\nimport snesobc1tools\n")

        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
