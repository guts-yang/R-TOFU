"""Recompute entity-leak metrics from raw eval JSONL after fixing entity extraction.

Original runs used a key_phrase extractor that kept possessive "'s" and "Author "
prefixes, which systematically undercounted leaks. This script rewrites both the
JSONL and the summary JSON, keeping the original values under *_raw fields.
"""
import json

from data_utils import key_phrase
from leak_metrics import rouge_l_recall
from paths import RESULTS


def _stat(rows, key):
    n = len(rows)
    if not n:
        return {}
    return {
        "n": n,
        "leak_rate": round(sum(x["entity_leak"] for x in rows) / n, 6),
        "answer_leak_rate": round(sum(x["answer_entity_leak"] for x in rows) / n, 6),
        "rouge_mean": round(sum(x["rougeL_recall"] for x in rows) / n, 6),
        "truncated_rate": round(sum(x.get("truncated", 0) for x in rows) / n, 6),
        "answer_reached_rate": round(sum(x.get("answer_reached", 0) for x in rows) / n, 6),
    }


def main():
    for p in sorted(RESULTS.glob("eval_*.jsonl")):
        tag = p.stem[len("eval_"):]
        rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not rows:
            continue
        for r in rows:
            r["key_phrase_raw"] = r.get("key_phrase")
            r["entity_leak_raw"] = r.get("entity_leak")
            gold, resp, ans = r["gold_answer"], r.get("response", ""), r.get("answer", "")
            kp = key_phrase(gold)
            r["key_phrase"] = kp
            r["entity_leak"] = int(bool(kp) and kp.lower() in resp.lower())
            r["answer_entity_leak"] = int(bool(kp) and kp.lower() in ans.lower())
            r["rougeL_recall"] = rouge_l_recall(gold, resp)
            r["answer_rougeL_recall"] = rouge_l_recall(gold, ans)
            r["leak_any"] = int(r["entity_leak"] == 1 or r["rougeL_recall"] >= 0.60)
        with open(p, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        groups = {}
        for r in rows:
            gkey = r["strategy"].replace(":retain", "")
            groups.setdefault(gkey, {"forget": [], "retain": []})
            side = "retain" if int(r.get("is_retain", 0)) == 1 else "forget"
            groups[gkey][side].append(r)
        new_groups = {k: {"forget": _stat(v["forget"], k),
                          "retain": _stat(v["retain"], k)} for k, v in groups.items()}
        rates = [g["forget"]["leak_rate"] for g in new_groups.values() if g["forget"].get("n")]
        sp = RESULTS / f"eval_{tag}.summary.json"
        if sp.exists():
            s = json.loads(sp.read_text(encoding="utf-8"))
            s["groups"] = new_groups
            s["gamma"] = round(max(rates) - min(rates), 6) if rates else None
            s["max_leak"] = round(max(rates), 6) if rates else None
            s["recomputed"] = True
            s["recompute_note"] = "entity extractor fixed: stripped 'Author ' prefix and possessive 's; see recompute_leak.py"
            sp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[recompute] {tag}: gamma={s.get('gamma') if sp.exists() else None} "
              f"max_leak={s.get('max_leak') if sp.exists() else None}", flush=True)


if __name__ == "__main__":
    main()
