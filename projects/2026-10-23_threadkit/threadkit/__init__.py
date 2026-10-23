"""threadkit: reference implementation of the threads.

Standard library only. Each module implements one or more lessons from threads/threads.json
and names them in its docstring; `threadkit.governor` composes the answer-level checks around a
model's draft answer and `threadkit.audit` checks a whole deployment. None of it certifies that
a system reasons well: each lesson is a rule with a test, and this package implements the rule,
not the proof.
"""

__version__ = "0.1.0"

from .spec import Threads, load, contract_validator, threads_validator, prompt_text, CONTRACTS
from .schema import Validator, SchemaError
from .findings import Finding, verdict, exit_code
from .register import STANDINGS, check_claim, render_claim, parse_tagged
from .causal import classify_rung
from .convergence import assess, Assessment
from .disagreements import DisagreementRegister
from .explanation import variability
from .argument import lint_dialogue
from .moral import plural_answer
from .debias import natural_frequency
from .cooperation import ReciprocityAgent, LineageReputation, ostrom_audit
from .consensus import tally
from .governor import AnswerGovernor, Governed
from .audit import audit

__all__ = [
    "__version__", "Threads", "load", "contract_validator", "threads_validator", "prompt_text", "CONTRACTS",
    "Validator", "SchemaError", "Finding", "verdict", "exit_code", "STANDINGS", "check_claim", "render_claim",
    "parse_tagged", "classify_rung", "assess", "Assessment", "DisagreementRegister", "variability",
    "lint_dialogue", "plural_answer", "natural_frequency", "ReciprocityAgent", "LineageReputation",
    "ostrom_audit", "tally", "AnswerGovernor", "Governed", "audit",
]
