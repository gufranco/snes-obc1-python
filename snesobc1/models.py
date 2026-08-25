"""The one model this package publishes, and how a caller names it.

One entry rather than none. The family's other parts carry a catalogue because
they have several models, and a caller moving between them should not have to
learn that this one is the exception. A catalogue of one also gives the
constructor a model argument to reject, so a typo is refused here rather than
ignored.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

from . import chip
from .errors import UnknownModelError


class Model:
    """One chip: what it is, where it answers, and how to build one."""

    __slots__ = ("aliases", "name", "summary")

    def __init__(self, name: str, summary: str, aliases: Sequence[str] = ()) -> None:
        self.name = name
        self.summary = summary
        self.aliases = tuple(aliases)

    def build(self, ram: bytearray | None = None, **options: Any) -> chip.Chip:
        built = chip.Chip(ram, **options)
        built.model = self.name
        return built

    @override
    def __repr__(self) -> str:
        return f"<Model {self.name}, answering at {chip.WINDOW_START:#06x}>"


_CATALOGUE = (
    Model(
        name="obc1",
        summary=(
            "The OBC1, the sprite remapper one Super Nintendo cartridge carried. "
            "Eight kilobytes of memory with seven addresses that lie: five of them "
            "are a window onto somewhere else, and where that somewhere is comes "
            "from the other two."
        ),
        aliases=("obc-1", "obc"),
    ),
)

MODELS = {model.name: model for model in _CATALOGUE}

DEFAULT_MODEL = _CATALOGUE[0].name

_BY_ALIAS: dict[str, Model] = {}
for _model in _CATALOGUE:
    _BY_ALIAS[_model.name.replace("-", "")] = _model
    for _alias in _model.aliases:
        _BY_ALIAS[_alias.replace("-", "")] = _model


def _normalise(name: str) -> str:
    return str(name).strip().lower().replace("-", "").replace("_", "").replace(" ", "")


def describe(name: str) -> Model:
    """The model that goes by that name, or a refusal naming the ones that do."""
    found = _BY_ALIAS.get(_normalise(name))
    if found is None:
        raise UnknownModelError(
            f"no model called {name!r}; this package publishes " + ", ".join(sorted(MODELS))
        )
    return found
