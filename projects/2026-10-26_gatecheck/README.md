# gatecheck

A linter for commitment records against the gate-versus-target discipline (Rule A11): a
`gate` promises not to do X and must declare its trigger, its enforcer, its dependencies
and the scope of any escape clause; a `target` promises to do X and must declare a metric
and a deadline; a commitment that is competitor-contingent must name the competitor and
the measurable signal.

> Part of [convergent-disciplines-lab](https://github.com/epimystic-dev/convergent-disciplines-lab).
> Clean-room reference implementation of Rule A11 from the threads (CC-BY-SA-4.0), with
> twelve rules, a schema, and a scanner this lab's own.

## The problem

Published AI red-lines and commitments are routinely written as prose: "we will not deploy
a model that could meaningfully assist in weapons of mass destruction", "we commit to
pause unilaterally if a redline is approached". The industry-watch finding of Autumn 2026
is that several of the strongest published pledges have been weakened under
competitor-contingent clauses, with no measurable trigger, no named enforcer, no stated
dependencies, and an escape clause that nullifies the commitment under conditions the
original audience was never told.

The gate-versus-target discipline (Rule A11 of the threads) names what a commitment needs
to carry: a `kind` (`gate` vs `target`), a measurable `trigger`, an identified `enforcer`,
declared `dependencies` and `escape_clauses` whose `scope` is narrower than the trigger.
`gatecheck` turns that discipline into a machine-readable schema and a linter.

## Install and run

```
git clone https://github.com/epimystic-dev/convergent-disciplines-lab.git
cd convergent-disciplines-lab/projects/2026-10-26_gatecheck
python -m pip install -e .           # Python 3.9+, standard library only

python -m gatecheck rules                                             # the twelve rules
python -m gatecheck show GATE-007                                     # one rule in full
python -m gatecheck scan examples/conforming/gate_healthy.json        # healthy; rc 0
python -m gatecheck scan examples/non_conforming/escape_broader.json  # unhealthy; rc 2
python -m gatecheck validate examples/non_conforming/unknown_kind.json  # schema-only; rc 2
python -m gatecheck schema > commitment.schema.json                   # the schema
```

Exit codes follow the lab contract: `0` healthy, `1` needs-attention (MEDIUM only or INFO
under `--strict`), `2` unhealthy (any HIGH, unreadable input, or schema violation under
`validate`).

Scan a JSONL file or a JSON array in one shot:

```
python -m gatecheck scan all-commitments.jsonl --json > report.json
```

Disable a rule for a run (for example, a research project that intentionally publishes
self-attested gates):

```
python -m gatecheck scan path.json --disable GATE-003 --disable GATE-006
```

## Library

```python
from gatecheck import scan_record

record = {
    "id": "ex-pause-under-threshold",
    "title": "No deployment above a measurable threshold",
    "kind": "gate",
    "committed_at": "2026-04-15",
    "last_reviewed_at": "2026-10-01",
    "trigger": {"metric": "bio-uplift-benchmark-v1", "threshold": 0.08, "measurable": True},
    "enforcer": {"kind": "independent-reviewer", "named": "External Review Panel"},
    "dependencies": [{"kind": "benchmark", "statement": "the benchmark remains valid"}],
}
result = scan_record(record)
print(result.verdict)        # 'healthy'
print(result.findings)       # ()
```

## The schema

The commitment schema lives at `gatecheck/data/commitment.schema.json` (printable with
`python -m gatecheck schema`). The required fields are `id`, `title`, `kind`,
`committed_at`; everything else is optional but the twelve rules fire against missing
substance.

Key fields:

| Field | For | Carries |
|---|---|---|
| `kind` | all | `gate` (promise not to do X) or `target` (promise to do X) |
| `trigger` | gates | `statement`, `metric`, `threshold`, `measurement_window`, `measurable` |
| `enforcer` | all | `kind` (self-attested / internal / independent / regulator / contractual), `named`, `escalation`, `external_check` |
| `dependencies` | gates | an array of `{kind, statement}` entries: external facts whose change would alter the gate |
| `escape_clauses` | all | an array of `{statement, scope, competitor_contingent, named_competitor, trigger_metric}` entries |
| `target_metric`, `target_deadline` | targets | the measurable and the date |
| `externally_verifiable`, `enforcer.external_check` | all | whether an outside reader can verify, and where |
| `committed_at`, `last_reviewed_at`, `derived_from` | all | provenance and freshness |

The schema is deliberately permissive: `additionalProperties` is `true`, so an organisation
can add its own fields and still pass. The discipline is in the rules, not in the schema.

## The rules

Twelve rules, severities HIGH / MEDIUM / INFO, every one documented. `python -m gatecheck
rules` prints the registry; `python -m gatecheck show GATE-007` prints one rule in full.

| ID | Severity | Applies to | Rule |
|---|---|---|---|
| `GATE-001` | HIGH | gate | a gate must declare a trigger (a gate without a trigger is a hope) |
| `GATE-002` | HIGH | gate | a gate must declare an enforcer (name who or what checks and enforces) |
| `GATE-003` | MEDIUM | gate | self-attested enforcement is weaker than independent / regulatory / contractual |
| `GATE-004` | MEDIUM | any | a competitor-contingent clause must name the competitor and the metric |
| `GATE-005` | MEDIUM | any | a commitment must have `committed_at` and `last_reviewed_at` dates |
| `GATE-006` | INFO | gate | declare dependencies so an auditor can watch what the gate rests on |
| `GATE-007` | HIGH | any | an escape clause must have `scope` or a `trigger_metric` matching the gate's trigger |
| `GATE-008` | HIGH | target | a target must declare `target_metric` and `target_deadline` |
| `GATE-009` | MEDIUM | any | `last_reviewed_at` more than 365 days ago, or before `committed_at` |
| `GATE-010` | HIGH | any | unknown `kind` (must be `gate` or `target`) |
| `GATE-011` | MEDIUM | gate | the trigger has no metric and is not marked `measurable: true` |
| `GATE-012` | MEDIUM | any | `externally_verifiable: true` but the enforcer has no `external_check` |

GATE-007 is the central rule: a competitor-contingent clause with no named signal, or a
clause whose `trigger_metric` differs from the gate's, is the shape of the pledges the
industry-watch finding flagged.

## Honest scope

- `gatecheck` lints **shape**, not substance. A gate can pass every rule and still be a bad
  commitment: the chosen metric could be wrong, the chosen threshold could be too permissive,
  the chosen enforcer could be captured. The linter checks that the structure is one an
  auditor can read.
- A **passing scan is origin-valid, not verified-safe.** It means the record met the shape
  rules this run. The commitment the record describes may still fail to bind the organisation
  in a crisis.
- The linter does not verify any **external claim**: the `enforcer.named` field is a string
  of text; the linter does not check that the panel exists, has agreed to the role, or is
  independent in fact. That is for a human reviewer.
- The staleness threshold (365 days for `GATE-009`) is a default. For slower-moving domains
  longer intervals may be defensible; use `--disable GATE-009` and declare the review cadence
  elsewhere.
- The schema is a **minimal draft-07 subset**; the bundled validator supports required,
  properties, type, enum, minLength, items and additionalProperties. If a user adds a complex
  schema extension that uses features beyond that subset, swap in the `jsonschema` package.

## Known false positives

- A gate whose trigger is deliberately open-ended (`"we will revisit this gate quarterly in
  light of new eval results"`) will fire `GATE-011` because the trigger has no fixed metric.
  Either declare `measurable: false` with a human-readable `measurement_window`, or disable
  the rule for that record.
- A gate that passes `GATE-004` has at least one of `named_competitor` and `trigger_metric`;
  it does not have *both*. If an organisation wants both to be required, add a project-local
  rule.
- `GATE-009` is a strict time threshold. A commitment whose `last_reviewed_at` is exactly
  365 days ago passes; 366 fires. Teams that want warning before the hard threshold should
  schedule their own alert.

## How it is made

Every artifact in this lab is produced by **a human-machine hybrid intelligence**, under
maker-checker, and passes an external, deterministic gate before publication: a de-brand
and secret scan, tests green under the public CI command, and a claims pass. A passing
gate means **origin-valid, content-unverified**.

The engineering contract is in [`docs/CONVENTIONS.md`](../../docs/CONVENTIONS.md).

## License

`gatecheck` code and schema: Apache-2.0 (`LICENSE`).

The derivation of the rules from Rule A11 of the threads is an adaptation of a CC-BY-SA-4.0
source; the rule descriptions are therefore CC-BY-SA-4.0. If you publish a modified version
of the rule texts, release under the same licence and credit the source as `NOTICE.md` in
the lab root describes.
