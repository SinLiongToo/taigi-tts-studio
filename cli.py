# -*- coding: utf-8 -*-
"""
cli.py - 臺灣台語多模型長文語音合成命令列工具 (Taigi TTS CLI)
支援長篇 (500+ 字) 文章自動分句朗讀、多種模型切換（Edge-TTS、Meta MMS-TTS）、連讀變調切換。

使用範例：
  # 1. 朗讀簡短句子
  python cli.py --text "逐家好！歡迎使用台語語音合成系統。" --output hello.mp3

  # 2. 朗讀 500 字長文（使用 Edge-TTS 自然女聲 曉臻）
  python cli.py --input samples/sample_article_500words.txt --model edge --voice HsiaoChen --output article_edge.mp3

  # 3. 使用 Meta MMS-TTS (結合台語連讀變調 POJ Pipeline)
  python cli.py --input samples/sample_article_500words.txt --model mms --sandhi --output article_mms.wav

  # 4. 列出可用模型與聲音
  python cli.py --list-models
"""

import argparse
import asyncio
import sys
import os
from taigi_sandhi import TaigiTextPipeline, split_article_into_sentences
from edge_engine import EdgeTtsEngine, SUPPORTED_VOICES


def list_models():
    print("=" * 60)
    print(" 🎙️ 台語語音合成系統 (Taigi TTS Hub) - 可用模型與聲音清單")
    print("=" * 60)
    print("\n【模型 1: Microsoft Edge-TTS 類神經語音】")
    for key, info in SUPPORTED_VOICES.items():
        print(f"  • --voice {key:10s} : {info['name']} [{info['id']}]")

    print("\n【模型 2: Meta MMS-TTS (facebook/mms-tts-nan)】")
    print("  • 架構: VITS (Variational Inference End-to-End TTS, ~36M 參數)")
    print("  • 前處理引擎: 內建 taigi_sandhi 自動連讀變調 G2P (POJ)")
    print("  • 特色: 開源離線推論，已解決原模型缺乏變調推論之生硬問題")

    print("\n【模型 3: 教育部臺灣台語常用詞辭典真人錄音 (Web 端專屬)】")
    print("  • 採用教育部台語辭典官方數萬筆真實發音，支援同音借調與逐字拼接")
    print("=" * 60)


async def run_edge(text: str, voice_key: str, output: str, rate: str, pitch: str):
    voice_info = SUPPORTED_VOICES.get(voice_key, SUPPORTED_VOICES["HsiaoChen"])
    voice_id = voice_info["id"]
    print(f"[Edge-TTS] 正在使用聲音: {voice_info['name']}")
    print(f"[Edge-TTS] 輸入文字長度: {len(text)} 字")

    engine = EdgeTtsEngine(default_voice=voice_id)
    res = await engine.synthesize_article(
        article_text=text,
        voice=voice_id,
        rate=rate,
        pitch=pitch,
        output_file=output
    )
    print(f"✅ 合成成功！")
    print(f"   總時長: {res['total_duration_ms'] / 1000.0:.2f} 秒")
    print(f"   分句數: {res['sentence_count']} 句")
    print(f"   輸出檔案: {os.path.abspath(output)}")


def run_mms(text: str, sandhi: bool, output: str):
    print(f"[Meta MMS-TTS] 正在初始化 facebook/mms-tts-nan 模型...")
    print(f"[Meta MMS-TTS] 連讀變調 Pipeline: {'啟用 (已修正外國人機械腔)' if sandhi else '停用 (使用本調)'}")
    print(f"[Meta MMS-TTS] 輸入文字長度: {len(text)} 字")

    from mms_engine import MmsTtsEngine
    engine = MmsTtsEngine()
    res = engine.synthesize_article(
        article_text=text,
        apply_sandhi=sandhi,
        output_file=output
    )
    print(f"✅ 合成成功！")
    print(f"   採樣率: {res['sample_rate']} Hz")
    print(f"   總時長: {res['total_duration_ms'] / 1000.0:.2f} 秒")
    print(f"   分句數: {res['sentence_count']} 句")
    print(f"   輸出檔案: {os.path.abspath(output)}")


def main():
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Taigi TTS - 臺灣台語長文語音合成系統")
    parser.add_argument("--text", type=str, help="欲合成的文字內容（漢字/漢羅/台羅皆可）")
    parser.add_argument("--input", "-i", type=str, help="欲合成的長篇文章檔案路徑 (.txt)")
    parser.add_argument("--model", "-m", type=str, choices=["edge", "mms"], default="edge", help="TTS 語音模型 (預設 edge)")
    parser.add_argument("--voice", "-v", type=str, default="HsiaoChen", choices=list(SUPPORTED_VOICES.keys()), help="Edge-TTS 聲音選擇")
    parser.add_argument("--sandhi", action="store_true", default=True, help="是否套用連讀變調規則（MMS 模型強烈建議開啟）")
    parser.add_argument("--no-sandhi", action="store_false", dest="sandhi", help="關閉連讀變調")
    parser.add_argument("--rate", type=str, default="+0%", help="語速調整（如 +10%%, -15%%）")
    parser.add_argument("--pitch", type=str, default="+0Hz", help="音調調整（如 +50Hz, -20Hz）")
    parser.add_argument("--output", "-o", type=str, default="output.mp3", help="輸出音訊檔案路徑")
    parser.add_argument("--list-models", action="store_true", help="列出所有支援模型與聲音選項")

    args = parser.parse_args()

    if args.list_models:
        list_models()
        return

    text = ""
    if args.input:
        if not os.path.exists(args.input):
            print(f"錯誤: 找不到輸入檔案 {args.input}")
            sys.exit(1)
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read().strip()
    elif args.text:
        text = args.text.strip()
    else:
        print("提示: 請提供 --text 或 --input 參數，或使用 --help 查看說明。")
        return

    if not text:
        print("錯誤: 輸入文字為空")
        sys.exit(1)

    if args.model == "edge":
        asyncio.run(run_edge(text, args.voice, args.output, args.rate, args.pitch))
    elif args.model == "mms":
        # MMS 輸出建議使用 .wav 或 .mp3
        run_mms(text, args.sandhi, args.output)


if __name__ == '__main__':
    main()
