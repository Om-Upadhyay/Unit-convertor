"""Module 3: parser agent. It extracts value/source/target and asks instead of guessing."""
from __future__ import annotations

import re
from dataclasses import dataclass
from conversion_agent import resolve_unit

@dataclass
class ParsedRequest:
    value: float | None
    from_unit: str | None
    to_unit: str | None
    clarification: str | None = None

class ParserAgent:
    """A transparent parser: deterministic extraction is safer than guessed units."""
    def parse(self, text: str) -> ParsedRequest:
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        value = float(match.group()) if match else None
        words = re.findall(r"[A-Za-z]+", text.lower())
        units = [word for word in words if resolve_unit(word)]
        if value is None:
            return ParsedRequest(None, None, None, "Please provide a numeric value.")
        if not units:
            return ParsedRequest(value, None, None, "Please provide both the source and target units.")
        if len(units) == 1:
            return ParsedRequest(value, None, units[0], "What is the source unit? I will not guess it.")
        return ParsedRequest(value, units[-2], units[-1])
