(() => {
  const $ = id => document.getElementById(id);
  const form = $("linkForm");
  const input = $("heroUrl");
  const status = $("apiStatus");

  form.addEventListener("submit", event => {
    event.preventDefault();
    const value = input.value.trim();
    if (!value) {
      input.focus();
      return;
    }
    try {
      const parsed = new URL(value);
      if (!["http:", "https:"].includes(parsed.protocol)) throw new Error("invalid");
      window.location.href = "/app/?url=" + encodeURIComponent(parsed.href);
    } catch (_) {
      input.setCustomValidity("Cole um endereço válido começando com https://");
      input.reportValidity();
      input.addEventListener("input", () => input.setCustomValidity(""), {once:true});
    }
  });

  fetch("/api/health", {headers: {"Accept":"application/json"}})
    .then(response => {
      if (!response.ok) throw new Error("Servidor indisponível");
      return response.json();
    })
    .then(data => {
      if (!data.ok || data.app !== "CortaViral AI") throw new Error("API não validada");
      status.classList.add("online");
      status.innerHTML = '<span class="status-dot"></span> Estúdio conectado · versão ' +
        String(data.version).replace(/[<>&"]/g, "") + ' · API ativa';
    })
    .catch(() => {
      status.classList.add("offline");
      status.innerHTML = '<span class="status-dot"></span> O servidor pode estar iniciando. Você ainda pode abrir o estúdio.';
    });

  const menuButton = $("mobileMenu");
  let menu;
  menuButton.addEventListener("click", () => {
    if (!menu) {
      menu = document.createElement("nav");
      menu.className = "mobile-nav-panel";
      menu.innerHTML = '<a href="#como-funciona">Como funciona</a><a href="#recursos">Recursos</a><a href="#planos">Acesso</a><a href="#duvidas">Dúvidas</a><a class="mobile-nav-cta" href="/app/">Abrir estúdio ↗</a>';
      document.querySelector(".site-header").appendChild(menu);
      menu.querySelectorAll("a").forEach(link => link.addEventListener("click", () => {
        menu.classList.remove("open");
        menuButton.setAttribute("aria-expanded", "false");
      }));
    }
    const open = menu.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", String(open));
    menuButton.textContent = open ? "×" : "☰";
  });
})();