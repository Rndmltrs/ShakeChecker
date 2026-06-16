"""Repeat Ball catch chain: consecutive catches of the same species.

The chain grows by one each time the SAME species is caught in a row and
restarts at the new species when a DIFFERENT species is caught. Only catching
another species breaks it -- KO'ing, fleeing or the wild fleeing leave it intact
(in-game observation). Session-only: the app loop holds one instance and nothing
is persisted to disk. The Repeat Ball multiplier reads the chain via catch_calc.
"""

from __future__ import annotations


class CatchChain:
    def __init__(self) -> None:
        self.species: int | None = None  # the species currently being chained
        self.count = 0  # consecutive catches of that species

    def record_catch(self, species_id: int) -> int:
        """Register a successful catch; return the new chain length. Same species
        -> +1, a different one -> restart the chain at this species (length 1)."""
        if species_id == self.species:
            self.count += 1
        else:
            self.species = species_id
            self.count = 1
        return self.count

    def length_for(self, species_id: int | None) -> int:
        """Chain length that applies to an enemy of this species: the running
        chain if it matches, else 0 (a fresh species gets no Repeat Ball boost)."""
        if species_id is None or species_id != self.species:
            return 0
        return self.count
