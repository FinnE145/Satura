class HaltSignal(Exception):
    """Raised by halt keyword or a runtime halt condition. Actions taken stand."""


class ResetSignal(Exception):
    """Raised when the entire execution must be undone."""
