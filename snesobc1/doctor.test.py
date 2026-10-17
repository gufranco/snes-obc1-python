import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesobc1 import doctor

SOURCE = Path(doctor.__file__).resolve()

VERDICT = re.compile(r"^  (\d+ checks, nothing to report|\d+ of \d+ checks did not pass)$")


def a_finding(
    name: str = "something", ok: bool = True, detail: str = "detail", advice: str | None = None
) -> Any:
    return doctor.Finding(name, ok, detail, advice)


class FindingTest(unittest.TestCase):
    def test_a_finding_says_what_was_checked_and_whether_it_was_well(self) -> None:
        # Arrange
        name = "the window"

        # Act
        found = a_finding(name=name, ok=False)

        # Assert
        self.assertEqual((found.name, found.ok), ("the window", False))

    def test_a_healthy_finding_prints_with_a_mark_that_says_so(self) -> None:
        # Arrange
        found = a_finding(ok=True, detail="8192 bytes")

        # Act
        line = found.line

        # Assert
        self.assertEqual(line, "  ok    something: 8192 bytes")

    def test_and_an_unhealthy_one_prints_differently(self) -> None:
        # Arrange
        found = a_finding(ok=False)

        # Act
        line = found.line

        # Assert
        self.assertEqual(line, "     !  something: detail")

    def test_an_unhealthy_finding_says_what_to_do_about_it(self) -> None:
        # Arrange
        found = a_finding(ok=False, advice="go and look")

        # Act
        report = found.report

        # Assert
        self.assertEqual(report, "     !  something: detail\n         go and look")

    def test_a_healthy_one_carries_no_advice(self) -> None:
        # Arrange
        found = a_finding(ok=True, advice="x")

        # Act
        report = found.report

        # Assert
        self.assertEqual(report, found.line)

    def test_a_finding_prints_as_itself(self) -> None:
        # Arrange
        found = a_finding()

        # Act
        printed = repr(found)

        # Assert
        self.assertEqual(printed, "<Finding something ok>")


class ReportTest(unittest.TestCase):
    def test_the_report_has_a_line_for_every_finding(self) -> None:
        # Arrange
        found = [a_finding(name="first"), a_finding(name="second")]

        # Act
        lines = doctor.report(found)

        # Assert
        start = lines.index("  this package") + 1
        self.assertEqual(
            lines[start : start + 3], ["  ok    first: detail", "  ok    second: detail", ""]
        )

    def test_it_opens_with_something_that_says_what_it_is(self) -> None:
        # Arrange
        found = [a_finding()]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertTrue(lines[0].startswith(f"snesobc1 {doctor.VERSION} on "), lines[0])

    def test_an_unhealthy_run_says_how_many_did_not_pass(self) -> None:
        # Arrange
        found = [a_finding(ok=False), a_finding(ok=True)]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertEqual(lines[-1], "  1 of 2 checks did not pass")

    def test_a_healthy_run_says_there_is_nothing_to_report(self) -> None:
        # Arrange
        found = [a_finding(ok=True)]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertEqual(lines[-1], "  1 checks, nothing to report")


class EntryTest(unittest.TestCase):
    def test_a_healthy_run_reports_success_and_prints_the_report(self) -> None:
        # Arrange
        said: list[str] = []

        # Act
        code = doctor.main([], examine=lambda **_: [a_finding(ok=True)], say=said.append)

        # Assert
        self.assertEqual((code, said[-1]), (0, "  1 checks, nothing to report"))

    def test_an_unhealthy_one_reports_failure(self) -> None:
        # Arrange
        said: list[str] = []

        # Act
        code = doctor.main([], examine=lambda **_: [a_finding(ok=False)], say=said.append)

        # Assert
        self.assertEqual((code, said[-1]), (1, "  1 of 1 checks did not pass"))

    def test_a_real_run_says_something_about_this_machine(self) -> None:
        # Arrange
        said: list[str] = []

        # Act
        doctor.main([], say=said.append)

        # Assert
        self.assertRegex(said[-1], VERDICT)


class TheDoctorRunsAsTheReadmeSaysTest(unittest.TestCase):
    def test_running_it_as_a_file_from_elsewhere_prints_a_report_rather_than_a_traceback(
        self,
    ) -> None:
        # Arrange
        elsewhere = tempfile.mkdtemp()
        environment = {name: value for name, value in os.environ.items() if name != "PYTHONPATH"}

        # Act
        finished = subprocess.run(
            [sys.executable, str(SOURCE)],
            capture_output=True,
            text=True,
            cwd=elsewhere,
            env=environment,
            check=False,
        )

        # Assert
        self.assertEqual(
            (finished.returncode in (0, 1), "Traceback" in finished.stderr), (True, False)
        )
        self.assertRegex(finished.stdout.splitlines()[-1], VERDICT)


if __name__ == "__main__":
    unittest.main()
