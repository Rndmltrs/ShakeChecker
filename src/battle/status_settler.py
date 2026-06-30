"""Debounce the enemy status reading.

The status badge is re-read every frame. During the ball-throw / catch animation
the thrown ball flashes blue/cyan over the badge region, which the hue classifier
briefly misreads (e.g. as FRZ). Real status changes persist for many frames, so
we only switch the reported status once a new value has been seen for a few
consecutive frames; short animation blips are ignored.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StatusSettler:
    # consecutive frames a *different* status must hold before we switch to it.
    # At ~0.2 s/frame this rides out the ~0.5 s ball-flash; a real status change
    # lasts far longer and still gets through.
    stable_needed: int = 4

    _committed: str | None = None
    _candidate: str | None = None
    _count: int = 0

    def update(self, status: str) -> str:
        """Fold in this frame's raw status; return the settled status to show."""
        if self._committed is None:
            self._committed = status  # first reading shows immediately
            self._candidate = status
            self._count = self.stable_needed
            return self._committed

        # If the incoming status matches our current candidate, build confidence.
        # Once it hits the threshold, it becomes the committed status.
        if status == self._candidate:
            self._count = min(self._count + 1, self.stable_needed)
            if self._count == self.stable_needed:
                self._committed = self._candidate
        else:
            # Otherwise, drain confidence. If confidence drops to 0,
            # we switch candidates. This ensures a single frame of noise
            # doesn't completely wipe out progress toward a new status!
            self._count -= 1
            if self._count <= 0:
                self._candidate = status
                self._count = 1

        return self._committed

    def reset(self) -> None:
        """Call at the start of each battle."""
        self._committed = None
        self._candidate = None
        self._count = 0
