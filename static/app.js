const $ = id => document.getElementById(id);
const HISTORY_KEY = "cortaviral_local_history_v1";
let activeJob = "";
let activeSource = "";
let pollTimer = null;
let API_BASE = (localStorage.getItem("cortaviral_server_url") || location.origin).replace(/\/+$/, "");
const apiUrl = path => API_BASE + path;

function safeText(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function formatTime(seconds) {
  const n = Math.max(0, Math.floor(Number(seconds) || 0));
  return String(Math.floor(n / 60)).padStart(2,"0") + ":" + String(n % 60).padStart(2,"0");
}
function getHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch (_) { return []; }
}
function saveHistory(entry) {
  const list = getHistory().filter(item => item.jobId !== entry.jobId);
  list.unshift(entry);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, 30)));
  renderHistory();
}
function renderHistory() {
  const list = getHistory();
  const host = $("historyList");
  if (!list.length) {
    host.innerHTML = '<div class="empty-state">Suas análises concluídas aparecerão aqui.</div>';
    return;
  }
  host.innerHTML = list.map(item => `
    <article class="history-item">
      <div><strong>${safeText(item.title || "Vídeo analisado")}</strong><small>${safeText(item.date)} · ${Number(item.count)||0} corte(s)</small></div>
      <button type="button" data-open-job="${safeText(item.jobId)}">Ver cortes</button>
    </article>`).join("");
  host.querySelectorAll("[data-open-job]").forEach(button => button.addEventListener("click", () => {
    const item = getHistory().find(x => x.jobId === button.dataset.openJob);
    if (item) renderResults(item.job, item.jobId, false);
  }));
}
function setProgress(message, percent) {
  $("progressPanel").hidden = false;
  $("progressMessage").textContent = message || "Processando…";
  $("progressPercent").textContent = Math.max(0, Math.min(100, percent || 0)) + "%";
  $("progressFill").style.width = Math.max(0, Math.min(100, percent || 0)) + "%";
}
function showError(message) {
  if (pollTimer) clearTimeout(pollTimer);
  $("errorPanel").hidden = false;
  $("errorPanel").textContent = message || "Não foi possível concluir. Tente importar um vídeo da galeria.";
  $("analyzeButton").disabled = false;
  $("analyzeButton").innerHTML = 'Tentar novamente <span>→</span>';
  $("progressMessage").textContent = "Análise não concluída";
}
async function checkServer() {
  const badge = $("connection");
  try {
    const response = await fetch(apiUrl("/api/health"), {cache:"no-store"});
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error("Servidor indisponível");
    badge.className = "connection online";
    badge.querySelector("span").textContent = "Servidor conectado · v" + (data.version || "?");
  } catch (_) {
    badge.className = "connection offline";
    badge.querySelector("span").textContent = "Servidor indisponível";
  }
}
async function startAnalysis() {
  const file = $("videoFile").files[0];
  const url = $("videoUrl").value.trim();
  if (!file && !url) {
    $("videoUrl").focus();
    showError("Cole um link ou escolha um vídeo da galeria.");
    return;
  }
  $("errorPanel").hidden = true;
  $("resultsSection").hidden = true;
  $("analyzeButton").disabled = true;
  $("analyzeButton").textContent = "Enviando…";
  activeSource = file ? file.name : url;
  try {
    let response;
    if (file) {
      const form = new FormData();
      form.append("file", file, file.name);
      form.append("clips", $("clipCount").value);
      form.append("aspect_ratio", $("aspectRatio").value);
      response = await fetch(apiUrl("/api/analyze-upload"), {method:"POST", body:form});
    } else {
      response = await fetch(apiUrl("/api/analyze"), {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({url, clips:Number($("clipCount").value), aspect_ratio:$("aspectRatio").value})
      });
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "O servidor não aceitou o vídeo.");
    activeJob = data.job_id;
    setProgress("Vídeo recebido. Preparando análise…", 3);
    $("progressHint").textContent = "O histórico será salvo neste aparelho quando a análise terminar.";
    $("analyzeButton").textContent = "Analisando…";
    poll(activeJob, Date.now());
  } catch (error) {
    showError(error.message);
  }
}
async function poll(jobId, startedAt) {
  try {
    if (Date.now() - startedAt > 35 * 60 * 1000) throw new Error("O processamento demorou mais que o limite de espera. Verifique a conexão e tente novamente.");
    const response = await fetch(apiUrl("/api/jobs/" + encodeURIComponent(jobId)), {cache:"no-store"});
    const job = await response.json();
    if (!response.ok) throw new Error(job.detail || "A tarefa não está mais ativa no servidor.");
    setProgress(job.message || "Processando…", job.progress || 0);
    if (job.status === "completed") {
      $("analyzeButton").disabled = false;
      $("analyzeButton").innerHTML = 'Analisar outro vídeo <span>→</span>';
      const entry = {
        jobId,
        title: activeSource || "Vídeo analisado",
        date: new Date().toLocaleString("pt-BR"),
        count: (job.results || []).length,
        job
      };
      saveHistory(entry);
      renderResults(job, jobId, true);
      return;
    }
    if (job.status === "error") throw new Error(job.message || "Falha no processamento.");
    pollTimer = setTimeout(() => poll(jobId, startedAt), 1800);
  } catch (error) {
    showError(error.message);
  }
}
function renderResults(job, jobId, scroll) {
  const results = job.results || [];
  $("resultsSection").hidden = false;
  $("resultsSummary").textContent = results.length + " corte(s) · " + safeText(job.transcript_note || "Análise concluída");
  $("scoreNote").textContent = job.score_note || "A pontuação é uma estimativa, não uma promessa de viralização.";
  $("resultGrid").innerHTML = results.map(clip => {
    const videoUrl = new URL(clip.url, API_BASE + "/").href;
    const tags = (clip.reasons || []).map(reason => '<span class="tag">' + safeText(reason) + '</span>').join("");
    return `<article class="clip-card">
      <div class="clip-top"><div><h3>${safeText(clip.hook || "Melhor momento")}</h3><div class="clip-meta">${formatTime(clip.start)}–${formatTime(clip.end)} · ${Math.round(clip.duration || 0)}s</div></div><div class="score">${Number(clip.score)||0}</div></div>
      <p>${safeText(clip.text || "Trecho selecionado automaticamente.")}</p>
      <div>${tags}</div>
      <video controls playsinline preload="metadata" src="${safeText(videoUrl)}"></video>
      <div class="clip-actions"><a href="${safeText(videoUrl)}" download>Baixar MP4</a></div>
    </article>`;
  }).join("");
  $("downloadAll").onclick = () => {
    if (!jobId) return;
    location.href = apiUrl("/api/jobs/" + encodeURIComponent(jobId) + "/download-all");
  };
  if (scroll) $("resultsSection").scrollIntoView({behavior:"smooth", block:"start"});
}
$("analyzeButton").addEventListener("click", startAnalysis);
$("pasteButton").addEventListener("click", async () => {
  try { $("videoUrl").value = await navigator.clipboard.readText(); }
  catch (_) { $("videoUrl").focus(); $("videoUrl").placeholder = "Toque e segure para colar o link"; }
});
$("videoFile").addEventListener("change", () => {
  const file = $("videoFile").files[0];
  $("fileName").textContent = file ? file.name : "MP4, MOV, MKV ou WEBM";
});
$("clearHistory").addEventListener("click", () => {
  if (!getHistory().length) return;
  if (confirm("Apagar o histórico salvo neste aparelho? Os vídeos baixados não serão apagados.")) {
    localStorage.removeItem(HISTORY_KEY);
    renderHistory();
  }
});
$("videoUrl").addEventListener("keydown", event => { if (event.key === "Enter") startAnalysis(); });
renderHistory();
checkServer();

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
    const parsed = new URL($("serverUrl").value.trim());
    if (parsed.protocol !== "https:" || !parsed.hostname) throw new Error("Use um endereço HTTPS válido.");
    const next = parsed.origin;
    localStorage.setItem("cortaviral_server_url", next);
    API_BASE = next;
    $("settingsModal").hidden = true;
    checkServer();
  } catch (error) {
    alert(error.message || "Endereço inválido. Use o endereço HTTPS do servidor.");
  }
});
