# -*- coding: utf-8 -*-
"""
server.py - 台語多模型語音合成 Studio 後端伺服器 (Taigi TTS FastAPI Server)
提供：
1. Edge-TTS 長文非同步串流與拼接
2. Meta MMS-TTS (facebook/mms-tts-nan) VITS 推論與變調 Pipeline
3. 台語 G2P、斷詞與連讀變調解析服務
4. 靜態網頁託管 (Web Studio UI)
"""

import os
import io
import re
import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from taigi_sandhi import TaigiTextPipeline, split_article_into_sentences, parse_syllable, apply_sandhi_to_word
from edge_engine import EdgeTtsEngine, SUPPORTED_VOICES

# 載入教育部台語真人錄音索引 (14,489 筆官方原聲)
MOE_INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moe_audio_index.json")
moe_audio_index = {}
moe_rom_index = {}
if os.path.exists(MOE_INDEX_PATH):
    try:
        with open(MOE_INDEX_PATH, "r", encoding="utf-8") as f:
            moe_audio_index = json.load(f)
        for title, info in moe_audio_index.items():
            trs = info.get("trs", "")
            if trs:
                parts = [parse_syllable(p) for p in re.split(r'-+', trs.strip()) if p]
                if parts and all(s is not None for s in parts):
                    key = "-".join([f"{s.skeleton}{s.tone}" for s in parts])
                    if key not in moe_rom_index:
                        moe_rom_index[key] = {
                            "hanzi": title,
                            "id": info["id"],
                            "trs": trs
                        }
    except Exception as e:
        print(f"載入教育部音檔索引失敗: {e}")


def resolve_moe_audio(word: str, rom_key: Optional[str] = None) -> Optional[str]:
    """取得教育部官方真人錄音音檔 CDN 網址 (支援漢字與羅馬字 key 反查)"""
    if word in moe_audio_index:
        return f"https://r2-assets.moedict.tw/audio/t/{moe_audio_index[word]['id']}.mp3"
    if rom_key and rom_key in moe_rom_index:
        return f"https://r2-assets.moedict.tw/audio/t/{moe_rom_index[rom_key]['id']}.mp3"
    return None

app = FastAPI(
    title="Taigi TTS Studio API",
    description="臺灣台語長文多模型語音合成與連讀變調發音調校系統",
    version="2.0.0"
)

# 啟用 CORS 跨域請求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

g2p_pipeline = TaigiTextPipeline(dialect="south")
edge_engine = EdgeTtsEngine()
mms_engine_instance = None  # Lazy loaded


def get_mms_engine():
    global mms_engine_instance
    if mms_engine_instance is None:
        from mms_engine import MmsTtsEngine
        mms_engine_instance = MmsTtsEngine()
    return mms_engine_instance


def _mms_sandhi_kwargs(req) -> Dict[str, Any]:
    return {} if req.apply_sandhi is None else {"apply_sandhi": bool(req.apply_sandhi)}


class TTSRequest(BaseModel):
    text: str
    model: str = "edge"  # "edge" | "mms"
    voice: Optional[str] = "HsiaoChen"
    rate: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"
    volume: Optional[str] = "+0%"
    # None = 用 MMS 引擎預設（送本調，讓模型自己變調）；True = 先套規則變調再送
    apply_sandhi: Optional[bool] = None
    pause_ms: Optional[int] = 300


class ParseRequest(BaseModel):
    text: str
    dialect: Optional[str] = "south"


@app.get("/api/models")
async def list_available_models():
    """回傳所有支援的語音合成模型與音色配置"""
    return {
        "models": [
            {
                "id": "edge",
                "name": "Microsoft Edge-TTS 臺灣華語語音",
                "type": "neural",
                "description": "微軟沒有台語語音：這是臺灣華語 (zh-TW)，台語漢字會以華語讀音唸出",
                "voices": [
                    {"id": k, "name": v["name"], "gender": v["gender"]}
                    for k, v in SUPPORTED_VOICES.items()
                ],
                "default_voice": "HsiaoChen"
            },
            {
                "id": "mms",
                "name": "Meta MMS-TTS (facebook/mms-tts-nan)",
                "type": "vits_neural",
                "description": "開源 VITS 端到端台語模型 (~36M 參數)；送入本調白話字，由模型自行處理連讀變調",
                "voices": [
                    {"id": "default", "name": "Meta MMS 台語單發音人 (VITS)", "gender": "Male"}
                ],
                "default_voice": "default"
            },
            {
                "id": "moe_concat",
                "name": "教育部辭典真人錄音拼接 (MOE Concatenative)",
                "type": "concatenative",
                "description": "前端載入教育部臺灣台語常用詞辭典真人錄音檔，支援同音借調與逐字拼接",
                "voices": [
                    {"id": "moe_official", "name": "教育部官方辭典原聲", "gender": "Official"}
                ],
                "default_voice": "moe_official"
            },
            {
                "id": "web_speech",
                "name": "瀏覽器 Web Speech API (本機語音)",
                "type": "browser_local",
                "description": "零網路延遲，使用用戶作業系統/瀏覽器內建語音引擎",
                "voices": [
                    {"id": "browser_default", "name": "系統預設語音", "gender": "Native"}
                ],
                "default_voice": "browser_default"
            }
        ]
    }


@app.post("/api/g2p/parse")
async def parse_text(req: ParseRequest):
    """
    台語文字剖析 API：
    輸入漢字或漢羅，輸出句子分割、詞塊 Tokens、台羅本調、變調與 POJ。
    """
    if not req.text.strip():
        return {"sentences": [], "total_chars": 0}

    chunks = split_article_into_sentences(req.text)
    results = []

    for item in chunks:
        raw_s = item["text"]
        tailo_base = g2p_pipeline.g2p_raw(raw_s, system="Tailo")
        tailo_sandhi = g2p_pipeline.convert_to_sandhi_tailo(raw_s)
        poj_sandhi = g2p_pipeline.convert_to_sandhi_poj(raw_s)
        tokens = g2p_pipeline.parse_sentence_to_tokens(raw_s)
        # 為每個 token 注入教育部真人原聲音檔網址 (支援漢字與全羅反查)
        for t in tokens:
            if t.get("type") == "word":
                w = t.get("hanzi", "")
                tailo = t.get("tailo_base", "")
                rom_key = None
                if tailo:
                    sylls = [parse_syllable(p) for p in re.split(r'-+', tailo) if p]
                    if sylls and all(s is not None for s in sylls):
                        rom_key = "-".join([f"{s.skeleton}{s.tone}" for s in sylls])

                audio_url = resolve_moe_audio(w, rom_key)
                if t.get("is_roman") and rom_key and rom_key in moe_rom_index:
                    t["matched_hanzi"] = moe_rom_index[rom_key]["hanzi"]

                t["audio_url"] = audio_url

                # 若無整詞錄音，提供逐音節備援音檔
                if not audio_url:
                    parts = []
                    if t.get("is_roman") and tailo:
                        sub_sylls = [parse_syllable(p) for p in re.split(r'-+', tailo) if p]
                        for s in sub_sylls:
                            if s:
                                k = f"{s.skeleton}{s.tone}"
                                u = resolve_moe_audio("", k)
                                if u:
                                    parts.append(u)
                    elif len(w) > 1:
                        parts = [resolve_moe_audio(ch) for ch in w if resolve_moe_audio(ch)]
                    if parts:
                        t["fallback_audios"] = parts

        results.append({
            "index": item["index"],
            "text": raw_s,
            "char_count": item["char_count"],
            "tailo_base": tailo_base,
            "tailo_sandhi": tailo_sandhi,
            "poj_sandhi": poj_sandhi,
            "tokens": tokens
        })

    return {
        "total_chars": len(req.text),
        "sentence_count": len(chunks),
        "sentences": results
    }


@app.post("/api/tts/synthesize")
async def synthesize_text(req: TTSRequest):
    """
    多模型長文語音合成 API：
    回傳合成詳細結果與分句時間戳記 (含 base64 音訊或直接下載)
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="請提供欲合成的文字內容")

    if req.model == "edge":
        voice_info = SUPPORTED_VOICES.get(req.voice, SUPPORTED_VOICES["HsiaoChen"])
        result = await edge_engine.synthesize_article(
            article_text=text,
            voice=voice_info["id"],
            rate=req.rate or "+0%",
            pitch=req.pitch or "+0Hz",
            volume=req.volume or "+0%",
            pause_ms=req.pause_ms or 300
        )
        return Response(
            content=result["audio_bytes"],
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=synthesized_edge.mp3"}
        )

    elif req.model == "mms":
        engine = get_mms_engine()
        result = engine.synthesize_article(
            article_text=text,
            **_mms_sandhi_kwargs(req),
            pause_ms=req.pause_ms or 300
        )
        return Response(
            content=result["audio_bytes"],
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=synthesized_mms.wav"}
        )

    else:
        raise HTTPException(status_code=400, detail=f"不支援的模型標識: {req.model}")


@app.post("/api/tts/synthesize_json")
async def synthesize_text_json(req: TTSRequest):
    """回傳 JSON 格式（包含分句計時資訊與音訊 Base64，供前端 Karaoke 進度跟隨）"""
    import base64
    import traceback
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="請提供欲合成的文字內容")

    try:
        if req.model == "edge":
            voice_info = SUPPORTED_VOICES.get(req.voice, SUPPORTED_VOICES["HsiaoChen"])
            result = await edge_engine.synthesize_article(
                article_text=text,
                voice=voice_info["id"],
                rate=req.rate or "+0%",
                pitch=req.pitch or "+0Hz",
                volume=req.volume or "+0%",
                pause_ms=req.pause_ms or 300
            )
            audio_b64 = base64.b64encode(result["audio_bytes"]).decode("utf-8")
            return {
                "model": "edge",
                "voice": voice_info["name"],
                "total_duration_ms": result["total_duration_ms"],
                "sentence_count": result["sentence_count"],
                "sentence_timings": result["sentence_timings"],
                "audio_data_url": f"data:audio/mp3;base64,{audio_b64}"
            }

        elif req.model == "mms":
            engine = get_mms_engine()
            result = engine.synthesize_article(
                article_text=text,
                **_mms_sandhi_kwargs(req),
                pause_ms=req.pause_ms or 300
            )
            audio_b64 = base64.b64encode(result["audio_bytes"]).decode("utf-8")
            return {
                "model": "mms",
                "voice": "facebook/mms-tts-nan",
                "total_duration_ms": result["total_duration_ms"],
                "sentence_count": result["sentence_count"],
                "sentence_timings": result["sentence_timings"],
                "audio_data_url": f"data:audio/wav;base64,{audio_b64}"
            }
        else:
            raise HTTPException(status_code=400, detail="未知的模型選擇")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"語音合成發生錯誤: {str(e)}")


# 掛載 Web 靜態目錄 (若存在)
web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
if os.path.exists(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print("啟動 Taigi TTS Studio 伺服器: http://localhost:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
