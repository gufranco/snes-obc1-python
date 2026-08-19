"""The OBC1, which is eight kilobytes of memory with seven addresses that lie.

One cartridge carried this chip. It holds sprite attributes and hands the console
a moving window onto them, so a program can write one sprite's four bytes to the
same four addresses every time and let the chip decide where they land. That is
the whole idea and the whole difficulty.

Six of the addresses are that window. Four reach four consecutive bytes at a
place a pointer register chooses, and a fifth reaches a single byte a quarter as
far along, where four sprites share one byte two bits each. Writing through that
fifth address changes two bits and leaves the other six, which is the one place a
read-modify-write happens inside the chip rather than in the program.

Two things are easy to get wrong.

The pointer register does two jobs from one byte. Its low seven bits choose which
sprite the window points at, and its low two bits, the same two, also choose which
corner of the shared byte the fifth address reaches. They are not separate fields.

And every write to a register is also written straight into memory at the address
it arrived on, underneath the remapping. That looks like it should let a reset
recover the state, and it does not: the reset sets every byte to `FF` first and
reads the base and pointer back out of the bytes it just wrote, so it always
comes up in the same state no matter what was there. The read-back is vestigial.
Modelling it as a recovery would be modelling something the chip does not do.

Restoring a saved cartridge is a different operation and is spelled differently:
`adopt` takes an image and derives the state from it without wiping. That is this
package's own, for tools that carry save states around, not the reset line.
"""

WINDOW_START = 0x6000

WINDOW_END = 0x8000

RAM_BYTES = 0x2000

BASE_HIGH = 0x1C00

BASE_LOW = 0x1800

PACKED_OFFSET = 0x200

FIRST_REGISTER = 0x7FF0

PACKED_REGISTER = 0x7FF4

BASE_REGISTER = 0x7FF5

POINTER_REGISTER = 0x7FF6

ADDRESS_MASK = 0x7F

PACKED_MASK = 0x03

UNWRITTEN = 0xFF


class OutOfRange(Exception):
    pass


class Obc1:
    """One OBC1, and the window it puts over its own memory."""

    def __init__(self, ram=None):
        self.ram = bytearray(RAM_BYTES)
        self.base = BASE_HIGH
        self.address = 0
        self.shift = 0
        if ram is None:
            self.reset()
        else:
            self.adopt(ram)

    def reset(self):
        """What the reset line does, which is less useful than it looks.

        Every byte is set before anything is read, so the base and pointer are
        derived from the bytes the reset itself just wrote. Whatever the cartridge
        held is gone, and the chip always comes up the same way.
        """
        self.ram = bytearray([UNWRITTEN] * RAM_BYTES)
        return self._derive()

    def adopt(self, ram):
        """Take a saved image and derive the state from it, which no reset does."""
        self.ram = bytearray(ram)
        return self._derive()

    def _derive(self):
        self.base = BASE_LOW if self.ram[BASE_REGISTER - WINDOW_START] & 1 else BASE_HIGH
        pointer = self.ram[POINTER_REGISTER - WINDOW_START]
        self.address = pointer & ADDRESS_MASK
        self.shift = (pointer & PACKED_MASK) << 1
        return self

    def _offset(self, address):
        if not WINDOW_START <= address < WINDOW_END:
            raise OutOfRange(f"{address:#06x} is not an address this chip answers")
        return address - WINDOW_START

    def _quad(self, index):
        return self.base + (self.address << 2) + index

    def _packed(self):
        return self.base + (self.address >> 2) + PACKED_OFFSET

    def read(self, address):
        offset = self._offset(address)
        if FIRST_REGISTER <= address < PACKED_REGISTER:
            return self.ram[self._quad(address - FIRST_REGISTER)]
        if address == PACKED_REGISTER:
            return self.ram[self._packed()]
        return self.ram[offset]

    def write(self, address, value):
        offset = self._offset(address)
        value &= 0xFF
        if FIRST_REGISTER <= address < PACKED_REGISTER:
            self.ram[self._quad(address - FIRST_REGISTER)] = value
        elif address == PACKED_REGISTER:
            at = self._packed()
            held = self.ram[at]
            self.ram[at] = (held & ~(PACKED_MASK << self.shift) & 0xFF) | (
                (value & PACKED_MASK) << self.shift
            )
        elif address == BASE_REGISTER:
            self.base = BASE_LOW if value & 1 else BASE_HIGH
        elif address == POINTER_REGISTER:
            self.address = value & ADDRESS_MASK
            self.shift = (value & PACKED_MASK) << 1
        self.ram[offset] = value

    def __repr__(self):
        return f"<OBC1 base {self.base:#06x} pointer {self.address:#04x} shift {self.shift}>"
