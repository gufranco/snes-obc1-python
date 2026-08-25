# Working in this repository

This file is for a coding agent. A person reading it will not be harmed, but
[README.md](README.md) is the document written for them.

## What this project is, in one paragraph

The OBC1: eight kilobytes of memory with seven addresses at the top that do not
read or write where they say. It holds sprite attributes and hands the console a
moving window onto them, so a program can write one sprite's four bytes to the
same four addresses every time and let a pointer decide which sprite it was. The
state space is small enough to exhaust, so it is: every base and every pointer,
3,126 accesses compared against a second implementation with no disagreements.
No manufacturer document for the part is known to exist.

## The interface a caller drives

The chip answers accesses. There is no clock, no instruction to step through and
no cycle count to hand back, so none of the family's clocked interface appears
here.

- `Obc1()` builds a chip and resets it. `Obc1(ram=image)` takes an image and
  derives the window state from it without wiping, which is this package's own
  and not something the chip offers.
- `chip.reset()` is the reset line: every byte to `FF`, then the base and the
  pointer read back out of the bytes it just wrote.
- `chip.read(address)` and `chip.write(address, value)` go through the window
  where the address is one of the seven, and reach memory directly where it is
  not.
- `chip.base`, `chip.address` and `chip.shift` are the derived state. They are
  read from memory rather than kept beside it, which is why `adopt` works at all.

Everything the package raises lives in [`snesobc1/errors.py`](snesobc1/errors.py)
and nowhere else, and that module imports nothing from the package so it can
never be the far end of a cycle. There is one exception, because the chip makes
one refusal.

## The authority ladder

Every factual question is answered by the highest rung that has an answer, and a
lower rung never overrules a higher one.

1. **Manufacturer documentation.** There is none for this part. That is not a
   gap somebody has not filled in yet; it was searched for on 2026-08-21 and
   nothing was found, and the chip appears in a single cartridge.
2. **Nintendo's documented OAM structure**, for anything this chip's layout
   mirrors. This chip exists to feed OAM, so the shape of what it holds is the
   shape OAM expects, and that is documented. The packed offset is `0x200`
   because 128 sprites times four bytes is 512, and that is the one constant here
   that does not rest on a reimplementation.
3. **The reference implementation**, for everything else: every register address,
   both base addresses, the memory size.
4. **Anything else.** Nothing is cited from below rung three.

Rung three is doing most of the work, and the record says so rather than
promoting it. A second implementation written by reading one cartridge is one
lineage, not two.

## What is settled and what is not

**Settled: every state, against the reference.** Two bases and a hundred and
twenty eight pointers, each visited, with all five window addresses written and
read and all eight kilobytes compared byte for byte. 3,076 steps, no
disagreements.

**Settled: the reset is not a recovery.** Fifty steps from ten different starting
states confirm both sides ignore whatever memory held.

**Settled: the packed offset.** From Nintendo's OAM layout rather than from the
reference, which is why it is the only figure here that survives the reference
being wrong.

**Not settled: 3 things**, each in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with
what would close it. Two of them are the same shape: one cartridge and one
reimplementation cannot constrain what the chip does in a state that cartridge
never reaches. Do not close one by argument.

## The pointer register does two jobs from one byte

Its low seven bits choose which sprite the window points at. Its low two bits,
the same two, also choose which corner of the shared byte `$7FF4` reaches. They
are not separate fields, so moving the pointer by one moves both. A change that
treats them as separate will pass every test that writes through `$7FF0` to
`$7FF3` and fail only where four sprites share a byte.

## `$7FF4` is a read-modify-write inside the chip

Four sprites share one byte, two bits each, so a write there changes two bits and
leaves the other six. Writing the whole byte destroys three neighbours and looks
correct until four sprites are on screen at once. The read hands back the whole
byte, because that is what the address answers; extracting a corner is the
caller's business.

## Every gate, in the order to run them

```bash
ruff format --check .
ruff check .
mypy
pnpm run format:check
python3 -m coverage erase
for file in $(find snesobc1 conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

Then the throughput floor, which runs outside the coverage step because a tracer
costs about ten times what the model does:

```bash
python3 -m conformance.speed
```

The conformance walk needs the reference, which is fetched rather than vendored
and needs a C++ compiler:

```bash
python3 -m conformance.build
python3 -m conformance.exhaustive
```

Everything under `conformance/` runs as a module. Run as a script, its own
directory goes on the import path and a file there shadows any standard library
module of the same name.

## Conventions that are not negotiable

| Thing | Rule |
|:------|:-----|
| Language | Python only |
| Comments | None in source. Docstrings carry the reasoning |
| Test layout | `<module>.test.py` beside the module it covers |
| Test shape | Arrange, blank line, one act, blank line, assert. No section labels |
| Coverage | 100% statements and branches, enforced |
| Types | `mypy` at strict, plus every optional error class |
| Commits | Conventional Commits, subject under 50 characters |
| The reference | Fetched and pinned by commit, never vendored |
| Documents | There are none to pin. The record says that rather than leaving it blank |
| Fidelity | Where the chip and convenience disagree, the chip wins |
| Public API | This and the rest of the family present the same shape where the hardware allows. See [FAMILY.md](FAMILY.md) |

## Layout

```
snesobc1/
  chip.py        the memory, the window over it, and the seven addresses that move it
  errors.py      the one refusal this package makes, importing nothing from it
  doctor.py      what is actually on this machine, for an issue report
  version.py     rewritten by the release job and by nothing else
conformance/
  pinned.json    which reference, at which commit, and the markers that bound it
  build.py       fetching it and lifting the chip's two functions out
  exhaustive.py  every state the chip has, against that reference
  ref/driver.cpp the driver that wraps those two functions
  hardware.json  what this model asserts, and where each assertion comes from
  divergences.json  where a source is weaker than it looks
  links.py       the weekly check that every cited address still answers
  speed.py       the throughput floor
```

## Things that will bite you

**The reference is a lineage, not a measurement.** It agrees with this model
everywhere, and that is what an exhaustive walk between two implementations can
tell you. It cannot tell you either of them is the chip. Do not write a sentence
anywhere in this repository that treats agreement with it as verification against
hardware.

- **`conformance/ref/` is built, not committed.** The fetched source is somebody
  else's work under its own licence. A test that reads it and does not say so
  when it is absent passes here and fails everywhere else.
- **The markers that bound the two functions come from the pin.** A file whose
  text has moved fails loudly rather than yielding something else, and that is on
  purpose. If the build starts failing after a bump, read the upstream commit
  that moved the text before touching the markers.
- **The reset looks like a recovery and is not.** Every write to a register also
  lands in memory underneath the remapping, which looks like it exists so the
  state can be restored. The reset overwrites all of it first, so the read-back
  is vestigial.
- **A plain `bytearray` is correct here.** The sibling packages start scrambled
  because a read of a byte nothing wrote is observable on those parts. Here the
  reset writes every byte before anything reads one.

## Before calling anything finished

[`FAMILY.md`](FAMILY.md) carries a checklist under "What a new repository has to
have before it is a member". Every line on it was a defect found in one of these
repositories and fixed in all of them, so it is the list of things that have
actually gone wrong here rather than a list of good intentions. Read it before
adding a surface, and read it again before saying a change is done.

A change to `FAMILY.md` is a change to every member. Nothing here can catch it
being made in one of them and forgotten in the others, because a test in this
repository cannot see the others, so the check is a command rather than a suite:

```sh
shared() { sed '/^\*Everything above this line/q' "$1"; }

grep -o 'github\.com/[^/]*/\([a-z0-9-]*\))' FAMILY.md | sed 's|.*/||; s|)||' | sort -u |
while read -r member; do
  other="../$member/FAMILY.md"
  [ -f "$other" ] || { echo "not on this machine: $member"; continue; }
  cmp <(shared FAMILY.md) <(shared "$other") && echo "match: $member"
done
```

The members come from the table at the top of `FAMILY.md` rather than from a glob
over the parent directory. Several repositories beside these carry a copy of this
file because somebody started from one. Those are working notes: they bind
nothing, they are not expected to match, and a sweep that reports them as drifted
invites somebody to edit a file that was never a member.

Two rules from that file are worth repeating because they are the ones skipped
most often:

**A check nobody has seen fail is not known to work.** Drive it, once,
deliberately, against input that should fail it. The conformance runner here is
pointed at a driver that answers wrongly, for exactly this reason.

**Silence and success produce the same output.** A walk that visited no state
exits zero exactly like one that visited all of them. Print what was examined,
and say so when the answer is nothing.

## What a change is expected to leave behind

A gate that would have caught the bug. A change to how an address is remapped
also runs the exhaustive walk, because that is the only thing here that can tell
you whether it still agrees with anything outside this repository.
