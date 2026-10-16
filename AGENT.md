# Instructions for the scheduled question-bank agents

This repo holds a practice question bank for the AWS Certified Generative AI Developer - Professional exam (AIP-C01) and a Telegram quiz bot that serves it. Scheduled cloud agents extend the bank. Read this whole file before changing anything.

## Hard rules
1. **No exam dumps.** Never use ExamTopics, "dumps", "braindump", "real exam questions", hydranode, awsready, Keren66/aws-aip-c01-chinese, pass4success, certempire, or any site or repo whose questions are "most-voted answers from the internet". Using them breaks the AWS certification agreement. When unsure, skip the source.
2. **Respect robots.txt** of every site you read. Fetch pages with `curl -s https://r.jina.ai/<URL>` or plain curl. No proxies, no captcha bypass, no logins.
3. **Attribute every question** to its source (site or repo, with URL) in the bank file header. Prefer sources with explanations. Banks already shipped are in `banks/`; sources the owner uses privately are listed in `AGENT.md` below; do not re-add them.
4. **Never commit secrets.** `bot.env` and `data/state.json` are gitignored and must stay that way.
5. **Deduplicate** against the existing bank: before adding a question, check that its first 80 characters do not already appear in `AIP-C01_practice_questions_2026.csv` (case-insensitive).
6. Only touch `banks/`, `README.md` and `CHANGELOG.md` (the CSVs are gitignored build outputs; `sources/` is not committed). Do not edit `bot.py`, `build_csv.py` or `test_bot.py`.

## How to add questions
Create one file per source per run: `banks/YYYY-MM-DD-<source-slug>.md`, in exactly this layout (the builder parses it):

```
# <title>

source: <Source name as it should appear in the CSV>
url: <https://...>
version: AIP-C01

## <Topic or domain heading>

1. <Question text on one line> (Select TWO)   <- only if more than one answer
   A. <option>
   B. <option>
   C. <option>
   D. <option>
   E. <option>              <- optional, up to E

2. ...

## Answers

| # | Answer | Why |
| --- | --- | --- |
| 1 | B | <explanation, one line, no pipes> |
| 2 | A,C | <explanation> |
```

Numbering must be continuous within the file. Multi-answer uses `A,C` with no spaces. Every question needs an explanation.

## Build and verify
```
python3 -I build_csv.py
```
It rewrites `AIP-C01_practice_questions_2026.csv` and `data/questions.csv` (both gitignored), prints a per-source count, and exits non-zero on any malformed row. The count for your new bank must equal the number of questions you added. Do not run `test_bot.py` in the cloud (it needs Telegram and Graphviz packages).

## Record and commit
- Append one line to `CHANGELOG.md`: `- YYYY-MM-DD â€” <what was added or "weekly check: nothing new">`. Always add this line, even when nothing was found, so the Telegram notification fires.
- Update the bank list in `README.md` (section "What ships in this repo") when you add a source.
- Commit to `main` with a Conventional Commit message, for example `feat(bank): add 12 AIP-C01 questions from <source>` or `chore(bank): weekly check, nothing new`, and push. A GitHub Actions workflow posts the commit summary to the owner's Telegram topic (secrets TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOPIC_ID).

## Judging a candidate source
Good: an author's own practice questions with explanations (blogs, course sample pages, MIT/CC-licensed GitHub banks, AWS official sample questions and exam guides). Bad: anything that reproduces questions people saw in the real exam. When a page mixes both, skip it.

## Sources already used (do not re-add)
JeremyEngineer/aws-aip-c01-practice-exam (MIT) · open-exam-prep.com · certsafari.com free samples · certland.net free samples · AWS Skill Builder practice sets and trivia (private) · a vendor sample .docx (private). Rejected as dumps or copied official content: Keren66/aws-aip-c01-chinese, pass4success, certempire, certshield, the BenchPrep-tagged items and atypicalsam1228/aip-c01-quiz. Not yet licensed for reuse: ghaliba3/GenAI (ask the author first).

