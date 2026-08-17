# Painel Rápido de Campanhas — CleverTap

Painel simplificado de análise de campanhas (push e in-app) do Cartão de TODOS.
Um único `index.html`, sem build: abre em qualquer navegador e consome ao vivo a
API do painel original (`relatorio-campanhas-clevertap.onrender.com`).

## O que ele faz

- **Período**: presets (Hoje, Ontem, 7, 15, 30 dias, Este mês) ou datas manuais
- **Filtros instantâneos** (client-side): tipo (push × in-app), labels
  (**todas as labels encontradas nas campanhas**, com contagem), status e busca por nome/ID
- **KPIs** do recorte: campanhas, envios, impressões, cliques e CTR (cliques ÷ envios)
- **Gráfico diário** com métrica alternável (envios/impressões/cliques/CTR) + visão em tabela
- **Tabela ordenável** com detalhe por campanha (dia a dia, evento de conversão, ID)
- **Exportar CSV** e **Copiar IDs** do recorte filtrado
- **Conversão por evento** (respeita período + labels selecionadas)

Períodos longos são consultados **mês a mês, em sequência** (limite da API/CleverTap),
com indicador de progresso. Dados disponíveis a partir de **jan/2026**.

## Publicação

### GitHub Pages
Settings → Pages → *Deploy from a branch* → `main` / `(root)`.
URL: `https://victoroliveirageral-alt.github.io/report-campanhas-rapido/`

### Render (opcional)
O `render.yaml` já deixa a configuração versionada:

- Type: Static Site
- Name: `report-campanhas-rapido`
- Branch: `main`
- Build Command: `echo "No build step"`
- Publish Directory: `.`

## Fonte de dados

- `GET /api/dashboard?from=YYYY-MM-DD&to=YYYY-MM-DD` — campanhas, diário, labels, eventos
- `POST /api/conversao-geral` — eventos disparados e perfis únicos do evento escolhido

O servidor do Render pode "dormir": a primeira consulta do dia leva até ~1 min.
