# AGENTS.md — rules for AI tools working in this repo

Read `docs/PROJECT_MEMORY.md` before starting. Append durable facts, decisions and gotchas
there (one or two lines, ending `YYYY-MM-DD · <tool>`), and fix or delete entries that turn out wrong.
Whenever you change that file, also update the **Last updated** line at its top.

## Project
Taigi (Taiwanese Hokkien) TTS studio. Static site at the repo root (GitHub Pages) plus an
optional FastAPI backend (`server.py`) for Meta MMS and Edge-TTS.

## Rules
- `web/` is a copy of the root site (`index.html`, `style.css`, `js/*`) served by `server.py`.
  After editing any root frontend file, copy it to `web/` so both stay identical.
- Do not describe Edge-TTS or the browser voice as Taiwanese. Both are Mandarin (zh-TW) only.
- Do not claim a voice-quality improvement without listening or measuring. The existing
  `verify_voice.py` only checks loudness and speed, not pronunciation.
- Run `python -m unittest test_system` after changing Python code.
- Keep user-facing text in Traditional Chinese.
