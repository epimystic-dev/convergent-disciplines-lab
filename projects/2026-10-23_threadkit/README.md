# threadkit

**Reference implementation of the threads**: the fifty-eight operational lessons of
[`threads/threads.json`](../../threads/threads.json) as small, standard-library-only Python
modules, plus a CLI that governs answers, grades convergence claims, lints dialogues, reviews
designs and audits deployments.

The threads come from a cross-disciplinary synthesis that asks physics, biology, cognitive
science, history, political economy, ethics and the world's philosophical traditions to carry
one argument. Its method is what an AI system most needs from it: mark how much weight each
claim can bear; count agreement only across independent routes; agree on shape and keep
content plural; keep open what is open. `threadkit` turns that method, and the lessons built on
it, into checks a system can run on its own output.

## Install and run

Python 3.9 or later. No third-party dependencies.

```
python -m pip install -e .
python -m threadkit list                                  # the 58 lessons
python -m threadkit list --layer context                  # the 33 a prompt can carry
python -m threadkit show M3                               # one lesson in full
python -m threadkit check examples/answer_bad.json        # govern an answer record
python -m threadkit assess examples/convergence_flattened.json
python -m threadkit lint examples/dialogue_evasive.json
python -m threadkit review examples/review_weak.json
python -m threadkit decide examples/decision_weak.json
python -m threadkit consensus examples/consensus_copies.json
python -m threadkit audit examples/deployment_weak.json
python -m threadkit validate answer examples/answer_good.json
python -m threadkit prompt > system-prompt.txt            # the drop-in system prompt
python -m threadkit catalogue --output LESSONS.md         # the human-readable catalogue
python examples/reference_advisor.py                      # a governed revise-until-healthy loop
```

Exit codes:

- `0` clean: healthy, every record valid
- `1` needs attention (MEDIUM findings, or INFO under `--strict`)
- `2` unhealthy (any HIGH finding), an invalid record, or unreadable input

Results go to stdout and a one-line summary to stderr, so `--json` output can be piped. Text
output is ASCII: diacritics are folded (`niskama`) and the standing glyphs are shown as
`<U+25CF>` on a console that cannot print them; `check --ascii` renders standings as
`[settled]`-style tags instead. Files written with `--output` keep the original characters.

## The modules

| Module | Lessons | What it checks |
|---|---|---|
| `threadkit.register` | M1, M2, M5, M7, S1, K6, A6, F1, R6 | each claim's standing (settled, established, contested, limit, bridge, method) and whether its wording, basis and evidence fit it: no proof language on contested claims, no settled claim on a partial convergence or an own thesis, primary sources for numbers, self-reports not asserted as fact, forecasts as windows not destinies, risk probabilities with their own source |
| `threadkit.causal` | R4 | the rung of each causal claim (association, intervention, counterfactual), declared or read from its phrasing; rung 2 needs causal assumptions, rung 3 a structural model; a correlation dressed as a recommendation; parity-only fairness audits |
| `threadkit.convergence` | M2, M3, M4, M6, M7 | orthogonality-as-evidence: routes linked by a shared upstream source or a shared method collapse into one witness; three or more independent routes can support strong, two partial, one withdrawn; identity phrasing and duplicated content (the anti-Capra discipline) withdraw the claim; citation artefacts are dropped |
| `threadkit.disagreements` | M4 | a register of preserved disagreements, each with two or more attributed positions, resolvable only by a stated new piece of evidence |
| `threadkit.explanation` | R2 | hard-to-vary explanations: what constrains each detail, and the counterfactuals the explanation commits to |
| `threadkit.argument` | D1, D2, D3, K4 | inquiry or advocacy declared; a persuasive purpose in inquiry form; the points of defeat in a structured dialogue (unanswered questions, answers to unasked questions, repetition, unacknowledged contradiction, quiet thesis shift) and refutation without a position |
| `threadkit.moral` | D4, D5 | the seven moral convergences as firm ground, the five foundational disagreements answered with attributed positions and no default verdict, and no identity glosses between traditions |
| `threadkit.debias` | S8, S7 | high-stakes decisions start from a reference class, run a pre-mortem, record discarded alternatives, are checked by someone other than the decider and are revisited; probabilities as natural frequencies |
| `threadkit.cooperation` | K1, K2, K3 | a published reciprocity policy (nice, forgiving, provokable, clear) and an agent that plays it; reputation bound to lineage so forks and merges inherit open findings; Ostrom's eight principles |
| `threadkit.consensus` | A5 | multi-agent votes grouped by lineage, each lineage one witness, with a diversity attestation required |
| `threadkit.review` | F1-F5, A1, A3, A4, A10, A12, D7, K5, F7, P1 | the four-move design review with its impact sections: practice and foundations, no self-continuation objective, the relations and shared media, who gains and who pays, the three freedoms and four commons, the eight capacities, the infrastructure layers, the discourse test |
| `threadkit.governor` | the answer-level lessons | `AnswerGovernor` composes the claim, causal, deliberation, self-description, mode, moral and disagreement checks around a model's draft answer and renders it with each claim's standing visible |
| `threadkit.audit` | all | audits a deployment declaration (rules below) |

## Library use

```python
import threadkit
from threadkit.governor import AnswerGovernor

t = threadkit.load()
print(len(t.lessons), t.convergence("CV2")["grade"])                       # 58 strong

draft = {
    "id": "a1", "question": "Do all religions teach the same thing?", "mode": "inquiry",
    "claims": [{"id": "c1", "text": "Science has proven that all religions teach the same thing.",
                "standing": "contested", "basis": {"kind": "recall"}}],
    "deliberation": {"kind": "fast"},
}
result = AnswerGovernor(t).govern(draft)
print(result.verdict, [f.code for f in result.findings])                   # unhealthy ['REG-001']

record = {"id": "cv", "shape": "Relations come before things.", "declared_grade": "strong",
          "falsifier": "a shared upstream source", "disagreements_preserved": ["what a relation is"],
          "routes": [{"id": "a", "tradition": "physics", "method": "experiment", "distinct_content": "x"},
                     {"id": "b", "tradition": "dialectic", "method": "refutation", "distinct_content": "y"}]}
print(threadkit.assess(record).computed_grade)                             # partial
```

The test suite runs this example.

## The audit rules

`threadkit audit` reads a deployment declaration
([`threadkit/data/deployment.schema.json`](threadkit/data/deployment.schema.json)): which
lessons a team has adopted, at which layer, with an owner, a merge date, a test and a review
date.

| id | severity | finding |
|---|---|---|
| `THR-001` | MEDIUM | nothing adopted |
| `THR-002` | HIGH | an unknown lesson id |
| `THR-003` | MEDIUM | a lesson adopted at a layer that cannot enforce it |
| `THR-004` | MEDIUM | an adopted item with no owner or no merge date |
| `THR-005` | MEDIUM | lessons adopted without the method baseline (M1-M4) |
| `THR-006` | MEDIUM | a four-move lesson (F1-F4) adopted without F5 |
| `THR-007` | INFO | an adopted lesson with no recorded test or review date |
| `THR-008` | INFO | a review date that has passed |
| `THR-009` | INFO | a strand with nothing adopted |

The other checkers' codes (`REG-`, `CAU-`, `CON-`, `DIS-`, `EXP-`, `ARG-`, `DLG-`, `MOR-`,
`DEB-`, `COOP-`, `OST-`, `CNS-`, `REV-`, `GOV-`) are listed in each module's docstring, and every
finding names the lesson it enforces.

## The data contracts

Ten JSON Schemas in [`threads/schemas/`](../../threads/schemas/) (copied into
`threadkit/data/schemas/`): `claim`, `answer`, `convergence`, `disagreement`, `explanation`,
`dialogue`, `decision-record`, `design-review`, `consensus`, `agent-policy`. They use a small
subset of JSON Schema 2020-12, so any conforming validator accepts them; the bundled validator
refuses a schema that uses anything else rather than silently ignoring it.

## Honest scope

What this does:

- Implements the checkable part of the lessons, with tests for what each check refuses as well
  as what it accepts.
- Reads structured records: a model (or a person) states the standing of each claim, the rung
  of each causal claim, the routes of each convergence, the turns of a dialogue. The checks
  then hold the record to the lessons.

What this does not do:

- It does not read minds or free text. A model can mislabel a claim's standing; the governor
  catches wording that contradicts the label and records that contradict each other, not a
  label that is consistently wrong. Pair it with independent review (lesson R3).
- The rung classifier and the identity-phrasing detectors are English-language heuristics.
  They err toward flagging, and they will miss paraphrases.
- A computed convergence grade is a ceiling, not a verdict. It depends on the routes and links
  the assessor recorded; the method's own test is a critic searching for the upstream source
  the assessor missed.
- It does not certify that a system reasons well, is fair, or is safe. A healthy result means
  the record is consistent with the lessons. It is **origin-valid, content-unverified**, never
  **verified-safe**.
- Many lessons (the shared medium, diversity among agents, the freedoms, the discourse test,
  the institutional moves) need architecture and people. `threadkit` checks that their records
  exist and are coherent; it cannot do the work.

False-positive modes:

- `REG-001` flags proof language on non-settled claims even when it appears inside a quotation
  or a report of someone else's view; reword or mark the claim's standing accordingly.
- `CAU-003` reads phrasing such as "leads to" as interventional even in a sentence that is
  only reporting an association; tag the rung explicitly.
- `CON-004` flags a shape that mentions a route's tradition name; a neutral restatement fixes it.

## How it is made

Produced by **a human-machine hybrid intelligence** under a maker-checker discipline. The
lessons are adapted from *The Convergent Threads: A Synthesis for the Age of Mind*
(CC-BY-SA-4.0); see [`NOTICE.md`](../../NOTICE.md) for the attribution and changes. The module
design, the contracts and the finding rules are this lab's own and are not claims of the book.

## License

Apache-2.0 for the code. See `LICENSE`. The threads data bundled in `threadkit/data/` (the
lessons, schemas and prompts) is CC-BY-SA-4.0, as stated in
[`threads/LICENSE`](../../threads/LICENSE); it travels with its own licence.
