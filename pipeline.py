"""Orchestration for the four modules."""
from conversion_agent import convert_units
from checker_agent import CheckerAgent
from memory_rag import UnitMemory
from parser_agent import ParserAgent

class ConversionPipeline:
    def __init__(self):
        self.memory = UnitMemory()
        self.parser = ParserAgent()
        self.checker = CheckerAgent()

    def ask(self, query: str) -> tuple[str, dict]:
        follow = self.memory.resolve_follow_up(query)
        parsed = self.parser.parse(f"{follow[0]} {follow[1]} to {follow[2]}" if follow else query)
        trace = ["HumanMessage", "ParserAgent"]
        if parsed.clarification:
            return parsed.clarification, {"trace": trace + ["Clarification"]}
        result = convert_units.invoke({"value": parsed.value, "from_unit": parsed.from_unit, "to_unit": parsed.to_unit})
        trace.append("ConverterAgent/convert_units")
        # Keep the original quantity so a follow-up such as "now in pounds"
        # converts the same quantity into a new target unit.
        self.memory.remember(parsed.value, parsed.from_unit)
        check = self.checker.verify(parsed.value, parsed.from_unit, parsed.to_unit, result)
        trace += ["CheckerAgent(reverse)", "FinalResponse"]
        return result + "\n" + check["message"], {"trace": trace, "tool_result": result, "checker": check}
