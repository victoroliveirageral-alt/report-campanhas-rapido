# Painel App Launched (atualização automática)

URL: https://report-campanhas-rapido.onrender.com/app-launched/

## Como se atualiza
1. GitHub Actions (`.github/workflows/atualizar-app-launched.yml`) roda às 04:30 BRT, com repescagem às 08:30.
2. `atualizar.py` consulta `/api/conversao-geral` do backend: dias que faltam + reconsulta dos 3 últimos, períodos do D-1 (dias corridos e calendário) e até 4 dias de horário por noite (amostragem por CT Session Id).
3. Grava `dados.json` e faz commit só se mudou. O Render publica sozinho (auto-deploy por commit).
4. O `index.html` lê `dados.json`. Se estiver em dia, não chama a API; se estiver atrasado, tenta a API ao vivo; se nada responder, mostra o retrato embutido.

## Regras do script
- Falha nunca vira zero: consulta que falha mantém o valor anterior.
- Se o D-1 não vier da API, o job falha e nada é gravado (aparece em Actions).
- Horário só é gravado quando todas as 24 horas têm amostra.

## Rodar na mão
Actions > Atualizar painel App Launched > Run workflow. Ou local: `python app-launched/atualizar.py`.
