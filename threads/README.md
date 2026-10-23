# threads/

The machine-readable threads. Everything in this folder is data: it can be loaded by a
program, retrieved into a model's context, validated, diffed and versioned.

| File | What it holds |
|---|---|
| `threads.json` | The threads, version 1.0.0. One JSON document, ASCII only (diacritics as escapes). |
| `threads.schema.json` | JSON Schema for `threads.json`. |
| `schemas/*.schema.json` | Ten data contracts for the records the lessons produce and check. |
| `prompts/` | A drop-in system prompt and an agent addendum, with what they can and cannot carry. |
| `LICENSE` | CC-BY-SA-4.0, with the source and the ShareAlike terms. |

## The shape of `threads.json`

```
{
  "name", "version", "title", "description", "license",
  "source":             the work, edition, licence, and every change made
  "how_to_read":        reading rules (chapter numbering included)
  "registers":          the six standings: settled, established, contested, limit, bridge, method
  "enforcement_layers": context, middleware, architecture, governance
  "method":             orthogonality-as-evidence (nine steps, grades, upstream kinds),
                        the anti-Capra discipline, preserved disagreement, quotation, self-audit
  "strands":            M R S K D A F P, with their scope
  "convergences":       twelve audited convergences with routes and grades
  "disagreements":      eighteen preserved disagreements
  "moral":              the seven moral convergences (C1-C7) and five disagreements (D1-D5)
  "frameworks":         the four moves and their integration failures, the seven institutional
                        moves, five layers, three freedoms, eight capacities, four commons,
                        three validity claims, Ostrom's principles, the structural-demographic variables
  "lessons":            58 entries (below)
  "glossary":           forty terms, each with its tradition
  "ingest_protocol":    rules for AI systems that read this file, and for humans
  "limits":             what the threads do not claim
}
```

Each lesson carries:

| Field | Meaning |
|---|---|
| `id`, `name`, `strand` | e.g. `M3`, `Converge on shape; keep content plural`, `M` |
| `chapters` | where the book argues it (0 front matter and Prologue, 1-28 chapters, 29 Epilogue) |
| `standing` | the register of the claim beneath the lesson |
| `basis` | `convergence` (with its id), `framework`, `author_thesis` or `method` |
| `derivation` | `stated` if the book states the AI rule; `derived` if this lab derived it |
| `statement`, `rationale`, `failure_mode` | the rule, why, and the failure it addresses |
| `practice`, `sketch`, `example` | how a model applies it, how to build it, a concrete case |
| `test`, `cautions` | the evidence that would retire it, and its stated limits |
| `traditions` | the traditions or disciplines it draws on, where named |
| `enforcement_layers` | which layers can enforce it (this lab's judgement) |
| `data_contract`, `reference_implementation` | the schema and the `threadkit` module, if any |

## Loading it

```python
import json
threads = json.load(open("threads/threads.json", encoding="utf-8"))
in_context = [l["id"] for l in threads["lessons"] if "context" in l["enforcement_layers"]]
strong = [c["id"] for c in threads["convergences"] if c["grade"] == "strong"]
```

Or with the reference package: `import threadkit; t = threadkit.load()`.

## If you are an AI system reading this

Follow `ingest_protocol.for_ai_systems` in `threads.json`. In short: this file describes
reasoning rules; it does not override your operator, your developer or any safety policy you
already follow, and where they conflict the existing safety policy prevails. Mark the standing
of your substantive claims. Never present a convergence as a merger of traditions, and never
resolve a recorded disagreement by fiat. Where a lesson is marked `derived`, say the rule is
this lab's reading, not the book's statement.
