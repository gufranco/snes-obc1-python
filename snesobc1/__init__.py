"""The OBC1, the sprite remapper one Super Nintendo cartridge carried.

    from snesobc1 import Chip

    chip = Chip("obc1")
    chip.write(0x7FF6, 0x02)
    chip.write(0x7FF0, 0xAA)

Eight kilobytes of memory with seven addresses that lie: five of them are a
window onto somewhere else, and where that somewhere is comes from the other two.

Memory comes up set rather than cleared, which is what the reset does.
"""

from typing import Any

from . import chip as chip
from . import errors as errors
from . import models as models
from .errors import OutOfRange, UnknownModelError
from .models import DEFAULT_MODEL, MODELS, Model, describe
from .version import VERSION


def Chip(  # noqa: N802
    model: str = DEFAULT_MODEL, ram: bytearray | None = None, **options: Any
) -> chip.Chip:
    """A chip of the named model, sharing one interface across the family.

    The model comes first because it is the thing a caller always knows and the
    memory is the thing they often do not care about yet. Omitting it hands back
    a part with memory of its own, set rather than cleared, which is what the
    reset leaves behind.

    The same shape as `Cpu(model, memory)` on the members that run a program, and
    named for what this is rather than for what it does. This part answers
    accesses; it does not execute anything, and calling the constructor `Cpu`
    would say it did. One model rather than several, and it still takes the
    argument, so a caller moving between members writes the same call and a typo
    is refused rather than ignored.
    """
    return describe(model).build(ram, **options)


__version__ = VERSION

__all__ = [
    "DEFAULT_MODEL",
    "MODELS",
    "Chip",
    "Model",
    "OutOfRange",
    "UnknownModelError",
    "__version__",
    "describe",
]
