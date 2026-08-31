"""Terminal demo for a local Ollama-powered unit-conversion agent."""

from __future__ import annotations

import argparse
import math
import sys
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


# Factors convert each accepted unit to its category's base unit: metre or gram.
UNITS: dict[str, dict[str, tuple[str, float]]] = {
    "length": {
        "meter": ("meter", 1.0), "meters": ("meter", 1.0), "m": ("meter", 1.0),
        "kilometer": ("kilometer", 1000.0), "kilometers": ("kilometer", 1000.0), "km": ("kilometer", 1000.0),
        "centimeter": ("centimeter", 0.01), "centimeters": ("centimeter", 0.01), "cm": ("centimeter", 0.01),
        "millimeter": ("millimeter", 0.001), "millimeters": ("millimeter", 0.001), "mm": ("millimeter", 0.001),
        "mile": ("mile", 1609.344), "miles": ("mile", 1609.344), "mi": ("mile", 1609.344),
        "yard": ("yard", 0.9144), "yards": ("yard", 0.9144), "yd": ("yard", 0.9144),
        "foot": ("foot", 0.3048), "feet": ("foot", 0.3048), "ft": ("foot", 0.3048),
        "inch": ("inch", 0.0254), "inches": ("inch", 0.0254), "in": ("inch", 0.0254),
    },
    "weight": {
        "kilogram": ("kilogram", 1000.0), "kilograms": ("kilogram", 1000.0), "kg": ("kilogram", 1000.0),
        "gram": ("gram", 1.0), "grams": ("gram", 1.0), "g": ("gram", 1.0),
        "milligram": ("milligram", 0.001), "milligrams": ("milligram", 0.001), "mg": ("milligram", 0.001),
        "pound": ("pound", 453.59237), "pounds": ("pound", 453.59237), "lb": ("pound", 453.59237), "lbs": ("pound", 453.59237),
        "ounce": ("ounce", 28.349523125), "ounces": ("ounce", 28.349523125), "oz": ("ounce", 28.349523125),
    },
}


def find_unit(unit: str) -> tuple[str, str, float] | None:
    """Return (category, display name, base-unit factor) for a normalized unit."""
    if not isinstance(unit, str):
        return None
    normalized = unit.strip().lower().replace(".", "")
    for category, aliases in UNITS.items():
        if normalized in aliases:
            name, factor = aliases[normalized]
            return category, name, factor
    return None


@tool
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert one length or weight value between supported units.

    Use this tool for every actual conversion. All three arguments are required:
    value is a finite number, from_unit is the source unit, and to_unit is the
    requested target unit. Never guess a missing source unit: ask the user for
    clarification instead. Only convert within the same category; length and
    weight cannot be mixed.

    Supported length units: meter/meters/m, kilometer/kilometers/km,
    centimeter/centimeters/cm, millimeter/millimeters/mm, mile/miles/mi,
    yard/yards/yd, foot/feet/ft, inch/inches/in.
    Supported weight units: kilogram/kilograms/kg, gram/grams/g,
    milligram/milligrams/mg, pound/pounds/lb/lbs, ounce/ounces/oz.
    """
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return "Error: value must be a valid number."
    if not math.isfinite(numeric_value):
        return "Error: value must be a finite number."

    source = find_unit(from_unit)
    target = find_unit(to_unit)
    if source is None:
        return f"Error: unsupported source unit '{from_unit}'."
    if target is None:
        return f"Error: unsupported target unit '{to_unit}'."
    if source[0] != target[0]:
        return (
            f"Error: incompatible conversion from {source[1]} ({source[0]}) "
            f"to {target[1]} ({target[0]})."
        )

    converted = numeric_value * source[2] / target[2]
    return f"{numeric_value:g} {source[1]} = {converted:.10g} {target[1]}"


SYSTEM_PROMPT = """You are a unit conversion assistant. Respond naturally to users.
For every actual supported conversion, call the convert_units tool; do not calculate
the result yourself. Do not perform unsupported or incompatible conversions. Never
guess a missing source unit. If the user gives a target unit but no source unit, ask
for the source unit and do not call the tool. Use only the tool's supported units."""


def build_agent():
    """Create the current LangChain agent backed by the local Ollama model."""
    model = ChatOllama(model="qwen2.5:3b", temperature=0)
    return create_agent(model=model, tools=[convert_units], system_prompt=SYSTEM_PROMPT)


def content_as_text(content: Any) -> str:
    """Make string or structured LangChain message content readable."""
    if isinstance(content, str):
        return content
    return str(content)


def print_trace(messages: list[Any]) -> None:
    print("\nFull message trace:")
    for index, message in enumerate(messages, start=1):
        print(f"  {index}. {type(message).__name__}")
        if isinstance(message, HumanMessage):
            print(f"     content: {content_as_text(message.content)}")
        elif isinstance(message, AIMessage):
            if message.tool_calls:
                for call in message.tool_calls:
                    print(f"     tool call: {call['name']}({call['args']})")
            if message.content:
                print(f"     content: {content_as_text(message.content)}")
        elif isinstance(message, ToolMessage):
            print(f"     tool result: {content_as_text(message.content)}")
        else:
            print(f"     content: {content_as_text(message.content)}")


TESTS = [
    ("TEST 1: Length Conversion", "Convert 10 kilometers to miles."),
    ("TEST 2: Weight Conversion", "How many kilograms are 5000 grams?"),
    ("TEST 3: Another Length Conversion", "Convert 12 inches to centimeters."),
    ("TEST 4: Ambiguous Query", "Convert 5 to kg."),
]


def run_demo() -> None:
    print("=" * 50)
    print("UNIT CONVERTER ASSISTANT")
    print("=" * 50)
    agent = build_agent()

    for title, query in TESTS:
        print(f"\n{title}")
        print("-" * 50)
        print(f"User query: {query}")
        # Local models can take a moment to load or generate; show that work started.
        print("Agent activity: deciding whether to call convert_units...", flush=True)
        result = agent.invoke({"messages": [{"role": "user", "content": query}]})
        messages = result["messages"]
        print_trace(messages)
        print(f"\nFinal agent response: {content_as_text(messages[-1].content)}")


def run_live_chat() -> None:
    """Let a user ask new natural-language conversion questions interactively."""
    print("=" * 50)
    print("UNIT CONVERTER ASSISTANT - LIVE MODE")
    print("=" * 50)
    print("Ask a conversion question, or type 'quit' to exit.")
    agent = build_agent()

    while True:
        try:
            query = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return

        if query.lower() in {"quit", "exit"}:
            print("Goodbye.")
            return
        if not query:
            print("Please enter a conversion question.")
            continue

        print("Agent activity: deciding whether to call convert_units...", flush=True)
        result = agent.invoke({"messages": [{"role": "user", "content": query}]})
        messages = result["messages"]
        print_trace(messages)
        print(f"\nAssistant: {content_as_text(messages[-1].content)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Ollama unit-conversion agent")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="run the four prewritten jury demonstration questions",
    )
    arguments = parser.parse_args()

    try:
        if arguments.demo:
            run_demo()
        else:
            run_live_chat()
    except Exception as error:
        print(f"\nCould not run the local agent: {error}", file=sys.stderr)
        print("Check that Ollama is installed, running, and has qwen2.5:3b pulled.", file=sys.stderr)
        raise SystemExit(1)
