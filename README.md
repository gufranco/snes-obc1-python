# OBC1

The OBC1 sprite remapper from one Super Nintendo cartridge in Python, compared against a pinned snes9x build in every state it has.

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-obc1-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-obc1-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-obc1-python)](https://github.com/gufranco/snes-obc1-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**7** addresses, **256** states, all of them visited, **3,126** steps compared against the reference, **0** disagreements, **612** tests, **100%** statement and branch coverage, no dependencies

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

The program sets the pointer to sprite 2 and writes four bytes to `$7FF0` through `$7FF3`. They land at offset 6152 of the chip's memory, 8 bytes past the base the reset selected. A game writes every sprite's four attribute bytes to the same four addresses and moves the pointer between sprites.

## Install

| Requirement | Version |
|:--|:--|
| Python | 3.12 or newer |
| git | Any, to fetch the submodule |
| A C++17 compiler, `g++` | Only to build the reference for the conformance walk |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-obc1-python.git
cd snes-obc1-python
python3 snesobc1/doctor.py
```

The package imports nothing outside the standard library. The submodule is `snes-driver-python`, and only [`conformance/against_cartridges.py`](conformance/against_cartridges.py) uses it.

The doctor checks the machine and the checkout and ends with one line. It exits 0 when every check passes and 1 otherwise. Paste its whole output into any bug report.

```
  7 checks, nothing to report
```

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/snes-obc1-python/releases).

## The interface

`snesobc1.Chip(model, ram=None)` builds one chip. `model` is required. Without `ram` the chip runs its reset. With `ram`, a `bytearray` of 8,192 bytes, the chip copies it and derives the base and the pointer from the copy without wiping anything. The real chip has no such input; `ram` exists for tools that carry save states.

| Model | Aliases | Window | Memory |
|:--|:--|:--|:--|
| `obc1` | `obc-1`, `obc` | `$6000` to `$7FFF` | 8,192 bytes |

A model name is matched without regard to case, hyphens, underscores or spaces, so `Chip("OBC-1")` builds the same chip.

### Calls

| Call | Effect |
|:--|:--|
| `reset()` | Sets all 8,192 bytes to `FF`, then reads the base and the pointer back out of them. Returns the chip |
| `adopt(ram)` | Copies `ram` into the chip and derives the base and the pointer from it. Returns the chip |
| `read(address)` | Returns one byte. `$7FF0` to `$7FF4` read through the window; every other address reads its own byte |
| `write(address, value)` | Writes the low 8 bits of `value`. `$7FF0` to `$7FF6` also store the byte at their own offset, under the remapping. Returns `None` |

### State

| Attribute | Meaning |
|:--|:--|
| `ram` | The 8,192 bytes as a `bytearray`. Index 0 is address `$6000` |
| `base` | Offset of the sprite table the window sits over: `0x1800` or `0x1C00` |
| `address` | The pointer, 0 to 127 |
| `shift` | The bit position in the shared byte that `$7FF4` reaches: 0, 2, 4 or 6 |
| `model` | The canonical model name |

### Module contents

| Name | Content |
|:--|:--|
| `snesobc1.MODELS` | The `Model` records, keyed by canonical name |
| `snesobc1.Model` | A record with `name`, `aliases` and `summary`. `build(ram=None)` returns a chip |
| `snesobc1.models.lookup(name)` | Returns the `Model` a name or alias matches, under the same matching as `Chip`. Raises `UnknownModelError` otherwise |
| `snesobc1.UnknownModelError` | Raised when no model is named, or the name matches no model. The message lists the models there are |
| `snesobc1.OutOfRange` | Raised by `read` and `write` for an address below `$6000` or above `$7FFF` |
| `snesobc1.__version__` | The installed version |
| `snesobc1.chip` | The constants behind the addresses: `WINDOW_START`, `WINDOW_END`, `RAM_BYTES`, `BASE_HIGH`, `BASE_LOW`, `PACKED_OFFSET`, `FIRST_REGISTER`, `PACKED_REGISTER`, `BASE_REGISTER`, `POINTER_REGISTER`, `ADDRESS_MASK`, `PACKED_MASK`, `UNWRITTEN` |

```python
import snesobc1

for name, model in snesobc1.MODELS.items():
    print(name, model.aliases, model)

chip = snesobc1.Chip("OBC-1")
print(chip, chip.model)

for named in (None, "obc2"):
    try:
        snesobc1.Chip(named)
    except snesobc1.UnknownModelError as error:
        print(error)

try:
    chip.read(0x8000)
except snesobc1.OutOfRange as error:
    print(error)
```

```
obc1 ('obc-1', 'obc') <Model obc1, answering at 0x6000>
<OBC1 base 0x1800 pointer 0x7f shift 6> obc1
no model was named, and this package will not choose one for you. Name one of: obc1
no model called 'obc2'; this package publishes obc1
0x8000 is not an address this chip answers
```

An address outside the window raises `OutOfRange` instead of returning a value. On a cartridge, another part of the board decodes that address.

### Reading and writing the registers

```python
from snesobc1 import Chip

chip = Chip("obc1")
chip.write(0x7FF5, 0x00)
chip.write(0x7FF6, 0x7F)
chip.write(0x7FF3, 0x12)
print(hex(chip.base), chip.address, chip.shift)
print(hex(chip.read(0x7FF3)), hex(chip.ram[0x1C00 + 0x7F * 4 + 3]))
print(hex(chip.read(0x7FF5)), hex(chip.read(0x7FF6)), hex(chip.read(0x6000)))
chip.write(0x6000, 0x1FF)
print(hex(chip.read(0x6000)))
```

```
0x1c00 127 6
0x12 0x12
0x0 0x7f 0xff
0xff
```

Bit 0 of `$7FF5` selects the base: 0 gives `0x1C00`, 1 gives `0x1800`. The byte written to `$7FF3` lands at the last byte of sprite 127's entry. `$7FF5` and `$7FF6` read back the byte last written to them. A value wider than 8 bits keeps its low 8.

### Command-line tools

Every tool runs from the repository root.

| Command | Arguments | Exit codes |
|:--|:--|:--|
| `python3 snesobc1/doctor.py` | None | 0 when every check passes, 1 otherwise |
| `python3 -m conformance.build` | `--sources DIR`, `--output PATH`, `--pinned FILE`, `--driver-source FILE` | 0 built, 1 the compiler failed, 2 a bad option, a failed fetch, a missing `obc1.cpp` or missing markers |
| `python3 -m conformance.exhaustive` | `--driver PATH` | 0 no disagreement, 1 a walk disagreed, 2 no driver, a driver that exited nonzero, or a bad option |
| `python3 -m conformance.speed` | None | 0 at or above the floor, 1 below it |
| `python3 -m conformance.documents` | `--check`, `--only SUBSTRING` | 0 every document verified, 1 one refused, none matched, or a bad option |
| `python3 -m conformance.against_cartridges` | `CARTRIDGES OUTPUT` | 0 registers reached, 1 none reached, 2 fewer than two arguments, no directory, or no cartridge with the part |
| `python3 -m conformance.package` | `WHEEL` | 0 every module shipped and no test, 1 a fault or no file, 2 no argument |
| `python3 -m conformance.links` | None | 0 every address answers, 1 one is gone |
| `python3 -m conformance.quotes` | None | 0 every quote is on the page it cites, or the document is not on this machine, 1 a quote is not there or the record quotes nothing |

An installed copy also provides `snesobc1-doctor`, which runs the same checks.

## What the chip does

The chip holds 8,192 bytes. Seven addresses at the top of its window do not read or write the byte they name.

| Address | What it reaches |
|:--|:--|
| `$7FF0` to `$7FF3` | Four consecutive bytes at `base + pointer * 4` |
| `$7FF4` | Two bits of the byte at `base + 0x200 + pointer // 4` |
| `$7FF5` | Bit 0 chooses the base, `0x1800` or `0x1C00` |
| `$7FF6` | The pointer, and the two bits `$7FF4` reaches |
| Any other address from `$6000` to `$7FFF` | Its own byte |

## The two things that are easy to get wrong

**The pointer register does two jobs from one byte.** Its low 7 bits choose which sprite the window points at. Its low 2 bits, the same two, also choose which pair of bits in the shared byte `$7FF4` reaches. Moving the pointer by one moves both.

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

**`$7FF4` is a read-modify-write inside the chip.** Four sprites share one byte, 2 bits each. A write there changes 2 bits and leaves the other 6.

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

The reset leaves every byte at `FF`. Clearing through pointer 1 clears bits 2 and 3. Clearing through pointer 2 then clears bits 4 and 5 and keeps the first change. A model that wrote the whole byte would print `0x00` twice and erase three other sprites' bits.

The read returns the whole byte. To extract one sprite's 2 bits, shift right by `chip.shift` and mask with 3.

## The reset does not do what it looks like

A write to a register also stores the byte at the register's own offset, under the remapping. The reset does not use those bytes to recover the state. It sets every byte to `FF` first, then reads the base and the pointer from the bytes it just wrote, so it always ends with base `0x1800`, pointer 127 and shift 6. The conformance walk checks this from 10 starting states.

Restoring a saved image is a separate call:

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

`Chip(model, ram=...)` reads pointer 9 out of the saved image. `reset()` discards the image and reads pointer 127.

## Non-obvious decisions

- Memory is a plain `bytearray`, not the scrambled memory the processor members of this family use. The reset writes every byte before anything reads one, so no unwritten byte is observable.
- [`conformance/build.py`](conformance/build.py) lifts the two OBC1 functions out of snes9x's `obc1.cpp` between two markers instead of compiling the file whole. The rest of that file is a memory mapper that needs most of the emulator to build.
- The package is a part, not a clocked part. It answers accesses and has no instruction to step, so it has no `step`, `run_for` or cycle counters.

## Is it right

The state is a base, one of 2, and a pointer, one of 128. Every one of the 256 combinations is reachable in a few writes, so the walk visits all of them.

| Walk | Steps | What it compares |
|:--|--:|:--|
| Every state | 3,076 | Each base and pointer, with all five window addresses written and read, then all 8,192 bytes byte for byte |
| The reset | 50 | That the reset ignores what memory held, from 10 starting states |

```bash
python3 -m conformance.build
python3 -m conformance.exhaustive
```

```
  every state: 3,076 steps agreed
  the reset: 50 steps agreed
3,126 steps, 0 walks disagreed
```

The build fetches [snes9x](https://github.com/snes9xgit/snes9x) at the commit pinned in [`conformance/pinned.json`](conformance/pinned.json) and compiles the two functions with [`conformance/ref/driver.cpp`](conformance/ref/driver.cpp). It fails when the pinned file no longer holds the markers. The tests also point the runner at a driver that answers wrongly and confirm it reports the disagreement.

snes9x is a second implementation, not a measurement of the chip. Agreement with it shows the two implementations match.

The cartridge's own code is a second source for the register addresses. [`conformance/against_cartridges.py`](conformance/against_cartridges.py) walks the driver routine in both releases of the one cartridge without running it. Together they reach six of the seven registers: `$7FF0` to `$7FF3`, `$7FF5` and `$7FF6`. [`conformance/cartridges.json`](conformance/cartridges.json) holds that reading with the digests of both cartridges and none of their bytes. A walk sees only instructions that carry the whole address, so `$7FF4` going unreached does not show it is absent.

[`conformance/hardware.json`](conformance/hardware.json) holds each value this model asserts and where it comes from. Only the packed offset, `0x200`, comes from a document: Nintendo's OAM layout of 128 sprites of 4 bytes. Every other value comes from the reference. No manufacturer document names this part. [`conformance/divergences.json`](conformance/divergences.json) records where the sources are weak, and [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) lists the 3 open questions with what would settle each.

`python3 -m conformance.speed` reads through the window 20,000 times, 5 times over, and fails below 500,000 reads per second.

## Working on it

| Need | Where |
|:--|:--|
| Every gate and the order to run them | [CONTRIBUTING.md](CONTRIBUTING.md) |
| The same material for a coding agent | [AGENTS.md](AGENTS.md) |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md) |
| Bug reports | [GitHub Issues](https://github.com/gufranco/snes-obc1-python/issues) |
| Security reports | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 -m coverage erase
for file in $(find snesobc1 conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

Each module has a test file beside it, named after it. Coverage is a hard gate at 100% statement and branch. Everything under `conformance/` runs as a module, because a script's own directory goes first on the import path and a file there would shadow a standard library module of the same name.

## References

- snes9x, `obc1.cpp` at commit `2971061cf07fdc6fc7d18883edf4e648eb16a6d2`, https://github.com/snes9xgit/snes9x. The reference the walk compares against. It is fetched at build time and never carried here.
- *SNES Development Manual, Book I*, Nintendo of America Inc. 240 pages, 21,022,582 bytes, SHA-256 `f1405241000046abba7849376d2ec53cf85f1ad2e9950d69a7c2cf1f3ff6b791`. Its OAM structure gives the packed offset. It is not redistributable and is not in this repository. `python3 -m conformance.documents` downloads it from https://archive.org/download/SNESDevManual/book1_text.pdf into `docs/`, which git ignores, and refuses any other file. `--check` verifies a copy already there.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE). snes9x is a separate work under its own licence, fetched at build time and not redistributed.
