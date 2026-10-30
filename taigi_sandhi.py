# -*- coding: utf-8 -*-
"""
taigi_sandhi.py - 臺灣話（台語 / 閩南語）連讀變調引擎與 G2P（Grapheme-to-Phoneme）前處理器
支援台羅（Tâi-lô）與白話字（POJ）雙向轉換、音節剖析、聲調循環變調、喉塞入聲舒聲化，
並特別為 Meta MMS-TTS (facebook/mms-tts-nan) 提供「變調後 POJ」的標準化輸入。
"""

import re
import unicodedata
from typing import List, Dict, Optional, Tuple, Any

# 台語聲調符號 (Combining Diacritics)
TONE_MARK_MAP = {
    1: '',
    2: '\u0301',  # acute (ˊ)
    3: '\u0300',  # grave (ˋ)
    4: '',
    5: '\u0302',  # circumflex (ˆ)
    6: '\u0301',  # 陽上 (同第2聲調號)
    7: '\u0304',  # macron (ˉ)
    8: '\u030d',  # vertical line above (̍)
    9: '\u0306',  # breve (˘)
}

MARK_TO_TONE = {
    '\u0301': 2,
    '\u0300': 3,
    '\u0302': 5,
    '\u0304': 7,
    '\u030d': 8,
    '\u0306': 9,
}

CHECKED_FINALS = ('p', 't', 'k', 'h')
DOT_ABOVE_RIGHT = '\u0358'  # 白話字 o͘
NASAL_MARK = '\u207f'       # 白話字 ⁿ

# 傳統台語五調循環（一般非入聲、非最後一字）：
# 1 -> 7 -> 3 -> 2 -> 1
# 5 -> 7 (南部偏優勢腔) 或 5 -> 3 (北部偏漳腔)
SANDHI_CYCLE_SOUTH = {1: 7, 2: 1, 3: 2, 5: 7, 7: 3}
SANDHI_CYCLE_NORTH = {1: 7, 2: 1, 3: 2, 5: 3, 7: 3}


class Syllable:
    """代表單一台語音節"""
    def __init__(self, skeleton: str, tone: int, neutral: bool = False):
        self.skeleton = skeleton.lower()  # 純 ASCII 字母骨架（如 tsiah, png）
        self.tone = tone                  # 1-8
        self.neutral = neutral            # 是否為輕聲

    def copy(self) -> 'Syllable':
        return Syllable(self.skeleton, self.tone, self.neutral)

    def is_checked(self) -> bool:
        """是否為入聲（-p, -t, -k, -h）"""
        return self.skeleton.endswith(CHECKED_FINALS)

    def is_glottal_stop(self) -> bool:
        """是否為喉塞音入聲（-h）"""
        return self.skeleton.endswith('h')

    def __repr__(self):
        return f"Syllable({self.skeleton}{self.tone}{'--' if self.neutral else ''})"


def parse_syllable(raw: str) -> Optional[Syllable]:
    """
    將任何書寫方式的單一音節（台羅、白話字、數字調或符號調），
    解析為 Syllable 物件（包含 ASCII 骨架與調號數字）。
    """
    s = raw.strip()
    if not s:
        return None

    # 檢查是否為數字調 (例如 tsiah8, png7, ho2)
    num_match = re.match(r'^([A-Za-z·͘ⁿ\u0358\u207f]+)([1-9])$', s)
    if num_match:
        plain = num_match.group(1)
        tone = int(num_match.group(2))
    else:
        # 符號調：NFD 分解後找出調號
        nfd = unicodedata.normalize('NFD', s)
        found_tone = None
        letters = []
        for ch in nfd:
            if ch in MARK_TO_TONE:
                found_tone = MARK_TO_TONE[ch]
            else:
                letters.append(ch)
        plain = unicodedata.normalize('NFC', "".join(letters))
        if found_tone is None:
            last = plain[-1].lower() if plain else ''
            found_tone = 4 if last in CHECKED_FINALS else 1
        tone = found_tone

    # 白話字 o· / o͘ / ⁿ 正規化成台羅骨架 oo / nn
    plain = plain.replace('o' + DOT_ABOVE_RIGHT, 'oo')
    plain = plain.replace('o·', 'oo')
    plain = plain.replace('o\u00b7', 'oo')
    plain = plain.replace(NASAL_MARK, 'nn')
    plain = plain.replace('\u207f', 'nn')

    # 白話字轉台羅骨架
    plain = re.sub(r'chh', 'tsh', plain, flags=re.IGNORECASE)
    plain = re.sub(r'ch', 'ts', plain, flags=re.IGNORECASE)
    plain = re.sub(r'oa', 'ua', plain, flags=re.IGNORECASE)
    plain = re.sub(r'oe', 'ue', plain, flags=re.IGNORECASE)
    plain = re.sub(r'eng$', 'ing', plain, flags=re.IGNORECASE)
    plain = re.sub(r'ek$', 'ik', plain, flags=re.IGNORECASE)

    # 骨架必須純為英文縮寫
    if not re.match(r'^[a-z]+$', plain, re.IGNORECASE):
        return None

    return Syllable(plain.lower(), tone)


def place_tone_mark(letters: str, tone: int) -> str:
    """根據教育部台羅規則將調號符號置於正確元音字母上"""
    mark = TONE_MARK_MAP.get(tone, '')
    if not mark:
        return letters

    low = letters.lower()
    # 標號優先順序：a > oo > e > o > iu/ui 中的後者 > i > u > m > ng
    idx = -1
    if 'a' in low:
        idx = low.index('a')
    elif 'oo' in low:
        idx = low.index('oo')
    elif 'e' in low:
        idx = low.index('e')
    elif 'o' in low:
        idx = low.index('o')
    elif 'iu' in low:
        idx = low.index('iu') + 1  # 標在 u
    elif 'ui' in low:
        idx = low.index('ui') + 1  # 標在 i
    elif 'i' in low:
        idx = low.index('i')
    elif 'u' in low:
        idx = low.index('u')
    elif 'm' in low:
        idx = low.index('m')
    elif 'ng' in low:
        idx = low.index('n')
    else:
        # fallback: 標在第一個字母
        idx = 0

    # 組合音符
    res = letters[:idx + 1] + mark + letters[idx + 1:]
    return unicodedata.normalize('NFC', res)


def skeleton_to_tailo(skeleton: str, tone: int) -> str:
    """台羅骨架轉台羅符號調"""
    return place_tone_mark(skeleton, tone)


def skeleton_to_poj(skeleton: str, tone: int) -> str:
    """台羅骨架轉白話字（POJ）標準格式（含 o͘ 及 ⁿ）"""
    s = skeleton
    s = re.sub(r'tsh', 'chh', s)
    s = re.sub(r'ts', 'ch', s)
    s = re.sub(r'ua', 'oa', s)
    s = re.sub(r'ue', 'oe', s)
    s = re.sub(r'ing$', 'eng', s)
    s = re.sub(r'ik$', 'ek', s)
    s = re.sub(r'oo', 'o' + DOT_ABOVE_RIGHT, s)
    s = re.sub(r'nn$', NASAL_MARK, s)
    return place_tone_mark(s, tone)


def skeleton_to_poj_ascii(skeleton: str, tone: int) -> str:
    """白話字純 ASCII / 簡化形式（適合某些模型純文字 Tokenizer）"""
    s = skeleton
    s = re.sub(r'tsh', 'chh', s)
    s = re.sub(r'ts', 'ch', s)
    s = re.sub(r'ua', 'oa', s)
    s = re.sub(r'ue', 'oe', s)
    s = re.sub(r'ing$', 'eng', s)
    s = re.sub(r'ik$', 'ek', s)
    s = re.sub(r'oo', 'o.', s)
    s = re.sub(r'nn$', 'n', s)
    return place_tone_mark(s, tone)


def apply_sandhi_to_syllable(syll: Syllable, dialect: str = 'south') -> Syllable:
    """
    對單個音節套用連讀變調規則：
    1. 舒聲循環：1 -> 7 -> 3 -> 2 -> 1，5 -> 7 (南) 或 5 -> 3 (北)
    2. 入聲循環（-p, -t, -k）：4 <-> 8
    3. 喉塞入聲舒聲化（-h）：
       - 第 4 聲喉塞（-h）去 h 變第 2 聲舒聲（如：出 tshut4, 煞 suah4 -> sua2）
       - 第 8 聲喉塞（-h）去 h 變第 3 聲舒聲（如：白 peh8 -> pe3）
    """
    if syll.neutral:
        # 輕聲不變調或由語境處理
        return syll.copy()

    skel = syll.skeleton
    tone = syll.tone

    if tone in (4, 8):
        if syll.is_glottal_stop():
            # 喉塞韻尾 -h 脫落舒聲化
            new_skel = skel[:-1]
            new_tone = 2 if tone == 4 else 3
            return Syllable(new_skel, new_tone)
        else:
            # -p, -t, -k 對調
            new_tone = 8 if tone == 4 else 4
            return Syllable(skel, new_tone)

    cycle = SANDHI_CYCLE_NORTH if dialect == 'north' else SANDHI_CYCLE_SOUTH
    new_tone = cycle.get(tone, tone)
    return Syllable(skel, new_tone)


def apply_triple_sandhi_first(syll: Syllable) -> Syllable:
    """
    三疊字（AAA，如「紅紅紅」ang-ang-ang）首字特殊變調：
    本調 2/3/4 照一般變調；1/5/7/8 變為「中升調（第5調值）」，喉塞 -h 去除。
    """
    if syll.tone in (2, 3, 4):
        return apply_sandhi_to_syllable(syll)
    skel = syll.skeleton
    if syll.tone == 8 and syll.is_glottal_stop():
        skel = skel[:-1]
    return Syllable(skel, 5)


def apply_sandhi_to_word(sylls: List[Syllable], dialect: str = 'south') -> List[Syllable]:
    """
    對一個詞（以連字號連接的音節序列）進行連讀變調：
    - 變調組除最後一個音節外，前面的音節皆需變調。
    - 若遇輕聲（--），輕聲前的音節維持本調。
    - 支援三疊字特殊變調。
    """
    if not sylls:
        return []
    if len(sylls) == 1:
        return [sylls[0].copy()]

    # 檢查是否為三疊字（3個音節骨架與聲調皆相同）
    if len(sylls) == 3 and (sylls[0].skeleton == sylls[1].skeleton == sylls[2].skeleton) and \
       (sylls[0].tone == sylls[1].tone == sylls[2].tone):
        first = apply_triple_sandhi_first(sylls[0])
        second = apply_sandhi_to_syllable(sylls[1], dialect)
        third = sylls[2].copy()  # 最後一字維持本調
        return [first, second, third]

    result = []
    n = len(sylls)
    for i in range(n):
        curr = sylls[i].copy()
        is_last = (i == n - 1)
        next_is_neutral = (i + 1 < n and sylls[i + 1].neutral)

        if is_last or next_is_neutral:
            # 最後一個音節，或下一個音節是輕聲 -> 維持本調
            result.append(curr)
        else:
            # 連讀變調
            result.append(apply_sandhi_to_syllable(curr, dialect))
    return result


class TaigiTextPipeline:
    """
    台語綜合文本處理管線：
    整合 taibun 庫進行 G2P（漢字/漢羅 -> 台羅/POJ），
    並精確套用連讀變調規則，產出各類下游 TTS 所需格式。
    """
    def __init__(self, dialect: str = 'south'):
        self.dialect = dialect
        try:
            import taibun
            self.tb_tailo = taibun.Converter(system='Tailo', dialect=dialect, format='mark')
            self.tb_poj = taibun.Converter(system='POJ', dialect=dialect, format='mark')
            self.has_taibun = True
        except ImportError:
            self.has_taibun = False

    def g2p_raw(self, text: str, system: str = 'Tailo') -> str:
        """漢字/漢羅轉未變調標音（本調）"""
        if self.has_taibun:
            conv = self.tb_tailo if system.lower() == 'tailo' else self.tb_poj
            return conv.get(text)
        return text

    def convert_to_sandhi_poj(self, text: str) -> str:
        """
        將輸入文本（無論漢字、漢羅或台羅）轉換為【變調後的 POJ（白話字）】。
        這是 Meta MMS-TTS (facebook/mms-tts-nan) 能念得自然順暢的關鍵核心！
        """
        raw_roman = self.g2p_raw(text, system='Tailo')
        # 依詞與標點符號分詞處理
        tokens = re.split(r'(\s+|[，。！？；、：“”「」『』,.!?;:\n\r\t]+)', raw_roman)
        out_tokens = []

        for tok in tokens:
            if not tok or re.match(r'^(\s+|[，。！？；、：“”「」『』,.!?;:\n\r\t]+)$', tok):
                out_tokens.append(tok)
                continue

            # 處理連字號相連的詞（如 Tsia̍h-pn̄g）
            sub_parts = tok.split('-')
            parsed_sylls = []
            for p in sub_parts:
                s = parse_syllable(p)
                if s:
                    parsed_sylls.append(s)
                else:
                    parsed_sylls.append(None)

            if all(s is not None for s in parsed_sylls) and parsed_sylls:
                # 成功剖析為台語詞
                sandhi_sylls = apply_sandhi_to_word(parsed_sylls, self.dialect)
                poj_words = [skeleton_to_poj(s.skeleton, s.tone) for s in sandhi_sylls]
                out_tokens.append("-".join(poj_words))
            else:
                # 無法剖析的純文字或英文，直接保留
                out_tokens.append(tok)

        return "".join(out_tokens)

    def convert_to_sandhi_tailo(self, text: str) -> str:
        """轉換為【變調後的教育部台羅】"""
        raw_roman = self.g2p_raw(text, system='Tailo')
        tokens = re.split(r'(\s+|[，。！？；、：“”「」『』,.!?;:\n\r\t]+)', raw_roman)
        out_tokens = []

        for tok in tokens:
            if not tok or re.match(r'^(\s+|[，。！？；、：“”「」『』,.!?;:\n\r\t]+)$', tok):
                out_tokens.append(tok)
                continue

            sub_parts = tok.split('-')
            parsed_sylls = [parse_syllable(p) for p in sub_parts]

            if all(s is not None for s in parsed_sylls) and parsed_sylls:
                sandhi_sylls = apply_sandhi_to_word(parsed_sylls, self.dialect)
                tailo_words = [skeleton_to_tailo(s.skeleton, s.tone) for s in sandhi_sylls]
                out_tokens.append("-".join(tailo_words))
            else:
                out_tokens.append(tok)

        return "".join(out_tokens)

    def convert_to_poj_raw(self, text: str) -> str:
        """
        將輸入轉換為【標準 POJ 白話字符號調】(維持指定調號，不套用連讀變調)。
        可處理漢字、台羅符號調或台羅數字調（例如 tsiah2-png7 -> chiáh-pn̄g），
        確保送入 Meta MMS 的字串永遠具備合法的 POJ 調號符號。
        """
        raw_roman = self.g2p_raw(text, system='Tailo')
        tokens = re.split(r'(\s+|[，。！？；、：“”「」『』,.!?;:\n\r\t]+)', raw_roman)
        out_tokens = []

        for tok in tokens:
            if not tok or re.match(r'^(\s+|[，。！？；、：“”「」『』,.!?;:\n\r\t]+)$', tok):
                out_tokens.append(tok)
                continue

            sub_parts = tok.split('-')
            parsed_sylls = [parse_syllable(p) for p in sub_parts]

            if all(s is not None for s in parsed_sylls) and parsed_sylls:
                poj_words = [skeleton_to_poj(s.skeleton, s.tone) for s in parsed_sylls]
                out_tokens.append("-".join(poj_words))
            else:
                out_tokens.append(tok)

        return "".join(out_tokens)

    def parse_sentence_to_tokens(self, sentence: str) -> List[Dict[str, Any]]:
        """
        將單一句子解析為詳細的詞塊 (Tokens) 清單：
        利用 taibun 進行台語語義斷詞，並依序求出本調、變調、台羅與 POJ。
        """
        if not self.has_taibun:
            return [{"type": "literal", "text": sentence}]

        import taibun
        tokeniser = taibun.Tokeniser()
        words = tokeniser.tokenise(sentence)
        tokens = []

        for w in words:
            if taibun.is_cjk(w):
                tailo_base = self.g2p_raw(w, system="Tailo").lower()
                tailo_sandhi = self.convert_to_sandhi_tailo(w).lower()
                poj_base = self.g2p_raw(w, system="POJ").lower()
                poj_sandhi = self.convert_to_sandhi_poj(w).lower()
                has_sandhi = (tailo_base != tailo_sandhi)

                tokens.append({
                    "type": "word",
                    "hanzi": w,
                    "tailo_base": tailo_base,
                    "tailo_sandhi": tailo_sandhi,
                    "poj_base": poj_base,
                    "poj_sandhi": poj_sandhi,
                    "has_sandhi": has_sandhi,
                    "is_roman": False
                })
            elif re.search(r'[a-zA-Z\u00C0-\u024F\u0300-\u036F\u1E00-\u1EFF·͘ⁿ]', w):
                # 🌟 支援全羅（Tâi-lô）、白話字（POJ）與數字調直接輸入
                clean_w = w.strip()
                sub_parts = [p for p in re.split(r'-+', clean_w) if p]
                parsed_sylls = [parse_syllable(p) for p in sub_parts]

                if parsed_sylls and all(s is not None for s in parsed_sylls):
                    sandhi_sylls = apply_sandhi_to_word(parsed_sylls, self.dialect)
                    tailo_base = "-".join([skeleton_to_tailo(s.skeleton, s.tone) for s in parsed_sylls])
                    tailo_sandhi = "-".join([skeleton_to_tailo(s.skeleton, s.tone) for s in sandhi_sylls])
                    poj_base = "-".join([skeleton_to_poj(s.skeleton, s.tone) for s in parsed_sylls])
                    poj_sandhi = "-".join([skeleton_to_poj(s.skeleton, s.tone) for s in sandhi_sylls])
                    has_sandhi = (tailo_base != tailo_sandhi)

                    tokens.append({
                        "type": "word",
                        "hanzi": w,
                        "roman_input": w,
                        "tailo_base": tailo_base,
                        "tailo_sandhi": tailo_sandhi,
                        "poj_base": poj_base,
                        "poj_sandhi": poj_sandhi,
                        "has_sandhi": has_sandhi,
                        "is_roman": True
                    })
                else:
                    tokens.append({"type": "literal", "text": w})
            else:
                tokens.append({"type": "literal", "text": w})

        return tokens


def split_article_into_sentences(text: str, max_chunk_len: int = 120) -> List[Dict[str, Any]]:
    """
    智慧長文分句引擎：
    將 500～3000 字以上的長篇文章切分成語義完整、適合神經網路與拼接 TTS 合成的句子。
    依標點符號優先順序進行分段，防止過長句子導致音訊模型截斷或記憶體暴增。
    """
    # 標點分割正則（包含換行、句末標點、分號等，以及英文/全羅句尾 . ）
    raw_sentences = re.split(r'([。！？!?\n\r]+|(?<=[a-zA-Z0-9\u0300-\u0358\u207f])\.\s+)', text)
    chunks = []
    curr_text = ""

    for i in range(0, len(raw_sentences), 2):
        sentence = raw_sentences[i]
        punct = raw_sentences[i + 1] if i + 1 < len(raw_sentences) else ""
        combined = (sentence + punct).strip()

        if not combined:
            continue

        if len(curr_text) + len(combined) <= max_chunk_len:
            curr_text += (" " if curr_text and not curr_text.endswith(('\n', ' ')) else "") + combined
        else:
            if curr_text:
                chunks.append(curr_text)
            curr_text = combined

    if curr_text:
        chunks.append(curr_text)

    # 進一步檢查是否有單句仍然超過 max_chunk_len（以逗號、分號次級切割）
    final_chunks = []
    for c in chunks:
        if len(c) > max_chunk_len:
            sub = re.split(r'([，,；;、])', c)
            temp = ""
            for j in range(0, len(sub), 2):
                part = sub[j] + (sub[j + 1] if j + 1 < len(sub) else "")
                if len(temp) + len(part) <= max_chunk_len:
                    temp += part
                else:
                    if temp:
                        final_chunks.append(temp.strip())
                    temp = part
            if temp:
                final_chunks.append(temp.strip())
        else:
            final_chunks.append(c.strip())

    return [{"index": idx, "text": ch, "char_count": len(ch)} for idx, ch in enumerate(final_chunks) if ch]


if __name__ == '__main__':
    pipe = TaigiTextPipeline(dialect='south')
    sample = "食飽未？逐家好！我今仔日去市場買魚。天氣真好，心情爽快。"
    print("原句:", sample)
    print("台羅本調:", pipe.g2p_raw(sample, 'Tailo'))
    print("台羅變調:", pipe.convert_to_sandhi_tailo(sample))
    print("POJ 變調 (for Meta MMS):", pipe.convert_to_sandhi_poj(sample))
    print("\n長句切分測試:")
    chunks = split_article_into_sentences(sample)
    for c in chunks:
        print(f"[{c['index']}] {c['text']}")
