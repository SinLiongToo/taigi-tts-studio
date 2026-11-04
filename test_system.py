# -*- coding: utf-8 -*-
"""
test_system.py - 系統自動化測試腳本
測試項目：
1. 變調引擎正確性 (五調循環 1->7->3->2->1, 入聲 4<->8, 喉塞 -h 舒聲化, 三疊字 AAA)
2. 500+ 字長篇文章分句與長度驗證
3. G2P 轉為 Meta MMS-TTS 變調 POJ 測試
4. Edge-TTS 語音合成測試
5. FastAPI Server 路由與 API 回應測試
"""

import sys
import os
import unittest
from fastapi.testclient import TestClient

from taigi_sandhi import (
    parse_syllable,
    apply_sandhi_to_word,
    TaigiTextPipeline,
    split_article_into_sentences,
    skeleton_to_poj
)
from server import app


class TestTaigiTTS(unittest.TestCase):
    def setUp(self):
        self.pipeline = TaigiTextPipeline(dialect="south")
        self.client = TestClient(app)

    def test_tone_sandhi_cycle(self):
        """測試台語基本變調五調循環"""
        # 第 1 聲變第 7 聲：東 tang1 -> tang7
        s1 = parse_syllable("tang1")
        w1 = apply_sandhi_to_word([s1, s1])
        self.assertEqual(w1[0].tone, 7)
        self.assertEqual(w1[1].tone, 1)  # 組末維持本調

        # 第 7 聲變第 3 聲：洞 tong7 -> tong3
        s7 = parse_syllable("tong7")
        w7 = apply_sandhi_to_word([s7, s7])
        self.assertEqual(w7[0].tone, 3)

        # 第 3 聲變第 2 聲：黨 tong3 -> tong2
        s3 = parse_syllable("tong3")
        w3 = apply_sandhi_to_word([s3, s3])
        self.assertEqual(w3[0].tone, 2)

        # 第 2 聲變第 1 聲：董 tong2 -> tong1
        s2 = parse_syllable("tong2")
        w2 = apply_sandhi_to_word([s2, s2])
        self.assertEqual(w2[0].tone, 1)

        # 第 5 聲變第 7 聲 (南)：同 tong5 -> tong7
        s5 = parse_syllable("tong5")
        w5 = apply_sandhi_to_word([s5, s5])
        self.assertEqual(w5[0].tone, 7)

    def test_checked_tone_and_glottal_stop(self):
        """測試入聲對調 (4<->8) 與喉塞音 -h 弱化舒聲變調 (4h->2, 8h->3)"""
        # 入聲 -t 對調：4 -> 8 (結 kiat4 -> kiat8)
        sk4 = parse_syllable("kiat4")
        wk4 = apply_sandhi_to_word([sk4, sk4])
        self.assertEqual(wk4[0].tone, 8)

        # 入聲 -k 對調：8 -> 4 (逐 tak8 -> tak4)
        sk8 = parse_syllable("tak8")
        wk8 = apply_sandhi_to_word([sk8, sk8])
        self.assertEqual(wk8[0].tone, 4)

        # 喉塞音 4h 脫落去 h 變第 2 聲：煞 suah4 -> sua2
        sh4 = parse_syllable("suah4")
        wh4 = apply_sandhi_to_word([sh4, sh4])
        self.assertEqual(wh4[0].skeleton, "sua")
        self.assertEqual(wh4[0].tone, 2)

        # 喉塞音 8h 脫落去 h 變第 3 聲：白 peh8 -> pe3
        sh8 = parse_syllable("peh8")
        wh8 = apply_sandhi_to_word([sh8, sh8])
        self.assertEqual(wh8[0].skeleton, "pe")
        self.assertEqual(wh8[0].tone, 3)

    def test_triple_word_sandhi(self):
        """測試三疊字 (AAA) 變調：紅紅紅 ang5-ang5-ang5 -> 第一字變第 5 聲中升調"""
        s = parse_syllable("ang5")
        res = apply_sandhi_to_word([s, s, s])
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0].tone, 5)  # 首字中升調 (5)
        self.assertEqual(res[1].tone, 7)  # 次字一般變調 (5->7)
        self.assertEqual(res[2].tone, 5)  # 末字本調 (5)

    def test_sample_article_length(self):
        """驗證範文滿足 500 字以上長文標準"""
        sample_path = os.path.join(os.path.dirname(__file__), "samples", "sample_article_500words.txt")
        self.assertTrue(os.path.exists(sample_path))
        with open(sample_path, "r", encoding="utf-8") as f:
            content = f.read()
        char_count = len(content.replace("\n", "").replace(" ", ""))
        self.assertGreaterEqual(char_count, 500, f"文章長度 {char_count} 應至少 500 字")

        # 測試分句
        chunks = split_article_into_sentences(content)
        self.assertGreater(len(chunks), 3)

    def test_mms_poj_pipeline(self):
        """測試 G2P 轉為 Meta MMS 所需的連讀變調 POJ"""
        text = "食飽未？逐家好！"
        poj = self.pipeline.convert_to_sandhi_poj(text)
        self.assertIn("chià-pá", poj.lower())
        self.assertIn("tak-kē", poj.lower())

    def test_server_api_models(self):
        """測試後端 /api/models 回應"""
        res = self.client.get("/api/models")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("models", data)
        model_ids = [m["id"] for m in data["models"]]
        self.assertIn("edge", model_ids)
        self.assertIn("mms", model_ids)

    def test_server_api_parse(self):
        """測試後端 /api/g2p/parse 文字解析"""
        res = self.client.post("/api/g2p/parse", json={"text": "天氣真好，心情爽快。"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data["sentences"]), 1)

    def test_direct_romanization_parsing(self):
        """測試直接輸入全羅 (Tâi-lô)、白話字 (POJ) 與數字調的解析與變調"""
        # 1. 教育部台羅符號調
        tailo_input = "Tâi-oân chá-tshī-á ê tsu-bī."
        tokens = self.pipeline.parse_sentence_to_tokens(tailo_input)
        word_tokens = [t for t in tokens if t.get("type") == "word"]
        self.assertGreaterEqual(len(word_tokens), 4)
        self.assertTrue(word_tokens[0].get("is_roman"))
        self.assertEqual(word_tokens[0]["tailo_base"], "tâi-uân")
        self.assertEqual(word_tokens[0]["tailo_sandhi"], "tāi-uân")  # 5 -> 7 變調

        # 2. 直接輸入白話字 (POJ) 轉變調 POJ
        poj_input = "Tâi-oân chá-chhī-á ê chu-bī."
        poj_sandhi = self.pipeline.convert_to_sandhi_poj(poj_input)
        self.assertIn("tāi-oân", poj_sandhi.lower())
        self.assertIn("cha-chhì-á", poj_sandhi.lower())

        # 3. 測試後端 API 支援全羅並反查教育部官方錄音檔
        res = self.client.post("/api/g2p/parse", json={"text": "tsu-bī"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        words = [t for s in data["sentences"] for t in s["tokens"] if t.get("type") == "word"]
        self.assertEqual(len(words), 1)
        self.assertIsNotNone(words[0].get("audio_url"))
        self.assertIn("08630", words[0]["audio_url"])  # 滋味 official ID

    def test_tone_mark_placement(self):
        """調號位置：成音節 ng 標在 n（門 mn̂g），-nnh 轉白話字為 ⁿh"""
        self.assertEqual(skeleton_to_poj("mng", 5), "mn̂g")
        self.assertEqual(skeleton_to_poj("ng", 7), "n̄g")
        self.assertEqual(skeleton_to_poj("hm", 5), "hm̂")
        self.assertEqual(skeleton_to_poj("hannh", 4), "haⁿh")
        self.assertEqual(skeleton_to_poj("sinn", 1), "siⁿ")


class TestMmsTextCleaning(unittest.TestCase):
    """MMS 詞表只有 48 個字元（無標點、無 ⁿ）：確認送進模型的字串只含詞表字元，且字母不會被整個刪掉"""

    @classmethod
    def setUpClass(cls):
        try:
            from transformers import AutoTokenizer
            from mms_engine import MmsTtsEngine
            tok = AutoTokenizer.from_pretrained("facebook/mms-tts-nan")
        except Exception as e:  # 沒裝 transformers 或離線無快取
            raise unittest.SkipTest(f"MMS tokenizer 不可用: {e}")
        cls.engine = MmsTtsEngine.__new__(MmsTtsEngine)
        cls.engine._vocab_cache = set(tok.get_vocab().keys())

    def test_only_vocab_chars(self):
        out = self.engine.clean_poj_for_mms("Goá m̀-chai-iáⁿ, chiàⁿ-chhiú!")
        self.assertTrue(set(out) <= self.engine._vocab_cache, out)
        self.assertEqual(out, "goá m-chai-iá chià-chhiú")

    def test_keeps_supported_marks(self):
        self.assertEqual(self.engine.clean_poj_for_mms("chia̍h-pá bē?"), "chia̍h-pá bē")
        self.assertEqual(self.engine.clean_poj_for_mms("ô͘-á"), "ô͘-á")


if __name__ == '__main__':
    unittest.main()
