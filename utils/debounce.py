"""Debounce utility for throttling rapid input changes.

Provides a small callable object that defers execution of the wrapped
callback until a quiet period has passed.
"""

from typing import Callable


class Debouncer:
    def __init__(self, callback: Callable[[], None], delay_ms: int = 200):
        self.callback = callback
        self.delay_ms = delay_ms
        self._timer = None
        self._qobject = None

    def bind(self, qobject):
        """Attach a QObject so the timer runs on its thread/event loop."""
        from PyQt6.QtCore import QTimer

        self._qobject = qobject
        self._timer = QTimer(qobject)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self.delay_ms)
        self._timer.timeout.connect(self.callback)

    def __call__(self):
        if self._timer is None:
            raise RuntimeError("Debouncer must be bound to a QObject first.")
        self._timer.start()

    def cancel(self):
        if self._timer is not None:
            self._timer.stop()

    def fire_now(self):
        if self._timer is not None:
            self._timer.stop()
        self.callback()
