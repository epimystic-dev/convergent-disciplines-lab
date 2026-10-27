"""Shared helpers for the probeset tests."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from typing import Dict, Optional, Tuple

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(PKG_DIR, "examples")


def good(name: str) -> str:
    return os.path.join(EXAMPLES, "good", name + ".txt")


def bad(name: str) -> str:
    return os.path.join(EXAMPLES, "bad", name + ".txt")


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def run_cli(*args: str, env_extra: Optional[Dict[str, str]] = None,
            stdin_bytes: Optional[bytes] = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = PKG_DIR + os.pathsep + env.get("PYTHONPATH", "")
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, "-m", "probeset"] + list(args),
                          input=stdin_bytes, capture_output=True, env=env,
                          timeout=60, cwd=PKG_DIR)


def run_main(*args: str) -> Tuple[int, str, str]:
    from probeset.cli import main
    out, err = io.StringIO(), io.StringIO()
    rc = main(list(args), stdout=out, stderr=err)
    return rc, out.getvalue(), err.getvalue()


def codes(findings) -> list:
    return [f.code for f in findings]
