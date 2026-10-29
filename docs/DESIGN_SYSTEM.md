# Design system TCC·FH

Interface escura, offline e sem Bootstrap nas telas redesenhadas (o arquivo `bootstrap.min.css` continua em
`static/`, usado apenas pelo admin do Django se necessário; nenhuma página do app o carrega mais).

## Arquivos
| Arquivo | Papel |
|---|---|
| `static/avaliacao/tema.css` | Tokens (`:root`), base, shell (sidebar/topbar), componentes. Camadas `@layer tokens, base, layout, components, pages, utilities`. |
| `dashboard.css` / `questionario.css` / `inicio.css` / `login.css` | Estilos por página (camada `pages`). |
| `app.js` | Menu lateral (recolher/mobile), menu da conta, avisos, modal de confirmação, estado de envio, saudação, mostrar senha. |
| `dashboard.js` | Chart.js (opções, plugins de faixas e rótulos). Só lê `#dashboard-dados`. |
| `questionario.js` | Progresso ao vivo, contador, estados visuais, aviso de alterações não salvas. |
| `shell-init.js` | Restaura o estado do menu antes da pintura. |
| `fonts/` | Manrope variável (OFL) embarcada. |
| `templatetags/ui.py` | Filtros/tags só de apresentação (`pct`, `campo`, `niveis`, `progresso`, `tom_risco`...). Somente leitura. |
| `templates/avaliacao/componentes/` | `icones.html` (sprite SVG), `campo.html`, `gauge.html`, `painel_grafico.html`. |

## Convenções
- Cores, raios, sombras, tempos e espaços só por variáveis CSS (`--blue`, `--r-lg`, `--sh-2`, `--sp-4`...).
- Valores de barras vêm de `--p` (0–100) calculado pelo filtro `pct`; não depende de JavaScript.
- Confirmação em modal: `<form data-confirm="..." data-confirm-titulo="..." data-confirm-ok="..." data-confirm-tom="perigo|ok|info">`.
  Sem JavaScript o formulário envia direto (comportamento anterior).
- Risco nunca só por cor: toda cor acompanha texto/ícone (classe do RSDM, "Nível N", "Mandatório").
- Movimento respeita `prefers-reduced-motion`; não há animações infinitas.
