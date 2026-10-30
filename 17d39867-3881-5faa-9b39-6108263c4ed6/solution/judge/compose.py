#!/usr/bin/env python3
"""Compose the deterministic outcome with the judged channel into one score.

The formula is the one the reference bundles record in their own grading.json:

    score_eval = gate * ((1 - 2*alpha) * outcome + 2*alpha * process)

ALPHA is 0.05, the same value the reference bundles compose at, so the judged channel carries
2*0.05 = 10 percent of the score. It was 0 while the rubric was uncalibrated, because weighting a
rubric nobody has checked lets an unmeasured judge move real scores. The operator has since run
the agreement pass over the eleven diffs in solution/calibration/ and confirmed the channel
separates them, which is what admits a non-zero weight.

alpha lives here and nowhere else. Harbor and its Reward Kit have no composition step and read the
reward key alone, task.toml carries no alpha, and the approved contract does not bind one, so this
value is the author's to set. SCORE_ALPHA overrides it at run time, and the grading record writes
down whichever value was used.

At this weight a deterministically perfect run carrying slop scores 0.971 rather than 1.0, and a
run that fails every test but worked cleanly earns 0.088 rather than 0.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

ALPHA = 0.05


def compose(
    outcome: float, rubric: float | None, alpha: float = ALPHA
) -> dict[str, Any]:
    gate = 1
    if rubric is None:
        return {
            "alpha": alpha,
            "gate": gate,
            "outcome": round(outcome, 4),
            "process": None,
            "score_eval": round(outcome, 4),
            "formula": "gate * ((1 - 2*alpha) * outcome + 2*alpha * process)",
            "fallback": "outcome only: the judged channel produced no score",
        }
    score_eval = gate * ((1 - 2 * alpha) * outcome + 2 * alpha * rubric)
    return {
        "alpha": alpha,
        "gate": gate,
        "outcome": round(outcome, 4),
        "process": round(rubric, 4),
        "score_eval": round(score_eval, 4),
        "formula": "gate * ((1 - 2*alpha) * outcome + 2*alpha * process)",
        "fallback": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bundle", type=Path, help="bundle root holding tests/judge.toml")
    ap.add_argument(
        "--out", type=Path, required=True, help="log dir holding final.diff"
    )
    ap.add_argument(
        "--outcome", type=float, required=True, help="the deterministic reward"
    )
    ap.add_argument(
        "--alpha", type=float, default=float(os.environ.get("SCORE_ALPHA", ALPHA))
    )
    args = ap.parse_args()

    from judge import score

    rubric, detail = score(args.bundle, args.out)
    doc = {
        "schema_version": "scout-grading/1",
        "rubric": {"score": rubric, **detail},
        "composition": compose(args.outcome, rubric, args.alpha),
    }
    doc["reward"] = doc["composition"]["score_eval"]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "grading.json").write_text(
        json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "reward": doc["reward"],
                "rubric": rubric,
                "state": detail["state"],
                "alpha": args.alpha,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
