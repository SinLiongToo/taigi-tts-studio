# -*- coding: utf-8 -*-
"""
mms_engine.py - Meta MMS (Massively Multilingual Speech) 台語 VITS 模型推論引擎
模型標識: facebook/mms-tts-nan (約 36M 參數，基於 VITS 架構)
特點與痛點克服：
- 原生模型輸入僅支援白話字（POJ），且無法自行處理台語語境中的「連讀變調（Tone Sandhi）」。
- 本模組自動在前處理層結合 taigi_sandhi.py：
  1. 漢字/漢羅 -> 台羅/POJ 音節剖析 (G2P)
  2. 套用五調循環 + 入聲對調 + 喉塞音舒聲化變調規則
  3. 預設送「本調」POJ（模型訓練文本即為本調書寫，變調由模型自行處理）；
     可選擇先套用規則變調（apply_sandhi=True）做比較實驗。
- 支援長篇文章（500+ 字）自動分句推論與波形平滑拼接。
"""

import io
import os
import re
import unicodedata
import numpy as np
import torch
from typing import List, Dict, Any, Optional
from taigi_sandhi import TaigiTextPipeline, split_article_into_sentences
from pydub import AudioSegment

MMS_MODEL_ID = "facebook/mms-tts-nan"

# 子句切分：MMS 詞表沒有標點，必須在送進模型前切開，自己補停頓
CLAUSE_SPLIT_RE = re.compile(r"([，,、；;：:。！？!?…「」『』“”()（）]+|\.(?=\s|$))")
CLAUSE_PAUSE_MS = 160        # 逗號等句中停頓
SENTENCE_END_PAUSE_MS = 320  # 句號、問號等句末停頓


def _fade_edges(wav: np.ndarray, sr: int, ms: float = 8.0) -> np.ndarray:
    """子句頭尾各做幾毫秒淡入淡出，避免拼接處出現「啪」一聲"""
    n = min(len(wav) // 2, int(sr * ms / 1000))
    if n <= 0:
        return wav
    wav = wav.copy()
    ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
    wav[:n] *= ramp
    wav[-n:] *= ramp[::-1]
    return wav


class MmsTtsEngine:
    def __init__(self, model_id: str = MMS_MODEL_ID, device: Optional[str] = None):
        self.model_id = model_id
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.model = None
        self.tokenizer = None
        self.g2p = TaigiTextPipeline(dialect="south")
        self.sample_rate = 16000
        self.seed = 0

    def _ensure_loaded(self):
        """延遲載入（Lazy Load），避免伺服器啟動時阻塞，並配置多核心極速推論"""
        if self.model is None or self.tokenizer is None:
            # 啟用 CPU 多執行緒加速
            num_cores = os.cpu_count() or 4
            torch.set_num_threads(num_cores)
            print(f"[MMS-TTS] 正在載入 Meta MMS 模型 ({self.model_id}) 至 {self.device} (CPU 執行緒: {num_cores})...")
            from transformers import VitsModel, AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self.model = VitsModel.from_pretrained(self.model_id).to(self.device)
            self.model.eval()
            self.sample_rate = self.model.config.sampling_rate
            print(f"[MMS-TTS] 模型載入完畢，採樣率: {self.sample_rate}Hz")

    def _vocab_chars(self) -> set:
        if getattr(self, "_vocab_cache", None) is None:
            self._ensure_loaded()
            self._vocab_cache = set(self.tokenizer.get_vocab().keys())
        return self._vocab_cache

    def clean_poj_for_mms(self, poj_text: str) -> str:
        """
        把 POJ 整理成 MMS 模型「認得」的字元。
        MMS 台語詞表只有 48 個字元：POJ 字母、部分帶調號字母、o͘ 的點、- 和 '。
        沒有標點、也沒有鼻化符號 ⁿ —— 不在詞表的字元會被 tokenizer 默默刪掉。
        這裡先把不認得的帶調號字母拆開 (NFD)，只丟掉不認得的那個符號、保留字母本身。
        """
        vocab = self._vocab_chars()
        text = unicodedata.normalize("NFC", poj_text.lower())
        out = []
        for ch in text:
            if ch in vocab:
                out.append(ch)
            elif ch.isspace():
                out.append(" ")
            else:
                out.extend(c for c in unicodedata.normalize("NFD", ch) if c in vocab)
        text = "".join(out)
        text = re.sub(r"-{3,}", "--", text)
        return re.sub(r"\s+", " ", text).strip(" -")

    def _infer(self, cleaned_poj: str) -> np.ndarray:
        inputs = self.tokenizer(cleaned_poj, return_tensors="pt").to(self.device)
        # VITS 每次推論帶隨機雜訊；固定種子讓同一句每次聽起來都一樣 (也方便快取與比較)
        torch.manual_seed(self.seed)
        with torch.inference_mode():
            output = self.model(**inputs)
        return output.waveform[0].cpu().float().numpy()

    def text_to_poj(self, sentence_text: str, apply_sandhi: bool = False) -> str:
        if apply_sandhi:
            return self.g2p.convert_to_sandhi_poj(sentence_text)
        return self.g2p.convert_to_poj_raw(sentence_text)

    def synthesize_sentence(self, sentence_text: str, apply_sandhi: bool = False) -> np.ndarray:
        """
        合成單一句子。
        - 預設送「本調」POJ：MMS 的訓練文本 (白話字聖經) 本來就是寫本調，
          模型自己學會了念出變調。若先幫它變調，等於變調兩次，聲調會跑掉。
        - 依標點切成子句分別合成，中間補上停頓。MMS 詞表沒有標點，
          整句一起送的話，逗號、句號都會被刪掉，變成一口氣念到底。
        """
        self._ensure_loaded()
        poj_text = self.text_to_poj(sentence_text, apply_sandhi)

        pieces = []
        parts = CLAUSE_SPLIT_RE.split(poj_text)
        for i in range(0, len(parts), 2):
            clause = self.clean_poj_for_mms(parts[i])
            punct = parts[i + 1] if i + 1 < len(parts) else ""
            if not clause:
                continue
            wav = self._infer(clause)
            pieces.append(_fade_edges(wav, self.sample_rate))
            pause = SENTENCE_END_PAUSE_MS if re.search(r"[。！？!?.…]", punct) else CLAUSE_PAUSE_MS
            pieces.append(np.zeros(int(self.sample_rate * pause / 1000), dtype=np.float32))

        if not pieces:
            return np.zeros(int(self.sample_rate * 0.2), dtype=np.float32)
        pieces.pop()  # 句尾停頓交給呼叫端 (pause_ms) 決定
        return np.concatenate(pieces)

    def synthesize_article(
        self,
        article_text: str,
        apply_sandhi: bool = False,
        pause_ms: int = 300,
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        長篇 500+ 字文章連續合成與波形拼接：
        1. 智慧分句
        2. 依序或批次進行 VITS 推論
        3. 拼接並加入語音間隔
        """
        self._ensure_loaded()
        chunks = split_article_into_sentences(article_text)
        if not chunks:
            raise ValueError("文章內容為空，無法合成")

        pause_samples = int(self.sample_rate * (pause_ms / 1000.0))
        pause_wav = np.zeros(pause_samples, dtype=np.float32)

        all_waveforms = []
        sentence_timings = []
        sentence_poj_list = []
        current_sample = 0

        for item in chunks:
            raw_text = item["text"]
            poj_converted = self.text_to_poj(raw_text, apply_sandhi)

            sentence_poj_list.append({
                "index": item["index"],
                "text": raw_text,
                "poj": poj_converted
            })

            wav = self.synthesize_sentence(raw_text, apply_sandhi=apply_sandhi)

            start_ms = int((current_sample / self.sample_rate) * 1000)
            current_sample += len(wav)
            end_ms = int((current_sample / self.sample_rate) * 1000)

            all_waveforms.append(wav)
            all_waveforms.append(pause_wav)
            current_sample += len(pause_wav)

            sentence_timings.append({
                "index": item["index"],
                "text": raw_text,
                "poj": poj_converted,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_ms": end_ms - start_ms
            })

        # 串聯所有波形
        final_waveform = np.concatenate(all_waveforms)

        # 轉成 16-bit PCM WAV
        import scipy.io.wavfile as wavfile
        wav_io = io.BytesIO()
        scaled = np.int16(np.clip(final_waveform, -1.0, 1.0) * 32767)
        wavfile.write(wav_io, self.sample_rate, scaled)
        wav_bytes = wav_io.getvalue()

        # 輸出為檔案 (若有指定)
        if output_file:
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            # 若副檔名為 mp3，透過 pydub 轉成 mp3
            if output_file.lower().endswith('.mp3'):
                seg = AudioSegment.from_file(io.BytesIO(wav_bytes), format="wav")
                seg.export(output_file, format="mp3", bitrate="192k")
            else:
                with open(output_file, "wb") as f:
                    f.write(wav_bytes)

        total_duration_ms = int((len(final_waveform) / self.sample_rate) * 1000)

        return {
            "model": "facebook/mms-tts-nan",
            "sample_rate": self.sample_rate,
            "total_chars": len(article_text),
            "sentence_count": len(chunks),
            "total_duration_ms": total_duration_ms,
            "sentence_timings": sentence_timings,
            "audio_bytes": wav_bytes,
            "audio_format": "wav"
        }


if __name__ == '__main__':
    print("Meta MMS-TTS Engine 模組定義完成。")
