# -*- coding: utf-8 -*-
"""
measure_moe_silence.py - 量測教育部辭典每個真人錄音檔「前後的靜音長度」

為什麼需要：教育部音檔前後各有 60～670ms 不等的空白。逐詞串接時，這些空白
加起來會讓每個詞之間停頓 0.2～1 秒，聽起來一頓一頓、很不自然。
音檔 CDN 沒有 CORS 標頭，瀏覽器無法自行分析波形，所以先在這裡離線量好，
輸出 js/moe_trim.json：{ "音檔id": [前段可略過 ms, 後段可略過 ms], ... }
前端播放時直接從語音開頭播、在語音結尾就接下一個詞。

用法：
    python tools/measure_moe_silence.py            # 量測全部（約 14,500 檔）
    python tools/measure_moe_silence.py --limit 50 # 先試 50 檔
已量過的 id 會沿用，不會重複下載（可中斷後續跑）。
"""

import argparse
import io
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from pydub import AudioSegment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(ROOT, "moe_audio_index.json")
OUT_PATHS = [os.path.join(ROOT, "js", "moe_trim.json"), os.path.join(ROOT, "web", "js", "moe_trim.json")]
URL = "https://r2-assets.moedict.tw/audio/t/{}.mp3"

FRAME_MS = 5
REL_THRESHOLD = 0.025   # 峰值的 2.5%：夠低，不會切到 s-、h- 等輕聲母
SAFETY_MS = 25          # 偵測到的語音邊界外再保留 25ms


def measure(audio_id: str):
    req = urllib.request.Request(URL.format(audio_id), headers={"User-Agent": "taigi-tts-studio-trim/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    seg = AudioSegment.from_file(io.BytesIO(data), format="mp3")
    a = np.array(seg.get_array_of_samples(), dtype=np.float32) / float(1 << (8 * seg.sample_width - 1))
    if seg.channels > 1:
        a = a.reshape(-1, seg.channels).mean(axis=1)
    fr = max(1, int(seg.frame_rate * FRAME_MS / 1000))
    n = len(a) // fr
    if n == 0:
        return audio_id, [0, 0]
    env = np.abs(a[: n * fr]).reshape(n, fr).max(axis=1)
    th = max(0.003, float(env.max()) * REL_THRESHOLD)
    voiced = np.where(env > th)[0]
    if len(voiced) == 0:
        return audio_id, [0, 0]
    lead = max(0, int(voiced[0]) * FRAME_MS - SAFETY_MS)
    tail = max(0, (n - 1 - int(voiced[-1])) * FRAME_MS - SAFETY_MS)
    return audio_id, [lead, tail]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    with open(INDEX_PATH, encoding="utf-8") as f:
        index = json.load(f)
    ids = sorted({str(v["id"]) for v in index.values() if v.get("id")})

    result = {}
    if os.path.exists(OUT_PATHS[0]):
        with open(OUT_PATHS[0], encoding="utf-8") as f:
            result = json.load(f)
    todo = [i for i in ids if i not in result]
    if args.limit:
        todo = todo[: args.limit]
    print(f"共 {len(ids)} 檔，已量 {len(result)}，本次量測 {len(todo)}", flush=True)

    def save():
        text = json.dumps(dict(sorted(result.items())), separators=(",", ":"))
        for p in OUT_PATHS:
            if os.path.isdir(os.path.dirname(p)):
                with open(p, "w", encoding="utf-8") as f:
                    f.write(text)

    failed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(measure, i) for i in todo]
        for k, fut in enumerate(as_completed(futs), 1):
            try:
                audio_id, trim = fut.result()
                result[audio_id] = trim
            except Exception as e:  # noqa: BLE001 - 單檔失敗不影響其他檔
                failed += 1
                print(f"  失敗: {e}", file=sys.stderr)
            if k % 500 == 0:
                save()
                print(f"  {k}/{len(todo)}", flush=True)
    save()
    print(f"完成：{len(result)} 檔已量測，失敗 {failed}", flush=True)


if __name__ == "__main__":
    main()
