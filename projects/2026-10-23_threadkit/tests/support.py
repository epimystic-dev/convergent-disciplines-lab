"""Shared helpers for the threadkit tests."""

from __future__ import annotations

import copy
import io
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(PKG_DIR, "examples")
LAB_ROOT = os.path.dirname(os.path.dirname(PKG_DIR))
ROOT_THREADS = os.path.join(LAB_ROOT, "threads")


def example(name: str) -> str:
    return os.path.join(EXAMPLES, name)


def load_example(name: str) -> Any:
    with open(example(name), encoding="utf-8") as fh:
        return json.load(fh)


def deepcopy(obj: Any) -> Any:
    return copy.deepcopy(obj)


def run_cli(*args: str, env_extra: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = PKG_DIR + os.pathsep + env.get("PYTHONPATH", "")
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, "-m", "threadkit"] + list(args),
                          capture_output=True, env=env, timeout=60, cwd=PKG_DIR)


def run_main(*args: str) -> Tuple[int, str, str]:
    from threadkit.cli import main
    out, err = io.StringIO(), io.StringIO()
    rc = main(list(args), stdout=out, stderr=err)
    return rc, out.getvalue(), err.getvalue()


def codes(findings) -> List[str]:
    return [f.code for f in findings]


def claim(**kw) -> Dict[str, Any]:
    base = {"id": "c", "text": "The sky is blue at noon on a clear day.", "standing": "settled",
            "basis": {"kind": "observation"}}
    base.update(kw)
    return base


def answer(claims=None, **kw) -> Dict[str, Any]:
    base = {"id": "a", "question": "What colour is the sky?", "mode": "inquiry", "mode_disclosed": True,
            "claims": claims if claims is not None else [claim()], "deliberation": {"kind": "fast"}}
    base.update(kw)
    return base
