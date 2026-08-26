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


_BY_ALIAS: dict[str, Model] = {}
for _model in _CATALOGUE:
    _BY_ALIAS[_model.name.replace("-", "")] = _model
    for _alias in _model.aliases:
        _BY_ALIAS[_alias.replace("-", "")] = _model


def _normalise(name: str) -> str:
    return str(name).strip().lower().replace("-", "").replace("_", "").replace(" ", "")


def lookup(name: str | None) -> Model:
    """The model of that name, however it happens to be written.

    Naming nothing is refused rather than filled in. A default would be the one
    implicit thing in the call that builds a part, and it is worst where it looks
    most harmless: a caller who learns to leave the model out against a member
    covering one part writes the same call against a member covering sixteen.
    The refusal names every model there is, so somebody who did not know what to
    pass learns it here rather than from the source.

    Not exported from the package. What a caller wants is the part, and the part
    carries its own model; handing back a description of a part nobody built
    reads like a test fixture rather than an interface.
    """
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
