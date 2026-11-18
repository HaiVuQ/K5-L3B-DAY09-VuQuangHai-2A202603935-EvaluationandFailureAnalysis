"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate."""
    problems: list[str] = []

    for mid, val in (pr.get("metrics") or {}).items():
        if isinstance(val, float) and not math.isfinite(val):
            problems.append(f"metric {mid} is not finite ({val})")

    if pr.get("evaluator_failures"):
        problems.append(f"evaluator_failures non-empty ({len(pr['evaluator_failures'])})")

    rows = pr.get("rows") or []
    manifest = pr.get("manifest") or {}
    expected_n = int(manifest.get("items", 0)) * len(manifest.get("seeds") or [])
    if len(rows) != expected_n:
        problems.append(f"row count {len(rows)} != manifest items*seeds ({expected_n})")

    pr_keys = [(r.get("item_id"), r.get("seed")) for r in rows]
    if len(pr_keys) != len(set(pr_keys)):
        problems.append("duplicate (item_id, seed) rows in PR report")

    base_rows = base.get("rows") or []
    base_keys = {(r.get("item_id"), r.get("seed")) for r in base_rows}
    if set(pr_keys) != base_keys:
        problems.append("(item_id, seed) set of PR differs from baseline")

    base_slices = {(r.get("item_id"), r.get("seed")): tuple(sorted(r.get("slices") or [])) for r in base_rows}
    for r in rows:
        k = (r.get("item_id"), r.get("seed"))
        if k in base_slices and tuple(sorted(r.get("slices") or [])) != base_slices[k]:
            problems.append(f"slice tags for {k} differ from baseline")
            break

    summary_only = {"pass_5", "cost_per_success"}
    row_metrics = [
        m["id"]
        for m in spec.get("metrics") or []
        if m["id"] not in summary_only and not m["id"].startswith(("pass_at_", "pass_hat_"))
    ]
    for mid in row_metrics:
        if any(r.get(mid) is None for r in rows):
            problems.append(f"metric {mid} has None value(s) in PR rows")

    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        pr_metrics = {m["id"]: m for m in spec.get("metrics") or []}
        for bm in base_spec.get("metrics") or []:
            mid = bm["id"]
            if mid not in pr_metrics:
                problems.append(f"ratchet: metric {mid} removed")
                continue
            pm = pr_metrics[mid]
            if bm.get("blocking") and not pm.get("blocking"):
                problems.append(f"ratchet: metric {mid} became non-blocking")
            bth = bm.get("threshold") or {}
            pth = pm.get("threshold") or {}
            if "max" in bth and (pth.get("max") is None or pth["max"] > bth["max"]):
                problems.append(f"ratchet: metric {mid} max loosened ({bth['max']} -> {pth.get('max')})")
            if "min" in bth and (pth.get("min") is None or pth["min"] < bth["min"]):
                problems.append(f"ratchet: metric {mid} min loosened ({bth['min']} -> {pth.get('min')})")
            if "max_increase" in bth and (
                pth.get("max_increase") is None or pth["max_increase"] > bth["max_increase"]
            ):
                problems.append(f"ratchet: metric {mid} max_increase loosened")
            if bth.get("no_significant_drop") and not pth.get("no_significant_drop"):
                problems.append(f"ratchet: metric {mid} dropped no_significant_drop")

        pr_slices = {(s["name"], s["metric"]): s for s in spec.get("slices") or []}
        for bs in base_spec.get("slices") or []:
            skey = (bs["name"], bs["metric"])
            if skey not in pr_slices:
                problems.append(f"ratchet: slice {skey} removed")
                continue
            ps = pr_slices[skey]
            if bs.get("blocking") and not ps.get("blocking"):
                problems.append(f"ratchet: slice {skey} became non-blocking")
            if "min" in bs and (ps.get("min") is None or ps["min"] < bs["min"]):
                problems.append(f"ratchet: slice {skey} min loosened")
            if "max" in bs and (ps.get("max") is None or ps["max"] > bs["max"]):
                problems.append(f"ratchet: slice {skey} max loosened")
            if bs.get("no_significant_drop") and not ps.get("no_significant_drop"):
                problems.append(f"ratchet: slice {skey} dropped no_significant_drop")

    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for s in spec.get("slices") or []:
        name, mid = s["name"], s["metric"]
        a = per_item(pr, mid, slice_name=name)
        b = per_item(base, mid, slice_name=name)
        val = sum(a.values()) / len(a) if a else None
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        else:
            if "min" in s and val < s["min"]:
                verdict = "fail"
            if "max" in s and val > s["max"]:
                verdict = "fail"
            if s.get("no_significant_drop"):
                keys = sorted(set(a) & set(b))
                if keys:
                    d, lo, hi = stats.paired_bootstrap(
                        [a[k] for k in keys],
                        [b[k] for k in keys],
                        n_resamples=bs.get("n_resamples", 1000),
                        rng=bs.get("rng", 2027),
                    )
                    note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                    if hi < 0:
                        verdict = "fail"
        sid = f"slice:{name}/{mid}"
        if verdict != "ok" and s.get("blocking"):
            blocked.append(sid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if s.get("blocking") else "warn")
        val_str = f"{val:.4f}" if val is not None else "None"
        lines.append(f"  {sid:<30} {val_str:<8} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
