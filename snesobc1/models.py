from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

from . import chip
from .errors import UnknownModelError


class Model:
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


_BY_ALIAS: dict[str, Model] = {}
for _model in _CATALOGUE:
    _BY_ALIAS[_model.name.replace("-", "")] = _model
    for _alias in _model.aliases:
        _BY_ALIAS[_alias.replace("-", "")] = _model


def _normalise(name: str) -> str:
    return str(name).strip().lower().replace("-", "").replace("_", "").replace(" ", "")


def lookup(name: str | None) -> Model:
    if name is None:
        raise UnknownModelError(
            "no model was named, and this package will not choose one for you."
            f" Name one of: {', '.join(sorted(MODELS))}"
        )
    found = _BY_ALIAS.get(_normalise(name))
    if found is None:
        raise UnknownModelError(
            f"no model called {name!r}; this package publishes " + ", ".join(sorted(MODELS))
        )
    return found
