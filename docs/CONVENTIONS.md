# Engineering contract for convergent-disciplines-lab

Every project in this lab is small, self-contained, tested and independently licensed, and
meets the same contract so a reader who has used one needs no new instructions for the next.
This page is what CI and the publish gate hold a project to.

## Project kinds

`project.json` declares a `kind`. The gate checks the contract for that kind.

| kind | what it is | contract |
|---|---|---|
| `linter` | reads a file surface, reports shape defects with rule ids | the full CLI contract below, plus severity HIGH / MEDIUM / INFO, a verdict rollup (`healthy`, `needs-attention`, `unhealthy`, `unknown`), rule ids `<PREFIX>-001..`, a package surface exporting `__version__`, `Severity`, `Verdict`, `Finding`, `ScanResult`, `ALL_RULES`, `Rule`, and every rule documented in the README |
| `cli` | a command that reads inputs and writes results | the CLI contract below, with documented exit codes |
| `library` | an importable package | `__version__`, a documented public API, a README example the tests execute |
| `spec` | a schema plus a reference validator | the schema file, a validator meeting `cli` or `library`, valid and invalid conformance examples the tests run |
| `harness` | an evaluation or probe runner | the `cli` contract, an authored dataset with provenance notes, a metric whose scope is stated honestly |

## The CLI contract

- Invokable as `python -m <tool>`. `--help` returns 0. An unknown flag returns 2.
- `--version` prints `<tool> x.y.z` and returns 0.
- Results on **stdout**, diagnostics on **stderr**, so `--json` output can be piped unread.
- `rc == 0` means clean. Non-zero means the caller should look: findings, unreadable input,
  or an internal error. Linters use 1 for warnings only and 2 for any HIGH finding or
  unreadable input.
- Linters also accept `--json`, `--strict`, `--include-info` and `--disable <RULE>`.

## Invariants for every kind

- Tests pass under exactly the command CI runs, from the project directory:
  `python -m unittest discover -s tests`. `project.json` declares that same string.
- Python 3.9 or later, standard library only. Optional integrations are imported under
  try / except and every test passes with none of them installed.
- `tests/test_shared_contract.py` locks the invariants above for CLI kinds.
- Plain ASCII punctuation in prose and code. Non-ASCII that a tool must handle lives in
  fixtures as escapes, never as raw characters, and the text report renders any non-ASCII
  it echoes as `<U+XXXX>`.
- No vendor, product, operator or internal names. Authorship is credited to a human-machine
  hybrid intelligence.
- A README with an honest scope section: what the tool does, what it does not do, and its
  real false-positive modes. A clean run is origin-valid, never verified-safe.
- A permissive LICENSE in the project folder.

## How publishing works

A build produces a project locally. A deterministic gate runs the checks above plus a
de-brand / secret scan. A human approves the batch. Only then is it pushed, on a scheduled
day, together with its row in the root README index. Daily maintenance commits land only on
already-published projects.

## Invariants for the threads

The threads data in `threads/` is shared by every project here, so it carries extra rules.

- `threads/threads.json` is ASCII on disk and validates against `threads/threads.schema.json`.
  Diacritics and glyphs appear only as JSON escapes.
- Every lesson keeps its standing, its basis, its derivation and its test. A change that removes
  or weakens a test is a change to the threads, versioned and noted in `NOTICE.md`.
- A lesson marked `derivation: "derived"` is this lab's reading; documentation must say so where
  it presents the lesson.
- A project that bundles threads files keeps byte-identical copies and a test that fails if they
  drift from `threads/`.
- `docs/LESSONS.md`, `docs/WHAT-AI-GAINS.md` and the SVGs in `docs/diagrams/` are generated from
  `threads.json`. CI fails if any is out of date; regenerate rather than edit.
- The data is CC-BY-SA-4.0. Material that adapts it stays CC-BY-SA-4.0; code that only reads it
  carries its own licence. Attribution follows `NOTICE.md`.
- No text of the book is reproduced; every entry is a paraphrase.
