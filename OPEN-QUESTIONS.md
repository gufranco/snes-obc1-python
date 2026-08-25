# Open questions

What this project does not know for certain, and what it would take to find out.

Everything here is a place where being faithful to the silicon is still a claim
rather than a measurement. There are few entries and one of them is large: no
manufacturer document for this part is known to exist, so the top rung of the
authority ladder is empty and everything below rests on a reimplementation
somebody else wrote.

The settled surface is complete in one narrow sense and thin in another. Every
state the chip has is visited and compared, 3,126 steps with no disagreements,
and the state space really is exhaustible: two base addresses and a hundred and
twenty eight pointer values. What that settles is that this model and the
reference agree everywhere. It does not settle that either of them is the chip.

## Why a reference cannot close these

The reference is a second implementation, not a measurement. It is very good, and
it is one lineage: it was written by reading the behaviour of one cartridge, and
anything that cartridge never does is unconstrained in it exactly as it is here.
Two implementations that agree because one was written from the other are one
source, not two.

## What would settle almost all of them

A die photograph, or a board schematic, or a Nintendo application note naming the
part. Failing that, a logic analyser on the one cartridge that carries it, which
would at least turn a reimplementation's claim into a measurement for the paths
that cartridge exercises.

Every entry is also carried in
[`conformance/divergences.json`](conformance/divergences.json) with its status
and severity, so a program can read what a person reads here.

## Where no document exists at all

### Every register address, both base addresses, and the memory size.

**The document says.** Nothing. No manufacturer document for the OBC1 is known to
exist. It was searched for on 2026-08-21 and nothing was found.

**What this project follows.** The reference implementation, which gives all of
them.

**Why.** There is nothing above it to follow. What matters is that the record
says so rather than promoting a second implementation to the rung a data sheet
would occupy, which would make a reader believe these figures were printed
somewhere.

**What would settle or reopen it.** A die photograph, a board schematic, or a
Nintendo application note naming the part.

### What the chip does in a state the one cartridge never puts it in.

**The document says.** Nothing.

**What this project follows.** The reference, which behaves as the one driver
that exists needs it to.

**Why.** A sibling package cross-checks a behaviour across dozens of cartridges,
and one driver could be wrong where thirty six could not be wrong the same way
about the same thing. Here there is one driver. The chip could do something else
entirely with a base address that cartridge never selects, and nothing in this
repository or in the reference would notice.

**What would settle or reopen it.** A second cartridge carrying this chip, which
does not exist, or a die photograph.

## Where the question is a scope boundary, not an unknown

### How long the chip takes to answer.

**What this project follows.** Nothing. It answers immediately, as the reference
does, and neither of them is a timing claim.

**Why.** It is a part rather than a clocked part: there is no instruction to step
through and no cycle count to hand back, so there is nothing here that could
carry a duration even if one were known.

**What would settle or reopen it.** A measurement on a real cartridge, which
would make a timing model possible rather than making this one wrong.

## What is not in question

So the boundary is visible rather than implied:

- **That this model and the reference agree in every state the chip has.** 256
  states, each visited, with all five window addresses written and read and all
  eight kilobytes compared byte for byte, plus fifty steps confirming the reset
  ignores whatever memory held.
- **The offset from a base to the packed attributes.** `0x200`, which is 128
  sprites times four bytes, from Nintendo's documented OAM layout. It is the one
  constant here that does not rest on a reimplementation, because this chip lays
  its memory out the way OAM is laid out and feeding OAM is the whole of what it
  does.
- **That the reset is not a recovery.** It writes every byte before reading any,
  so the read-back is vestigial and the chip always comes up the same way. The
  walk checks it from ten different starting states.
- **That the checker can fail.** The tests point the runner at a driver that
  answers wrongly and confirm it says so, because a check nobody has seen fail is
  not known to work.

## What is deliberately not modelled

Absent rather than unknown, and absent on purpose:

- **A clock.** The chip answers accesses. There is no program to step through and
  no budget of cycles to spend, so none of the family's clocked interface appears
  here rather than appearing as a stub.
- **A model argument.** One cartridge carried this chip and there is no second
  variant to choose between. An argument with one legal value is an argument that
  exists to look like its neighbours.
- **Unwritten memory.** The sibling packages start scrambled because a read of a
  byte nothing wrote is observable on those parts. Here the reset writes every
  byte before anything reads one, so there is no unwritten byte for a program to
  observe and a plain `bytearray` is the honest shape.
- **What decodes an address outside the window.** `OutOfRange` is raised rather
  than a value returned, because on a real cartridge that address belongs to
  something else and answering it would be this package inventing the rest of the
  board.
