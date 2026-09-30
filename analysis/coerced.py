#!/usr/bin/env python3
"""Type-coerced secondary tool-calling score, plus failure classification.

A strict BFCL verdict rejects a call whose argument is the right value in the wrong type, for
example {"base": "10"} where the schema says integer. This module re-checks every strict failure
with BFCL's own simple_function_checker after coercing string-typed arguments to the type the
function schema declares (integer, float, boolean, array, tuple, dict), when the string parses as
that type. Nothing is generated again: the inputs are the score rows BFCL wrote, which carry the
decoded call, the function schema and the reference answer. An item is coerced-correct when it
passed strict scoring or when the coerced re-check passes, so the coerced score is never below the
strict one. Values that do not parse, or that parse to something the reference does not hold, stay
failures; so do wrong function names and missing arguments.

Decode failures (BFCL error type ast_decoder) are re-read once from the raw output (29 Sep 2026):
the Llama 3.1 handler in bfcl-eval 2026.3.23 decodes a single call with Python's eval(), which
refuses the JSON literals true, false and null that Meta's tool-call format allows. A raw output
that json.loads() reads as exactly one {"name": ..., "parameters": {...}} object is treated as
that call and then checked like any other; anything else stays a decode failure.

Failure classes reported per run (all from BFCL's own error_type strings):
  type_err     type_error:*            (a parameter of the wrong type)
  value_err    value_error:*           (a parameter with the wrong value)
  decode_err   ast_decoder:*           (the handler decoded no call)
  decode_json  decode failures whose raw output is one well-formed JSON call
  wrong_name   simple_function_checker:wrong_func_name
  wrong_count  simple_function_checker:wrong_count (no call, or the wrong number of calls)
  no_call      decode failures plus wrong_count rows whose decoded list is empty
  missing      simple_function_checker:missing_required / missing_optional
  struct       decode_err + wrong_name + wrong_count + missing (the call's shape is wrong)
  semantic     type_err + value_err (the call's shape is right, a value or type is not)
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

def json_call(raw):
    """One well-formed JSON tool call in Meta's format, as {name: params}, or None."""
    if not isinstance(raw, str): return None
    try:
        v = json.loads(raw.replace("<|python_tag|>", "").strip())
    except Exception:
        return None
    if isinstance(v, list) and len(v) == 1: v = v[0]
    if isinstance(v, dict) and isinstance(v.get("name"), str) and isinstance(v.get("parameters"), dict):
        return {v["name"]: v["parameters"]}
    return None

def decoded_call(row):
    """The single decoded call of a strict-failure row, from the handler or from a JSON re-read."""
    dec = row.get("model_result_decoded")
    if isinstance(dec, list) and len(dec) == 1 and isinstance(dec[0], dict) and len(dec[0]) == 1:
        return dec[0], False
    if str(row.get("error_type", "")).startswith("ast_decoder"):
        jc = json_call(row.get("model_result_raw"))
        if jc: return jc, True
    return None, False

def coerced_pass(row):
    """True when a strict failure row passes BFCL's checker after argument coercion."""
    call, _ = decoded_call(row)
    if call is None: return False
    fname, args = next(iter(call.items()))
    if not isinstance(args, dict): return False
    funcs = row.get("prompt", {}).get("function") or []
    if not funcs: return False
    fd = next((f for f in funcs if f.get("name") == fname), funcs[0])
    try:
        r = simple_function_checker(fd, {fname: coerce_args(fd, args)}, row["possible_answer"][0], Language.PYTHON, row["model_name"])
        return bool(r.get("valid"))
    except Exception:
        return False

STAT_KEYS = ("fails", "type_err", "value_err", "decode_err", "decode_json", "wrong_name", "wrong_count",
             "no_call", "missing", "struct", "semantic", "coercible", "coercible_decode")

def score_run(score_file, result_file):
    """Return (n, strict_verdicts, coerced_verdicts, stats, error_types) for one rung.
    Verdict dicts map id -> bool; error_types maps failing id -> BFCL error_type."""
    rows = [json.loads(l) for l in open(score_file) if l.strip()]
    fails = rows[1:]
    ids = [json.loads(l)["id"] for l in open(result_file) if l.strip()]
    bad = {r["id"]: r for r in fails}
    strict = {i: (i not in bad) for i in ids}
    coerced = dict(strict)
    st = {k: 0 for k in STAT_KEYS}; st["fails"] = len(fails)
    et = {}
    for i, r in bad.items():
        e = str(r.get("error_type", "")); et[i] = e
        st["type_err"] += e.startswith("type_error")
        st["value_err"] += e.startswith("value_error")
        dec = e.startswith("ast_decoder"); st["decode_err"] += dec
        st["wrong_name"] += e.endswith("wrong_func_name")
        st["wrong_count"] += e.endswith("wrong_count")
        st["missing"] += ("missing_required" in e) or ("missing_optional" in e)
        st["no_call"] += dec or (e.endswith("wrong_count") and not r.get("model_result_decoded"))
        _, via_json = decoded_call(r); st["decode_json"] += via_json
        if coerced_pass(r):
            coerced[i] = True; st["coercible"] += 1; st["coercible_decode"] += via_json
    st["struct"] = st["decode_err"] + st["wrong_name"] + st["wrong_count"] + st["missing"]
    st["semantic"] = st["type_err"] + st["value_err"]
    return len(ids), strict, coerced, st, et

if __name__ == "__main__":
    for stem in ["Qwen3-1.7B", "Qwen3-8B", "Qwen3-14B", "Llama-3.2-3B", "Llama-3.1-8B"]:
        for q in ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M"]:
            base = HERE / "runs" / (q if stem == "Qwen3-1.7B" else f"{stem}/{q}")
            sc = list((base / "score").rglob("*simple_python*score.json")); rs = list((base / "result").rglob("*simple_python*.json"))
            if not sc or not rs: continue
            n, s, c, st, _ = score_run(sc[0], rs[0])
            print(f"{stem:13s} {q:7s} n={n} strict={100*sum(s.values())/n:.2f} coerced={100*sum(c.values())/n:.2f} {st}")
