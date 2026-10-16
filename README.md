# AWS Certified Generative AI Developer — Professional Portable

A self-hosted Telegram study bot for the **AWS Certified Generative AI Developer – Professional (AIP-C01)** exam. It drills you with practice questions, draws an **AWS GenAI architecture diagram with official AWS icons** when you get one wrong, serves study cards from your own slide deck, tracks your progress, and tells you every Sunday whether you are ready to sit the exam. The same bank and progress are served on the web by [Exam Portal](https://github.com/gcjk768/exam-portal).

"Portable" because the whole thing is one container: give it a Telegram bot token and a Claude Code login and study from your phone.

> Unofficial and independent. Not affiliated with or endorsed by Amazon Web Services. Never use exam dumps: they break the AWS certification agreement.

## The exam (AIP-C01, checked 2026-10-16)

75 questions (65 scored), 180 minutes, USD 300, pass 750/1000. Domains: FM integration, data management and compliance 31%; implementation and integration 26%; AI safety, security and governance 20%; operational efficiency and optimization 12%; testing, validation and troubleshooting 11%. Official guide: <https://docs.aws.amazon.com/aws-certification/latest/ai-professional-01/ai-professional-01.html>.

## What you get

Same bot as the [SAP-C03 one](https://github.com/gcjk768/aws-certified-solutions-architect-professional-portable): one tap to answer, verdict plus explanation, Claude tutor with a `diagrams` + Graphviz picture on a wrong answer, hourly drill, study cards every few hours, Sunday weekly report with predicted score and coach note. Commands: `/quiz` `/study` `/explain` `/report` `/stats` `/refresh` `/reset` `/whoami`.

## Question bank

`build_csv.py` builds `data/questions.csv` from whatever it finds:

| Source | Questions | Where | Licence |
|---|---|---|---|
| [JeremyEngineer/aws-aip-c01-practice-exam](https://github.com/JeremyEngineer/aws-aip-c01-practice-exam) easy / hard / very hard | 434 | `fetch_sources.py` | MIT, per-option explanations; the 20 items tagged BenchPrep are dropped |
| [open-exam-prep.com](https://open-exam-prep.com/practice/aws-genai-developer-pro) | 100 | `fetch_sources.py` | site content, with explanations |
| [certsafari.com](https://certsafari.com/aws/gen-ai-developer-professional/practice-questions) free samples | 35 | `fetch_sources.py` | site content, with explanations |
| [certland.net](https://certland.net/exams/aws-certified-generative-ai-developer-professional-aip-c01/practice-questions/) free samples | 8 | `fetch_sources.py` | site content, with explanations |
| Your own files in `sources/` (Skill Builder practice sets, vendor samples) | private | by hand | personal use, never committed |
| `banks/*.md` | authored banks in the format in `AGENT.md` | repo | MIT |

`python fetch_sources.py` downloads the online sources once (a few seconds apart, robots.txt allowed, no logins), `python -I build_csv.py` parses them, dedupes by stem and writes the CSVs. Nothing third-party is redistributed in this repo.

Study cards: `python build_notes.py <slides.pdf>` turns a course slide deck into `data/study_notes.csv` (private, gitignored).

## Setup

1. `@BotFather` → `/newbot` → token into `bot.env` (`TELEGRAM_BOT_TOKEN`). Send `/whoami` and put your ID in `ALLOWED_USER_IDS`.
2. `python fetch_sources.py && python -I build_csv.py`
3. `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` in `bot.env`, then `docker compose up -d --build`. Or `.\run.ps1` locally.

## Files

`bot.py` the bot · `build_csv.py` the bank builder · `fetch_sources.py` online sources · `build_notes.py` study notes · `test_bot.py` self-check · `Dockerfile`, `compose.yaml`, `run.ps1`, `bot.env.example` · `AGENT.md` rules for bank-growing agents.

## License

MIT for the code.
