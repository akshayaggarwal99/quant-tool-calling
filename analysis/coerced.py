#!/usr/bin/env python3
"""Type-coerced secondary tool-calling score.

A strict BFCL verdict rejects a call whose argument is the right value in the wrong type, for
example {"base": "10"} where the schema says integer. This module re-checks every strict failure
with BFCL's own simple_function_checker after coercing string-typed arguments to the type the
function schema declares (integer, float, boolean, array, tuple, dict), when the string parses as
that type. Nothing is generated again: the inputs are the score rows BFCL wrote, which carry the
decoded call, the function schema and the reference answer. An item is coerced-correct when it
passed strict scoring or when the coerced re-check passes, so the coerced score is never below the
strict one. Values that do not parse, or that parse to something the reference does not hold, stay
failures; so do decode failures, wrong function names and missing arguments.
"""
import ast, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from bfcl_eval.eval_checker.ast_eval.ast_checker import simple_function_checker
from bfcl_eval.constants.enums import Language

_INT = re.compile(r"\s*[+-]?\d+\s*$")
_FLOAT = re.compile(r"\s*[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?\s*$")

def parse_as(t, s):
    """Parse string s as schema type t; None when it does not parse as that type."""
    try:
        if t == "integer":
            return int(s) if _INT.match(s) else None
        if t == "float":
            return float(s) if _FLOAT.match(s) else None
        if t == "boolean":
            return {"true": True, "false": False}.get(s.strip().lower())
        if t in ("array", "tuple", "dict"):
            try: v = json.loads(s)
            except Exception: v = ast.literal_eval(s)
            want = dict if t == "dict" else (list, tuple)
            return v if isinstance(v, want) else None
    except Exception:
        return None
    return None

def coerce_args(func_desc, args):
    props = func_desc.get("parameters", {}).get("properties", {})
    out = {}
    for k, v in args.items():
        t = props.get(k, {}).get("type")
        cv = parse_as(t, v) if isinstance(v, str) and t in ("integer", "float", "boolean", "array", "tuple", "dict") else None
        out[k] = v if cv is None else cv
    return out

def coerced_pass(row):
    """True when a strict failure row passes BFCL's checker after argument coercion."""
    dec = row.get("model_result_decoded")
    if not isinstance(dec, list) or len(dec) != 1 or not isinstance(dec[0], dict) or len(dec[0]) != 1:
        return False
    fname, args = next(iter(dec[0].items()))
    if not isinstance(args, dict): return False
    funcs = row.get("prompt", {}).get("function") or []
    if not funcs: return False
    fd = next((f for f in funcs if f.get("name") == fname), funcs[0])
    try:
        r = simple_function_checker(fd, {fname: coerce_args(fd, args)}, row["possible_answer"][0], Language.PYTHON, row["model_name"])
        return bool(r.get("valid"))
    except Exception:
        return False

def score_run(score_file, result_file):
    """Return (n, strict_verdicts, coerced_verdicts, stats) for one rung. Verdict dicts map id -> bool."""
    rows = [json.loads(l) for l in open(score_file) if l.strip()]
    fails = rows[1:]
    ids = [json.loads(l)["id"] for l in open(result_file) if l.strip()]
    bad = {r["id"]: r for r in fails}
    strict = {i: (i not in bad) for i in ids}
    coerced = dict(strict)
    stats = {"fails": len(fails), "type_err": 0, "decode_err": 0, "coercible": 0}
    for i, r in bad.items():
        et = str(r.get("error_type", ""))
        stats["type_err"] += et.startswith("type_error")
        stats["decode_err"] += et.startswith("ast_decoder")
        if coerced_pass(r):
            coerced[i] = True; stats["coercible"] += 1
    return len(ids), strict, coerced, stats

if __name__ == "__main__":
    import glob
    for stem in ["Qwen3-1.7B", "Qwen3-8B", "Qwen3-14B", "Llama-3.2-3B", "Llama-3.1-8B"]:
        for q in ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M"]:
            base = HERE / "runs" / (q if stem == "Qwen3-1.7B" else f"{stem}/{q}")
            sc = list((base / "score").rglob("*simple_python*score.json")); rs = list((base / "result").rglob("*simple_python*.json"))
            if not sc or not rs: continue
            n, s, c, st = score_run(sc[0], rs[0])
            print(f"{stem:13s} {q:7s} n={n} strict={100*sum(s.values())/n:.2f} coerced={100*sum(c.values())/n:.2f} {st}")
