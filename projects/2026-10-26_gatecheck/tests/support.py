"""Shared helpers for the gatecheck tests."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(PKG_DIR, "examples")


def ok(name: str) -> str:
    return os.path.join(EXAMPLES, "conforming", name + ".json")


def bad(name: str) -> str:
    return os.path.join(EXAMPLES, "non_conforming", name + ".json")


def load(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run_cli(*args: str, env_extra: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = PKG_DIR + os.pathsep + env.get("PYTHONPATH", "")
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, "-m", "gatecheck"] + list(args),
                          capture_output=True, env=env, timeout=60, cwd=PKG_DIR)


def run_main(*args: str) -> Tuple[int, str, str]:
    from gatecheck.cli import main
    out, err = io.StringIO(), io.StringIO()
    rc = main(list(args), stdout=out, stderr=err)
    return rc, out.getvalue(), err.getvalue()


def codes(findings) -> List[str]:
    return [f.code for f in findings]
