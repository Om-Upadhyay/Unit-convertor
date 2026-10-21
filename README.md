# Unit Converter Assistant

A small terminal-based Agentic AI project that converts length and weight units with a locally running Ollama model (`qwen2.5:3b`). It uses one LangChain tool, `convert_units`, and LangChain's current `create_agent()` API.

## Why this is Agentic AI

The LLM does not just generate a conversion answer. It reads the natural-language request, decides whether it has enough information, chooses the conversion tool, supplies structured arguments, receives the tool result, and turns that result into a user-friendly answer. The conversion arithmetic remains deterministic Python code.

## Architecture

```text
User question
    -> ChatOllama (qwen2.5:3b, temperature=0)
    -> LangChain create_agent()
    -> convert_units tool (when needed)
    -> tool result
    -> final natural-language answer
```

`main.py` invokes the agent separately for four jury test questions and prints every returned LangChain message, including tool-call names and arguments.

## Requirements and installation

- Python 3.10 or newer
- [Ollama for Windows](https://ollama.com/download) installed and running locally
- No cloud API key and no web API are used at runtime

In PowerShell, from this project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
ollama pull qwen2.5:3b
ollama list
python main.py
```

`python main.py` starts live mode: type any conversion question yourself and type
`quit` when finished. For the four fixed jury questions and their traces, run:

```powershell
python main.py --demo
```

Ollama normally starts its local service automatically after installation. If it is not running, start it with:

```powershell
ollama serve
```

Then use another PowerShell window to run `python main.py`.

## Supported units

| Category | Units |
| --- | --- |
| Length | meter/meters/m, kilometer/kilometers/km, centimeter/centimeters/cm, millimeter/millimeters/mm, mile/miles/mi, yard/yards/yd, foot/feet/ft, inch/inches/in |
| Weight | kilogram/kilograms/kg, gram/grams/g, milligram/milligrams/mg, pound/pounds/lb/lbs, ounce/ounces/oz |

The tool normalizes capitalization, spacing around a unit, and a trailing period. It uses metre and gram base-unit factors, validates every unit, and rejects mixed categories such as kilograms to metres.

## Example queries

```text
Convert 10 kilometers to miles.
How many kilograms are 5000 grams?
Convert 12 inches to centimeters.
Convert 5 to kg.
```

The last question is deliberately ambiguous. It has a value and target unit but no source unit. The system prompt and tool documentation instruct the agent to ask for the missing source unit rather than assume one. It should not call the tool for this question.

## Tool-calling flow

For a successful conversion, the actual printed trace should have this shape:

```text
HumanMessage
  -> AIMessage with tool call: convert_units({'value': 10, 'from_unit': 'kilometers', 'to_unit': 'miles'})
  -> ToolMessage with the Python conversion result
  -> AIMessage with the natural-language answer
```

The demo does not manufacture this trace: it prints the `messages` returned by `agent.invoke()`. Exact prose and argument spelling may vary slightly by local model version, but the numerical result comes from the tool.

## Why `temperature=0`

Temperature controls sampling randomness. For a deterministic task like selecting a conversion tool and extracting units, lower randomness makes the tool choice, arguments, and wording more predictable. `temperature=0` is therefore useful for reliable demonstrations, although it does not mathematically guarantee identical behavior across every model/runtime implementation.

## Why the tool docstring matters

The model sees the tool's name, input schema, and docstring when deciding how to act. This project's docstring states what the tool does, lists its supported units and categories, requires both `from_unit` and `to_unit`, rejects incompatible categories, and explicitly says never to guess a missing source unit. Those constraints reduce ambiguity before the tool call is created.

## Limitations

- Only the listed length and weight units are supported.
- The quality of natural-language tool selection depends on the local model and installed Ollama/LangChain versions.
- This is a one-turn demo; it does not retain conversational history between the four tests.
- It requires a local Ollama service and the `qwen2.5:3b` model to run.

## Unit 3 and Unit 4 extension (four-person team)

The extension is split into four easy-to-present modules:

1. `memory_rag.py` — stores the preferred metric/imperial system and remembers the last conversion. It resolves follow-ups such as `now in pounds`.
2. `conversion_agent.py` — the deterministic `convert_units` tool plus an offline reference-sheet lookup in `reference_units.md`. The sheet adds aliases such as `quintal` and `stone`.
3. `parser_agent.py` — extracts the number and units. If a source unit is missing or ambiguous, it asks a clarification question instead of guessing.
4. `checker_agent.py` — performs a reverse conversion and compares it with the original value. The critic loop is limited to two rounds.

`pipeline.py` connects the four modules. The reverse check makes an error visible: if the forward result is wrong, converting it back will not match the original value within tolerance.

### GUI

The project also includes a lightweight Tkinter interface (no extra GUI package is needed):

```powershell
python gui.py
```

The GUI accepts real-time natural-language questions and displays four visible stage cards: Memory + RAG, Parser Agent, Converter Tool, and Checker Agent. Each card changes status after a query. For an ambiguous query, the Parser card says "Clarification asked" and the Converter card says "Not called", making the before-tool behavior visible. The `Show Wrong-Result Evidence` button displays the Checker catching a deliberately incorrect conversion.

## Single-file runner

All Unit 3 and Unit 4 features are also bundled in `unit_converter_all_in_one.py`:

```powershell
python unit_converter_all_in_one.py              # GUI
python unit_converter_all_in_one.py --chat       # live terminal mode
python unit_converter_all_in_one.py --demo       # four required examples
python unit_converter_all_in_one.py --evidence   # wrong-result and ambiguity evidence
```

The preferred system is changed by typing `metric` or `imperial` in chat/GUI. When a target is omitted, that preference supplies the default target (kilograms/meters for metric, pounds/feet for imperial). The resolver reads `reference_units.md` for documented aliases such as quintal and stone. The evidence command visibly demonstrates that ambiguity is handled before a converter call and that the reverse checker catches an intentionally wrong result.

### Four-person presentation split

Each person can present one module: (1) memory and local RAG, (2) conversion tool, (3) parser and ambiguity handling, and (4) reverse checker/critic loop. A fifth shared part, if needed, is the GUI and integration.

### Reverse-check evidence

For a valid request the trace includes `ConverterAgent/convert_units` followed by `CheckerAgent(reverse)` and the message `Reverse check passed.` If a deliberately altered forward result is supplied to the checker, the recovered value differs and it reports `Reverse check caught a possible conversion error.`

## Jury Questions

### Q1. Why does temperature=0 matter for this kind of tool-calling task?

Temperature controls how much randomness is used when the model chooses its next tokens. A lower temperature makes tool selection, argument extraction, and answers more predictable, which is desirable for deterministic conversion tasks. Temperature 0 reduces randomness, but it does not mathematically guarantee identical behavior across every implementation, model build, or runtime.

### Q2. What would you change in your docstring to reduce the ambiguous-question failure?

State explicitly that both `from_unit` and `to_unit` are required; list the supported units and their length/weight categories; prohibit guessing a missing unit; and instruct the agent to ask the user for clarification before calling the tool when the source unit is missing.
