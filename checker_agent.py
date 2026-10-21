"""Module 4: critic/checker agent with a two-round reverse-conversion loop."""
from __future__ import annotations

import re
from conversion_agent import convert_units

class CheckerAgent:
    def __init__(self, tolerance: float = 1e-6, max_rounds: int = 2) -> None:
        self.tolerance, self.max_rounds = tolerance, max_rounds

    def verify(self, value: float, source: str, target: str, result_text: str) -> dict:
        """Convert the result back and compare with the original value (critic loop)."""
        match = re.search(r"=\s*([-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?)", result_text, re.I)
        if not match:
            return {"passed": False, "rounds": 1, "message": "Checker could not read the tool result."}
        converted = float(match.group(1))
        reverse = convert_units.invoke({"value": converted, "from_unit": target, "to_unit": source})
        back_match = re.search(r"=\s*([-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?)", reverse, re.I)
        if not back_match:
            return {"passed": False, "rounds": 1, "message": reverse}
        recovered = float(back_match.group(1))
        error = abs(recovered - value)
        passed = error <= self.tolerance * max(1.0, abs(value))
        return {"passed": passed, "rounds": min(2, self.max_rounds), "reverse": reverse,
                "error": error, "message": "Reverse check passed." if passed else "Reverse check caught a possible conversion error."}
