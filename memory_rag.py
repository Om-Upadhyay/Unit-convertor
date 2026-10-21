"""Module 1: preference memory and tiny offline RAG helper."""
from __future__ import annotations

from conversion_agent import resolve_unit

class UnitMemory:
    """Thread-scoped memory for preferred system and the latest conversion."""
    def __init__(self) -> None:
        self.preferred_system = "metric"
        self.last_value = None
        self.last_unit = None

    def set_preference(self, system: str) -> str:
        system = system.lower().strip()
        if system not in {"metric", "imperial"}:
            return "Preference must be metric or imperial."
        self.preferred_system = system
        return f"Preferred unit system set to {system}."

    def default_unit(self, category: str) -> str:
        if category == "weight":
            return "kilogram" if self.preferred_system == "metric" else "pound"
        return "meter" if self.preferred_system == "metric" else "foot"

    def remember(self, value: float, unit: str) -> None:
        self.last_value, self.last_unit = value, unit

    def resolve_follow_up(self, text: str) -> tuple[float, str, str] | None:
        """Resolve a follow-up such as 'now in pounds' using the last turn."""
        words = text.lower().replace(".", " ").split()
        if len(words) >= 2 and words[0] in {"now", "and"}:
            for word in reversed(words):
                if word in {"now", "and", "in", "to"}:
                    continue
                if resolve_unit(word) and self.last_value is not None and self.last_unit:
                    return self.last_value, self.last_unit, word
        return None
