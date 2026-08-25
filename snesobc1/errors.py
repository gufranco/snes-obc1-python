"""Everything this package raises, in one place.

One module so a caller can see the whole set at once, and so `except` has
somewhere to import from. It imports nothing from the rest of the package, which
is what keeps it from ever closing a cycle: everything here raises, so everything
here imports this, and an import running the other way would make the order
modules happen to load in decide whether the package works at all.

One refusal is the whole set, because this chip does one thing. A package with a
single exception is not a package that forgot the others.
"""

from __future__ import annotations


class OutOfRange(Exception):
    """The address is not one of the seven this chip answers.

    Raised rather than answered with open bus, because the chip is not what
    decides that. On a real cartridge an address outside the window is decoded by
    something else entirely, so a value returned here would be this package
    inventing the rest of the board.
    """
