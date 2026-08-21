# Working in this repository

This file is for a coding agent. A person reading it will not be harmed, but
[README.md](README.md) is the document written for them.

## What this project is, in one paragraph

The OBC1, which is eight kilobytes of memory with seven addresses that lie. It
holds sprite attributes and hands the console a moving window onto them, so a
program can write one sprite's four bytes to the same four addresses every time
and let the chip decide where they land. One cartridge carried it.

## The authority ladder, and the fact that its top rung is empty

1. **A manufacturer document for the OBC1.** There is none, and nothing suggests
   one exists.
2. **Nintendo's documented OAM structure**, for anything this chip's layout
   mirrors. This chip exists to feed OAM, so the shape of what it holds is the
   shape of what OAM expects.
3. **The reference implementation**, for everything else.

Rung 2 reaches exactly one constant and rung 3 carries the rest.

## The one constant that comes from a document

The offset from a base address to the packed two-bit attributes is `0x200`, which
is the size of an OAM low table: 128 sprites of four bytes, a figure Nintendo
prints. The two base addresses are `0x400` apart, which is room for a table and
its attributes twice over.

That is why `conformance/hardware.test.py` asserts that **exactly one** constant
is marked verified. If a change makes that two, either a document has been found,
in which case say which, or something has drifted into claiming a citation it
does not have.

## One cartridge is not a corpus

The sibling packages cross-check a behaviour across dozens of cartridges, where
one driver could be wrong and thirty six could not be wrong the same way. Here
there is one driver.

**Anything that driver never exercises is unconstrained.** The chip could do
something else entirely with a base address it never selects, and neither the
reference nor this model would notice. That is recorded in
`conformance/divergences.json` and it is the honest limit of everything here.

## Every gate, in the order to run them

```bash
ruff format --check .                     # formatting
ruff check .                              # lint, zero warnings
mypy                                      # types, strict
pnpm run format:check                     # every JSON file
for f in snesobc1/*.test.py conformance/*.test.py; do python3 "$f"; done
python3 -m coverage report                # fails below 100%

python3 conformance/build.py              # builds the reference from pinned source
python3 conformance/exhaustive.py         # walks it against this model
python3 -m snesobc1.doctor                # what is missing on this machine
```

`conformance/hardware.test.py` needs nothing else on the machine and is the part
of the gate that does not depend on a compiler.

## Things that will bite you

**Memory comes up set, not cleared.** Every byte reads as `0xFF` before anything
is written, and the reset restores that. A chip that came up cleared would let a
program depend on a byte it never wrote and never fail.

**The window position is derived, not stored.** It comes from the base register
and the pointer register, and adopting a saved image re-derives it from the bytes
in that image rather than leaving it where it was.

**The exhaustive walk is against the reference**, not against the part. It
settles that this model and snes9x agree on every step, which is a real check and
is not a measurement of hardware.

## Conventions

| Thing | Rule |
|:------|:-----|
| Language | Python only |
| Comments | None in source. Docstrings carry the reasoning, and say why rather than what |
| Test layout | `<module>.test.py` beside the module it covers |
| Test structure | Arrange, blank line, one act, blank line, assert. No section labels |
| Package manager for tooling | pnpm, never npm |
| Commits | Conventional Commits |
| Promoting a constant to verified | Needs a document or a measurement, never another implementation that agrees |
