#!/usr/bin/env python3
"""Atualiza app-launched/dados.json a partir do backend relatorio-campanhas-clevertap.

Roda todo dia pelo GitHub Actions (madrugada BRT). Só biblioteca padrão.
Regras:
- nunca grava zero no lugar de falha: consulta que falha mantém o valor anterior
- reconsulta os 3 últimos dias (D-1, D-2, D-3), o resto fica guardado
- consulta os períodos (semana/quinzena/mês nos dois modos) do D-1 atual
- horário: até MAX_DIAS_HORA dias por execução, amostragem de 1 segundo por minuto
Saída != 0 só se D-1 não vier da API (aí o workflow falha e o arquivo não muda).
"""
import json, os, sys, time, datetime as dt, urllib.request, concurrent.futures as cf, calendar

API = os.environ.get("API", "https://relatorio-campanhas-clevertap.onrender.com").rstrip("/")
EVENTO = "App Launched"
ARQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados.json")
DIAS_SERIE, DIAS_GUARDADOS, DIAS_HORA = 120, 150, 28
MAX_DIAS_HORA = int(os.environ.get("MAX_DIAS_HORA", "4"))
CONC, CONC_HORA = 3, 3
BRT = dt.timezone(dt.timedelta(hours=-3))


def post(filtros, de, ate, tentativas=5):
    corpo = json.dumps({"from": de, "to": ate, "labels": [], "evento": {"nome": EVENTO, "filtros": filtros}}).encode()
    for t in range(tentativas):
        try:
            req = urllib.request.Request(API + "/api/conversao-geral", corpo, {"Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=150))
            if d.get("sucesso") and isinstance(d.get("eventos_disparados"), int) and isinstance(d.get("perfis_unicos"), int):
                if filtros and not (d.get("filtros") and len(d["filtros"][0].get("value", [])) == len(filtros[0]["value"])):
                    raise ValueError("backend não aplicou o filtro inteiro")
                return d
        except Exception as e:
            print(f"  tentativa {t+1} {de}..{ate}: {e}", file=sys.stderr)
        time.sleep(3 * (t + 1))
    return None


def add(s, n):
    return (dt.date.fromisoformat(s) + dt.timedelta(days=n)).isoformat()


def periodos(d1):
    """Mesma lógica de periodos() do index.html, nos dois modos."""
    pares = [(d1, d1), (add(d1, -7), add(d1, -7))]
    pares += [(add(d1, -6), d1), (add(d1, -13), add(d1, -7)),
              (add(d1, -14), d1), (add(d1, -29), add(d1, -15)),
              (add(d1, -29), d1), (add(d1, -59), add(d1, -30))]
    D = dt.date.fromisoformat(d1)
    seg = add(d1, -D.weekday())
    pares += [(seg, d1), (add(seg, -7), add(d1, -7))]
    y, m, d = D.year, D.month, D.day
    py, pm = (y - 1, 12) if m == 1 else (y, m - 1)
    ult_pm = calendar.monthrange(py, pm)[1]
    q_ini = 1 if d <= 15 else 16
    ql = d - q_ini + 1
    pares.append((f"{y}-{m:02d}-{q_ini:02d}", d1))
    if q_ini == 16:
        pares.append((f"{y}-{m:02d}-01", f"{y}-{m:02d}-{min(ql, 15):02d}"))
    else:
        pares.append((f"{py}-{pm:02d}-16", f"{py}-{pm:02d}-{min(15 + ql, ult_pm):02d}"))
    pares += [(f"{y}-{m:02d}-01", d1), (f"{py}-{pm:02d}-01", f"{py}-{pm:02d}-{min(d, ult_pm):02d}")]
    return list(dict.fromkeys(pares))


def amostrar_dia(dia):
    tarefas = []
    for h in range(24):
        base = int(dt.datetime.fromisoformat(dia).replace(hour=h, tzinfo=BRT).timestamp())
        segs = [str(base + mi * 60 + ((mi * 37 + h * 11) % 60)) for mi in range(60)]
        for i in range(0, 60, 20):
            tarefas.append((h, segs[i:i + 20]))
    with cf.ThreadPoolExecutor(CONC_HORA) as ex:
        res = list(ex.map(lambda t: post([{"name": "CT Session Id", "operator": "equals", "value": t[1]}], dia, dia, 4), tarefas))
    a, ok = [0] * 24, [0] * 24
    for (h, _), r in zip(tarefas, res):
        if r:
            a[h] += r["eventos_disparados"]
            ok[h] += 1
    return {"a": a, "ok": ok} if all(ok) else None


def main():
    t0 = time.time()
    dados = json.load(open(ARQ)) if os.path.exists(ARQ) else {}
    consultas = dados.get("consultas", {})
    horas = dados.get("horas", {})
    hoje = dt.datetime.now(BRT).date().isoformat()
    d1 = add(hoje, -1)
    print(f"D-1 = {d1}")

    # acorda o backend (Render free)
    try:
        urllib.request.urlopen(API + "/health", timeout=90).read()
    except Exception as e:
        print("health:", e, file=sys.stderr)

    # dias: busca os que faltam + reconsulta os 3 últimos
    dias = [add(d1, -i) for i in range(DIAS_SERIE)]
    buscar = [d for d in dias if f"{d}|{d}" not in consultas or d >= add(d1, -2)]
    # períodos do D-1 atual (ranges mudam todo dia)
    pares = [(d, d) for d in buscar] + [p for p in periodos(d1) if p[0] != p[1]]
    print(f"consultas: {len(pares)}")
    with cf.ThreadPoolExecutor(CONC) as ex:
        res = list(ex.map(lambda p: post([], p[0], p[1]), pares))
    falhas = 0
    for (de, ate), r in zip(pares, res):
        if r:
            consultas[f"{de}|{ate}"] = [r["eventos_disparados"], r["perfis_unicos"]]
        else:
            falhas += 1
    if f"{d1}|{d1}" not in consultas:
        print("D-1 não veio da API; nada gravado", file=sys.stderr)
        sys.exit(1)

    # limpeza: dias antigos e ranges que não são do D-1 atual
    corte = add(d1, -(DIAS_GUARDADOS - 1))
    atuais = {f"{a}|{b}" for a, b in periodos(d1)}
    consultas = {k: v for k, v in consultas.items()
                 if (k.split("|")[0] == k.split("|")[1] and k.split("|")[0] >= corte) or k in atuais}

    # horário: preenche os dias mais recentes que faltam
    janela = [add(d1, -i) for i in range(DIAS_HORA)]
    horas = {k: v for k, v in horas.items() if k in janela}
    faltam = [d for d in janela if d not in horas][:MAX_DIAS_HORA]
    for d in faltam:
        t1 = time.time()
        r = amostrar_dia(d)
        if r:
            horas[d] = r
            est = sum(c * 3600 / (20 * o) for c, o in zip(r["a"], r["ok"]))
            real = consultas.get(f"{d}|{d}", [None])[0]
            print(f"horário {d}: {round(time.time()-t1)}s, soma {round(est)} vs real {real}")
        else:
            print(f"horário {d}: incompleto, fica para a próxima", file=sys.stderr)

    novo = {
        "evento": EVENTO,
        "d1": d1,
        "gerado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "consultas": dict(sorted(consultas.items())),
        "horas": dict(sorted(horas.items())),
        "horas_metodo": "CT Session Id equals: 1 segundo por minuto (60/3600), x60",
    }
    json.dump(novo, open(ARQ, "w"), separators=(",", ":"))
    print(f"ok em {round(time.time()-t0)}s; falhas {falhas}; dias com horário {len(horas)}/{DIAS_HORA}")


if __name__ == "__main__":
    main()
