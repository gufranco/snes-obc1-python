from typing import Any

from . import chip as chip
from . import errors as errors
from . import models as models
from .errors import OutOfRange, UnknownModelError
from .models import MODELS, Model
from .version import VERSION


def Chip(  # noqa: N802
    model: str | None = None, ram: bytearray | None = None, **options: Any
) -> chip.Chip:
    return models.lookup(model).build(ram, **options)


__version__ = VERSION

__all__ = [
    "MODELS",
    "Chip",
    "Model",
    "OutOfRange",
    "UnknownModelError",
    "__version__",
]
