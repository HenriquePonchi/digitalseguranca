"use strict";
/* TCC·FH — comportamento global: menu lateral, menu da conta, avisos, confirmações, estado de envio. */
(() => {
  const root = document.documentElement;
  const body = document.body;
  const desktop = window.matchMedia("(min-width:1024px)");
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
  const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* sem armazenamento */ } };

  /* ---------- menu lateral ---------- */
  const abrir = $("#sb-open"), recolher = $("#sb-toggle"), sidebar = $("#sidebar");
  const fecharMobile = (devolverFoco) => {
    if (!body.classList.contains("sb-open")) return;
    body.classList.remove("sb-open");
    abrir && abrir.setAttribute("aria-expanded", "false");
    if (devolverFoco && abrir) abrir.focus();
  };
  if (abrir && sidebar) {
    abrir.addEventListener("click", () => {
      body.classList.add("sb-open");
      abrir.setAttribute("aria-expanded", "true");
      const primeiro = $(".nav-link", sidebar); primeiro && primeiro.focus();
    });
    $$("[data-sb-close]").forEach(el => el.addEventListener("click", () => fecharMobile(true)));
    $$(".nav-link", sidebar).forEach(a => a.addEventListener("click", () => fecharMobile(false)));
    desktop.addEventListener("change", () => fecharMobile(false));
  }
  if (recolher) {
    const aplicar = (min) => {
      root.classList.toggle("sb-collapsed", min);
      recolher.setAttribute("aria-pressed", String(min));
      recolher.setAttribute("aria-label", min ? "Expandir menu lateral" : "Recolher menu lateral");
    };
    aplicar(root.classList.contains("sb-collapsed"));
    recolher.addEventListener("click", () => {
      const min = !root.classList.contains("sb-collapsed");
      aplicar(min); guardar("tccfh.sb", min ? "min" : "full");
    });
  }

  /* ---------- menu da conta ---------- */
  const menu = $("#user-menu");
  if (menu) {
    document.addEventListener("click", (e) => { if (menu.open && !menu.contains(e.target)) menu.open = false; });
    menu.addEventListener("keydown", (e) => { if (e.key === "Escape" && menu.open) { menu.open = false; $("summary", menu).focus(); } });
  }
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") fecharMobile(true); });

  /* ---------- avisos ---------- */
  const dispensar = (aviso) => {
    aviso.classList.add("is-saindo");
    setTimeout(() => aviso.remove(), 220);
  };
  $$("[data-fechar-aviso]").forEach(b => b.addEventListener("click", () => dispensar(b.closest(".aviso"))));
  $$(".aviso--success").forEach(a => setTimeout(() => a.isConnected && dispensar(a), 8000));

  /* ---------- confirmação em modal (progressivo: sem JS o formulário envia direto, como antes) ---------- */
  const dlg = $("#dlg-confirmar");
  if (dlg && typeof dlg.showModal === "function") {
    const titulo = $("#dlg-titulo"), texto = $("#dlg-texto"), ok = $("#dlg-ok"), cancelar = $("#dlg-cancelar");
    const icone = $(".modal__ico use", dlg);
    const tons = {
      perigo: ["modal--perigo", "btn btn--danger-solid", "#i-trash"],
      ok: ["modal--ok", "btn btn--ok", "#i-shield-check"],
      info: ["", "btn btn--primary", "#i-info"],
    };
    let pendente = null, gatilho = null;
    document.addEventListener("submit", (e) => {
      const form = e.target;
      if (!form.matches || !form.matches("form[data-confirm]") || form.dataset.confirmado === "1") return;
      e.preventDefault();
      pendente = { form, submitter: e.submitter };
      gatilho = document.activeElement;
      const tom = tons[form.dataset.confirmTom] || tons.info;
      dlg.classList.remove("modal--perigo", "modal--ok");
      if (tom[0]) dlg.classList.add(tom[0]);
      ok.className = tom[1];
      icone.setAttribute("href", tom[2]);
      titulo.textContent = form.dataset.confirmTitulo || "Confirmar ação";
      texto.textContent = form.dataset.confirm;
      ok.textContent = form.dataset.confirmOk || "Confirmar";
      dlg.showModal();
      cancelar.focus();
    });
    dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close("cancelar"); });
    dlg.addEventListener("close", () => {
      const alvo = pendente; pendente = null;
      if (alvo && dlg.returnValue === "confirmar") {
        alvo.form.dataset.confirmado = "1";
        alvo.form.requestSubmit(alvo.submitter || undefined);
      } else if (gatilho && gatilho.focus) gatilho.focus();
      dlg.returnValue = "";
    });
  }

  /* ---------- estado de envio (evita duplo clique e mostra progresso) ---------- */
  document.addEventListener("submit", (e) => {
    if (e.defaultPrevented) return;
    const form = e.target;
    if (!form.matches || form.matches("[data-sem-carregando]") || form.method === "dialog") return;
    if (form.dataset.enviando === "1") { e.preventDefault(); return; }
    form.dataset.enviando = "1";
    const botao = e.submitter || $("button[type=submit],button:not([type])", form);
    if (botao) setTimeout(() => { botao.classList.add("is-loading"); botao.setAttribute("aria-busy", "true"); }, 0);
  });
  window.addEventListener("pageshow", (e) => {
    if (!e.persisted) return;
    $$("form[data-enviando]").forEach(f => { delete f.dataset.enviando; delete f.dataset.confirmado; });
    $$(".is-loading").forEach(b => { b.classList.remove("is-loading"); b.removeAttribute("aria-busy"); });
  });

  /* ---------- saudação contextual ---------- */
  $$("[data-saudacao]").forEach(el => {
    const h = new Date().getHours();
    el.textContent = h < 5 ? "Boa madrugada" : h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite";
  });

  /* ---------- mostrar/ocultar senha ---------- */
  $$("[data-toggle-senha]").forEach(btn => {
    const campo = document.getElementById(btn.getAttribute("aria-controls"));
    if (!campo) return;
    btn.hidden = false;
    btn.addEventListener("click", () => {
      const ver = campo.type === "password";
      campo.type = ver ? "text" : "password";
      btn.setAttribute("aria-pressed", String(ver));
      btn.setAttribute("aria-label", ver ? "Ocultar senha" : "Mostrar senha");
    });
  });
})();
