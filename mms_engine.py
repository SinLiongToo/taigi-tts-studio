# -*- coding: utf-8 -*-
"""
mms_engine.py - Meta MMS (Massively Multilingual Speech) 台語 VITS 模型推論引擎
模型標識: facebook/mms-tts-nan (約 36M 參數，基於 VITS 架構)
特點與痛點克服：
- 原生模型輸入僅支援白話字（POJ），且無法自行處理台語語境中的「連讀變調（Tone Sandhi）」。
- 本模組自動在前處理層結合 taigi_sandhi.py：
  1. 漢字/漢羅 -> 台羅/POJ 音節剖析 (G2P)
  2. 套用五調循環 + 入聲對調 + 喉塞音舒聲化變調規則
  3. 轉化為變調後的標準 POJ 送入 MMS-TTS，徹底消除外國人念經文的機械呆滯感！
- 支援長篇文章（500+ 字）自動分句推論與波形平滑拼接。
"""

import io
import os
import re
import numpy as np
import torch
from typing import List, Dict, Any, Optional
from taigi_sandhi import TaigiTextPipeline, split_article_into_sentences
from pydub import AudioSegment

MMS_MODEL_ID = "facebook/mms-tts-nan"


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

    def clean_poj_for_mms(self, poj_text: str) -> str:
        """
        將 POJ 正規化為 MMS Tokenizer 易於識別的字符：
        將白話字特殊符號與全形標點標準化，去除不相干符號
        """
        text = poj_text.lower()
        # 替換特殊全形符號
        text = text.replace('，', ', ').replace('。', '. ').replace('！', '! ').replace('？', '? ')
        text = text.replace('；', '; ').replace('、', ', ').replace('：', ': ')
        # 清除連續多餘空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def synthesize_sentence(self, sentence_text: str, apply_sandhi: bool = True) -> np.ndarray:
        """
        合成單一句子 (極速推論模式):
        使用 torch.inference_mode() 避免梯隊構建，大幅縮短 CPU 耗時。
        """
        self._ensure_loaded()

        if apply_sandhi:
            poj_text = self.g2p.convert_to_sandhi_poj(sentence_text)
        else:
            poj_text = self.g2p.convert_to_poj_raw(sentence_text)

        cleaned_poj = self.clean_poj_for_mms(poj_text)
        if not cleaned_poj:
            return np.zeros(int(self.sample_rate * 0.2), dtype=np.float32)

        inputs = self.tokenizer(cleaned_poj, return_tensors="pt").to(self.device)

        with torch.inference_mode():
            output = self.model(**inputs)
            waveform = output.waveform[0].cpu().float().numpy()

        return waveform

    def synthesize_article(
        self,
        article_text: str,
        apply_sandhi: bool = True,
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
            if apply_sandhi:
                poj_converted = self.g2p.convert_to_sandhi_poj(raw_text)
            else:
                poj_converted = self.g2p.convert_to_poj_raw(raw_text)

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
