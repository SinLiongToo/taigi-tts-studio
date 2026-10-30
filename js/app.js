// ==========================================================================
// Taigi TTS Studio - 核心應用腳本 (app.js)
// 支援 500+ 字長文朗讀、多模型切換、連讀變調前處理與互動式發音校正
// ==========================================================================

(() => {
  const el = id => document.getElementById(id);

  // DOM 元素快取
  const backendBadge = el('backendBadge');
  const backendStatusText = el('backendStatusText');
  const themeToggle = el('themeToggle');
  const helpBtn = el('helpBtn');
  const helpModal = el('helpModal');
  const helpCloseBtn = el('helpCloseBtn');
  const helpOkBtn = el('helpOkBtn');

  const modelSelect = el('modelSelect');
  const activeModelTag = el('activeModelTag');
  const modelHint = el('modelHint');
  const voiceGroup = el('voiceGroup');
  const voiceSelect = el('voiceSelect');
  const sandhiToggle = el('sandhiToggle');
  const sandhiText = el('sandhiText');
  const speedRange = el('speedRange');
  const speedValue = el('speedValue');
  const pauseRange = el('pauseRange');
  const pauseValue = el('pauseValue');

  const articleInput = el('articleInput');
  const charCounter = el('charCounter');
  const loadSampleBtn = el('loadSampleBtn');
  const clearTextBtn = el('clearTextBtn');

  const playBtn = el('playBtn');
  const pauseBtn = el('pauseBtn');
  const stopBtn = el('stopBtn');
  const downloadBtn = el('downloadBtn');
  const playerStatus = el('playerStatus');

  const progressContainer = el('progressContainer');
  const progressBarFill = el('progressBarFill');
  const currentTimeLabel = el('currentTimeLabel');
  const currentSentenceLabel = el('currentSentenceLabel');
  const totalTimeLabel = el('totalTimeLabel');

  const sentenceStudioList = el('sentenceStudioList');

  const dictStatusText = el('dictStatusText');
  const reloadDictBtn = el('reloadDictBtn');
  const customCountText = el('customCountText');
  const importCustomFile = el('importCustomFile');
  const exportCustomBtn = el('exportCustomBtn');
  const clearCustomBtn = el('clearCustomBtn');

  // Modal 元素
  const tokenModal = el('tokenModal');
  const modalCloseBtn = el('modalCloseBtn');
  const modalCancelBtn = el('modalCancelBtn');
  const modalSaveBtn = el('modalSaveBtn');
  const modalHanzi = el('modalHanzi');
  const modalCandidateList = el('modalCandidateList');
  const modalReadingInput = el('modalReadingInput');
  const modalSyllableTuner = el('modalSyllableTuner');
  const modalForceBaseTone = el('modalForceBaseTone');
  const modalSandhiPreview = el('modalSandhiPreview');
  const modalTestPlayBtn = el('modalTestPlayBtn');

  // 台語八聲調定義
  const TAIGI_TONES = [
    { tone: 1, name: '1聲', desc: '高平 55' },
    { tone: 2, name: '2聲', desc: '高降 51' },
    { tone: 3, name: '3聲', desc: '低降 31' },
    { tone: 4, name: '4聲', desc: '低入 32' },
    { tone: 5, name: '5聲', desc: '低升 24' },
    { tone: 7, name: '7聲', desc: '中平 33' },
    { tone: 8, name: '8聲', desc: '高入 4' }
  ];

  // 系統狀態
  let backendOnline = false;
  let backendBaseUrl = '';
  let availableModels = [];
  let parsedSentences = [];
  let activeTokenRef = null; // 當前在 Modal 中編輯的 Token
  let customOverrides = new Map(); // 使用者自訂發音快取: hanzi -> { reading, forceBase }

  // 播放器狀態
  let currentAudio = null;
  let isPlaying = false;
  let isPaused = false;
  let currentSentenceIndex = -1;
  let sentenceTimings = [];
  let currentAudioDataUrl = null;

  // 500+ 字台語精采範文 (662 字)
  const SAMPLE_ARTICLE = `台灣早市仔的滋味佮人情味

透早五點外，天猶未光，街仔路的早市仔就已經熱鬧滾滾。菜販推車入去巷仔口，魚販共透早對港口載來的現撈魚蝦一盤一盤排齊齊，頂頭猶含著碎冰，透出令儂心涼脾透開的鮮甜味。賣菜的歐巴桑用伊親切又大聲的喉嚨喝：「逐家緊來買喔！這粒高麗菜是梨山剛送下來的，脆閣甜，無買你會後悔！」

行入市仔內，第一吸引儂的就是彼股煎粿佮麵羹的香氣。轉角彼間開了四、五十年的米粉羹店，店頭的大鼎滾甲煙霧四界飛，空氣中散發著蝦米、香菇佮油蔥酥的古早味。頭家娘看著熟客行入來，就笑瞇瞇問：「阿明仔，今仔日猶原是老規矩，一碗炒米粉加一顆滷卵，閣加一碗豬血湯是無？」少年人點頭笑講：「無毋著，就是這味！一工若無食著，歸身軀攏無力！」

早市仔毋但是買菜買肉的所在，伊更加是庄頭鄰里情感交流的心臟。不管是七、八十歲的老大人，抑是牽著囡仔的後生爸母，逐家佇遮相拄，攏會停落來開講三幾句。「你今仔日的氣色真好喔！」「昨暝彼場雨落甲真大，田裡的菜毋知敢有拍損？」「恁孫仔今年考大學，讀佗一間學校？」逐句關心攏透出溫暖的人情。

市仔尾猶有一擔賣水果的，紅豔豔的王梨、金黃色的愛文檨仔，佮青翠的芭樂整整齊齊排佇案桌頂。頭家手攑著果刀，隨手削了一塊芭樂請路過的阿伯試食：「阿伯，先食一塊看覓，有甜才買，無甜免錢！」這款大方閣自在的待客之道，就是台灣上美、上純樸的人情風景。

行出市場，天已經大光，日頭金熾熾照佇滿載而歸的菜籃仔內。手中提著滿滿的菜蔬魚肉，心內嘛裝滿了溫暖。這个充滿活力的市仔，陪伴著逐一代台灣儂過日子，將土地的滋味佮人心的溫度，一代接一代傳承落去。`;

  // ========================================================================
  // 1. 初始化與主題
  // ========================================================================
  const THEME_KEY = 'taigi-tts-studio-theme';
  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.dataset.theme = saved;
    themeToggle.textContent = saved === 'dark' ? '☀️ 明亮' : '🌙 深色';
  }
  themeToggle.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem(THEME_KEY, next);
    themeToggle.textContent = next === 'dark' ? '☀️ 明亮' : '🌙 深色';
  });
  initTheme();

  // 說明彈窗
  helpBtn.addEventListener('click', () => { helpModal.hidden = false; });
  helpCloseBtn.addEventListener('click', () => { helpModal.hidden = true; });
  helpOkBtn.addEventListener('click', () => { helpModal.hidden = true; });

  // 點擊彈窗外部背景關閉
  helpModal.addEventListener('click', (e) => {
    if (e.target === helpModal) {
      helpModal.hidden = true;
    }
  });

  tokenModal.addEventListener('click', (e) => {
    if (e.target === tokenModal) {
      tokenModal.hidden = true;
    }
  });

  // 按下 ESC 鍵關閉所有彈窗
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      helpModal.hidden = true;
      tokenModal.hidden = true;
    }
  });

  // ========================================================================
  // 2. 後端伺服器檢測與模型載入
  // ========================================================================
  async function checkBackend() {
    backendStatusText.textContent = '連線檢測中...';
    try {
      const candidates = [
        window.location.origin,
        'http://localhost:8000',
        'http://127.0.0.1:8000'
      ];
      let ok = false;
      for (const base of candidates) {
        try {
          const res = await fetch(`${base}/api/models`, { method: 'GET' });
          if (res.ok) {
            const data = await res.json();
            backendBaseUrl = base;
            availableModels = data.models || [];
            ok = true;
            break;
          }
        } catch (e) {
          // continue checking
        }
      }

      if (ok) {
        backendOnline = true;
        backendBadge.className = 'backend-badge online';
        backendStatusText.textContent = '後端連線正常 (全模型解鎖)';
        updateModelUI();
      } else {
        throw new Error('No local server');
      }
    } catch (err) {
      backendOnline = false;
      backendBadge.className = 'backend-badge offline';
      backendStatusText.textContent = '本機純前端模式 (辭典錄音/WebSpeech)';
      updateModelUI();
    }
  }

  function updateModelUI() {
    const currentModel = modelSelect.value;
    if (currentModel === 'moe_concat') {
      activeModelTag.textContent = '教育部臺灣台語辭典 (真人原聲拼接，秒出聲推薦)';
      modelHint.textContent = '播放教育部辭典官方真人錄音檔，逐詞拼接，正港台語發音，零等待秒出聲！';
      voiceGroup.style.display = 'flex';
      voiceSelect.innerHTML = `<option value="moe" selected>教育部官方真人台語錄音</option>`;
    } else if (currentModel === 'mms') {
      activeModelTag.textContent = 'Meta MMS-TTS (正港台語 VITS 模型)';
      modelHint.textContent = 'Meta 官方台語端到端 VITS 模型。結合本系統連讀變調 POJ Pipeline，正港台語發音 (本機 CPU 運算約需數秒)。';
      voiceGroup.style.display = 'flex';
      voiceSelect.innerHTML = `<option value="default" selected>Meta MMS 台語講者 (facebook/mms-tts-nan)</option>`;
    } else if (currentModel === 'edge') {
      activeModelTag.textContent = 'Microsoft Edge-TTS (臺灣腔國語/華語混讀)';
      modelHint.textContent = '微軟神經語音（zh-TW-HsiaoChenNeural 為臺灣國語/華語腔調，非純台語發音）。';
      voiceGroup.style.display = 'flex';
      voiceSelect.innerHTML = `
        <option value="HsiaoChen" selected>曉臻 (HsiaoChen - 臺灣國語女聲)</option>
        <option value="YunJhe">雲哲 (YunJhe - 臺灣國語男聲)</option>
        <option value="HsiaoYu">曉雨 (HsiaoYu - 臺灣國語女聲)</option>
      `;
    } else if (currentModel === 'web_speech') {
      activeModelTag.textContent = 'Web Speech API (本機語音)';
      modelHint.textContent = '使用瀏覽器與本機作業系統內建語音引擎（通常為微軟 HanHan 國語）。';
      voiceGroup.style.display = 'none';
    }
  }

  modelSelect.addEventListener('change', updateModelUI);

  // 變調 Toggle 提示
  sandhiToggle.addEventListener('change', () => {
    sandhiText.textContent = sandhiToggle.checked
      ? '開啟 (套用五調循環與入聲變調)'
      : '關閉 (全部音節維持本調)';
    reAnalyzeText();
  });

  document.querySelectorAll('input[name="romanScheme"]').forEach(r => {
    r.addEventListener('change', () => reAnalyzeText());
  });

  function formatEdgeRate(val) {
    const percent = Math.round((parseFloat(val) - 1.0) * 100);
    return `${percent >= 0 ? '+' : ''}${percent}%`;
  }

  speedRange.addEventListener('input', () => {
    speedValue.textContent = `${parseFloat(speedRange.value).toFixed(2)}x`;
  });

  pauseRange.addEventListener('input', () => {
    pauseValue.textContent = `${pauseRange.value} ms`;
  });

  // ========================================================================
  // 3. 長文輸入與智慧分句引擎
  // ========================================================================
  function currentRomanScheme() {
    const checked = document.querySelector('input[name="romanScheme"]:checked');
    return checked ? checked.value : 'tailo';
  }

  function updateCharCount() {
    const text = articleInput.value.trim();
    const count = text.length;
    charCounter.textContent = `${count} 字 ${count >= 500 ? '✅ (已達 500+ 字長文標竿)' : '(目標 ≥ 500 字)'}`;
    if (count >= 500) {
      charCounter.classList.add('valid-500');
    } else {
      charCounter.classList.remove('valid-500');
    }
  }

  let debounceTimer = null;
  articleInput.addEventListener('input', () => {
    updateCharCount();
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      reAnalyzeText();
    }, 300);
  });

  loadSampleBtn.addEventListener('click', () => {
    articleInput.value = SAMPLE_ARTICLE;
    updateCharCount();
    reAnalyzeText();
  });

  clearTextBtn.addEventListener('click', () => {
    articleInput.value = '';
    updateCharCount();
    reAnalyzeText();
    stopAudio();
  });

  // ========================================================================
  // 4. 文本解析與逐句 Studio 渲染
  // ========================================================================
  function splitTextToSentences(text) {
    if (!text) return [];
    // 依句末標點與換行切分
    const rawChunks = text.split(/([。！？!?\n\r]+)/);
    const sentences = [];
    let current = '';

    for (let i = 0; i < rawChunks.length; i += 2) {
      const sentence = rawChunks[i];
      const punct = rawChunks[i + 1] || '';
      const combined = (sentence + punct).trim();
      if (!combined) continue;

      if (current.length + combined.length <= 100) {
        current += (current && !current.endsWith('\n') ? ' ' : '') + combined;
      } else {
        if (current) sentences.push(current);
        current = combined;
      }
    }
    if (current) sentences.push(current);
    return sentences;
  }

  function isHanChar(ch) {
    const cp = ch.codePointAt(0);
    return (cp >= 0x4e00 && cp <= 0x9fff) || (cp >= 0x3400 && cp <= 0x4dbf) ||
      (cp >= 0xf900 && cp <= 0xfaff) || (cp >= 0x20000 && cp <= 0x2ffff);
  }

  function segmentSentence(sentenceText) {
    const chars = Array.from(sentenceText);
    const tokens = [];
    const maxLen = typeof Dict !== 'undefined' ? Math.max(1, Dict.getMaxWordLen()) : 4;
    let i = 0;

    while (i < chars.length) {
      let matched = null;
      let matchLen = 0;
      const upper = Math.min(maxLen, chars.length - i);

      // 先查使用者自訂詞庫快取
      for (let len = upper; len >= 1; len--) {
        const candidate = chars.slice(i, i + len).join('');
        if (customOverrides.has(candidate)) {
          matched = {
            hanzi: candidate,
            custom: true,
            override: customOverrides.get(candidate)
          };
          matchLen = len;
          break;
        }
      }

      // 查官方教育部辭典
      if (!matched && typeof Dict !== 'undefined' && Dict.isLoaded()) {
        for (let len = upper; len >= 1; len--) {
          const candidate = chars.slice(i, i + len).join('');
          const entries = Dict.lookupWord(candidate);
          if (entries && entries.length) {
            matched = { hanzi: candidate, entries, choice: 0 };
            matchLen = len;
            break;
          }
        }
      }

      if (matched) {
        tokens.push({
          type: 'word',
          hanzi: matched.hanzi,
          entries: matched.entries || [],
          choice: matched.choice || 0,
          custom: !!matched.custom,
          override: matched.override || null
        });
        i += matchLen;
      } else if (isHanChar(chars[i])) {
        // 未收錄漢字
        tokens.push({
          type: 'word',
          hanzi: chars[i],
          entries: [],
          choice: 0,
          unlisted: true
        });
        i += 1;
      } else {
        tokens.push({
          type: 'literal',
          text: chars[i]
        });
        i += 1;
      }
    }

    return tokens;
  }

  function resolveTokenReading(token) {
    if (token.override && token.override.reading) {
      return token.override.reading;
    }
    if (token.entries && token.entries.length > 0) {
      const entry = token.entries[token.choice || 0];
      return entry.reading || entry.trs || '';
    }
    return '';
  }

  async function reAnalyzeText() {
    const text = articleInput.value.trim();
    if (!text) {
      sentenceStudioList.innerHTML = '<div class="empty-state">請在上方輸入台語文章或點擊「載入 500+ 字範文」開始解析。</div>';
      parsedSentences = [];
      return;
    }

    // 優先使用後端強大 G2P 斷詞與變調引擎 (解決辭典載入延遲與單字 ? 問題)
    if (backendOnline) {
      try {
        const res = await fetch(`${backendBaseUrl}/api/g2p/parse`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: text })
        });
        if (res.ok) {
          const data = await res.json();
          renderSentencesFromBackend(data.sentences);
          return;
        }
      } catch (err) {
        console.warn('後端 G2P 請求失敗，退回前端解析:', err);
      }
    }

    // 前端辭典模式 (純靜態備援)
    renderSentencesFromFrontend(text);
  }

  function renderSentencesFromBackend(sentences) {
    sentenceStudioList.innerHTML = '';
    parsedSentences = [];
    const scheme = currentRomanScheme();

    sentences.forEach((sItem, sIdx) => {
      const sentenceRecord = {
        index: sIdx,
        text: sItem.text,
        tokens: sItem.tokens || [],
        element: null
      };
      parsedSentences.push(sentenceRecord);

      const card = document.createElement('div');
      card.className = 'sentence-card';
      card.id = `sentence-card-${sIdx}`;

      const meta = document.createElement('div');
      meta.className = 'sentence-meta';
      meta.innerHTML = `
        <span><b>第 ${sIdx + 1} 句</b> (${sItem.char_count} 字)</span>
        <div class="sentence-actions">
          <button class="btn btn-sm btn-outline play-single-btn" data-index="${sIdx}">🔊 試聽此句</button>
        </div>
      `;
      card.appendChild(meta);

      const tokenBox = document.createElement('div');
      tokenBox.className = 'token-container';

      (sItem.tokens || []).forEach((t, tIdx) => {
        if (t.type === 'literal') {
          const lit = document.createElement('span');
          lit.className = 'literal-token';
          lit.textContent = t.text;
          tokenBox.appendChild(lit);
        } else {
          const chip = document.createElement('div');
          chip.className = 'token-chip';
          chip.id = `token-${sIdx}-${tIdx}`;
          t.chipElement = chip;

          // 檢查使用者自訂覆蓋
          const override = customOverrides.get(t.hanzi);
          if (override) {
            chip.classList.add('customized');
          }

          let displayRoman = scheme === 'poj' ? t.poj_base : t.tailo_base;
          let sandhiRoman = scheme === 'poj' ? t.poj_sandhi : t.tailo_sandhi;

          if (override && override.reading) {
            displayRoman = override.reading;
            sandhiRoman = override.reading;
          }

          const hasSandhi = sandhiToggle.checked && (displayRoman !== sandhiRoman) && (!override || !override.forceBase);
          chip.classList.add(hasSandhi ? 'sandhi' : 'base');

          chip.innerHTML = `
            <span class="token-roman">${displayRoman || t.hanzi}</span>
            <span class="token-hanzi">${t.hanzi}</span>
            ${hasSandhi ? `<span class="token-sandhi-hint">變: ${sandhiRoman}</span>` : ''}
          `;

          chip.addEventListener('click', () => {
            openTokenModal({
              hanzi: t.hanzi,
              entries: [{ reading: displayRoman }],
              audio_url: t.audio_url,
              override: override,
              choice: 0
            }, sIdx, tIdx);
          });

          tokenBox.appendChild(chip);
        }
      });

      card.appendChild(tokenBox);
      sentenceStudioList.appendChild(card);
      sentenceRecord.element = card;
    });

    bindPlaySingleButtons();
  }

  function renderSentencesFromFrontend(text) {
    const rawSentences = splitTextToSentences(text);
    parsedSentences = [];
    sentenceStudioList.innerHTML = '';

    rawSentences.forEach((sText, sIdx) => {
      const tokens = segmentSentence(sText);
      const sentenceItem = {
        index: sIdx,
        text: sText,
        tokens: tokens,
        element: null
      };
      parsedSentences.push(sentenceItem);

      const card = document.createElement('div');
      card.className = 'sentence-card';
      card.id = `sentence-card-${sIdx}`;

      const meta = document.createElement('div');
      meta.className = 'sentence-meta';
      meta.innerHTML = `
        <span><b>第 ${sIdx + 1} 句</b> (${sText.length} 字)</span>
        <div class="sentence-actions">
          <button class="btn btn-sm btn-outline play-single-btn" data-index="${sIdx}">🔊 試聽此句</button>
        </div>
      `;
      card.appendChild(meta);

      const tokenBox = document.createElement('div');
      tokenBox.className = 'token-container';

      tokens.forEach((t, tIdx) => {
        if (t.type === 'literal') {
          const lit = document.createElement('span');
          lit.className = 'literal-token';
          lit.textContent = t.text;
          tokenBox.appendChild(lit);
        } else {
          const chip = document.createElement('div');
          chip.className = 'token-chip';
          if (t.custom) chip.classList.add('customized');
          if (t.unlisted) chip.classList.add('unlisted');

          const rawReading = resolveTokenReading(t);
          let parsedSylls = Romanize.parseWord(rawReading);

          let displayRoman = rawReading;
          let sandhiRoman = rawReading;
          let hasSandhi = false;

          if (parsedSylls && parsedSylls.length > 0) {
            const scheme = currentRomanScheme();
            const formatFn = scheme === 'poj' ? Romanize.toPojMark : Romanize.toTailoMark;

            displayRoman = Romanize.joinSylls(parsedSylls, p => formatFn(p.skeleton, p.tone));

            const forceBase = t.override && t.override.forceBase;
            if (sandhiToggle.checked && !forceBase && parsedSylls.length > 1) {
              const sandhiSylls = parsedSylls.map((s, idx) => {
                if (idx === parsedSylls.length - 1 || s.neutral) return s;
                return Romanize.sandhiTone(s.skeleton, s.tone);
              });
              sandhiRoman = Romanize.joinSylls(sandhiSylls, p => formatFn(p.skeleton, p.tone));
              hasSandhi = (sandhiRoman !== displayRoman);
            }
          }

          chip.classList.add(hasSandhi ? 'sandhi' : 'base');

          chip.innerHTML = `
            <span class="token-roman">${displayRoman || t.hanzi}</span>
            <span class="token-hanzi">${t.hanzi}</span>
            ${hasSandhi ? `<span class="token-sandhi-hint">變: ${sandhiRoman}</span>` : ''}
          `;

          chip.addEventListener('click', () => {
            openTokenModal(t, sIdx, tIdx);
          });

          tokenBox.appendChild(chip);
        }
      });

      card.appendChild(tokenBox);
      sentenceStudioList.appendChild(card);
      sentenceItem.element = card;
    });

    bindPlaySingleButtons();
  }

  function bindPlaySingleButtons() {
    document.querySelectorAll('.play-single-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(e.target.dataset.index, 10);
        playSingleSentence(idx);
      });
    });
  }

  // ========================================================================
  // 5. 互動式發音與聲調微調彈窗 (Token & Tone Tuner Modal)
  // ========================================================================
  let currentModalSyllables = []; // 當前編輯詞彙的音節物件清單

  function openTokenModal(token, sIdx, tIdx) {
    activeTokenRef = { token, sIdx, tIdx };
    modalHanzi.textContent = token.hanzi;

    const currentReading = resolveTokenReading(token);
    modalReadingInput.value = currentReading;
    modalForceBaseTone.checked = !!(token.override && token.override.forceBase);

    // 渲染候選讀音 (官方辭典破音字)
    modalCandidateList.innerHTML = '';
    const entries = token.entries || [];
    if (entries.length > 1) {
      entries.forEach((ent, i) => {
        const pill = document.createElement('button');
        pill.className = `candidate-pill ${i === (token.choice || 0) ? 'active' : ''}`;
        pill.textContent = ent.reading || ent.trs || `讀音 ${i + 1}`;
        pill.addEventListener('click', () => {
          modalReadingInput.value = ent.reading || ent.trs;
          renderSyllableTuner();
          updateModalSandhiPreview();
        });
        modalCandidateList.appendChild(pill);
      });
    } else {
      modalCandidateList.innerHTML = '<span class="field-hint">官方辭典僅收錄單一讀音，您可直接在下方調校盤修改聲調。</span>';
    }

    renderSyllableTuner();
    updateModalSandhiPreview();
    tokenModal.hidden = false;
  }

  // 渲染逐音節 1~8 聲調微調盤
  function renderSyllableTuner() {
    modalSyllableTuner.innerHTML = '';
    const raw = modalReadingInput.value.trim();
    if (!raw) {
      modalSyllableTuner.innerHTML = '<div class="field-hint">請先輸入拼音以載入聲調控制盤。</div>';
      return;
    }

    const sylls = Romanize.parseWord(raw);
    if (!sylls || !sylls.length) {
      modalSyllableTuner.innerHTML = '<div class="field-hint">無法解析此拼音的音節結構。</div>';
      return;
    }

    currentModalSyllables = sylls;
    const scheme = currentRomanScheme();

    sylls.forEach((s, sIndex) => {
      const row = document.createElement('div');
      row.className = 'syllable-row';

      const header = document.createElement('div');
      header.className = 'syllable-header';
      const formattedSyll = scheme === 'poj'
        ? Romanize.toPojMark(s.skeleton, s.tone)
        : Romanize.toTailoMark(s.skeleton, s.tone);

      header.innerHTML = `
        <span>第 ${sIndex + 1} 字音節：<b class="syllable-name">${formattedSyll}</b> (骨架: ${s.skeleton})</span>
        <span class="field-hint">當前聲調: 第 ${s.tone} 聲</span>
      `;
      row.appendChild(header);

      const grid = document.createElement('div');
      grid.className = 'tone-buttons-grid';

      TAIGI_TONES.forEach(tDef => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `btn-tone ${s.tone === tDef.tone ? 'active' : ''}`;
        btn.innerHTML = `
          <span class="tone-num">${tDef.tone}</span>
          <span class="tone-desc">${tDef.desc}</span>
        `;

        btn.addEventListener('click', () => {
          // 修改該音節的聲調
          s.tone = tDef.tone;
          // 重組完整詞彙讀音字串
          const newWord = Romanize.joinSylls(sylls, p =>
            scheme === 'poj' ? Romanize.toPojMark(p.skeleton, p.tone) : Romanize.toTailoMark(p.skeleton, p.tone)
          );
          modalReadingInput.value = newWord;
          renderSyllableTuner();
          updateModalSandhiPreview();
        });

        grid.appendChild(btn);
      });

      row.appendChild(grid);
      modalSyllableTuner.appendChild(row);
    });
  }

  function updateModalSandhiPreview() {
    const raw = modalReadingInput.value.trim();
    if (!raw) {
      modalSandhiPreview.textContent = '（請輸入音標）';
      return;
    }
    const sylls = Romanize.parseWord(raw);
    if (!sylls) {
      modalSandhiPreview.textContent = '無法識別的拼音格式';
      return;
    }
    const scheme = currentRomanScheme();
    const formatFn = scheme === 'poj' ? Romanize.toPojMark : Romanize.toTailoMark;
    if (modalForceBaseTone.checked || sylls.length <= 1) {
      modalSandhiPreview.textContent = Romanize.joinSylls(sylls, p => formatFn(p.skeleton, p.tone)) + ' (鎖定指定聲調，不變調)';
    } else {
      const sandhi = sylls.map((s, idx) => {
        if (idx === sylls.length - 1 || s.neutral) return s;
        return Romanize.sandhiTone(s.skeleton, s.tone);
      });
      modalSandhiPreview.textContent = Romanize.joinSylls(sandhi, p => formatFn(p.skeleton, p.tone)) + ' (連讀發音)';
    }
  }

  modalReadingInput.addEventListener('input', () => {
    renderSyllableTuner();
    updateModalSandhiPreview();
  });
  modalForceBaseTone.addEventListener('change', updateModalSandhiPreview);

  modalCloseBtn.addEventListener('click', () => { tokenModal.hidden = true; });
  modalCancelBtn.addEventListener('click', () => { tokenModal.hidden = true; });

  modalSaveBtn.addEventListener('click', async () => {
    if (!activeTokenRef) return;
    const { token } = activeTokenRef;
    const reading = modalReadingInput.value.trim();
    const forceBase = modalForceBaseTone.checked;

    const override = { reading, forceBase };
    token.override = override;
    token.custom = true;
    customOverrides.set(token.hanzi, override);

    // 儲存至 IndexedDB
    if (typeof Dict !== 'undefined' && Dict.saveCustomEntry) {
      await Dict.saveCustomEntry(token.hanzi, reading);
    }
    updateCustomCount();

    tokenModal.hidden = true;
    reAnalyzeText();
  });

  modalTestPlayBtn.addEventListener('click', () => {
    const reading = modalReadingInput.value.trim();
    if (!reading) return;
    const hanzi = activeTokenRef ? activeTokenRef.token.hanzi : '';

    // 若有後端連線，直接將修改後的拼音送入 MMS-TTS 合成出精確的指定聲調！
    if (backendOnline) {
      playerStatus.textContent = '🔊 正在試聽您調整後的聲調唸法...';
      fetch(`${backendBaseUrl}/api/tts/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: reading,
          model: 'mms',
          apply_sandhi: !modalForceBaseTone.checked
        })
      }).then(res => {
        if (!res.ok) throw new Error('合成失敗');
        return res.blob();
      }).then(blob => {
        const a = new Audio(URL.createObjectURL(blob));
        a.play().catch(e => console.warn(e));
      }).catch(() => {
        const directUrl = activeTokenRef && activeTokenRef.token ? activeTokenRef.token.audio_url : null;
        playSingleWord(reading, hanzi, directUrl);
      });
    } else {
      const directUrl = activeTokenRef && activeTokenRef.token ? activeTokenRef.token.audio_url : null;
      playSingleWord(reading, hanzi, directUrl);
    }
  });

  // ========================================================================
  // 6. 語音合成與長文連續播放控制 (Player Core)
  // ========================================================================
  async function playSingleSentence(sIdx) {
    if (sIdx < 0 || sIdx >= parsedSentences.length) return;
    const item = parsedSentences[sIdx];
    highlightSentence(sIdx);

    try {
      if (modelSelect.value === 'moe_concat') {
        playerStatus.textContent = `🔊 正在播放教育部真人台語原聲 (第 ${sIdx + 1} 句)...`;
        await playSentenceViaMoeAudio(sIdx);
        playerStatus.textContent = '試聽結束';
      } else if (backendOnline && (modelSelect.value === 'edge' || modelSelect.value === 'mms')) {
        playerStatus.textContent = `正在試聽第 ${sIdx + 1} 句 (${modelSelect.value === 'mms' ? 'Meta MMS 台語' : 'Edge-TTS'})...`;
        await playViaBackend(item.text, sIdx);
      } else {
        await playViaFrontend(item.text, sIdx);
      }
    } catch (e) {
      console.error(e);
      playerStatus.textContent = `播放失敗: ${e.message}`;
    }
  }

  async function playFullArticle() {
    const text = articleInput.value.trim();
    if (!text) {
      alert('請先輸入台語文章內容！');
      return;
    }

    stopAudio();
    isPlaying = true;
    isPaused = false;
    updatePlayerButtons();

    const model = modelSelect.value;

    // 1. 優先推薦：教育部辭典真人台語錄音 (0 延遲瞬間出聲)
    if (model === 'moe_concat') {
      playerStatus.textContent = '🔊 正在啟動教育部真人台語原聲連續朗讀 (0 秒出聲)...';
      playSentencesSequentially(0);
      return;
    }

    // 2. Meta MMS-TTS：採用逐句串流極速朗讀 (算完第一句立刻播，避免長篇等待)
    if (model === 'mms') {
      playerStatus.textContent = '🔬 Meta MMS 台語神經模型：啟動逐句串流朗讀 (即將出聲)...';
      playSentencesSequentially(0);
      return;
    }

    // 3. Microsoft Edge-TTS (雲端並行極速合成，1.5 秒即出聲)
    try {
      if (backendOnline && model === 'edge') {
        playerStatus.textContent = '⚡ 正在進行 Edge-TTS 極速並行合成 (約 1~2 秒)...';

        const res = await fetch(`${backendBaseUrl}/api/tts/synthesize_json`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: text,
            model: model,
            voice: voiceSelect.value,
            rate: formatEdgeRate(speedRange.value),
            apply_sandhi: sandhiToggle.checked,
            pause_ms: parseInt(pauseRange.value, 10)
          })
        });

        if (!res.ok) {
          throw new Error(`伺服器回應錯誤: ${res.statusText}`);
        }

        const data = await res.json();
        sentenceTimings = data.sentence_timings || [];
        currentAudioDataUrl = data.audio_data_url;

        startAudioPlayback(data.audio_data_url, sentenceTimings);

      } else {
        // 純前端模式：逐句連續播放
        playerStatus.textContent = '啟動逐句連續朗讀...';
        playSentencesSequentially(0);
      }
    } catch (err) {
      console.error(err);
      playerStatus.textContent = `合成出錯: ${err.message}`;
      stopAudio();
    }
  }

  function startAudioPlayback(dataUrl, timings) {
    if (currentAudio) {
      currentAudio.pause();
    }

    currentAudio = new Audio(dataUrl);
    currentAudio.playbackRate = parseFloat(speedRange.value);

    currentAudio.addEventListener('loadedmetadata', () => {
      totalTimeLabel.textContent = formatTime(currentAudio.duration);
    });

    currentAudio.addEventListener('timeupdate', () => {
      if (!currentAudio) return;
      const current = currentAudio.currentTime;
      const total = currentAudio.duration || 1;
      const pct = (current / total) * 100;
      progressBarFill.style.width = `${pct}%`;
      currentTimeLabel.textContent = formatTime(current);

      const currentMs = current * 1000;
      let matchedIdx = -1;
      for (let i = 0; i < timings.length; i++) {
        if (currentMs >= timings[i].start_ms && currentMs <= timings[i].end_ms + 200) {
          matchedIdx = i;
          break;
        }
      }
      if (matchedIdx !== -1 && matchedIdx !== currentSentenceIndex) {
        highlightSentence(matchedIdx);
        currentSentenceLabel.textContent = `第 ${matchedIdx + 1} / ${timings.length} 句`;
      }
    });

    currentAudio.addEventListener('ended', () => {
      playerStatus.textContent = '長文朗讀完畢！';
      stopAudio();
    });

    currentAudio.play().catch(e => console.warn('Play error:', e));
    playerStatus.textContent = '正在朗讀全文...';
  }

  async function playSentencesSequentially(idx) {
    if (!isPlaying) return;
    if (idx >= parsedSentences.length) {
      playerStatus.textContent = '全文朗讀完畢！';
      stopAudio();
      return;
    }

    highlightSentence(idx);
    currentSentenceLabel.textContent = `第 ${idx + 1} / ${parsedSentences.length} 句`;
    progressBarFill.style.width = `${((idx + 1) / parsedSentences.length) * 100}%`;
    const item = parsedSentences[idx];

    try {
      if (modelSelect.value === 'moe_concat') {
        playerStatus.textContent = `🔊 正在播放教育部真人原聲 (第 ${idx + 1} / ${parsedSentences.length} 句)...`;
        await playSentenceViaMoeAudio(idx);
      } else if (modelSelect.value === 'mms') {
        playerStatus.textContent = `🔬 正在朗讀第 ${idx + 1} / ${parsedSentences.length} 句 (Meta MMS 台語)...`;
        await playViaBackend(item.text, idx);
      } else {
        await playViaFrontend(item.text, idx);
      }
      const pause = parseInt(pauseRange.value, 10);
      setTimeout(() => {
        if (isPlaying) {
          playSentencesSequentially(idx + 1);
        }
      }, pause);
    } catch (e) {
      console.warn(e);
      playSentencesSequentially(idx + 1);
    }
  }

  function playViaBackend(text, sIdx) {
    return new Promise(async (resolve, reject) => {
      try {
        const model = modelSelect.value;
        const res = await fetch(`${backendBaseUrl}/api/tts/synthesize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: text,
            model: model,
            voice: voiceSelect.value,
            rate: formatEdgeRate(speedRange.value),
            apply_sandhi: sandhiToggle.checked,
            pause_ms: 100
          })
        });
        if (!res.ok) throw new Error('伺服器錯誤');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.playbackRate = parseFloat(speedRange.value);
        audio.onended = () => {
          playerStatus.textContent = '試聽結束';
          resolve();
        };
        audio.onerror = reject;
        audio.play();
      } catch (err) {
        reject(err);
      }
    });
  }

  // 播放單詞發音 (優先使用教育部官方真人錄音)
  function playSingleWord(reading, hanzi, directAudioUrl) {
    if (directAudioUrl) {
      const a = new Audio(directAudioUrl);
      a.playbackRate = parseFloat(speedRange.value);
      a.play().catch(e => console.warn('Audio play failed:', e));
      return;
    }
    if (typeof Dict !== 'undefined' && Dict.isLoaded()) {
      const entries = Dict.lookupWord(hanzi);
      if (entries && entries.length) {
        const url = Dict.resolveAudioUrl(entries[0]);
        if (url) {
          const a = new Audio(url);
          a.playbackRate = parseFloat(speedRange.value);
          a.play().catch(e => console.warn('Audio play failed:', e));
          return;
        }
      }
    }
    // 後端 MMS 試聽單詞 (純台語)
    if (backendOnline) {
      fetch(`${backendBaseUrl}/api/tts/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: hanzi || reading,
          model: 'mms',
          apply_sandhi: true
        })
      }).then(res => {
        if (!res.ok) throw new Error('合成失敗');
        return res.blob();
      }).then(blob => {
        const a = new Audio(URL.createObjectURL(blob));
        a.play().catch(e => console.warn(e));
      }).catch(e => console.warn(e));
    }
  }

  // 依序播放音訊陣列 (Promise 串接)
  function playAudioUrl(url, rate = 1.0) {
    return new Promise((resolve) => {
      if (!url) return resolve();
      const a = new Audio(url);
      a.playbackRate = rate;
      a.onended = resolve;
      a.onerror = () => {
        console.warn('音檔載入失敗:', url);
        resolve();
      };
      a.play().catch((err) => {
        console.warn('播放被瀏覽器限制或失敗:', err);
        resolve();
      });
    });
  }

  // 教育部辭典真人錄音：整句依序朗讀各詞 (帶有醒目的念到哪裡高亮跟隨指示)
  async function playSentenceViaMoeAudio(sIdx) {
    if (sIdx < 0 || sIdx >= parsedSentences.length) return;
    const sItem = parsedSentences[sIdx];
    const tokens = sItem.tokens || [];
    const rate = parseFloat(speedRange.value);

    for (let t of tokens) {
      if (!isPlaying && !isPaused) break;
      if (t.type !== 'word') continue;

      // 🌟 念到哪裡的高亮跟隨指示 (Speaking Indicator)
      document.querySelectorAll('.token-chip').forEach(c => c.classList.remove('speaking-now'));
      if (t.chipElement) {
        t.chipElement.classList.add('speaking-now');
        t.chipElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }

      let audioUrl = t.audio_url;
      // 若詞塊無整詞音檔，嘗試逐字備援音檔
      if (!audioUrl && t.fallback_audios && t.fallback_audios.length) {
        for (let subUrl of t.fallback_audios) {
          if (!isPlaying && !isPaused) break;
          await playAudioUrl(subUrl, rate);
        }
      } else if (audioUrl) {
        await playAudioUrl(audioUrl, rate);
      } else {
        await new Promise(r => setTimeout(r, 220));
      }

      if (t.chipElement) {
        t.chipElement.classList.remove('speaking-now');
      }
    }
    document.querySelectorAll('.token-chip').forEach(c => c.classList.remove('speaking-now'));
  }

  function playViaFrontend(text, sIdx) {
    return new Promise(async (resolve) => {
      if (modelSelect.value === 'moe_concat') {
        // 教育部真人原聲拼接
        await playSentenceViaMoeAudio(sIdx);
        resolve();
      } else if (modelSelect.value === 'web_speech' && 'speechSynthesis' in window) {
        const utter = new SpeechSynthesisUtterance(text);
        utter.rate = parseFloat(speedRange.value);
        utter.onend = resolve;
        utter.onerror = resolve;
        speechSynthesis.speak(utter);
      } else {
        setTimeout(resolve, 800);
      }
    });
  }

  function highlightSentence(sIdx) {
    currentSentenceIndex = sIdx;
    document.querySelectorAll('.sentence-card').forEach((c, i) => {
      if (i === sIdx) {
        c.classList.add('active-reading');
        c.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } else {
        c.classList.remove('active-reading');
      }
    });
  }

  function stopAudio() {
    isPlaying = false;
    isPaused = false;
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      currentAudio = null;
    }
    if ('speechSynthesis' in window) {
      speechSynthesis.cancel();
    }
    progressBarFill.style.width = '0%';
    currentTimeLabel.textContent = '00:00';
    currentSentenceLabel.textContent = '已停止';
    document.querySelectorAll('.sentence-card').forEach(c => c.classList.remove('active-reading'));
    updatePlayerButtons();
  }

  function updatePlayerButtons() {
    playBtn.disabled = isPlaying && !isPaused;
    pauseBtn.disabled = !isPlaying;
    stopBtn.disabled = !isPlaying && !isPaused;
  }

  playBtn.addEventListener('click', playFullArticle);

  pauseBtn.addEventListener('click', () => {
    if (currentAudio && !currentAudio.paused) {
      currentAudio.pause();
      isPaused = true;
      pauseBtn.innerHTML = '<span class="icon">▶</span> 繼續';
      playerStatus.textContent = '已暫停';
    } else if (currentAudio && currentAudio.paused) {
      currentAudio.play();
      isPaused = false;
      pauseBtn.innerHTML = '<span class="icon">⏸</span> 暫停';
      playerStatus.textContent = '繼續朗讀...';
    }
  });

  stopBtn.addEventListener('click', stopAudio);

  downloadBtn.addEventListener('click', async () => {
    const text = articleInput.value.trim();
    if (!text) {
      alert('請先輸入欲合成下載的文章！');
      return;
    }
    playerStatus.textContent = '正在合成並準備下載全篇音檔...';
    try {
      if (backendOnline) {
        const model = modelSelect.value;
        const res = await fetch(`${backendBaseUrl}/api/tts/synthesize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: text,
            model: model,
            voice: voiceSelect.value,
            rate: formatEdgeRate(speedRange.value),
            apply_sandhi: sandhiToggle.checked,
            pause_ms: parseInt(pauseRange.value, 10)
          })
        });
        if (!res.ok) throw new Error('下載合成失敗');
        const blob = await res.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `taigi_${model}_article_${Date.now()}.${model === 'mms' ? 'wav' : 'mp3'}`;
        a.click();
        playerStatus.textContent = '音檔下載完成！';
      } else {
        alert('純前端模式目前僅支援本機播放。請啟動 Python 後端伺服器 (python server.py) 即可匯出高品質 MP3/WAV 音檔！');
      }
    } catch (e) {
      alert('下載失敗: ' + e.message);
    }
  });

  // ========================================================================
  // 7. 自訂詞庫與辭典快取管理
  // ========================================================================
  function updateCustomCount() {
    customCountText.textContent = `已存 ${customOverrides.size} 筆校正`;
  }

  exportCustomBtn.addEventListener('click', () => {
    const data = Object.fromEntries(customOverrides);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `taigi_custom_pronunciations_${Date.now()}.json`;
    a.click();
  });

  clearCustomBtn.addEventListener('click', () => {
    if (confirm('確定要清除所有自訂發音校正紀錄嗎？')) {
      customOverrides.clear();
      updateCustomCount();
      reAnalyzeText();
    }
  });

  function formatTime(sec) {
    if (!sec || isNaN(sec)) return '00:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  // ========================================================================
  // 8. 系統載入與辭典初始化
  // ========================================================================
  async function init() {
    await checkBackend();

    // 載入辭典狀態
    if (typeof Dict !== 'undefined') {
      dictStatusText.textContent = '載入教育部辭典中...';
      try {
        await Dict.init();
        dictStatusText.textContent = '教育部辭典快取就緒 (約 4 萬筆)';
        // 辭典快取載入完成後，自動重新解析一次，補全離線狀態下的發音
        if (!backendOnline) {
          reAnalyzeText();
        }
      } catch (e) {
        dictStatusText.textContent = '辭典連線中 (將使用線上備援)';
      }
    } else {
      dictStatusText.textContent = '辭典模組獨立運行';
    }

    // 預設載入範文
    loadSampleBtn.click();
  }

  init();
})();
