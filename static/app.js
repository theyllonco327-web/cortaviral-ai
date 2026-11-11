const $ = id => document.getElementById(id);
const HISTORY_KEY = "cortaviral_local_history_v2";
const DEFAULT_SERVER = "https://cortaviral-ai.onrender.com";
let activeJob = "";
let activeSource = "";
let pollTimer = null;
let serverHealth = null;
let serverOK = false;
let toastTimer = null;
function initialApiBase() {
  const saved = localStorage.getItem("cortaviral_server_url");
  if (!saved) return location.origin;
  try { return normaliseServer(saved); }
  catch (_) {
    localStorage.removeItem("cortaviral_server_url");
    return location.origin;
  }
}
let API_BASE = initialApiBase();
const apiUrl = path => API_BASE + path;

function safeText(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function formatTime(seconds) {
  const n = Math.max(0, Math.floor(Number(seconds) || 0));
  return String(Math.floor(n / 60)).padStart(2,"0") + ":" + String(n % 60).padStart(2,"0");
}
function toast(message) {
  let node = $("appToast");
  if (!node) {
    node = document.createElement("div");
    node.id = "appToast";
    node.className = "app-toast";
    document.body.appendChild(node);
  }
  node.textContent = message;
  node.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.remove("visible"), 3200);
}
function getHistory() {
  try {
    const value = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(value) ? value : [];
  } catch (_) { return []; }
}
function saveHistory(entry) {
  const list = getHistory().filter(item => item.jobId !== entry.jobId);
  list.unshift(entry);
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, 30)));
    renderHistory();
  } catch (_) {
    toast("Armazenamento local cheio. Baixe seus cortes e limpe o histórico antigo.");
  }
}
function renderHistory() {
  const list = getHistory();
  const host = $("historyList");
  if (!list.length) {
    host.innerHTML = '<div class="empty-state"><span>▤</span><strong>Sua biblioteca está vazia</strong><small>Seus projetos concluídos aparecerão aqui.</small></div>';
    return;
  }
  host.innerHTML = list.map(item =>
    '<article class="history-item"><div><strong>' + safeText(item.title || "Vídeo analisado") +
    '</strong><small>' + safeText(item.date || "") + ' · ' + (Number(item.count)||0) +
    ' corte(s)</small></div><button type="button" data-open-job="' + safeText(item.jobId) +
    '">Ver cortes</button></article>'
  ).join("");
  host.querySelectorAll("[data-open-job]").forEach(button => button.addEventListener("click", () => {
    const item = getHistory().find(x => x.jobId === button.dataset.openJob);
    if (item) renderResults(item.job, item.jobId, true);
  }));
}
function setProgress(message, percent) {
  $("progressPanel").hidden = false;
  $("progressMessage").textContent = message || "Processando…";
  const value = Math.max(0, Math.min(100, Number(percent) || 0));
  $("progressPercent").textContent = value + "%";
  $("progressFill").style.width = value + "%";
}
function showError(message) {
  if (pollTimer) clearTimeout(pollTimer);
  $("errorPanel").hidden = false;
  $("errorMessage").textContent = message || "Não foi possível concluir. Confira a conexão do servidor.";
  $("analyzeButton").disabled = false;
  $("analyzeButton").innerHTML = '<span class="button-icon">↻</span> Tentar novamente <b>→</b>';
}
function explainHttpFailure(status, detail, body) {
  const extra = detail ? " Detalhe: " + detail : "";
  if (status === 404) return "O servidor respondeu HTTP 404. A rota da API não existe nesta versão publicada. Isso normalmente significa que o Render ainda está executando uma versão antiga ou que o endereço configurado não é o servidor do CortaViral AI." + extra;
  if (status === 405) return "O servidor respondeu HTTP 405 (método não permitido). A versão publicada não reconhece este envio. O aplicativo e o backend estão fora de sincronia; atualizar somente o APK não corrige isso." + extra;
  if (status === 413) return "O servidor recusou o arquivo por tamanho (HTTP 413). Tente um vídeo menor ou um link público compatível." + extra;
  if (status === 415) return "O formato do arquivo não foi aceito (HTTP 415). Use MP4, MOV, MKV ou WEBM." + extra;
  if (status >= 500) return "O servidor apresentou uma falha interna (HTTP " + status + "). Pode ser falta de memória, tempo de processamento ou falha no serviço de mídia." + extra;
  return "A solicitação falhou com HTTP " + status + "." + extra + (body ? " Resposta: " + body.slice(0,180) : "");
}
async function requestJson(url, options, label) {
  let response;
  try {
    response = await fetch(url, options || {});
  } catch (error) {
    throw new Error("Não consegui alcançar o servidor. Verifique a internet e o endereço em Configurações. " + (error && error.message ? error.message : ""));
  }
  const raw = await response.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch (_) {
    if (/<!doctype html|<html[\s>]/i.test(raw) || /text\/html/i.test(response.headers.get("content-type") || "")) {
      throw new Error("O servidor devolveu uma página HTML, não os dados JSON da API (" + label + ", HTTP " + response.status + "). Isso confirma endereço incorreto, rota ausente ou publicação antiga. Abra Conexão → Testar agora para conferir a versão ativa.");
    }
    throw new Error("A resposta do servidor não é um JSON válido (" + label + ", HTTP " + response.status + ").");
  }
  if (!response.ok) {
    const detail = data && (data.detail || data.message || data.error);
    throw new Error(explainHttpFailure(response.status, typeof detail === "string" ? detail : "", raw));
  }
  return data;
}
function setDiagnostic(ok, title, detail, data) {
  serverOK = !!ok;
  $("connection").className = "connection " + (ok ? "online" : "offline");
  $("connection").querySelector("span").textContent = ok ? "Servidor conectado" : "Servidor com erro";
  $("diagnosticLed").className = "diagnostic-led " + (ok ? "online" : "offline");
  $("diagnosticTitle").textContent = title;
  $("diagnosticText").textContent = detail;
  $("serverAddress").textContent = API_BASE;
  $("serverVersion").textContent = data && data.version ? "v" + data.version : "SEM API";
  $("serverCommit").textContent = data && data.deployment_commit && data.deployment_commit !== "unknown"
    ? data.deployment_commit.slice(0,12) : "Não informado pelo servidor";
}
async function checkServer(silent) {
  $("testServerButton").disabled = true;
  $("testServerButton").textContent = "Verificando…";
  try {
    const data = await requestJson(apiUrl("/api/health"), {cache:"no-store"}, "verificação do servidor");
    if (data.ok !== true || data.app !== "CortaViral AI" || !data.version) {
      throw new Error("A URL respondeu, mas não identificou a API oficial do CortaViral AI. O endereço pode ser de outro serviço.");
    }
    serverHealth = data;
    const min = data.clip_duration_seconds && data.clip_duration_seconds.minimum;
    const max = data.clip_duration_seconds && data.clip_duration_seconds.maximum;
    const endpointsOK = data.upload_endpoint === "/api/analyze-upload" && data.url_endpoint === "/api/analyze";
    if (!endpointsOK) {
      setDiagnostic(false, "Versão incompleta do servidor", "A API respondeu, mas não confirmou os endpoints de URL e galeria. O deploy do backend está desatualizado.", data);
      if (!silent) toast("O servidor está online, mas está desatualizado.");
      return false;
    }
    setDiagnostic(true, "Servidor online · API validada", "API v" + data.version + " ativa. Cortes de " + min + " a " + max + " segundos. Endpoints de URL e galeria encontrados.", data);
    if (!silent) toast("Conexão validada. API v" + data.version + ".");
    return true;
  } catch (error) {
    serverHealth = null;
    setDiagnostic(false, "Não foi possível validar a API", error.message, null);
    if (!silent) toast("Falha no teste do servidor. Veja os detalhes abaixo.");
    return false;
  } finally {
    $("testServerButton").disabled = false;
    $("testServerButton").textContent = "Testar agora ↻";
  }
}
function captionFor(clip) {
  const hook = String(clip.hook || "Um momento que merece ser visto").trim();
  const body = String(clip.text || "").replace(/\s+/g," ").trim();
  const stop = new Set(["para","como","mais","muito","essa","esse","isso","aqui","sobre","porque","quando","onde","entao","tambem","voce","voces","com","sem","uma","uns","das","dos","que","por","pra","pro","the","and","you","are","this","that","from","with"]);
  const words = body.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").match(/[a-z0-9]{4,}/g) || [];
  const tags = [];
  for (const word of words) {
    if (!stop.has(word) && !tags.includes(word)) tags.push(word);
    if (tags.length >= 4) break;
  }
  const hashtags = ["#CortaViral","#Cortes", ...tags.map(x => "#" + x)].join(" ");
  return hook + (body ? "\n\n" + body.slice(0,280) : "") + "\n\n" + hashtags;
}
async function copyText(value) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(value);
    } else {
      const field = document.createElement("textarea");
      field.value = value;
      field.style.position = "fixed";
      field.style.opacity = "0";
      document.body.appendChild(field);
      field.select();
      const ok = document.execCommand("copy");
      field.remove();
      if (!ok) throw new Error("copy");
    }
    toast("Legenda copiada.");
  } catch (_) {
    toast("Não foi possível copiar automaticamente. Selecione o texto da legenda.");
  }
}
async function shareClip(clip, videoUrl) {
  const text = captionFor(clip);
  try {
    if (navigator.share) {
      await navigator.share({title:clip.hook || "Corte CortaViral", text, url:videoUrl});
    } else {
      await copyText(text + "\n" + videoUrl);
    }
  } catch (error) {
    if (error && error.name !== "AbortError") await copyText(text + "\n" + videoUrl);
  }
}
function makeClipCard(clip) {
  const card = document.createElement("article");
  card.className = "clip-card";
  const top = document.createElement("div");
  top.className = "clip-top";
  const heading = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = clip.hook || "Melhor momento";
  const meta = document.createElement("div");
  meta.className = "clip-meta";
  meta.textContent = formatTime(clip.start) + "–" + formatTime(clip.end) + " · " + Math.round(clip.duration || 0) + "s";
  heading.append(title,meta);
  const score = document.createElement("div");
  score.className = "score";
  score.textContent = (Number(clip.score)||0) + "/100";
  top.append(heading,score);
  const transcript = document.createElement("p");
  transcript.textContent = clip.text || "Trecho selecionado automaticamente.";
  const tags = document.createElement("div");
  tags.className = "clip-tags";
  (clip.reasons || []).forEach(reason => {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = reason;
    tags.appendChild(tag);
  });
  const video = document.createElement("video");
  const videoUrl = new URL(clip.url, API_BASE + "/").href;
  video.controls = true;
  video.playsInline = true;
  video.preload = "metadata";
  video.src = videoUrl;
  video.addEventListener("error", () => {
    video.replaceWith(Object.assign(document.createElement("p"), {
      className:"video-unavailable",
      textContent:"A prévia não está disponível no servidor. O serviço pode ter reiniciado ou removido o arquivo temporário."
    }));
  }, {once:true});
  const actions = document.createElement("div");
  actions.className = "clip-actions";
  const download = document.createElement("a");
  download.href = videoUrl;
  download.download = "CortaViral_corte_" + String(clip.number || 1).padStart(2,"0") + ".mp4";
  download.textContent = "↓ Baixar MP4";
  download.className = "wide";
  const copy = document.createElement("button");
  copy.type = "button";
  copy.textContent = "Copiar legenda";
  copy.addEventListener("click", () => copyText(captionFor(clip)));
  const share = document.createElement("button");
  share.type = "button";
  share.textContent = "Compartilhar";
  share.addEventListener("click", () => shareClip(clip, videoUrl));
  actions.append(download,copy,share);
  card.append(top,transcript,tags,video,actions);
  return card;
}
function renderResults(job, jobId, scroll) {
  const results = job.results || [];
  $("resultsSection").hidden = false;
  $("resultsSummary").textContent = results.length + " corte(s) · " + (job.source_duration ? formatTime(job.source_duration) + " de vídeo original" : "análise concluída");
  $("scoreNote").textContent = job.score_note || job.transcript_note || "A pontuação é uma estimativa, não uma promessa de viralização.";
  const host = $("resultGrid");
  host.replaceChildren();
  results.forEach(clip => host.appendChild(makeClipCard(clip)));
  $("downloadAll").onclick = () => {
    if (!jobId) return;
    const link = document.createElement("a");
    link.href = apiUrl("/api/jobs/" + encodeURIComponent(jobId) + "/download-all");
    link.download = "CortaViral_todos_os_cortes.zip";
    document.body.appendChild(link);
    link.click();
    link.remove();
  };
  if (scroll) $("resultsSection").scrollIntoView({behavior:"smooth", block:"start"});
}
async function startAnalysis() {
  const file = $("videoFile").files[0];
  const url = $("videoUrl").value.trim();
  if (!file && !url) {
    $("videoUrl").focus();
    showError("Cole uma URL de vídeo ou escolha um arquivo da galeria.");
    return;
  }
  if (file && url) {
    showError("Escolha apenas uma origem por vez: URL ou arquivo da galeria.");
    return;
  }
  $("errorPanel").hidden = true;
  $("resultsSection").hidden = true;
  $("analyzeButton").disabled = true;
  $("analyzeButton").textContent = "Verificando servidor…";
  activeSource = file ? file.name : url;
  try {
    const healthy = await checkServer(true);
    if (!healthy) throw new Error($("diagnosticText").textContent);
    $("analyzeButton").textContent = file ? "Enviando vídeo…" : "Enviando link…";
    let response;
    const controller = new AbortController();
    const uploadTimeout = setTimeout(() => controller.abort(), 12 * 60 * 1000);
    try {
      if (file) {
        const form = new FormData();
        form.append("file", file, file.name);
        form.append("clips", $("clipCount").value);
        form.append("aspect_ratio", $("aspectRatio").value);
        form.append("subtitles", $("subtitles").checked ? "true" : "false");
        response = await requestJson(apiUrl("/api/analyze-upload"), {
          method:"POST", body:form, signal:controller.signal
        }, "envio da galeria");
      } else {
        response = await requestJson(apiUrl("/api/analyze"), {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({
            url,
            clips:Number($("clipCount").value),
            aspect_ratio:$("aspectRatio").value,
            subtitles:$("subtitles").checked
          }),
          signal:controller.signal
        }, "envio da URL");
      }
    } finally {
      clearTimeout(uploadTimeout);
    }
    if (!response.job_id) throw new Error("O servidor aceitou a solicitação, mas não devolveu o identificador da análise. Verifique se o backend publicado está atualizado.");
    activeJob = response.job_id;
    setProgress("Vídeo recebido. Preparando análise…", 3);
    $("progressHint").textContent = "O histórico será salvo neste aparelho quando a análise terminar.";
    $("analyzeButton").textContent = "Analisando vídeo…";
    poll(activeJob, Date.now(), 0);
  } catch (error) {
    const message = error && error.name === "AbortError"
      ? "O envio demorou mais de 12 minutos e foi interrompido. Tente um vídeo menor ou uma conexão mais estável."
      : (error.message || "Falha desconhecida ao iniciar a análise.");
    showError(message);
  }
}
async function poll(jobId, startedAt, failures) {
  try {
    if (Date.now() - startedAt > 45 * 60 * 1000) {
      throw new Error("A análise ultrapassou 45 minutos. O servidor pode ter ficado sem memória ou reiniciado durante o processamento.");
    }
    const job = await requestJson(apiUrl("/api/jobs/" + encodeURIComponent(jobId)), {cache:"no-store"}, "consulta do processamento");
    setProgress(job.message || "Processando…", job.progress || 0);
    if (job.status === "completed") {
      $("analyzeButton").disabled = false;
      $("analyzeButton").innerHTML = '<span class="button-icon">✦</span> Criar outro projeto <b>→</b>';
      const entry = {
        jobId,
        title: activeSource || "Vídeo analisado",
        date: new Date().toLocaleString("pt-BR"),
        count: (job.results || []).length,
        job
      };
      saveHistory(entry);
      renderResults(job, jobId, true);
      toast("Projeto concluído. Seus cortes estão prontos.");
      return;
    }
    if (job.status === "error") throw new Error(job.message || "Falha no processamento do vídeo.");
    if (job.status !== "queued" && job.status !== "processing") {
      throw new Error("O servidor devolveu um estado desconhecido: " + String(job.status));
    }
    pollTimer = setTimeout(() => poll(jobId, startedAt, 0), 3000);
  } catch (error) {
    const message = error.message || "Erro ao consultar o andamento.";
    if (/HTTP 404/.test(message) && /tarefa|não está mais disponível|not found/i.test(message)) {
      showError("O servidor não encontrou esta tarefa. Isso acontece quando o processo reinicia ou quando o Render troca de instância. O arquivo pode precisar ser enviado novamente. Detalhe: " + message);
      return;
    }
    const next = (failures || 0) + 1;
    if (next >= 5) {
      showError("Não foi possível retomar a comunicação após 5 tentativas. Último erro: " + message);
      return;
    }
    setProgress("Reconectando ao servidor (" + next + "/5)…", 0);
    pollTimer = setTimeout(() => poll(jobId, startedAt, next), 5000);
  }
}
function normaliseServer(value) {
  const parsed = new URL(value.trim());
  if (parsed.protocol !== "https:") throw new Error("Use um endereço HTTPS seguro.");
  const host = parsed.hostname.toLowerCase();
  const forbidden = ["youtube.com","youtu.be","tiktok.com","instagram.com","facebook.com","x.com","twitter.com"];
  if (forbidden.some(domain => host === domain || host.endsWith("." + domain))) {
    throw new Error("Esse endereço parece ser de uma plataforma de vídeos. O endereço do servidor é diferente do link do vídeo.");
  }
  if (parsed.username || parsed.password) throw new Error("Não coloque usuário ou senha na URL do servidor.");
  return parsed.origin;
}
async function copyCurrentDiagnostics() {
  const info = [
    "CortaViral AI",
    "Servidor: " + API_BASE,
    "Estado: " + (serverOK ? "online" : "com erro"),
    "Versão: " + (serverHealth && serverHealth.version ? serverHealth.version : "não identificada"),
    "Commit: " + (serverHealth && serverHealth.deployment_commit ? serverHealth.deployment_commit : "não informado"),
    "Diagnóstico: " + $("diagnosticText").textContent
  ].join("\n");
  await copyText(info);
}
$("analyzeButton").addEventListener("click", startAnalysis);
$("retryButton").addEventListener("click", startAnalysis);
$("pasteButton").addEventListener("click", async () => {
  try {
    if (!navigator.clipboard || !navigator.clipboard.readText) throw new Error("clipboard");
    const value = await navigator.clipboard.readText();
    if (!value.trim()) throw new Error("empty");
    $("videoUrl").value = value.trim();
    $("videoFile").value = "";
    $("fileName").textContent = "Toque para selecionar MP4, MOV, MKV ou WEBM";
    toast("Link colado.");
  } catch (_) {
    $("videoUrl").focus();
    toast("Toque e segure no campo do link e escolha COLAR.");
  }
});
$("videoFile").addEventListener("change", () => {
  const file = $("videoFile").files[0];
  $("fileName").textContent = file ? file.name + " · " + (file.size / 1024 / 1024).toFixed(1) + " MB" : "Toque para selecionar MP4, MOV, MKV ou WEBM";
  if (file) $("videoUrl").value = "";
});
$("videoUrl").addEventListener("input", () => {
  if ($("videoUrl").value.trim()) {
    $("videoFile").value = "";
    $("fileName").textContent = "Toque para selecionar MP4, MOV, MKV ou WEBM";
  }
});
$("clearHistory").addEventListener("click", () => {
  if (!getHistory().length) return;
  if (confirm("Apagar o histórico salvo neste aparelho? Isso não apaga os vídeos já baixados.")) {
    localStorage.removeItem(HISTORY_KEY);
    renderHistory();
    toast("Histórico local limpo.");
  }
});
$("videoUrl").addEventListener("keydown", event => { if (event.key === "Enter") startAnalysis(); });
$("testServerButton").addEventListener("click", () => checkServer(false));
$("openHealthButton").addEventListener("click", copyCurrentDiagnostics);
$("settingsButton").addEventListener("click", () => {
  $("serverUrl").value = API_BASE;
  $("settingsModal").hidden = false;
});
$("closeSettings").addEventListener("click", () => { $("settingsModal").hidden = true; });
$("settingsModal").addEventListener("click", event => {
  if (event.target === $("settingsModal")) $("settingsModal").hidden = true;
});
$("saveSettings").addEventListener("click", () => {
  try {
    const next = normaliseServer($("serverUrl").value);
    localStorage.setItem("cortaviral_server_url", next);
    $("settingsModal").hidden = true;
    if (next !== location.origin) {
      location.replace(next + "/");
      return;
    }
    API_BASE = next;
    checkServer(false);
  } catch (error) {
    toast(error.message || "Endereço inválido.");
  }
});
$("useDefaultServer").addEventListener("click", () => {
  localStorage.setItem("cortaviral_server_url", DEFAULT_SERVER);
  $("settingsModal").hidden = true;
  if (location.origin !== DEFAULT_SERVER) location.replace(DEFAULT_SERVER + "/");
  else {
    API_BASE = DEFAULT_SERVER;
    checkServer(false);
  }
});
document.querySelectorAll("[data-scroll]").forEach(button => button.addEventListener("click", () => {
  const target = $(button.dataset.scroll);
  if (target) target.scrollIntoView({behavior:"smooth",block:"start"});
  document.querySelectorAll(".nav-item").forEach(item => item.classList.toggle("active", item === button));
}));
$("uploadDrop").addEventListener("dragover", event => { event.preventDefault(); $("uploadDrop").classList.add("dragging"); });
$("uploadDrop").addEventListener("dragleave", () => $("uploadDrop").classList.remove("dragging"));
$("uploadDrop").addEventListener("drop", event => {
  event.preventDefault();
  $("uploadDrop").classList.remove("dragging");
  const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
  if (file && file.type.startsWith("video/")) {
    try {
      const transfer = new DataTransfer();
      transfer.items.add(file);
      $("videoFile").files = transfer.files;
      $("videoFile").dispatchEvent(new Event("change"));
    } catch (_) {
      toast("Use o botão Escolher vídeo da galeria neste aparelho.");
    }
  } else toast("Solte um arquivo de vídeo válido.");
});
renderHistory();
$("serverAddress").textContent = API_BASE;
checkServer(true);
