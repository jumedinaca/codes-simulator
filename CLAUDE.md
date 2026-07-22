# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A digital transmission simulator built for a Information/Coding Theory course (UNAL, 2026). It models the
full pipeline from source analysis through lossless compression, transmission over a noisy channel, and
error correction. Code comments, docstrings, and CLI output are in Spanish; keep new user-facing strings
and docstrings in Spanish to match the existing style.

## Commands

```bash
uv sync                # install dependencies (Python >=3.14, managed via uv)
uv run main.py          # run the simulator, defaults to CLI mode
uv run main.py -m cli   # interactive terminal UI (InquirerPy prompts)
uv run main.py -m gui   # launches `streamlit run ui/app.py` (currently a stub — the only planned work, see Scope)
```

There is no test suite, linter, or type-checker configured in this repo yet — don't assume `pytest`,
`ruff`, or similar will work.

## Architecture

The simulator is a **five-stage pipeline** (M1–M5), where each stage lives in its own top-level package and
follows the same convention:

- `<package>/base.py` defines an ABC interface plus the `@dataclass` result types the stage produces.
  These base classes also carry shared, non-abstract helper methods (e.g. `compute_entropy`,
  `compute_ber`, `pad_bits`/`split_blocks`) that concrete implementations call into.
- Concrete implementations live as sibling modules (e.g. `s_compression/huffman.py`) and subclass the
  interface from `base.py`.
- `<package>/__init__.py` re-exports the interface, result dataclasses, and all concrete implementations,
  so callers do `from source import *` / `from s_compression import *` etc. rather than reaching into
  submodules directly.

Stages and their package names (note the package names diverge from the stage numbers used in
docstrings/README):

| Stage | Package    | Interface               | Result types                                   | Implementations |
|-------|-----------|--------------------------|-------------------------------------------------|------------------|
| M1 — Fuente | `source/` | `SourceReader` | `SourceStats` | `TextReader`, `ImageReader`, `BitsReader` |
| M2 — Compresión | `s_compression/` | `SourceCodec` | `Codebook`, `CompressionResult` | `HuffmanCodec`, `ShannonFanoCodec`, `TunstallCodec` |
| M3 — Canal | `channel/` | `Channel` | `TransmissionResult` | `BSChannel` (binary symmetric channel) |
| M4 — Corrección | `coding/` | `ErrorCorrectingCode` | `EncodedBlock`, `DecodedBlock`, `CodingStats` | `HammingCode` (Hamming(7,4)) |
| M5 — Métricas | `metrics/` | `MetricsCollector`/`Visualizer` (defined in `metrics/base.py`) | `PipelineReport` | `PipelineMetrics` (`metrics/pipeline_metrics.py`) — note: not exported via `metrics/__init__.py`, import directly from `metrics.pipeline_metrics` |

`core/simulator.py` wires stages M1–M4 together in `Simulator.run()`:

```
source.read(input) → SourceStats
compressor.build_codebook(probabilities) → Codebook
compressor.encode(symbols, codebook) → CompressionResult
code.encode(compression_result.bits) → EncodedBlock
channel.transmit(encoded_block.codeword_bits) → TransmissionResult
code.decode(transmission_result.received) → DecodedBlock
```

`Simulator` stores every intermediate result as an instance attribute (`_source_stats`, `_codebook`,
`_compressor_stats`, `_encoded_block`, `_decoded_block`, `_trans_result`) — the CLI reads these directly
after calling `sim.run(...)` rather than using a return value.

`cli.py` is the interactive entry point: it prompts (via InquirerPy) for source type/input and compression
algorithm, hardcodes `HammingCode()` and `BSChannel(p=0.2)` for now (channel/coding selection is not yet
wired to prompts — see the `#TODO` markers in `run_cli()`), builds a `Simulator`, runs it, then pretty-prints
each stage's dataclass with ANSI-colored tables/bars via the `show_*` helper functions at the top of the file.

`main.py` is a thin dispatcher: `-m cli` (default) calls `cli.run_cli()`, `-m gui` calls `gui.run_gui()`,
which shells out to `streamlit run ui/app.py`.

## Scope

The only remaining planned work is the **Streamlit GUI** (`ui/app.py`, currently a stub launched via
`gui.run_gui()` → `streamlit run ui/app.py`). Everything else below is a deliberate scope decision, not an
oversight — do not add AWGN, Reed-Solomon, metrics wiring, or channel/code CLI prompts unless explicitly
asked:

- `metrics/` (M5) is intentionally not invoked from `cli.py`/`main.py` — `PipelineMetrics`/CSV export exist
  but are out of scope for the run path.
- Only `BSChannel` exists for M3 (no AWGN) and only `HammingCode` exists for M4 (no Reed-Solomon) — both by
  design, not TODOs.
- Channel and coding scheme are permanently hardcoded in `cli.py` (`HammingCode()` — no constructor args,
  fixed at n=7, k=4 — and `BSChannel(p=0.2)`); there is no `ask_channel()`/`ask_code()` and none is planned.

The README describes a more elaborate/idealized module layout (e.g. `compression/` instead of
`s_compression/`, `channel/awgn.py`, `coding/reed_solomon.py`, `metrics/calculator.py`+`plotter.py`) that
does not match the current source tree or its scope — trust the actual code structure and the Scope section
above over the README when they disagree.
