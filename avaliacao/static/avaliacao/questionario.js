"use strict";
/* Questionário: progresso ao vivo, contador, estados visuais e aviso de alterações não salvas.
   Não altera nomes nem valores dos campos: o envio continua sendo o POST original. */
(() => {
  const form = document.getElementById("form-questionario");
  if (!form) return;
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
  const cartoes = $$("[data-controle]", form);
  const total = Number(form.dataset.total) || cartoes.length;
  const progresso = $("[data-etapa-resp]");
  const sujo = $("[data-sujo]");

  const valorDe = (cartao) => { const r = $("input[type=radio]:checked", cartao); return r ? r.value : ""; };
  const atualizar = () => {
    let feitos = 0;
    cartoes.forEach((c) => {
      const v = valorDe(c);
      c.classList.toggle("is-answered", v !== "");
      c.classList.toggle("is-na", v === "NA");
      const txt = $("[data-estado-txt]", c);
      if (txt) txt.textContent = v === "" ? "Pendente" : "Respondido";
      if (v !== "") feitos += 1;
      const area = $("textarea", c), cont = $("[data-contador]", c);
      if (area && cont) cont.textContent = `${area.value.length}/${cont.dataset.max}`;
    });
    if (progresso) progresso.textContent = `${feitos} de ${total} respondidos nesta etapa`;
  };

  /* alterações não salvas */
  const instantaneo = () => Array.from(new FormData(form).entries()).filter(([k]) => k !== "csrfmiddlewaretoken").map(([k, v]) => `${k}=${v}`).join("&");
  const inicial = instantaneo();
  let alterado = false;
  const checar = () => {
    alterado = instantaneo() !== inicial;
    if (sujo) sujo.hidden = !alterado;
  };
  form.addEventListener("input", () => { atualizar(); checar(); });
  form.addEventListener("change", () => { atualizar(); checar(); });
  form.addEventListener("submit", () => { alterado = false; });
  window.addEventListener("beforeunload", (e) => { if (alterado) { e.preventDefault(); e.returnValue = ""; } });

  /* finalizar: avisa se há alterações pendentes nesta etapa (não são salvas por finalizar) */
  const finalizar = document.getElementById("form-finalizar");
  if (finalizar) {
    const base = finalizar.dataset.confirm;
    finalizar.addEventListener("submit", () => {
      if (finalizar.dataset.confirmado === "1") { alterado = false; return; }
      finalizar.dataset.confirm = alterado ? base + " Atenção: as alterações não salvas nesta etapa serão descartadas." : base;
    });
  }

  atualizar();
  const erro = $(".campo--erro textarea, .campo--erro input", form);
  if (erro) { erro.scrollIntoView({block: "center"}); erro.focus({preventScroll: true}); }
})();
