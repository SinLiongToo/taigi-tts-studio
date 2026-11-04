# Project memory (shared by Claude Code, Antigravity and humans)

**Last updated:** 2026-11-05 · Claude Code

## Verified facts
- `facebook/mms-tts-nan` vocab has only 48 chars: POJ letters, some precomposed toned letters, combining U+030D/U+0304/U+0302/U+0358, `-`, `'`, space. No punctuation, no `ⁿ`, no combining grave/acute. Anything else is silently dropped by the tokenizer. Source: model `vocab.json`. 2026-11-04 · Claude Code
- 教育部 audio clips (`r2-assets.moedict.tw/audio/t/<id>.mp3`) have 60–670 ms silence before/after speech (avg ~320 ms per clip total). 2026-11-04 · Claude Code
- That CDN sends no CORS headers, so the browser cannot decode clips with Web Audio; only `<audio>` playback works. 2026-11-04 · Claude Code
- 39 of 14,489 ids in `moe_audio_index.json` return 404 on the CDN. 2026-11-04 · Claude Code
- Microsoft Edge-TTS has no Taiwanese (nan-TW) voice; HsiaoChen/YunJhe/HsiaoYu are Mandarin and read Taigi Hanzi as Mandarin. 2026-11-04 · Claude Code

## Decisions
- MMS gets citation-tone (本調) POJ by default (`apply_sandhi=False`): POJ training text is written in citation tones, so pre-applying sandhi likely double-applies it. Not proven by measurement; the ASR test was inconclusive. The frontend no longer sends `apply_sandhi`; the 變調 toggle only changes on-screen romanization. 2026-11-04 · Claude Code
- MMS synthesizes clause by clause (split on punctuation) with 160 ms / 320 ms pauses, because the model can't see punctuation. 2026-11-04 · Claude Code
- MOE playback skips each clip's silence using offline measurements in `js/moe_trim.json` (`{id: [lead_ms, tail_ms]}`, 25 ms safety margin), regenerated with `tools/measure_moe_silence.py` (resumable). It also preloads the next 3 clips. 2026-11-04 · Claude Code

## Gotchas
- This PC has 7.7 GB RAM; loading Whisper-size ASR alongside MMS pages heavily and runs very slowly. Use the int8 CTranslate2 build with 4 threads. 2026-11-04 · Claude Code
- `NUTN-KWS/Whisper-Taiwanese-model-v0.5` outputs Mandarin-style text and often hallucinates or returns empty on short TTS clips. It's not a reliable judge of MMS tone quality. 2026-11-04 · Claude Code
- Writing Python with `\1` or LaTeX backslashes through a bash heredoc can corrupt them (`\1` became byte 0x01). Write the script to a file instead. 2026-11-04 · Claude Code

## Open items
- Decide by ear whether MMS sounds better with citation or pre-sandhi input. Samples were made 2026-11-04 in the Claude Code scratchpad (`ab2_out/*_A_old_sandhi_*`, `*_C_new_citation_*`, `*_D_new_sandhi_*`). 2026-11-04 · Claude Code
- Consider removing the duplicate `web/` folder (e.g. let `server.py` serve the repo root) so the two copies can't drift. 2026-11-04 · Claude Code
- The MOE voice still uses standalone dictionary tones per word, so phrases lack natural sandhi. 2026-11-04 · Claude Code
