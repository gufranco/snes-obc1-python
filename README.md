<div align="center">

<h1>OBC1</h1>

<strong>The sprite remapper one Super Nintendo cartridge carried, settled against its own reference in every state it has.</strong>

<br>
<br>

[![CI](https://github.com/gufranco/snes-obc1-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-obc1-python/actions/workflows/ci.yml)
[![Conformance](https://img.shields.io/badge/conformance-every%20state-brightgreen)](#is-it-right)
[![Coverage](https://img.shields.io/badge/coverage-100%25%20statement%20%2B%20branch-brightgreen)](#working-on-it)
[![Types](https://img.shields.io/badge/mypy-strict-blue)](pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

<p align="center">
  <a href="#install">Install</a> &nbsp;|&nbsp;
  <a href="#the-interface">The interface</a> &nbsp;|&nbsp;
  <a href="#the-two-things-that-are-easy-to-get-wrong">The two traps</a> &nbsp;|&nbsp;
  <a href="#the-reset-does-not-do-what-it-looks-like">The reset</a> &nbsp;|&nbsp;
  <a href="#is-it-right">Is it right</a> &nbsp;|&nbsp;
  <a href="https://github.com/gufranco/snes-obc1-python/issues">Issues</a>
</p>

**7** addresses · **256** states, all of them visited · **3,126** steps compared against the reference, **0** disagreements · **369** tests · **100%** statement and branch coverage · no dependencies

```python
from snesobc1 import Chip

chip = Chip("obc1")
chip.write(0x7FF6, 0x02)
for offset, value in enumerate((0x10, 0x20, 0x30, 0x40)):
    chip.write(0x7FF0 + offset, value)

print(chip.base + (0x02 << 2))
print(list(chip.ram[chip.base + 8 : chip.base + 12]))
```

```
6152
[16, 32, 48, 64]
```

The four bytes went to a place the program never named. That is the entire point
of the chip: a program writes one sprite's attributes to the same four addresses
every time and lets the pointer decide which sprite it was.

## Install

```bash
pip install git+https://github.com/gufranco/snes-obc1-python.git
```

Python 3.12 or newer. Nothing else at runtime.

A C++ compiler is needed only to build the reference the conformance walk compares
against, and only if you want to run that walk yourself.

## The interface

Everything a caller touches. Nothing else is public.

One model, and the constructor still takes it. A caller moving between members of
this family writes the same call everywhere, and a name this package does not
know is refused rather than ignored.

| Model | Also answers to | Is |
|:--|:--|:--|
| `obc1` | `obc-1`, `obc` | The sprite remapper one cartridge carried |

| Call | Does | Returns |
|:--|:--|:--|
| `Chip(model, ram=None)` | Builds a chip. Given an image, derives the window state from it rather than wiping it | a `Chip` |
| `chip.reset()` | Drives the reset line: every byte to `FF`, then the state read back out of what it just wrote | the `Chip` |
| `chip.adopt(ram)` | Takes an image into an existing chip and derives the state from it | the `Chip` |
| `chip.read(address)` | Reads, through the window where the address is one of the seven | `int` |
| `chip.write(address, value)` | Writes, through the window where the address is one of the seven | nothing |

| Attribute | Is |
|:--|:--|
| `chip.ram` | The eight kilobytes, as a `bytearray` |
| `chip.base` | Which of the two places the window currently sits over |
| `chip.address` | Where the pointer points |
| `chip.shift` | Which two bits of the shared byte `$7FF4` reaches |

`OutOfRange` is raised for an address the chip does not answer, rather than a
value being returned for it. On a real cartridge that address is decoded by
something else entirely, so answering it here would be this package inventing the
rest of the board.

There is no model argument. One cartridge carried this chip and there is no
second variant to choose between.

## What the chip does

Eight kilobytes of memory with seven addresses at the top that do not read or
write where they say.

| Address | What it reaches |
|:--------|:----------------|
| `$7FF0` to `$7FF3` | Four consecutive bytes at the place the pointer chooses |
| `$7FF4` | One byte a quarter as far along, two bits of it |
| `$7FF5` | Chooses between the two places the window can sit |
| `$7FF6` | The pointer, and the two bits `$7FF4` reaches |
| anything else | Itself |

## The two things that are easy to get wrong

**The pointer register does two jobs from one byte.** Its low seven bits choose
which sprite the window points at. Its low two bits, the same two, also choose
which corner of the shared byte `$7FF4` reaches. They are not separate fields, so
moving the pointer by one moves both.

```python
from snesobc1 import Chip

chip = Chip("obc1")
chip.write(0x7FF6, 0x05)

print(chip.address)
print(chip.shift)
```

```
5
2
```

**`$7FF4` is a read-modify-write inside the chip.** Four sprites share one byte,
two bits each, so a write there changes two bits and leaves the other six. A
model that writes the whole byte destroys three neighbours and looks correct
until four sprites are on screen at once.

```python
from snesobc1 import Chip

chip = Chip("obc1")

chip.write(0x7FF6, 0x01)
chip.write(0x7FF4, 0x00)
print(f"{chip.read(0x7FF4):#04x}")

chip.write(0x7FF6, 0x02)
chip.write(0x7FF4, 0x00)
print(f"{chip.read(0x7FF4):#04x}")
```

```
0xf3
0xc3
```

The reset leaves every byte at `FF`. Clearing through pointer 1 takes out bits 2
and 3 and leaves the other six standing; clearing through pointer 2 then takes
out bits 4 and 5 and leaves the first change intact. A model that wrote the whole
byte would show `0x00` twice and have destroyed three sprites to set one.

The read hands back the whole byte rather than the two bits, because that is what
the address answers. Extracting a corner is the caller's business, and the shift
to do it with is on the chip.

## The reset does not do what it looks like

Every write to a register is also written straight into memory at the address it
arrived on, underneath the remapping. That looks like it exists so a reset can
recover the state, and it does not.

The reset sets every byte to `FF` first, then reads the base and the pointer back
out of the bytes it just wrote. So it always comes up the same way, whatever the
cartridge held, and the read-back is vestigial. Modelling it as a recovery would
be modelling something the chip does not do, and the conformance walk checks
exactly this by leaving memory in a chosen state and confirming both sides ignore
it.

Restoring a saved cartridge is a different operation and is spelled differently:

```python
from snesobc1 import Chip

saved = bytearray(0x2000)
saved[0x1FF6] = 0x09

print(Chip("obc1", ram=saved).address)
print(Chip("obc1", ram=saved).reset().address)
```

```
9
127
```

`Chip(model, ram=...)` is this package's own, for tools that carry save states around.
The chip has no such button, and the reset forgets whatever the image held.

## Non-obvious decisions

- Memory is a plain `bytearray` rather than the sparse, seeded kind the processor
  packages in this family use. This chip's reset writes every byte before reading
  any, so there is no unwritten byte for a program to observe.
- The reference's two functions are lifted out by markers rather than the file
  being compiled whole. The rest of that file is a memory mapper that would drag
  in most of an emulator to reach two hundred lines.
- It is a part rather than a clocked part. It answers accesses and has no
  instruction to step through, so it carries none of the interface the family
  standard describes for something driven by a budget of cycles.

## Is it right

The chip is small enough that there is no need to sample it. Its state is a base,
one of two, and a pointer, one of a hundred and twenty eight. Every combination
is reachable in a few writes, so every combination is visited.

| Walk | Steps | What it settles |
|:-----|------:|:----------------|
| Every state | 3,076 | Each base and pointer, with all five window addresses written and read, then all eight kilobytes compared byte for byte |
| The reset | 50 | That the reset ignores whatever memory held, from ten different starting states |

```bash
python3 -m conformance.build
python3 -m conformance.exhaustive
```

```
  every state: 3,076 steps agreed
  the reset: 50 steps agreed
3,126 steps, 0 walks disagreed
```

The reference is not vendored. The build fetches [snes9x](https://github.com/snes9xgit/snes9x)
at a pinned commit and lifts the chip's two functions out of the file they share
with a memory mapper this has no use for. The markers that bound them come from
the pin, so a file whose text has moved fails loudly rather than yielding
something else.

A check that cannot fail proves nothing, so the runner is also shown to fail: the
tests point it at a driver that answers wrongly and confirm it says so.

[`conformance/hardware.json`](conformance/hardware.json) holds what this model
asserts and where each assertion comes from.
[`conformance/divergences.json`](conformance/divergences.json) holds where a
source is weaker than it looks, and [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md)
carries every place fidelity here is a claim rather than a measurement. The
largest of those is that no manufacturer document names this part at all, so the
top rung of the authority ladder is empty and the rung below it is doing the
work.

When a run disagrees with something on this machine:

```bash
python3 snesobc1/doctor.py
```

It looks at this machine and prints what is actually there, and every line is
something it looked at just now rather than something that ought to be true. A
check that fails says what it saw. A check that itself throws is reported as what
it threw rather than taking the report down with it. Paste all of it into an
issue.

## Working on it

```bash
python3 -m coverage erase
for file in $(find snesobc1 conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

Coverage is a gate, not a report: the build fails below 100% of statements and
branches. Types are `mypy` at strict. Everything under `conformance/` runs as a
module rather than as a script, because run as a script its own directory goes on
the import path and a file there shadows any standard library module of the same
name.

Each module has its test file beside it, named after it.

| File | Holds |
|:-----|:------|
| [`snesobc1/chip.py`](snesobc1/chip.py) | The memory, the window over it, and the seven addresses that move it |
| [`snesobc1/errors.py`](snesobc1/errors.py) | The one refusal this package makes, importing nothing from the package |
| [`snesobc1/doctor.py`](snesobc1/doctor.py) | What is actually on this machine, for an issue report |
| [`conformance/exhaustive.py`](conformance/exhaustive.py) | Every state the chip has, against the reference |
| [`conformance/build.py`](conformance/build.py) | Fetches the pinned reference and lifts the chip out of it |
| [`conformance/ref/driver.cpp`](conformance/ref/driver.cpp) | The driver that wraps those functions |
| [`conformance/hardware.json`](conformance/hardware.json) | What this model asserts, and where each assertion comes from |
| [`conformance/divergences.json`](conformance/divergences.json) | Where a source is weaker than it looks |
| [`conformance/speed.py`](conformance/speed.py) | The throughput floor |
| [`conformance/links.py`](conformance/links.py) | The weekly check that every cited address still answers |

| Convention | Source |
|:-----------|:-------|
| Commit format | [Conventional Commits](https://www.conventionalcommits.org/) |
| Format and lint | [ruff](https://docs.astral.sh/ruff/), configured in [pyproject.toml](pyproject.toml) |
| Releases | [semantic-release](https://semantic-release.gitbook.io/), from the commit history |
| Test naming | A sentence stating the behaviour, not the function name |

[`AGENTS.md`](AGENTS.md) is the document for an agent working here.
[`FAMILY.md`](FAMILY.md) is the standard this repository shares with the rest of
the family, kept identical in every member above the marker at the end of its
shared part.

Measurements first. [CONTRIBUTING.md](CONTRIBUTING.md) has the gates a change is
expected to pass, [SECURITY.md](SECURITY.md) says what belongs in a private
report, and the [Code of Conduct](CODE_OF_CONDUCT.md) applies wherever this
project is discussed.

Never attach a copyrighted file, and never link to somewhere one can be
downloaded. A digest identifies a file without carrying it.

## References

This repository carries no documents and no cartridges.

**No manufacturer document for this part is known to exist.** It was searched for
on 2026-08-21 and nothing was found; the chip appears in a single cartridge. That
leaves the top rung of the authority ladder empty, which is recorded in
[`conformance/hardware.json`](conformance/hardware.json) rather than papered over
by promoting the rung below it.

| Source | Used for |
|:-------|:---------|
| [Nintendo's documented OAM structure](https://archive.org/stream/SNESDevManual/book1_djvu.txt) | The shape of what this chip holds, which is the shape OAM expects. Where the two line up, Nintendo's figure is evidence about this chip even though Nintendo never described it |
| [snes9xgit/snes9x](https://github.com/snes9xgit/snes9x) | The reference the walk compares against, pinned by commit in [`conformance/pinned.json`](conformance/pinned.json). Fetched at build time, never vendored, and it is a second implementation rather than a measurement |

## Citing this

[CITATION.cff](CITATION.cff) is kept in step with the released version by the
same script that stamps the package, so the version it names is the version that
shipped.

## License

[MIT](LICENSE).

The reference implementation is a separate work under its own licence, fetched at
build time and never redistributed here.
