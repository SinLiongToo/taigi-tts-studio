# Taigi TTS Studio (台語多模型長文語音合成工坊)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-teal.svg)](https://fastapi.tiangolo.com)
[![Meta MMS](https://img.shields.io/badge/Meta%20MMS-facebook%2Fmms--tts--nan-orange.svg)](https://huggingface.co/facebook/mms-tts-nan)

一套專為**臺灣話（台語 / 閩南語 / Tâi-gí）**量身打造的高品質、長文朗讀、多模型語音合成與連讀變調調校系統。

本專案承襲並大幅進化自先前開發之 [sinliongtoo/taigi-tts](https://sinliongtoo.github.io/taigi-tts/)，全面解決長篇文本（**500 字以上**）朗讀中斷、模型單一、以及台語特有「**連讀變調（Tone Sandhi）**」所造成的語調生硬機械感等核心痛點。

---

## 🌟 專案核心特色與突破

### 1. 📖 500+ 字長篇台語長文連續朗讀管線 (Long-Form Audio Engine)
- **智慧語句切分 (Smart Sentence Chunking)**：自動依據標點符號（`。！？…；，、`）進行語義段落切分，防止神經網路模型發生記憶體溢出（OOM）或聲音截斷。
- **Karaoke 逐句高亮跟隨 (Progress Tracking)**：朗讀長文時，畫面會即時同步光暈高亮當前讀到的句子與詞彙，避免聽讀時迷失位置。
- **全篇無縫拼接與整檔匯出**：自動在句間插入自然喘息間隔（預設 300ms，可自訂），一鍵將 500～3000 字文章合成並匯出完整 MP3 / WAV 檔。

### 2. 🎛️ 多模型自由切換 (Multi-Model Hub)
系統內建四大模型架構，滿足從離線開源研究到商業級自然流暢朗讀的不同需求：

| 語音模型 | 架構類型 | 核心特點 | 適用情境 |
| :--- | :--- | :--- | :--- |
| **Microsoft Edge-TTS** | 類神經語音 (Neural) | 極致自然流暢，支援台語/臺灣華語自然混讀，提供曉臻 (女聲)、雲哲 (男聲)、曉雨 (女聲) | **500+ 字長文朗讀首選**、廣播故事 |
| **Meta MMS-TTS** (`facebook/mms-tts-nan`) | 端到端 VITS (~36M 參數) | Meta 開源台語模型，**搭配本系統變調 POJ Pipeline 前處理**，徹底解決生硬朗讀問題 | 開源本地端推論、研究與無外部 API 依賴 |
| **教育部臺灣台語辭典** | 真人錄音拼接 (Concatenative) | 採用教育部辭典官方錄音檔，逐詞拼接，支援同音借調與逐字備援 | 官方標準教學發音、辭典比對 |
| **Web Speech API** | 瀏覽器原生語音 | 零網路傳輸、零延遲 | 輕量離線輔助 |

---

### 3. 🧠 解決 Meta MMS-TTS 核心痛點：台語連讀變調 Pipeline (Tone Sandhi Engine)

Meta 在 **MMS（Massively Multilingual Speech）** 專案釋出的 `facebook/mms-tts-nan` 是基於 VITS 架構的優秀模型，但實務應用時有兩大先天限制：
1. **輸入限制**：只吃純白話字（POJ），無法直接吃漢字或漢羅。
2. **語音生硬問題**：語料來自單一講者經文朗讀，且模型**缺乏台語句法連讀變調推論能力**。若直接送入辭典查出的「本調 POJ」，會以全本調念出，聽感帶有強烈的「外國人逐字生硬念經」感。

#### 💡 本系統之解決方案：
本系統在送入 MMS 之前，建立了一套標準台語 G2P 與連讀變調轉換管線（`taigi_sandhi.py`）：
$$\text{台語漢字 / 漢羅} \xrightarrow{\text{G2P 斷詞音節剖析}} \text{本調音標} \xrightarrow{\text{Tone Sandhi Engine}} \textbf{變調後 POJ (Sandhi-Tones)} \xrightarrow{\text{VITS}} \textbf{自然流暢語音}$$

#### 🎵 台語連讀變調規則實作細節：
- **舒聲循環 (Non-checked finals)**：變調組中除最後一個音節外，前面的音節依照嚴格規則轉換：
  $$1 \rightarrow 7 \rightarrow 3 \rightarrow 2 \rightarrow 1 \quad \text{與} \quad 5 \rightarrow 7 \text{ (南部腔) / } 5 \rightarrow 3 \text{ (北部腔)}$$
- **入聲對調 (Checked finals: -p, -t, -k)**：
  $$4 \longleftrightarrow 8 \quad (\text{陰入變陽入、陽入變陰入})$$
- **喉塞音脫落舒聲化 (Glottal Stop: -h)**：
  - 第 4 聲喉塞（`-h`）脫落轉為第 2 聲舒聲（例：`suah4` 煞 $\rightarrow$ `sua2`）
  - 第 8 聲喉塞（`-h`）脫落轉為第 3 聲舒聲（例：`peh8` 白 $\rightarrow$ `pe3`）
- **輕聲（`--`）與組末規則**：輕聲前音節維持本調；變調組最後一個音節維持本調。
- **三疊字特殊變調 (AAA)**：第一字轉為中升調（第 5 調值）。

---

### 4. ✏️ 互動式發音校正與調校工作坊 (Interactive Pronunciation Editor)
- **逐句 Tokens 視覺化檢視**：全文自動切分成詞塊，清晰標示本調、變調與教育部台羅/POJ。
- **點擊詞塊立即修正**：
  - **破音字候選清單**：快速切換官方辭典收錄的同形多音（如「食」`tsia̍h` / 「行」`kiânn` / `hîng`）。
  - **自訂讀音標註**：可手動輸入任何教育部台羅、POJ 或數字調。
  - **強制維持本調開關**：針對專有名詞、句尾詞或人名，可勾選強制不變調。
  - **單詞試聽與永久保存**：校正結果自動記憶至 IndexedDB 自訂詞庫，並支援匯入/匯出 JSON 與 CSV。

---

## 📂 目錄架構

```
TIGI_TTS_MOREMODL/
├── README.md                      # 專案詳細說明與參考來源文件
├── requirements.txt               # Python 依賴清單
├── server.py                      # FastAPI 後端伺服器 (多模型合成、G2P、靜態託管)
├── cli.py                         # 命令列長文合成工具 (支援 500+ 字文章)
├── taigi_sandhi.py                # 台語連讀變調核心引擎與 G2P 前處理器
├── edge_engine.py                 # Microsoft Edge-TTS 長文串流拼接引擎
├── mms_engine.py                  # Meta MMS-TTS (facebook/mms-tts-nan) 推論引擎
├── test_system.py                 # 自動化單元測試腳本 (涵蓋變調、長文、API)
├── samples/
│   ├── sample_article_500words.txt # 662 字經典長文範例 (台灣早市仔)
│   ├── edge_test.mp3              # Edge-TTS 測試音檔
│   └── article_662words_hsiaochen.mp3 # 662 字長文合成完整示範音檔 (~2.5 分鐘)
└── web/
    ├── index.html                 # 現代化專業 Taigi TTS Studio 介面
    ├── style.css                  # 精緻響應式排版 (支援明亮/深色主題)
    └── js/
        ├── app.js                 # 核心控制邏輯 (長文分句、Karaoke、互動校正)
        ├── romanize.js            # 台羅/POJ 雙向轉換與前端變調演算法
        ├── dict.js                # 教育部辭典快取 (IndexedDB) 與自訂詞庫
        └── audio_export.js        # Web 端多段音訊拼接與匯出
```

---

## 🚀 快速開始

### 1. 安裝環境依賴

```bash
pip install -r requirements.txt
```

> **主要套件說明**：`edge-tts`, `taibun`, `fastapi`, `uvicorn`, `pydub`, `torch`, `transformers`, `soundfile`。

---

### 2. 啟動 Web Studio (推薦)

執行本機後端伺服器：

```bash
python server.py
```

開啟瀏覽器前往：**`http://localhost:8000`**

- 介面自動檢測後端連線，解鎖全模型。
- 可一鍵點擊「**📋 載入 500+ 字範文**」，體驗 662 字長文連續朗讀與 Karaoke 逐句高亮追蹤！

> 💡 **純靜態離線模式**：若未啟動 Python 伺服器，直接雙擊開啟 `web/index.html` 亦可運作，系統會自動降級為「本機純前端模式」（使用教育部辭典真人錄音拼接與 Web Speech API）。

---

### 3. 命令列 CLI 工具使用

#### (1) 朗讀短句
```bash
python cli.py --text "食飽未？逐家好！" --output hello.mp3
```

#### (2) 朗讀 500+ 字長篇文章 (使用 Edge-TTS 曉臻女聲)
```bash
python cli.py --input samples/sample_article_500words.txt --model edge --voice HsiaoChen --output article_edge.mp3
```

#### (3) 使用 Meta MMS-TTS 搭配台語連讀變調 Pipeline
```bash
python cli.py --input samples/sample_article_500words.txt --model mms --sandhi --output article_mms.wav
```

#### (4) 查看所有支援的模型與聲音清單
```bash
python cli.py --list-models
```

---

### 4. 語音品質驗證與審計 (Taigi Voice Verification)

專案內建專業的台語語音審查工具，並已封裝為獨立 Agent Skill (`taigi-voice-verification`)：

```bash
# 驗證合成音訊的聲學健康度、削波失真與長文完整度 (CPS 字率)
python verify_voice.py --audio samples/mms_article_taigi.wav --text samples/sample_article_500words.txt
```

檢驗指標包含：
- **語言防偽**：自動辨識是否誤用臺灣國語模型。
- **長文完整度**：計算 CPS（字率 Characters Per Second，標準 3.2 ~ 5.2），防止神經網路漏讀或截斷。
- **聲學失真**：檢測峰值振幅、RMS 能量與削波比例（Clipping Ratio）。
- **連讀變調調值輪廓**：驗證是否正確套用變調而非生硬本調。

---

### 5. 執行自動化測試

```bash
python test_system.py
```

---

## 📚 參考來源與學術文獻 (References)

1. **Meta MMS (Massively Multilingual Speech)**
   - Vineel Pratap et al. (2023). *Scaling Speech Technology to 1,000+ Languages*. arXiv:2305.13516.
   - Hugging Face Model: [`facebook/mms-tts-nan`](https://huggingface.co/facebook/mms-tts-nan).
   - Meta Hokkien Speech Translation Project (2022).

2. **教育部臺灣台語常用詞辭典**
   - 中華民國教育部：《臺灣台語常用詞辭典》官方資料庫與錄音檔。
   - g0v 社群：[`g0v/moedict-data-twblg`](https://github.com/g0v/moedict-data-twblg).

3. **台語連讀變調 (Tone Sandhi) 學理依據**
   - 董峰政：《台灣閩南語的變調規律》.
   - 教育部臺灣台語羅馬字拼音方案與聲調標示規則.
   - `Romanize.js` 連讀變調狀態機：實作 1-7-3-2-1 五調循環、4-8 入聲對調與 -h 喉塞舒聲化.

4. **Taibun 台文處理庫**
   - [`taibun`](https://github.com/a-tsioh/taibun): Python Taiwanese Romanisation, Sandhi and Segmentation Toolkit.

5. **Microsoft Edge-TTS**
   - Microsoft Azure Neural Speech: `zh-TW-HsiaoChenNeural`, `zh-TW-YunJheNeural`.
   - [`edge-tts`](https://github.com/rany2/edge-tts): Python interface to Microsoft Edge's online TTS service.

---

## 📄 開源授權

本專案基於 **MIT License** 開源發布。歡迎社群自由擴充、微調訓練及應用於台語母語教育與科技推廣！
