# Laya-System 1 by Convai: notes from running a small local yes/no model

I run [Laya-System 1](https://huggingface.co/convaiinnovations/laya), an open decision model from Convai Innovations, on my home server. It answers yes/no and pick-one questions about short text. I use it as a first pass: it handles the easy calls for free, and only the unsure ones go to a paid model.

This repo holds what I measured, what went wrong, and a small script to try it. All examples here are made up. The numbers come from my own tests.

## What it can and can't do

- It picks from the options I give it and reports its odds for each one.
- It can't write text, count, or compare dates. I do those in code.
- The English model holds 512 tokens, question included. That is about 700 characters of text. 1,000 characters measured 510 tokens, so the end was being cut off.
- Longer text is cut into 700-character pieces. For a pick-one question, the most confident answer across the pieces wins. For a yes/no question, the highest yes-odds wins, so one piece that says yes makes the whole text yes.
- It runs on CPU, costs $0 per call, and the server listens on the server itself only (loopback).

## Speed (measured on my home server, CPU)

| Call | Time |
|---|---|
| 1 question, short text | 0.15 to 0.6 s |
| 3 to 6 questions, one text | 0.9 to 1.6 s |
| 400 characters x 5 questions | 4.0 s |
| 1,000 characters x 5 questions | 8.9 s |
| 6 log lines x 1 question, one batch | 1.6 s |

It reads the text once per question, so time grows with pieces x questions. Every question has to earn its place.

## Try it

You need the `laya` package from PyPI running `laya-serve` on port 8090.

```bash
python ask_laya.py --selftest
python ask_laya.py questions/log_check.json examples/log_lines.jsonl
```

Real output from 2026-11-12, six made-up log lines, 2.7 seconds:

| id | Log line | Answer | Odds |
|---|---|---|---|
| 1 | backup job finished: 412 files copied, 0 skipped | worked | 0.68 |
| 2 | ERROR fetch_forecast: request timed out after 30s (weather-feed) | failed | 0.55 |
| 3 | nightly report sent to inbox at 06:02 | other | 0.39 |
| 4 | disk check: 61% used on /srv | other | 0.55 |
| 5 | price-sync refused: API key expired | failed | 0.81 |
| 6 | starting worker 3 of 4 | worked | 0.39 |

Line 3 should be "worked", but its odds are low. That is why I only act alone on answers above a tested cutoff, and send the rest on.

## What I tested

Each test is a set of items with known answers, scored by a script.

| Question | Result |
|---|---|
| Did this log line fail? (pick-one: failed, worked, other) | 29 of 37 right. All 9 answers at 0.70 or higher were right. |
| The same, asked as plain yes/no | 22 of 37. It called almost every line a failure. |
| Sort a to-do item: small fix, big job, or needs the owner | 26 of 37. All 8 answers at 0.60 or higher were right. |
| Sort an incoming job before a paid model runs | 26 of 30 |
| Is a password or key written out in full? | 8 of 8 at 0.80 |
| Should this step stop and wait for a person? | 92 of 119 (77%) |
| Which element on a web page does this task? | 25 of 44, so it is a hint only and a bigger model picks |

## Lessons

- Pick-one beat yes/no. Give it the likely answers as options.
- Longer option descriptions made sorting worse in a small test: 2 of 6 right with rich wording, 3 of 6 with plain.
- A "none of these" option pulled wrong answers. In the page test, 27 of 32 wrong answers picked it.
- Raw JSON log lines looked like failures to it, even normal ones (odds 0.7 to 0.94). JSON lines now go to code.
- My own scripts run on another computer, so they send a whole batch in one SSH call. Opening the connection costs more than the answer. The small script here sends one request per piece, which is fine when it runs on the server itself.
- A cutoff is set per question, from a test. One number does not fit them all.

## Upgrades: test side by side first

New versions run on a second port while the old one keeps serving. Both answer the same 234 test items.

- 0.3.21 against 0.4.11: 144 and 142 right. Not switched.
- 0.3.21 against 0.4.17: 144 and 142 right again. I checked the 6 items whose answers changed, then switched on 2026-10-30.

## Fine-tuning on Kaggle

- Five training runs so far in a free Kaggle notebook. A sixth is planned.
- For run 5, a larger model wrote 858 fix-up cards and a second model checked them blind. I ruled every case where they disagreed.
- My goal is 95% right on every real question set.
- Run 4 scored 97.3% on its own test cards (1,962 of 2,017). On my real question sets it stayed below the goal: 21 of 31, 27 of 37, and 26 of 55.
- Run 5 against the live model, 420 items: 327 right against 257. But its odds sit between 0.8 and 0.9 almost everywhere, so the cutoffs I trust stopped separating right from wrong. Not switched yet. It needs new cutoffs, found on a fresh set.

## How I use it

- A daily cleanup job uses it to flag failed log lines and sort to-do items.
- My agents ask it first on yes/no and pick-one steps. It acts alone only where a test proved it. Everywhere else its answer is a hint, and a bigger model decides.

## Files

| File | What it is |
|---|---|
| `ask_laya.py` | Sends texts and a question set to a local Laya server and prints a CSV |
| `questions/log_check.json` | The pick-one log question from the first test above |
| `examples/log_lines.jsonl` | Six made-up log lines |

## Credits

Laya-System 1 is made by Convai Innovations: [model on Hugging Face](https://huggingface.co/convaiinnovations/laya), [`laya` on PyPI](https://pypi.org/project/laya/). This repo only holds my own notes and a small client.
