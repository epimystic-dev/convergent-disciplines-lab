"""gatecheck: a linter for commitment records against the gate-versus-target discipline.

Standard library only. The schema is in `data/commitment.schema.json`; the twelve rules
are defined in `rules.py` and run by `scan.py`. A clean scan means the record met the
shape rules A11 asks for - never that the commitment itself is wise, enforceable, or
likely to hold.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .findings import Finding, Severity, Verdict, verdict_from, exit_code
from .rules import ALL_RULES, Rule
from .scan import ScanResult, scan_record, scan_records
from .schema import SchemaError, Validator, load_schema

__all__ = [
    "__version__",
    "Finding",
    "Severity",
    "Verdict",
    "verdict_from",
    "exit_code",
    "ALL_RULES",
    "Rule",
    "ScanResult",
    "scan_record",
    "scan_records",
    "SchemaError",
    "Validator",
    "load_schema",
]
