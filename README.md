<div align="center">

<h1>OBC1</h1>

<strong>The sprite remapper one Super Nintendo cartridge carried, settled against its own reference in every state it has.</strong>

<br>
<br>

[![CI](https://github.com/gufranco/snes-obc1-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-obc1-python/actions/workflows/ci.yml)
[![Conformance](https://img.shields.io/badge/conformance-every%20state-brightgreen)](#how-this-is-settled)
[![Coverage](https://img.shields.io/badge/coverage-100%25%20statement%20%2B%20branch-brightgreen)](#tests)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

<p align="center">
  <a href="#quick-start">Quick start</a> &nbsp;|&nbsp;
  <a href="#what-the-chip-does">What it does</a> &nbsp;|&nbsp;
  <a href="#how-this-is-settled">How this is settled</a> &nbsp;|&nbsp;
  <a href="#the-reset-does-not-do-what-it-looks-like">The reset</a> &nbsp;|&nbsp;
  <a href="https://github.com/gufranco/snes-obc1-python/issues">Issues</a>
</p>

**7** addresses · **256** states, all of them visited · **3,126** steps agreeing with the reference · **84** tests · **100%** statement and branch coverage

```python
from snesobc1 import Obc1

chip = Obc1()
chip.write(0x7FF6, 0x02)
chip.write(0x7FF0, 0xAA)
```

## Quick start

### Prerequisites

| Tool | Version | Install |
|:-----|:--------|:--------|
| Python | 3.12 or newer | [python.org](https://www.python.org/downloads/) |
| A C++ compiler | any recent | only for running the conformance comparison |

### Install

```bash
pip install git+https://github.com/gufranco/snes-obc1-python.git
```

### Point the window somewhere and write through it

```python
from snesobc1 import Obc1

chip = Obc1()
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

Two things are easy to get wrong.

**The pointer register does two jobs from one byte.** Its low seven bits choose
which sprite the window points at. Its low two bits, the same two, also choose
which corner of the shared byte `$7FF4` reaches. They are not separate fields, so
moving the pointer by one moves both.

**`$7FF4` is a read-modify-write inside the chip.** Four sprites share one byte,
two bits each, so a write there changes two bits and leaves the other six. A
model that writes the whole byte destroys three neighbours and looks correct
until four sprites are on screen at once.

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
chip = Obc1(ram=saved)  # derives the state from the image
chip.reset()  # forgets it, as the reset line does
```

`Obc1(ram=...)` is this package's own, for tools that carry save states around.
The chip has no such button.

## How this is settled

The chip is small enough that there is no need to sample it. Its state is a base,
one of two, and a pointer, one of a hundred and twenty eight. Every combination
is reachable in a few writes, so every combination is visited.

| Walk | Steps | What it settles |
|:-----|------:|:----------------|
| Every state | 3,076 | Each base and pointer, with all five window addresses written and read, then all eight kilobytes compared byte for byte |
| The reset | 50 | That the reset ignores whatever memory held, from ten different starting states |

```bash
python conformance/build.py
python conformance/exhaustive.py
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

## Layout

| File | Holds |
|:-----|:------|
| [`snesobc1/chip.py`](snesobc1/chip.py) | The memory, the window over it, and the seven addresses that move it |
| [`conformance/exhaustive.py`](conformance/exhaustive.py) | Every state the chip has, against the reference |
| [`conformance/build.py`](conformance/build.py) | Fetches the pinned reference and lifts the chip out of it |
| [`conformance/ref/driver.cpp`](conformance/ref/driver.cpp) | The driver that wraps those functions |

## For contributors and reviewers

### Running the tests

Each module has its test file beside it, named after it.

```bash
python -m coverage erase
for file in $(find snesobc1 conformance -name '*.test.py' | sort); do
  python -m coverage run -a "$file"
done
python -m coverage report
```

Coverage is a gate, not a report: the build fails below 100% of statements and
branches.

### Project conventions

| Convention | Source |
|:-----------|:-------|
| Commit format | [Conventional Commits](https://www.conventionalcommits.org/) |
| Format and lint | [ruff](https://docs.astral.sh/ruff/), configured in [pyproject.toml](pyproject.toml) |
| Releases | [semantic-release](https://semantic-release.gitbook.io/), from the commit history |
| Test naming | A sentence stating the behaviour, not the function name |

### Non-obvious decisions

- Memory is a plain `bytearray` rather than the sparse, seeded kind the processor
  packages in this family use. This chip's reset writes every byte before reading
  any, so there is no unwritten byte for a program to observe.
- The reference's two functions are lifted out by markers rather than the file
  being compiled whole. The rest of that file is a memory mapper that would drag
  in most of an emulator to reach two hundred lines.
- There is no model argument. One cartridge carried this chip and there is no
  second variant to choose between.

## When something is wrong

```bash
python3 -m snesobc1.doctor
```

It looks at this machine and prints what is actually there, and every line is
something it looked at just now rather than something that ought to be true. A
check that fails says what it saw. A check that itself throws is reported as what
it threw rather than taking the report down with it. Paste all of it into an
issue.

## Contributing

Measurements first. [CONTRIBUTING.md](CONTRIBUTING.md) has the gates a change is
expected to pass, [SECURITY.md](SECURITY.md) says what belongs in a private
report, and the [Code of Conduct](CODE_OF_CONDUCT.md) applies wherever this
project is discussed.

Never attach a copyrighted file, and never link to somewhere one can be
downloaded. A digest identifies a file without carrying it.

## Citing this

[CITATION.cff](CITATION.cff) is kept in step with the released version by the
same script that stamps the package, so the version it names is the version that
shipped.

## Licence

[MIT](LICENSE).

The reference implementation is a separate work under its own licence, fetched at
build time and never redistributed here.
