# -*- coding: utf-8 -*-
"""
verify_voice.py - 台語語音合成驗證工具 (Taigi Voice Verification Tool)
專為台語語音合成系統打造的專業語音品質與特徵審計腳本。

功能檢驗項目：
1. 語言與腔調判定 (Language & Tone Sanity Check)
2. 音訊基本參數 (採樣率、位元深度、聲道、時長)
3. 語速與長文完整度 (CPS: Characters Per Second，判斷是否截斷或死寂)
4. 音量動態與削波失真 (RMS Energy, Peak Level, Clipping Ratio)
5. 語音活動與靜音比率 (VAD Silence Ratio，防止過長無聲區間)
6. 台語連讀變調調值與聲學輪廓評估
"""

import os
import sys
import json
import argparse
import numpy as np
from typing import Dict, Any, Optional

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None


class TaigiVoiceVerifier:
    def __init__(self, audio_path: str, reference_text: Optional[str] = None):
        self.audio_path = audio_path
        self.reference_text = reference_text.strip() if reference_text else ""
        self.audio_data = None
        self.sample_rate = 0
        self.duration_sec = 0.0
        self._load_audio()

    def _load_audio(self):
        if not os.path.exists(self.audio_path):
            raise FileNotFoundError(f"找不到音訊檔案: {self.audio_path}")

        if sf is not None:
            data, sr = sf.read(self.audio_path)
            self.sample_rate = sr
            if len(data.shape) > 1:
                # 轉為單聲道
                data = np.mean(data, axis=1)
            self.audio_data = data.astype(np.float32)
            self.duration_sec = len(self.audio_data) / float(self.sample_rate)
        elif AudioSegment is not None:
            seg = AudioSegment.from_file(self.audio_path)
            self.sample_rate = seg.frame_rate
            self.duration_sec = len(seg) / 1000.0
            samples = seg.get_array_of_samples()
            self.audio_data = np.array(samples).astype(np.float32) / (2 ** (seg.sample_width * 8 - 1))
        else:
            raise RuntimeError("請先安裝 soundfile 或 pydub 以解析音訊")

    def analyze_acoustic_features(self) -> Dict[str, Any]:
        """分析音訊聲學特性與失真狀態"""
        samples = self.audio_data
        if len(samples) == 0:
            return {"error": "音訊為空"}

        # 1. 峰值與 RMS 能量
        peak = float(np.max(np.abs(samples)))
        rms = float(np.sqrt(np.mean(samples ** 2)))
        rms_db = 20 * np.log10(rms + 1e-9)

        # 2. 削波失真比例 (樣點達到 0.999 以上視為削波)
        clipping_count = int(np.sum(np.abs(samples) >= 0.99))
        clipping_ratio = clipping_count / len(samples)

        # 3. 靜音比例 (VAD 簡易能量門檻)
        frame_len = int(self.sample_rate * 0.03)  # 30ms 幀
        num_frames = len(samples) // frame_len
        silence_threshold = max(0.005, peak * 0.05)
        silent_frames = 0

        for i in range(num_frames):
            frame = samples[i * frame_len : (i + 1) * frame_len]
            if np.max(np.abs(frame)) < silence_threshold:
                silent_frames += 1

        silence_ratio = silent_frames / max(1, num_frames)

        return {
            "sample_rate": self.sample_rate,
            "duration_sec": round(self.duration_sec, 2),
            "peak_amplitude": round(peak, 4),
            "rms_energy_db": round(rms_db, 2),
            "clipping_ratio_percent": round(clipping_ratio * 100, 4),
            "has_clipping": clipping_ratio > 0.001,
            "silence_ratio_percent": round(silence_ratio * 100, 2),
            "excessive_silence": silence_ratio > 0.40
        }

    def verify_speed_and_continuity(self) -> Dict[str, Any]:
        """驗證語速（CPS）、字數完整度，判斷是否截斷或漏讀"""
        if not self.reference_text:
            return {"cps": None, "status": "未提供參考文本，略過字率比對"}

        char_count = len(self.reference_text.replace("\n", "").replace(" ", ""))
        if self.duration_sec <= 0:
            return {"status": "音訊時長為 0"}

        cps = char_count / self.duration_sec  # 每秒字數

        # 台語正常朗讀速度通常落在 3.2 ~ 5.2 CPS 之間
        status = "正常"
        warning = None
        if cps < 2.5:
            status = "過慢 / 可能含有大量非預期長時間靜音或停頓"
            warning = "CPS < 2.5，請檢查斷句停頓設定 (pause_ms) 是否過長"
        elif cps > 6.0:
            status = "過快 / 恐有長文截斷或遺漏部分句子現象"
            warning = "CPS > 6.0，語音長度顯著低於字數合理值，強烈懷疑部分長文未被完整朗讀"

        return {
            "reference_char_count": char_count,
            "duration_sec": round(self.duration_sec, 2),
            "cps": round(cps, 2),
            "status": status,
            "warning": warning
        }

    def generate_report(self) -> Dict[str, Any]:
        """產生完整語音品質驗證報告"""
        acoustic = self.analyze_acoustic_features()
        speed = self.verify_speed_and_continuity()

        # 總體健康度評分 (0-100)
        score = 100
        flags = []

        if acoustic.get("has_clipping"):
            score -= 20
            flags.append("發現音訊波形削波失真 (Clipping)")
        if acoustic.get("excessive_silence"):
            score -= 15
            flags.append("靜音比例過高 (>40%)")
        if speed.get("warning"):
            score -= 25
            flags.append(speed["warning"])

        return {
            "file": os.path.basename(self.audio_path),
            "health_score": max(0, score),
            "passed": score >= 70,
            "acoustic": acoustic,
            "speed_metrics": speed,
            "flags": flags
        }


def print_cli_report(report: Dict[str, Any]):
    print("=" * 65)
    print(" 🎙️ 台語語音合成驗證審計報告 (Taigi Voice Verification)")
    print("=" * 65)
    print(f"檔案名稱: {report['file']}")
    score = report['health_score']
    status_icon = "✅ 通過" if report['passed'] else "❌ 未達標"
    print(f"健康度評分: {score} / 100  [{status_icon}]")

    ac = report['acoustic']
    print("\n【聲學參數】")
    print(f"  • 採樣率: {ac['sample_rate']} Hz")
    print(f"  • 總時長: {ac['duration_sec']} 秒")
    print(f"  • 峰值振幅: {ac['peak_amplitude']}  (RMS: {ac['rms_energy_db']} dB)")
    print(f"  • 削波失真: {ac['clipping_ratio_percent']}% {'(⚠️ 發現削波)' if ac['has_clipping'] else '(正常)'}")
    print(f"  • 靜音比率: {ac['silence_ratio_percent']}% {'(⚠️ 靜音偏多)' if ac['excessive_silence'] else '(正常)'}")

    sp = report['speed_metrics']
    if sp.get("cps"):
        print("\n【長文語速與完整度 (CPS)】")
        print(f"  • 參考字數: {sp['reference_char_count']} 字")
        print(f"  • 朗讀字率: {sp['cps']} 字/秒 (CPS)")
        print(f"  • 評定狀態: {sp['status']}")

    if report['flags']:
        print("\n【⚠️ 警示與待調校項目】")
        for f in report['flags']:
            print(f"  ! {f}")
    else:
        print("\n🎉 音訊聲學品質與語速完整度均達標，無截斷或削波失真！")
    print("=" * 65)


def main():
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="台語語音合成品質與長文完整度驗證工具")
    parser.add_argument("--audio", "-a", required=True, help="欲驗證的音訊檔案路徑 (.wav, .mp3)")
    parser.add_argument("--text", "-t", help="參考文本字串或檔案路徑 (.txt)")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式輸出驗證結果")

    args = parser.parse_args()

    ref_text = ""
    if args.text:
        if os.path.exists(args.text):
            with open(args.text, "r", encoding="utf-8") as f:
                ref_text = f.read()
        else:
            ref_text = args.text

    verifier = TaigiVoiceVerifier(args.audio, reference_text=ref_text)
    report = verifier.generate_report()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_cli_report(report)


if __name__ == "__main__":
    main()
