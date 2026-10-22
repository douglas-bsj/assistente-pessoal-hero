/* J.A.R.V.I.S. — interface de voz em tempo real */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const ui = {
    reactor: $("reactor"), stateLabel: $("stateLabel"), stateHint: $("stateHint"),
    caption: $("liveCaption"), chatLog: $("chatLog"), micBtn: $("micBtn"),
    promptForm: $("promptForm"), promptInput: $("promptInput"),
    handsFree: $("handsFree"), voiceOut: $("voiceOut"), resetBtn: $("resetBtn"),
    memForm: $("memForm"), memInput: $("memInput"), memSearch: $("memSearch"),
    memList: $("memList"), memCount: $("memCount"), toast: $("toast"), clock: $("clock"),
    brandTitle: $("brandTitle"), brandSub: $("brandSub"), protocolSelector: $("protocolSelector"),
  };

  const STATES = {
    connecting:   { label: "Conectando",   hint: "Estabelecendo link com o núcleo...", color: [120, 140, 160] },
    idle:         { label: "Online",       hint: "Segure Espaço ou o microfone para falar", color: [30, 220, 255] },
    listening:    { label: "Ouvindo",      hint: "Pode falar, senhor", color: [255, 70, 95] },
    transcribing: { label: "Processando",  hint: "Convertendo sua voz em texto", color: [255, 190, 60] },
    thinking:     { label: "Analisando",   hint: "Consultando memórias e raciocinando", color: [175, 120, 255] },
    speaking:     { label: "Respondendo",  hint: "Fale para interromper (mãos-livres) ou Esc", color: [40, 235, 255] },
  };

  // ------------------------------------------------------------------ estado
  let state = "connecting";
  let serverState = "idle";
  let ws = null;
  let wsQueue = [];
  let latestTurn = 0;
  const cancelledTurns = new Set();
  let currentJarvisMsg = null;
  let currentTurnMemories = [];
  let memories = [];
  let activeAgentId = "jarvis";
  let activeAgentName = "J.A.R.V.I.S.";

  // áudio
  let audioCtx = null, outAnalyser = null, micAnalyser = null, micStream = null;
  let recorder = null, recChunks = [], recStartedAt = 0;
  const playQueue = [];
  let playing = null;
  let pttActive = false;

  // ------------------------------------------------------------------ utilidades
  function setState(next) {
    state = next;
    const s = STATES[next] || STATES.idle;
    ui.stateLabel.textContent = s.label;
    ui.stateHint.textContent = s.hint;
  }

  function refreshState() {
    if (recorder && recorder.state === "recording") return setState("listening");
    if (playing || playQueue.length) return setState("speaking");
    if (!ws || ws.readyState !== WebSocket.OPEN) return setState("connecting");
    setState(serverState === "idle" ? "idle" : serverState);
  }

  let toastTimer;
  function toast(text, isError = false) {
    ui.toast.textContent = text;
    ui.toast.classList.toggle("err", isError);
    ui.toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => ui.toast.classList.remove("show"), 3800);
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function tickClock() {
    const d = new Date();
    ui.clock.textContent = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }
  setInterval(tickClock, 1000); tickClock();

  // ------------------------------------------------------------------ WebSocket
  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.binaryType = "arraybuffer";
    setState("connecting");

    ws.onopen = () => {
      cancelledTurns.clear();
      latestTurn = 0;
      wsQueue.splice(0).forEach((m) => ws.send(m));
      refreshState();
    };
    ws.onclose = () => {
      setState("connecting");
      setTimeout(connect, 1500);
    };
    ws.onmessage = (ev) => {
      if (typeof ev.data === "string") handleEvent(JSON.parse(ev.data));
      else handleAudio(ev.data);
    };
  }

  function send(payload) {
    const data = payload instanceof ArrayBuffer || payload instanceof Blob ? payload : JSON.stringify(payload);
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(data);
    else wsQueue.push(data);
  }

  function handleEvent(ev) {
    if (ev.turn) latestTurn = Math.max(latestTurn, ev.turn);
    switch (ev.type) {
      case "state":
        if (ev.turn && cancelledTurns.has(ev.turn) && ev.state !== "idle") return;
        serverState = ev.state;
        refreshState();
        break;
      case "user":
        addMessage("user", ev.text);
        ui.caption.innerHTML = `<em>Você:</em> ${escapeHtml(ev.text)}`;
        currentJarvisMsg = null;
        currentTurnMemories = [];
        break;
      case "agent":
        activeAgentId = ev.agent;
        activeAgentName = ev.name || "J.A.R.V.I.S.";
        if (ui.brandTitle) ui.brandTitle.textContent = activeAgentName;
        if (ui.brandSub) ui.brandSub.textContent = ev.role || "Protocolo Stark Ativo";
        if (ev.color && Array.isArray(ev.color)) {
          color = ev.color;
        }
        document.querySelectorAll(".proto-btn").forEach((b) => {
          b.classList.toggle("active", b.dataset.agent === ev.agent);
        });
        toast(`Protocolo ativado: ${activeAgentName}`);
        break;
      case "memories":
        currentTurnMemories = ev.items || [];
        break;
      case "token":
        if (cancelledTurns.has(ev.turn)) return;
        if (!currentJarvisMsg) currentJarvisMsg = addMessage("jarvis", "", true);
        currentJarvisMsg.text += ev.text;
        currentJarvisMsg.bubble.textContent = currentJarvisMsg.text;
        ui.caption.textContent = currentJarvisMsg.text;
        scrollChat();
        break;
      case "assistant_end":
        if (currentJarvisMsg) {
          currentJarvisMsg.el.classList.remove("streaming");
          if (currentTurnMemories.length) attachRecall(currentJarvisMsg.el, currentTurnMemories);
        }
        currentJarvisMsg = null;
        break;
      case "memory_added":
        (ev.items || []).forEach((m) => upsertMemory(m, true));
        toast(`🧠 Aprendi ${ev.items.length === 1 ? "algo novo" : ev.items.length + " coisas novas"} sobre você`);
        break;
      case "stt_empty":
        toast("Não captei nenhuma fala. Pode repetir, senhor?");
        break;
      case "error":
        addMessage("system", ev.message);
        toast(ev.message, true);
        break;
    }
  }

  // ------------------------------------------------------------------ chat
  function addMessage(kind, text, streaming = false, customWho = null) {
    const el = document.createElement("div");
    el.className = `msg ${kind}${streaming ? " streaming" : ""}`;
    const who = customWho || (kind === "jarvis" ? activeAgentName : { user: "Você", system: "Sistema" }[kind]);
    el.innerHTML = `<span class="who">${who}</span><div class="bubble"></div>`;
    const bubble = el.querySelector(".bubble");
    bubble.textContent = text;
    ui.chatLog.appendChild(el);
    scrollChat();
    return { el, bubble, text };
  }

  function attachRecall(el, items) {
    const box = document.createElement("div");
    box.className = "recall";
    items.slice(0, 4).forEach((m) => {
      const s = document.createElement("span");
      s.textContent = `◈ ${m.content.length > 42 ? m.content.slice(0, 42) + "…" : m.content}`;
      s.title = `Memória usada (relevância ${Math.round(m.score * 100)}%)`;
      box.appendChild(s);
    });
    el.appendChild(box);
  }

  const scrollChat = () => { ui.chatLog.scrollTop = ui.chatLog.scrollHeight; };

  // ------------------------------------------------------------------ áudio de saída
  function ensureAudio() {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      outAnalyser = audioCtx.createAnalyser();
      outAnalyser.fftSize = 256;
      outAnalyser.connect(audioCtx.destination);
    }
    if (audioCtx.state === "suspended") audioCtx.resume();
    return audioCtx;
  }

  async function handleAudio(buf) {
    const turn = new DataView(buf).getUint32(0);
    if (cancelledTurns.has(turn) || !ui.voiceOut.checked) return;
    try {
      const ctx = ensureAudio();
      const audio = await ctx.decodeAudioData(buf.slice(4));
      if (cancelledTurns.has(turn)) return;
      playQueue.push(audio);
      if (!playing) playNext();
    } catch (e) {
      console.warn("Falha ao decodificar áudio", e);
    }
  }

  function playNext() {
    const audio = playQueue.shift();
    if (!audio) { playing = null; refreshState(); return; }
    const src = audioCtx.createBufferSource();
    src.buffer = audio;
    src.connect(outAnalyser);
    src.onended = () => { if (playing === src) playNext(); };
    playing = src;
    refreshState();
    src.start();
  }

  function stopSpeaking() {
    playQueue.length = 0;
    if (playing) { const p = playing; playing = null; try { p.stop(); } catch (_) {} }
  }

  /** Barge-in: cala o Jarvis e cancela a geração no servidor. */
  function interrupt() {
    const wasBusy = playing || playQueue.length || serverState !== "idle";
    if (latestTurn) cancelledTurns.add(latestTurn);
    stopSpeaking();
    if (currentJarvisMsg) { currentJarvisMsg.el.classList.remove("streaming"); currentJarvisMsg = null; }
    if (wasBusy) send({ type: "interrupt" });
    serverState = "idle";
    refreshState();
  }

  // ------------------------------------------------------------------ microfone
  async function ensureMic() {
    ensureAudio();
    if (micStream) return micStream;
    try {
      micStream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
    } catch (e) {
      toast("Acesso ao microfone negado. Libere a permissão no navegador.", true);
      throw e;
    }
    micAnalyser = audioCtx.createAnalyser();
    micAnalyser.fftSize = 1024;
    audioCtx.createMediaStreamSource(micStream).connect(micAnalyser);
    return micStream;
  }

  function pickMime() {
    const options = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm", "audio/mp4"];
    return options.find((m) => window.MediaRecorder && MediaRecorder.isTypeSupported(m)) || "";
  }

  async function startRecording() {
    if (recorder && recorder.state === "recording") return;
    const stream = await ensureMic();
    interrupt();
    const mimeType = pickMime();
    const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    const chunks = [];
    recorder = rec;
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = async () => {
      const duration = performance.now() - recStartedAt;
      const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
      if (recorder === rec) recorder = null;
      ui.micBtn.classList.remove("recording");
      refreshState();
      if (duration < 350 || blob.size < 1500) return;
      send(await blob.arrayBuffer());
      serverState = "transcribing";
      refreshState();
    };
    recStartedAt = performance.now();
    recorder.start();
    ui.micBtn.classList.add("recording");
    ui.caption.innerHTML = "<em>Ouvindo...</em>";
    refreshState();
  }

  function stopRecording() {
    if (recorder && recorder.state === "recording") recorder.stop();
  }

  function micLevel() {
    if (!micAnalyser) return 0;
    const data = new Float32Array(micAnalyser.fftSize);
    micAnalyser.getFloatTimeDomainData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
    return Math.sqrt(sum / data.length);
  }

  function outLevel() {
    if (!outAnalyser || !playing) return 0;
    const data = new Uint8Array(outAnalyser.frequencyBinCount);
    outAnalyser.getByteFrequencyData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i++) sum += data[i];
    return sum / data.length / 255;
  }

  // ------------------------------------------------------------------ mãos-livres (VAD simples)
  const vad = { above: 0, below: 0, noise: 0.008 };
  function vadStep(dt) {
    if (!ui.handsFree.checked || !micAnalyser) return;
    const level = micLevel();
    const speaking = !!(playing || playQueue.length);
    const recording = recorder && recorder.state === "recording";
    if (!recording && !speaking) vad.noise = vad.noise * 0.995 + level * 0.005; // adapta ao ruído do ambiente
    const threshold = Math.max(0.018, vad.noise * 3.2) * (speaking ? 2.2 : 1);

    if (level > threshold) { vad.above += dt; vad.below = 0; } else { vad.below += dt; vad.above = 0; }

    if (!recording && !pttActive && vad.above > 90) startRecording();
    if (recording && !pttActive && vad.below > 950) stopRecording();
  }

  ui.handsFree.addEventListener("change", async () => {
    if (ui.handsFree.checked) {
      try { await ensureMic(); toast("Mãos-livres ativo: é só falar. Fale por cima para interromper."); }
      catch { ui.handsFree.checked = false; }
    } else {
      stopRecording();
    }
  });

  // ------------------------------------------------------------------ push-to-talk
  const pttDown = async (e) => { e.preventDefault(); pttActive = true; try { await startRecording(); } catch {} };
  const pttUp = (e) => { e && e.preventDefault(); if (!pttActive) return; pttActive = false; stopRecording(); };
  ui.micBtn.addEventListener("pointerdown", pttDown);
  ui.micBtn.addEventListener("pointerup", pttUp);
  ui.micBtn.addEventListener("pointerleave", pttUp);

  const typing = () => ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName);
  window.addEventListener("keydown", (e) => {
    if (e.code === "Space" && !typing() && !e.repeat) pttDown(e);
    if (e.code === "Escape") { interrupt(); stopRecording(); }
  });
  window.addEventListener("keyup", (e) => { if (e.code === "Space" && !typing()) pttUp(e); });

  // ------------------------------------------------------------------ texto
  ui.promptForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = ui.promptInput.value.trim();
    if (!text) return;
    ensureAudio();
    stopSpeaking();
    if (currentJarvisMsg) {
      currentJarvisMsg.el.classList.remove("streaming");
      currentJarvisMsg = null;
    }
    send({ type: "text", text, speak: ui.voiceOut.checked, agent: activeAgentId });
    ui.promptInput.value = "";
    serverState = "thinking";
    refreshState();
  });

  ui.resetBtn.addEventListener("click", () => {
    stopSpeaking();
    cancelledTurns.clear();
    currentJarvisMsg = null;
    send({ type: "reset" });
    ui.chatLog.innerHTML = "";
    ui.caption.textContent = "";
    toast("Nova sessão iniciada. A memória de longo prazo foi preservada.");
  });

  // Seletor de protocolo Stark
  document.querySelectorAll(".proto-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const ag = btn.dataset.agent;
      if (!ag) return;
      activeAgentId = ag;
      document.querySelectorAll(".proto-btn").forEach((b) => b.classList.toggle("active", b === btn));
      send({ type: "set_agent", agent: ag });
    });
  });

  ui.voiceOut.addEventListener("change", () => { if (!ui.voiceOut.checked) stopSpeaking(); });

  // ------------------------------------------------------------------ memórias
  async function api(path, opts = {}) {
    const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.detail || `Erro ${r.status}`);
    return body;
  }

  async function loadMemories() {
    try { memories = await api("/api/memories"); renderMemories(); }
    catch (_) { /* memória ainda inicializando */ }
  }

  function upsertMemory(m, fresh = false) {
    if (!memories.some((x) => x.id === m.id)) memories.unshift({ ...m, _fresh: fresh });
    renderMemories();
  }

  function renderMemories() {
    const q = ui.memSearch.value.trim().toLowerCase();
    const list = memories.filter((m) => !q || m.content.toLowerCase().includes(q));
    ui.memCount.textContent = memories.length;
    ui.memList.innerHTML = list.length ? "" : `<li class="mem-empty">${memories.length ? "Nada encontrado." : "Nenhuma memória ainda.<br/>Conte algo sobre você."}</li>`;
    for (const m of list) {
      const li = document.createElement("li");
      li.className = `mem-item${m._fresh ? " fresh" : ""}`;
      const date = m.created_at ? new Date(m.created_at).toLocaleDateString("pt-BR") : "";
      li.innerHTML = `${escapeHtml(m.content)}<span class="meta"><b>${escapeHtml(m.category || "geral")}</b> · ${m.source === "auto" ? "aprendido" : "manual"} · ${date}</span><button class="del" title="Esquecer">✕</button>`;
      li.querySelector(".del").addEventListener("click", async () => {
        try {
          await api(`/api/memories/${m.id}`, { method: "DELETE" });
          memories = memories.filter((x) => x.id !== m.id);
          renderMemories();
          toast("Memória apagada.");
        } catch (e) { toast(e.message, true); }
      });
      ui.memList.appendChild(li);
      if (m._fresh) setTimeout(() => { m._fresh = false; li.classList.remove("fresh"); }, 4000);
    }
  }

  ui.memSearch.addEventListener("input", renderMemories);
  ui.memForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const content = ui.memInput.value.trim();
    if (!content) return;
    try {
      const m = await api("/api/memories", { method: "POST", body: JSON.stringify({ content }) });
      ui.memInput.value = "";
      if (m.duplicate) toast("Eu já sabia disso, senhor.");
      else { upsertMemory(m, true); toast("Memória gravada."); }
    } catch (err) { toast(err.message, true); }
  });

  // ------------------------------------------------------------------ saúde do sistema
  function pill(id, cls) {
    const el = $(id);
    el.classList.remove("ok", "warn", "err");
    if (cls) el.classList.add(cls);
  }

  let memoriesLoaded = false;
  async function pollHealth() {
    try {
      const h = await api("/api/health");
      pill("pill-core", "ok");
      const o = h.ollama;
      pill("pill-ollama", !o.up ? "err" : o.pulling ? "warn" : "ok");
      $("pill-ollama").title = o.pulling ? `Baixando ${o.pulling}...` : `${o.chat_model} @ ${o.url}`;
      pill("pill-memory", h.memory.ready ? "ok" : h.memory.error ? "err" : "warn");
      $("pill-memory").title = h.memory.error || (h.memory.ready ? `pgvector · ${h.memory.dimension}d` : "Inicializando");
      pill("pill-stt", h.stt.status === "pronto" ? "ok" : h.stt.status.startsWith("erro") ? "err" : "warn");
      $("pill-stt").title = `Whisper ${h.stt.model}: ${h.stt.status}`;
      if (o.pulling && state === "idle") ui.stateHint.textContent = `Baixando modelo ${o.pulling}...`;
      if (!o.up && state === "idle") ui.stateHint.textContent = "Ollama offline — inicie o Ollama no host";
      if (h.memory.ready && !memoriesLoaded) { memoriesLoaded = true; loadMemories(); }
    } catch {
      ["pill-core", "pill-ollama", "pill-memory", "pill-stt"].forEach((p) => pill(p, "err"));
    }
  }
  setInterval(pollHealth, 4000);
  pollHealth();

  // ------------------------------------------------------------------ reator arc (canvas)
  const ctx2d = ui.reactor.getContext("2d");
  let color = [30, 220, 255];
  let energy = 0;
  let last = performance.now();

  function resizeCanvas() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = ui.reactor.getBoundingClientRect();
    ui.reactor.width = rect.width * dpr;
    ui.reactor.height = rect.height * dpr;
  }
  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();

  function frame(now) {
    const dt = now - last;
    last = now;
    vadStep(dt);

    const target = (STATES[state] || STATES.idle).color;
    color = color.map((c, i) => c + (target[i] - c) * 0.08);
    const level = state === "listening" ? Math.min(1, micLevel() * 9) : state === "speaking" ? Math.min(1, outLevel() * 2.6) : 0;
    const base = state === "thinking" || state === "transcribing" ? 0.35 + 0.25 * Math.sin(now / 180) : 0.12;
    energy += (Math.max(level, base) - energy) * 0.18;

    drawReactor(now / 1000, energy);
    requestAnimationFrame(frame);
  }

  function rgba(a) { return `rgba(${color[0] | 0},${color[1] | 0},${color[2] | 0},${a})`; }

  function drawReactor(t, e) {
    const c = ctx2d, W = ui.reactor.width, H = ui.reactor.height;
    const cx = W / 2, cy = H / 2, R = Math.min(W, H) / 2;
    c.clearRect(0, 0, W, H);

    // brilho de fundo
    const glow = c.createRadialGradient(cx, cy, R * 0.05, cx, cy, R * (0.75 + e * 0.2));
    glow.addColorStop(0, rgba(0.35 + e * 0.4));
    glow.addColorStop(0.35, rgba(0.08 + e * 0.12));
    glow.addColorStop(1, rgba(0));
    c.fillStyle = glow;
    c.fillRect(0, 0, W, H);

    c.lineCap = "round";
    // anel externo tracejado (gira lento)
    ring(cx, cy, R * 0.9, t * 0.15, 72, 0.6, R * 0.006, 0.35);
    // anel de segmentos (gira ao contrário)
    ring(cx, cy, R * 0.78, -t * 0.4, 12, 0.72, R * 0.028, 0.55 + e * 0.4);
    // arcos HUD
    arc(cx, cy, R * 0.68, t * 0.9, Math.PI * 0.55, R * 0.008, 0.8);
    arc(cx, cy, R * 0.68, t * 0.9 + Math.PI, Math.PI * 0.55, R * 0.008, 0.8);
    arc(cx, cy, R * 0.6, -t * 1.3, Math.PI * 0.3, R * 0.005, 0.6);

    // barras do espectro reagindo à voz
    const bars = 96;
    for (let i = 0; i < bars; i++) {
      const a = (i / bars) * Math.PI * 2 + t * 0.2;
      const wobble = 0.5 + 0.5 * Math.sin(i * 0.7 + t * 6);
      const len = R * (0.02 + e * 0.16 * wobble);
      const r0 = R * 0.5;
      c.strokeStyle = rgba(0.25 + e * 0.6);
      c.lineWidth = R * 0.008;
      c.beginPath();
      c.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0);
      c.lineTo(cx + Math.cos(a) * (r0 + len), cy + Math.sin(a) * (r0 + len));
      c.stroke();
    }

    // triângulo do Mark VI
    c.save();
    c.translate(cx, cy);
    c.rotate(-Math.PI / 2 + Math.sin(t * 0.5) * 0.04);
    c.strokeStyle = rgba(0.85);
    c.lineWidth = R * 0.014;
    c.shadowColor = rgba(1);
    c.shadowBlur = R * 0.08;
    c.beginPath();
    const tr = R * 0.36;
    for (let k = 0; k < 3; k++) {
      const a = (k / 3) * Math.PI * 2;
      c.lineTo(Math.cos(a) * tr, Math.sin(a) * tr);
    }
    c.closePath();
    c.stroke();
    c.restore();

    // núcleo
    const core = c.createRadialGradient(cx, cy, 0, cx, cy, R * (0.24 + e * 0.06));
    core.addColorStop(0, "rgba(255,255,255,0.95)");
    core.addColorStop(0.35, rgba(0.85));
    core.addColorStop(1, rgba(0));
    c.fillStyle = core;
    c.beginPath();
    c.arc(cx, cy, R * (0.24 + e * 0.06), 0, Math.PI * 2);
    c.fill();
  }

  function ring(cx, cy, r, rot, n, fill, width, alpha) {
    const c = ctx2d;
    c.strokeStyle = rgba(alpha);
    c.lineWidth = width;
    const seg = (Math.PI * 2) / n;
    for (let i = 0; i < n; i++) {
      c.beginPath();
      c.arc(cx, cy, r, rot + i * seg, rot + i * seg + seg * fill);
      c.stroke();
    }
  }

  function arc(cx, cy, r, start, len, width, alpha) {
    const c = ctx2d;
    c.strokeStyle = rgba(alpha);
    c.lineWidth = width;
    c.beginPath();
    c.arc(cx, cy, r, start, start + len);
    c.stroke();
  }

  // ------------------------------------------------------------------ boot
  addMessage("jarvis", "Sistemas online. Segure Espaço (ou o botão do microfone) para falar comigo, ou digite abaixo. Ative o modo mãos-livres para conversar sem tocar em nada.");
  connect();
  requestAnimationFrame(frame);
})();
