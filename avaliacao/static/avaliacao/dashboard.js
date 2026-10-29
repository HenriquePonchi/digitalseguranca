"use strict";
/* Gráficos do dashboard. Lê só o JSON entregue pelo backend (#dashboard-dados); não calcula indicadores. */
(() => {
  const fonte = document.getElementById("dashboard-dados");
  if (!fonte) return;
  const graficos = JSON.parse(fonte.textContent);
  const css = getComputedStyle(document.documentElement);
  const v = (nome) => css.getPropertyValue(nome).trim();
  const cor = {texto: v("--text"), texto2: v("--text-2"), azul: v("--blue"), ciano: v("--cyan"), violeta: v("--violet"),
               aviso: v("--warn"), perigo: v("--danger"), tooltip: "#1c2740", linha: "rgba(148,163,184,.14)", borda: "rgba(148,163,184,.28)"};
  const reduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const n2 = new Intl.NumberFormat("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});

  const indisponivel = (canvas, texto) => {
    canvas.hidden = true;
    const vazio = canvas.parentElement.querySelector(".chart-empty");
    if (vazio) { vazio.hidden = false; if (texto) vazio.querySelector("p").textContent = texto; }
    const detalhes = canvas.closest(".painel").querySelector("details.valores");
    if (texto && detalhes) detalhes.open = true;
  };

  if (typeof Chart === "undefined") {
    graficos.forEach((_, i) => {
      const c = document.getElementById(`dashboard-grafico-${i}`);
      if (c) indisponivel(c, "Gráfico indisponível. Consulte os valores na tabela abaixo.");
    });
    return;
  }

  Chart.defaults.font.family = v("--font") || "system-ui, sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.font.weight = 600;
  Chart.defaults.color = cor.texto2;

  const degrade = (ctx, de, para, horizontal) => {
    const area = ctx.chart.chartArea;
    if (!area) return para;
    const g = horizontal ? ctx.chart.ctx.createLinearGradient(area.left, 0, area.right, 0)
                         : ctx.chart.ctx.createLinearGradient(0, area.bottom, 0, area.top);
    g.addColorStop(0, de); g.addColorStop(1, para);
    return g;
  };

  /* faixas de referência: limites de classe do score geral (1,75 · 2,50 · 3,25) */
  const faixas = {
    id: "faixasMaturidade",
    beforeDatasetsDraw(chart) {
      const {ctx, chartArea: a, scales: {y}} = chart;
      if (!y) return;
      const lim = [[1, 1.75, "Inicial"], [1.75, 2.5, "Intermediário"], [2.5, 3.25, "Gerenciado"], [3.25, 4, "Otimizado"]];
      ctx.save();
      lim.forEach(([lo, hi, nome], i) => {
        const y1 = y.getPixelForValue(hi), y2 = y.getPixelForValue(lo);
        if (i % 2 === 0) { ctx.fillStyle = "rgba(255,255,255,.022)"; ctx.fillRect(a.left, y1, a.right - a.left, y2 - y1); }
        if (chart.$rotulosFaixa) {
          ctx.fillStyle = "rgba(148,163,184,.85)"; ctx.font = "600 10.5px " + Chart.defaults.font.family;
          ctx.textAlign = "left"; ctx.textBaseline = "middle";
          ctx.fillText(nome, a.right + 10, (y1 + y2) / 2);
        }
      });
      ctx.setLineDash([4, 5]); ctx.strokeStyle = "rgba(148,163,184,.4)"; ctx.lineWidth = 1;
      [1.75, 2.5, 3.25].forEach((valor) => {
        const py = Math.round(y.getPixelForValue(valor)) + .5;
        ctx.beginPath(); ctx.moveTo(a.left, py); ctx.lineTo(a.right, py); ctx.stroke();
      });
      ctx.restore();
    }
  };

  /* valor escrito junto de cada barra (o valor nunca depende só da cor) */
  const rotulos = {
    id: "rotulosValor",
    afterDatasetsDraw(chart, _args, opcoes) {
      const meta = chart.getDatasetMeta(0), dados = chart.data.datasets[0].data;
      const {ctx} = chart;
      ctx.save();
      ctx.fillStyle = cor.texto; ctx.font = "800 12.5px " + Chart.defaults.font.family;
      meta.data.forEach((barra, i) => {
        if (dados[i] === null || dados[i] === undefined) return;
        const texto = opcoes.formatar(dados[i]);
        if (opcoes.horizontal) { ctx.textAlign = "left"; ctx.textBaseline = "middle"; ctx.fillText(texto, barra.x + 10, barra.y); }
        else { ctx.textAlign = "center"; ctx.textBaseline = "bottom"; ctx.fillText(texto, barra.x, barra.y - 8); }
      });
      ctx.restore();
    }
  };

  graficos.forEach((dado, i) => {
    const canvas = document.getElementById(`dashboard-grafico-${i}`);
    if (!canvas) return;
    if (dado.sem_dados || dado.valores.every((x) => x === null)) { indisponivel(canvas); return; }

    const radar = dado.tipo === "radar";
    const horizontal = !radar && !!dado.percentual;
    const estreito = canvas.parentElement.clientWidth < 480;
    const maturidade = !radar && !dado.percentual && !dado.contagem;
    const formatar = (x) => dado.percentual ? n2.format(x) + "%" : dado.contagem ? String(x) : n2.format(x);

    const conjunto = radar ? {
      label: dado.titulo, data: dado.valores, spanGaps: false,
      backgroundColor: "rgba(34,211,238,.16)", borderColor: cor.ciano, borderWidth: 2.5,
      pointBackgroundColor: cor.ciano, pointBorderColor: "#0D1220", pointBorderWidth: 2, pointRadius: 5, pointHoverRadius: 7
    } : {
      label: dado.titulo, data: dado.valores, borderRadius: 9, borderSkipped: false, maxBarThickness: horizontal ? 38 : 54,
      backgroundColor: (ctx) => horizontal ? degrade(ctx, "rgba(251,191,36,.55)", cor.perigo, true)
        : dado.contagem ? degrade(ctx, "rgba(59,130,246,.45)", cor.violeta)
        : degrade(ctx, "rgba(59,130,246,.45)", cor.ciano)
    };

    const escala = {beginAtZero: true, min: 0, max: dado.contagem ? undefined : dado.percentual ? 100 : 4,
      grid: {color: cor.linha, drawTicks: false}, border: {display: false},
      ticks: {precision: dado.contagem ? 0 : undefined, padding: 8, color: cor.texto2,
              stepSize: radar || maturidade ? 1 : undefined, backdropColor: "transparent",
              callback: (x) => dado.percentual ? x + "%" : x}};
    const opcoesEscalas = radar
      ? {r: {...escala, angleLines: {color: cor.linha}, pointLabels: {color: cor.texto, font: {size: estreito ? 10 : 12, weight: 700}}}}
      : horizontal ? {x: escala, y: {grid: {display: false}, border: {display: false}, ticks: {color: cor.texto, font: {weight: 700}, padding: 6}}}
      : {y: escala, x: {grid: {display: false}, border: {color: cor.borda}, ticks: {color: cor.texto, font: {size: estreito ? 10 : 12, weight: 700}, maxRotation: 0, autoSkip: false,
          callback(valor) { const r = this.getLabelForValue(valor); if (typeof r !== "string" || !r.includes(" · ")) return r; const [cod, nome] = r.split(" · "); return estreito ? cod : [cod, nome]; }}}};

    const grafico = new Chart(canvas, {
      type: dado.tipo,
      data: {labels: dado.labels, datasets: [conjunto]},
      plugins: [...(maturidade ? [faixas] : []), ...(!radar ? [rotulos] : [])],
      options: {
        responsive: true, maintainAspectRatio: false, indexAxis: horizontal ? "y" : "x",
        layout: {padding: {top: radar ? 0 : 26, right: maturidade && !estreito ? 96 : horizontal ? 56 : 8}},
        animation: reduzido ? false : {duration: 950, easing: "easeOutQuart",
          delay: (ctx) => ctx.type === "data" && ctx.mode === "default" && !ctx.dropped ? ctx.dataIndex * 70 : 0},
        plugins: {
          legend: {display: false},
          rotulosValor: {formatar, horizontal},
          tooltip: {backgroundColor: cor.tooltip, borderColor: cor.borda, borderWidth: 1, padding: 12, cornerRadius: 10, displayColors: false,
            titleColor: cor.texto, titleFont: {weight: 800, size: 13}, bodyColor: cor.texto, bodyFont: {weight: 600, size: 12.5}, caretSize: 6,
            callbacks: {label: (ctx) => ctx.parsed === null || (ctx.parsed.y ?? ctx.parsed.r ?? ctx.parsed.x) === null ? "Sem dados aplicáveis"
              : dado.percentual ? `${n2.format(ctx.parsed.x)}%` : dado.contagem ? `${ctx.parsed.y} controle(s)` : `Maturidade ${n2.format(ctx.parsed.y ?? ctx.parsed.r)} de 4`}}
        },
        scales: opcoesEscalas
      }
    });
    grafico.$rotulosFaixa = maturidade && !estreito;
    grafico.update("none");
  });
})();
