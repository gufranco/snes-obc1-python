from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import quotes  # noqa: E402

BOOK = "book.pdf"

PAGE_TEXT = "PPU REGISTERS\n OBJECT        DATA\n   OAM\nADDRESS\n"


def a_record(**fact: Any) -> dict[str, Any]:
    return {
        "documents": {"manual": {"file": BOOK, "quote": "not a citation"}},
        "facts": {"offset": {"document": "manual", "filePage": 7, **fact}},
    }


def a_page(text: str) -> quotes.Reader:
    return lambda path, page: text if (path.name, page) == (BOOK, 7) else ""


def a_folder(record: dict[str, Any], book: bool = True) -> tuple[Path, Path]:
    folder = Path(tempfile.mkdtemp())
    (folder / "hardware.json").write_text(json.dumps(record))
    if book:
        (folder / BOOK).write_bytes(b"%PDF-1.4\n")
    return folder / "hardware.json", folder


def run_main(record: dict[str, Any], read: quotes.Reader, book: bool = True) -> tuple[int, str]:
    path, folder = a_folder(record, book)
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        code = quotes.main(path, folder, read)
    return code, said.getvalue()


def a_run(returncode: int, stdout: str) -> Any:
    def run(*_: Any, **__: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], returncode, stdout, "")

    return run


def no_reader(*_: Any, **__: Any) -> subprocess.CompletedProcess[str]:
    raise FileNotFoundError("pdftotext")


class FlattenTest(unittest.TestCase):
    def test_only_letters_and_digits_survive_in_lower_case(self) -> None:
        # Arrange
        text = "OBJECT  DATA\n(Decimal) D15"

        # Act
        found = quotes.flatten(text)

        # Assert
        self.assertEqual(found, "objectdatadecimald15")

    def test_an_accented_letter_keeps_its_base_letter(self) -> None:
        # Arrange
        text = "café"

        # Act
        found = quotes.flatten(text)

        # Assert
        self.assertEqual(found, "cafe")


class HeldTest(unittest.TestCase):
    def test_a_quote_read_from_the_text_layer_is_looked_for_as_written(self) -> None:
        # Arrange
        record = a_record(quote="OAM ADDRESS")

        # Act
        found = quotes.held(record)

        # Assert
        self.assertEqual(found, [quotes.Quote("facts/offset", "OAM ADDRESS", BOOK, 7)])

    def test_a_quote_assembled_from_a_figure_is_looked_for_by_its_heading(self) -> None:
        # Arrange
        record = a_record(quote="000 OBJ 0", assembled=True, section="OBJECT DATA")

        # Act
        found = quotes.held(record)

        # Assert
        self.assertEqual(found, [quotes.Quote("facts/offset", "OBJECT DATA", BOOK, 7)])

    def test_a_quote_inside_a_list_is_found_with_its_position(self) -> None:
        # Arrange
        record = {
            "documents": {"manual": {"file": BOOK}},
            "facts": [{"quote": "OAM", "document": "manual", "filePage": 2}],
        }

        # Act
        found = quotes.held(record)

        # Assert
        self.assertEqual(found, [quotes.Quote("facts[0]", "OAM", BOOK, 2)])

    def test_a_record_that_quotes_nothing_holds_no_quote(self) -> None:
        # Arrange
        record = {"documents": {}, "facts": {"offset": {"value": 512}}}

        # Act
        found = quotes.held(record)

        # Assert
        self.assertEqual(found, [])


class PageTextTest(unittest.TestCase):
    def test_the_text_of_a_page_that_reads_is_handed_back(self) -> None:
        # Arrange
        run = a_run(0, PAGE_TEXT)

        # Act
        found = quotes.page_text(Path(BOOK), 7, run)

        # Assert
        self.assertEqual(found, PAGE_TEXT)

    def test_a_page_the_reader_refuses_reads_as_nothing(self) -> None:
        # Arrange
        run = a_run(1, "partial")

        # Act
        found = quotes.page_text(Path(BOOK), 7, run)

        # Assert
        self.assertEqual(found, "")

    def test_a_machine_without_the_reader_reads_nothing(self) -> None:
        # Arrange
        path = Path(BOOK)

        # Act
        found = quotes.page_text(path, 7, no_reader)

        # Assert
        self.assertEqual(found, "")


class UnplacedTest(unittest.TestCase):
    def test_a_quote_on_the_page_it_cites_is_placed(self) -> None:
        # Arrange
        held = [quotes.Quote("facts/offset", "OBJECT DATA", BOOK, 7)]

        # Act
        found = quotes.unplaced(held, Path(), a_page(PAGE_TEXT))

        # Assert
        self.assertEqual(found, [])

    def test_a_quote_on_another_page_is_not(self) -> None:
        # Arrange
        held = [quotes.Quote("facts/offset", "OBJECT DATA", BOOK, 8)]

        # Act
        found = quotes.unplaced(held, Path(), a_page(PAGE_TEXT))

        # Assert
        self.assertEqual(found, ["facts/offset: not on page 8 of book.pdf"])


class MainTest(unittest.TestCase):
    def test_every_quote_found_passes_and_says_how_many(self) -> None:
        # Arrange
        record = a_record(quote="OAM ADDRESS")

        # Act
        code, said = run_main(record, a_page(PAGE_TEXT))

        # Assert
        self.assertEqual((code, said), (0, "1 quotes, 1 found on the page they cite\n"))

    def test_a_quote_not_found_fails_and_names_it(self) -> None:
        # Arrange
        record = a_record(quote="OBJ 127")

        # Act
        code, said = run_main(record, a_page(PAGE_TEXT))

        # Assert
        self.assertEqual(
            (code, said),
            (
                1,
                "  facts/offset: not on page 7 of book.pdf\n"
                "1 quotes, 0 found on the page they cite\n",
            ),
        )

    def test_a_document_not_on_this_machine_is_named_and_nothing_is_checked(self) -> None:
        # Arrange
        record = a_record(quote="OAM ADDRESS")

        # Act
        code, said = run_main(record, a_page(""), book=False)

        # Assert
        self.assertEqual(
            (code, said), (0, "1 quotes, none checked: book.pdf is not on this machine\n")
        )

    def test_a_record_with_no_quote_fails_rather_than_passing_in_silence(self) -> None:
        # Arrange
        record: dict[str, Any] = {"documents": {}, "facts": {}}

        # Act
        code, said = run_main(record, a_page(PAGE_TEXT))

        # Assert
        self.assertEqual((code, said), (1, "0 quotes, 0 found on the page they cite\n"))


if __name__ == "__main__":
    unittest.main()
