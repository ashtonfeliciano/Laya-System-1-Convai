"""Ask a local Laya-System 1 server a set of yes/no or pick-one questions about many short texts.

Usage:
    python ask_laya.py questions/log_check.json examples/log_lines.jsonl
    python ask_laya.py --selftest

Each input line is {"id": ..., "text": ...}. Prints one CSV row per text: id, then answer and odds
for each question. Laya reads about 700 characters at a time, so longer text is cut into pieces.
Pick-one: the most confident answer across pieces wins. Yes/no: the highest yes-odds wins, so one
piece that says yes makes the whole text yes (a key hidden in piece 3 still counts).
"""
import csv
import json
import sys
import urllib.request

URL = "http://127.0.0.1:8090/v1/systemone"  # laya-serve, loopback only
PIECE = 700  # the English model holds 512 tokens with the question; 1,000 characters overflowed


def post(state, questions):
    body = json.dumps({"state": state, "questions": questions}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def strength(answer):
    """(label, odds). A yes/no answer reports the odds of yes; a pick-one reports each option's odds."""
    if answer["type"] == "choice":
        return answer["choice"], answer["probabilities"][answer["choice"]]
    return "yes", answer["noul"]


def decide(replies, questions):
    """Merge one text's pieces, by the rule in the module docstring."""
    row = {}
    for q, spec in questions.items():
        label, odds = max((strength(r["answers"][q]) for r in replies), key=lambda x: x[1])
        if spec["type"] == "noul" and odds < 0.5:
            label, odds = "no", 1 - odds
        row[q] = (label, round(odds, 2))
    return row


def ask(text, questions, send=post):
    pieces = [text[i:i + PIECE] for i in range(0, max(len(text), 1), PIECE)]
    return decide([send(p, questions) for p in pieces], questions)


def selftest():
    q = {"broken": {"type": "noul"}, "kind": {"type": "choice"}}
    fake = iter([
        {"answers": {"broken": {"type": "noul", "noul": 0.2},
                     "kind": {"type": "choice", "choice": "worked", "probabilities": {"worked": 0.6, "failed": 0.4}}}},
        {"answers": {"broken": {"type": "noul", "noul": 0.9},
                     "kind": {"type": "choice", "choice": "failed", "probabilities": {"worked": 0.1, "failed": 0.9}}}},
    ])
    row = ask("x" * (PIECE + 1), q, send=lambda p, qs: next(fake))
    assert row == {"broken": ("yes", 0.9), "kind": ("failed", 0.9)}, row
    yn = {"broken": {"type": "noul"}}
    for yes_odds, want in ((0.3, ("no", 0.7)), (0.45, ("no", 0.55)), (0.55, ("yes", 0.55))):
        assert decide([{"answers": {"broken": {"type": "noul", "noul": yes_odds}}}], yn) == {"broken": want}, yes_odds
    pieces = [{"answers": {"broken": {"type": "noul", "noul": p}}} for p in (0.01, 0.51)]
    assert decide(pieces, yn) == {"broken": ("yes", 0.51)}, "one yes piece must make the text yes"
    print("selftest passed")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        sys.exit()
    questions = json.load(open(sys.argv[1], encoding="utf-8"))["questions"]
    out = csv.writer(sys.stdout)
    out.writerow(["id"] + [f"{q}{s}" for q in questions for s in ("", "_odds")])
    for line in open(sys.argv[2], encoding="utf-8"):
        if line.strip():
            item = json.loads(line)
            row = ask(item["text"], questions)
            out.writerow([item["id"]] + [v for q in questions for v in row[q]])
