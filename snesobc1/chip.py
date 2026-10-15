from typing import override

from .errors import OutOfRange

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


class Chip:
    __slots__ = ("address", "base", "model", "ram", "shift")

    model: str

    def __init__(self, ram: bytearray | None = None) -> None:
        self.ram = bytearray(RAM_BYTES)
        self.base = BASE_HIGH
        self.address = 0
        self.shift = 0
        if ram is None:
            self.reset()
        else:
            self.adopt(ram)

    def reset(self) -> "Chip":
        self.ram = bytearray([UNWRITTEN] * RAM_BYTES)
        return self._derive()

    def adopt(self, ram: bytearray) -> "Chip":
        self.ram = bytearray(ram)
        return self._derive()

    def _derive(self) -> "Chip":
        self.base = BASE_LOW if self.ram[BASE_REGISTER - WINDOW_START] & 1 else BASE_HIGH
        pointer = self.ram[POINTER_REGISTER - WINDOW_START]
        self.address = pointer & ADDRESS_MASK
        self.shift = (pointer & PACKED_MASK) << 1
        return self

    def _offset(self, address: int) -> int:
        if not WINDOW_START <= address < WINDOW_END:
            raise OutOfRange(f"{address:#06x} is not an address this chip answers")
        return address - WINDOW_START

    def _quad(self, index: int) -> int:
        return self.base + (self.address << 2) + index

    def _packed(self) -> int:
        return self.base + (self.address >> 2) + PACKED_OFFSET

    def read(self, address: int) -> int:
        offset = self._offset(address)
        if FIRST_REGISTER <= address < PACKED_REGISTER:
            return self.ram[self._quad(address - FIRST_REGISTER)]
        if address == PACKED_REGISTER:
            return self.ram[self._packed()]
        return self.ram[offset]

    def write(self, address: int, value: int) -> None:
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

    @override
    def __repr__(self) -> str:
        return f"<OBC1 base {self.base:#06x} pointer {self.address:#04x} shift {self.shift}>"
