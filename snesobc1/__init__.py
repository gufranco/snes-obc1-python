"""The OBC1, the sprite remapper one Super Nintendo cartridge carried.

    from snesobc1 import Obc1

    chip = Obc1()
    chip.write(0x7FF6, 0x02)
    chip.write(0x7FF0, 0xAA)

Eight kilobytes of memory with seven addresses that lie: five of them are a
window onto somewhere else, and where that somewhere is comes from the other two.

Memory comes up set rather than cleared, which is what the reset does.
"""

from . import chip
from .chip import Obc1, OutOfRange
from .version import VERSION

__version__ = VERSION

__all__ = ["Obc1", "OutOfRange", "__version__", "chip"]
