"""Shared helpers for the operational scripts.

Small on purpose. It exists because two scripts grew identical copies of the same
process check, and duplicated helpers are how a fix lands in one place and rots in the
other -- which happened three separate times in one evening with retry logic, pacing and
town resolution.
"""
from __future__ import annotations

import os
import subprocess


def already_running(marker: str) -> int | None:
    """The pid of another python process whose command line contains `marker`.

    Two long runs sharing one Bedrock throttle quota is not twice the throughput: they
    duplicate work, halve each other's rate, and interleave their logs into something
    nobody can read. That happened twice in one evening, both times because the check
    used to confirm the previous run had stopped was itself broken -- once counting its
    own shell command lines, once reading an empty PowerShell `.Count`, which returns
    nothing rather than 1 when exactly one process matches.

    Hence `@(...)`, which forces an array so `.Count` is always a number, and hence a
    single implementation rather than one per script.

    Returns None if the check itself fails: an unreliable guard should not be able to
    block a legitimate run.
    """
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             f"Where-Object {{ $_.CommandLine -like '*{marker}*' }} | "
             "Select-Object -ExpandProperty ProcessId) -join ','"],
            capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:                       # noqa: BLE001 - never block a run on the check
        return None
    mine = os.getpid()
    others = [int(x) for x in out.split(",") if x.strip().isdigit() and int(x) != mine]
    return others[0] if others else None


def refuse_if_running(marker: str, what: str) -> int | None:
    """Print the standard refusal and return an exit code, or None to proceed."""
    other = already_running(marker)
    if other is None:
        return None
    print("\n".join([
        "",
        f"Another {what} is already running (pid {other}).",
        "",
        "Two runs share one store and one throttle quota: they duplicate work,",
        "halve each other's rate, and interleave the log into nonsense.",
        "Stop it first, or pass --allow-concurrent if you genuinely mean to.",
        "",
        "Nothing was called and nothing was spent.",
    ]))
    return 2


#: Per-million-token prices, (input, output), by Bedrock model id.
#:
#: Lived as a private copy in each script that reported a cost, and one of them had a
#: single flat pair hardcoded: a $12 Sonnet run was reported as $1.00, which is the kind
#: of error that only ever runs one way. Unknown models default to the most expensive
#: entry, so a new model id understates nothing.
PRICES: dict[str, tuple[float, float]] = {
    "anthropic.claude-3-5-sonnet-20240620-v1:0": (3.00, 15.00),
    "anthropic.claude-3-haiku-20240307-v1:0": (0.25, 1.25),
}


def cost_of(calls, model: str) -> tuple[int, int, float]:
    """(input tokens, output tokens, dollars) for a slice of telemetry."""
    tin = sum(c.input_tokens for c in calls)
    tout = sum(c.output_tokens for c in calls)
    pin, pout = PRICES.get(model) or max(PRICES.values())
    return tin, tout, tin / 1e6 * pin + tout / 1e6 * pout
