import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import exhaustive

BUILT = Path(exhaustive.DEFAULT_DRIVER)

HAS_DRIVER = BUILT.exists()


class WalkTest(unittest.TestCase):
    def test_the_walk_visits_every_base_and_every_pointer(self) -> None:
        steps = exhaustive.walk()
        pointers = {second for verb, first, second in steps if first == 0x7FF6 and verb == "w"}

        self.assertEqual(len(pointers), 0x80)

    def test_it_exercises_every_window_address(self) -> None:
        steps = exhaustive.walk()
        written = {first for verb, first, _ in steps if verb == "w"}

        for register in exhaustive.WINDOW_REGISTERS:
            self.assertIn(register, written)

    def test_it_ends_by_comparing_the_whole_memory(self) -> None:
        self.assertEqual(exhaustive.walk()[-1][0], "dump")

    def test_the_reset_walk_leaves_state_behind_before_resetting(self) -> None:
        steps = exhaustive.resetting()

        self.assertEqual(steps[0][0], "poke")
        self.assertIn(("reset", 0, 0), steps)


class RenderTest(unittest.TestCase):
    def test_a_read_carries_only_its_address(self) -> None:
        self.assertEqual(exhaustive.render([("r", 0x7FF0, 0)]), "r 32752\n")

    def test_a_write_carries_both(self) -> None:
        self.assertEqual(exhaustive.render([("w", 0x7FF0, 5)]), "w 32752 5\n")

    def test_a_step_with_no_operand_is_a_word_on_its_own(self) -> None:
        self.assertEqual(exhaustive.render([("dump", 0, 0)]), "dump\n")

    def test_a_reset_is_a_word_on_its_own(self) -> None:
        self.assertEqual(exhaustive.render([("reset", 0, 0)]), "reset\n")

    def test_a_poke_carries_both(self) -> None:
        self.assertEqual(exhaustive.render([("poke", 1, 2)]), "poke 1 2\n")


class ReplayTest(unittest.TestCase):
    def test_a_read_produces_one_line(self) -> None:
        self.assertEqual(len(exhaustive.replay([("r", 0x6000, 0)])), 1)

    def test_a_write_produces_none(self) -> None:
        self.assertEqual(exhaustive.replay([("w", 0x6000, 5)]), [])

    def test_a_dump_produces_the_whole_memory(self) -> None:
        self.assertEqual(len(exhaustive.replay([("dump", 0, 0)])[0]), 0x4000)

    def test_a_state_line_names_the_base_the_pointer_and_the_shift(self) -> None:
        found = exhaustive.replay([("w", 0x7FF6, 0x03), ("state", 0, 0)])

        self.assertEqual(found[0].split()[1:], ["0003", "0006"])

    def test_a_poke_reaches_memory_without_going_through_the_window(self) -> None:
        found = exhaustive.replay([("poke", 0, 0x42), ("r", 0x6000, 0)])

        self.assertEqual(found[0], "42")

    def test_a_reset_ignores_the_pointer_the_memory_held(self) -> None:
        script = [("poke", 0x1FF6, 0x09), ("reset", 0, 0), ("state", 0, 0)]

        self.assertEqual(exhaustive.replay(script)[0].split()[1], "007F")

    def test_a_plain_reset_clears_the_memory_to_what_a_reset_leaves(self) -> None:
        found = exhaustive.replay([("poke", 0, 0x00), ("reset", 0, 0), ("r", 0x6000, 0)])

        self.assertEqual(found[0], "FF")


class ComparisonTest(unittest.TestCase):
    def test_two_identical_transcripts_report_nothing(self) -> None:
        self.assertEqual(exhaustive.differences(["AA"], ["AA"]), [])

    def test_a_line_that_differs_is_named_with_its_number(self) -> None:
        self.assertEqual(exhaustive.differences(["AA", "BB"], ["AA", "CC"]), [(1, "BB", "CC")])

    def test_a_transcript_that_stops_early_is_reported(self) -> None:
        self.assertEqual(exhaustive.differences(["AA", "BB"], ["AA"])[0][0], 1)


class OptionTest(unittest.TestCase):
    def test_the_default_driver_is_enough(self) -> None:
        self.assertEqual(exhaustive.options([]).driver, exhaustive.DEFAULT_DRIVER)

    def test_the_driver_can_be_pointed_elsewhere(self) -> None:
        self.assertEqual(exhaustive.options(["--driver", "here"]).driver, "here")

    def test_an_option_with_no_value_is_refused(self) -> None:
        with self.assertRaises(exhaustive.Usage):
            exhaustive.options(["--driver"])

    def test_an_option_it_does_not_know_is_refused(self) -> None:
        with self.assertRaises(exhaustive.Usage):
            exhaustive.options(["--nonsense"])


class DriverTest(unittest.TestCase):
    def scripted(self, body: str) -> Path:
        where = Path(tempfile.mkdtemp()) / "fake"
        where.write_text(body)
        where.chmod(where.stat().st_mode | stat.S_IXUSR)
        return where

    def test_a_driver_that_fails_is_reported_rather_than_read_as_agreement(self) -> None:
        with self.assertRaises(exhaustive.Usage):
            exhaustive.ask([("dump", 0, 0)], "/usr/bin/false")

    def test_a_driver_that_answers_differently_makes_the_run_fail(self) -> None:
        wrong = self.scripted(
            "#!/bin/sh\nwhile read -r line; do\n  case $line in\n  r*|dump*|state*) echo ZZ ;;\n  esac\ndone\n"
        )

        self.assertEqual(exhaustive.run(["--driver", str(wrong)]), 1)


@unittest.skipUnless(HAS_DRIVER, "the reference driver is not built")
class AgainstReferenceTest(unittest.TestCase):
    def test_the_model_agrees_with_the_reference_in_every_state(self) -> None:
        steps = exhaustive.walk()

        self.assertEqual(
            exhaustive.differences(exhaustive.ask(steps, str(BUILT)), exhaustive.replay(steps)), []
        )

    def test_and_on_what_a_reset_leaves_behind(self) -> None:
        steps = exhaustive.resetting()

        self.assertEqual(
            exhaustive.differences(exhaustive.ask(steps, str(BUILT)), exhaustive.replay(steps)), []
        )

    def test_a_full_run_reports_clean(self) -> None:
        self.assertEqual(exhaustive.run([]), 0)


class EntryTest(unittest.TestCase):
    def test_a_run_with_no_driver_present_says_so_rather_than_passing(self) -> None:
        self.assertEqual(exhaustive.main(["--driver", "/nowhere/at/all"]), 2)

    def test_an_option_it_does_not_know_is_reported(self) -> None:
        self.assertEqual(exhaustive.main(["--nonsense"]), 2)


if __name__ == "__main__":
    unittest.main()
