#!/usr/bin/env python3
"""Contas automáticas de teste do LEXDESK: Tomás Ferreira, Inês Carvalho e Rodrigo Matos.

Abrem o site com uma base de dados simulada (nunca tocam nos dados reais) e:
  - Tomás Ferreira (explorador): percorre todas as páginas (computador e telemóvel, claro e escuro) e carrega nos botões;
  - Inês Carvalho (calculista): testa as calculadoras com valores normais, extremos e inválidos, e confere resultados conhecidos;
  - Rodrigo Matos (estudante): faz uma simulação de exame, uma sessão de flashcards e abre casos práticos.

Uso:  python tests/robos.py [caminho/para/index.html] [--rapido]
Gera robos-relatorio.json e robos-relatorio.md e termina com código 1 se encontrar erros.
"""
import asyncio, json, os, sys, time, pathlib, datetime, hashlib, threading, functools, http.server, socketserver
from playwright.async_api import async_playwright

AQUI = pathlib.Path(__file__).resolve().parent
INDEX = pathlib.Path(next((a for a in sys.argv[1:] if not a.startswith('--')), AQUI.parent / 'index.html')).resolve()
RAPIDO = '--rapido' in sys.argv
MOCK = (AQUI / 'mock_supabase.js').read_text(encoding='utf-8')
INIT = "localStorage.setItem('lexdesk_sessao','on'); localStorage.setItem('lexdesk_onb','feito');"

VISTAS = ['painel', 'reputacao', 'flashcards', 'aula', 'lei', 'guias', 'glossario', 'calcheranca', 'calculadoras', 'mapapp', 'mapapc',
          'meet', 'instituicoes', 'atualidade', 'connect', 'chat', 'mensagens', 'salas', 'legal', 'prazos', 'agenda', 'dissertacao', 'ordem',
          'docente', 'apontamentos', 'cadeiras', 'workspaces', 'biblioteca', 'exames', 'casos', 'minutas']
# ações que não fazem sentido carregar às cegas (saem da sessão, apagam, abrem janelas do sistema)
EVITAR = ('sair', 'logout', 'apagar', 'eliminar', 'del', 'remov', 'limpar', 'print', 'imprimir', 'download', 'export', 'descarregar',
          'copiar', 'upload', 'ficheiro', 'gravar', 'microfone', 'partilhar', 'conta-', 'login', 'exam-quit', 'tema')
LIXO = ('NaN', 'Infinity', 'undefined', 'Invalid Date', '[object Object]')

class _Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def servir():
    """Serve a pasta do site por HTTP local, como no GitHub Pages."""
    h = functools.partial(_Silencioso, directory=str(INDEX.parent))
    srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), h)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{srv.server_address[1]}/{INDEX.name}'


URL = None
problemas = []   # {robo, onde, tipo, detalhe}
feito = {'explorador': 0, 'calculista': 0, 'estudante': 0}
NOMES = {'explorador': 'Tomás Ferreira', 'calculista': 'Inês Carvalho', 'estudante': 'Rodrigo Matos'}


def problema(robo, onde, tipo, detalhe):
    chave = (robo, onde, tipo, str(detalhe)[:200])
    if any((p['robo'], p['onde'], p['tipo'], p['detalhe'][:200]) == chave for p in problemas):
        return
    problemas.append({'robo': robo, 'onde': onde, 'tipo': tipo, 'detalhe': str(detalhe)[:600]})
    print(f'  ✗ [{robo}] {onde}: {tipo} — {str(detalhe)[:160]}', flush=True)


async def nova_pagina(b, W, H, escuro=False, movel=False):
    ctx = await b.new_context(viewport={'width': W, 'height': H}, is_mobile=movel, has_touch=movel)
    await ctx.add_init_script(INIT + ("localStorage.setItem('lexdesk_tema','escuro');" if escuro else "localStorage.setItem('lexdesk_tema','claro');"))
    pg = await ctx.new_page()
    pg._erros = []
    pg.on('pageerror', lambda e: pg._erros.append(str(e)))
    pg.on('console', lambda m: pg._erros.append('console: ' + m.text) if m.type == 'error' and 'net::' not in m.text and 'Failed to load resource' not in m.text else None)
    pg.on('dialog', lambda d: asyncio.ensure_future(d.dismiss()))
    await pg.route('**/supabase.js', lambda r: r.fulfill(body=MOCK, content_type='application/javascript'))
    await pg.route('**/*.supabase.co/**', lambda r: r.abort())
    await pg.goto(URL)
    await pg.wait_for_timeout(2000)
    if await pg.locator('[data-a="bv-cont"]').count():
        await pg.locator('[data-a="bv-cont"]').first.click()
        await pg.wait_for_timeout(400)
    return ctx, pg


def tirar_erros(pg):
    e = pg._erros[:]
    pg._erros.clear()
    return e


async def ir(pg, vista):
    await pg.evaluate("v => { location.hash = '#' + v; }", vista)
    await pg.wait_for_timeout(450)


async def fechar_modal(pg):
    for _ in range(3):
        if not await pg.locator('#ov, .modal').count():
            return
        await pg.keyboard.press('Escape')
        await pg.wait_for_timeout(150)


async def verificar_vista(pg, robo, onde, W):
    for e in tirar_erros(pg):
        problema(robo, onde, 'erro de JavaScript', e)
    info = await pg.evaluate("""() => { const m = document.querySelector('.main'); return {
        sw: document.documentElement.scrollWidth, txt: m ? m.innerText.trim().length : -1,
        lixo: m ? m.innerText.match(/\\b(NaN|undefined|Infinity|Invalid Date)\\b|\\[object Object\\]/) : null } }""")
    if info['sw'] > W + 2:
        problema(robo, onde, 'conteúdo sai do ecrã', f"largura {info['sw']}px num ecrã de {W}px")
    if info['txt'] == 0:
        problema(robo, onde, 'página vazia', 'a área principal não tem conteúdo')
    if info['lixo']:
        problema(robo, onde, 'texto inválido no ecrã', info['lixo'][0])


# ---------------- Robô Explorador ----------------
async def explorador(b):
    configs = [(1440, 900, False, False, 'computador claro'), (390, 844, False, True, 'telemóvel claro')]
    if not RAPIDO:
        configs += [(1440, 900, True, False, 'computador escuro'), (390, 844, True, True, 'telemóvel escuro')]
    for W, H, escuro, movel, nome in configs:
        ctx, pg = await nova_pagina(b, W, H, escuro, movel)
        for v in VISTAS:
            await ir(pg, v)
            await verificar_vista(pg, 'explorador', f'{v} ({nome})', W)
            feito['explorador'] += 1
        await ctx.close()
    # botões, só no computador em modo claro
    ctx, pg = await nova_pagina(b, 1440, 900)
    for v in VISTAS:
        await ir(pg, v)
        alvos = await pg.evaluate("""(evitar) => [...document.querySelectorAll('.main [data-a], .main [data-go]')]
            .filter(e => e.offsetParent && !e.disabled)
            .map(e => e.dataset.a ? ['a', e.dataset.a, e.dataset.id || ''] : ['go', e.dataset.go, ''])
            .filter(x => !evitar.some(k => x[1].toLowerCase().includes(k)))
            .filter((x, i, l) => l.findIndex(y => y[0] === x[0] && y[1] === x[1]) === i).slice(0, 25)""", list(EVITAR))
        for tipo, nome_acao, ident in alvos:
            sel = f'.main [data-{tipo}="{nome_acao}"]' + (f'[data-id="{ident}"]' if ident and '"' not in ident else '')
            try:
                await pg.locator(sel).first.click(timeout=1500)
                await pg.wait_for_timeout(200)
            except Exception:
                pass
            for e in tirar_erros(pg):
                problema('explorador', f'{v} → botão {nome_acao}', 'erro de JavaScript', e)
            feito['explorador'] += 1
            await fechar_modal(pg)
            if await pg.evaluate("location.hash") != '#' + v:
                await ir(pg, v)
    await ctx.close()


# ---------------- Robô Calculista ----------------
CASOS_CALC = {
    'custas': [({'valor': '30000'}, '510,00'), ({'valor': '300000'}, None), ({'valor': '0'}, None), ({'valor': '-5'}, None), ({'valor': 'abc'}, None)],
    'recurso': [({'valor': '12000', 'suc': '3000'}, 'Admissível'), ({'valor': '4000'}, 'Não admissível'), ({'valor': ''}, None)],
    'tribunal': [({'valor': '60000'}, 'Juízo central cível'), ({'valor': '10000'}, 'Juízo local cível'), ({'valor': '1e309'}, None)],
    'juros': [({'cap': '5000', 'ini': '2024-03-15', 'fim': '2026-11-20'}, '536,99'), ({'cap': '5000', 'ini': '2026-11-20', 'fim': '2024-01-01'}, None), ({'cap': '0'}, None)],
    'prescr': [({'ini': '2024-03-15'}, None), ({'ini': '2024-02-29'}, None)],
    'usura': [({'taeg': '18', 'lim': '16,5'}, 'Usurário'), ({'taeg': '10', 'lim': '16,5'}, 'Dentro do limite'), ({'taeg': '18', 'lim': '', 'mt': '12', 'mg': '10'}, None)],
    'prest': [({'cap': '150000', 'tan': '3,5', 'meses': '360'}, '673,57'), ({'cap': '1000', 'tan': '0', 'meses': '10'}, '100,00'), ({'cap': '1000', 'tan': '5', 'meses': '0'}, None), ({'cap': '1000', 'tan': '5', 'meses': '9999'}, None)],
    'reemb': [({'cap': '50000'}, '250,00'), ({'cap': '-1'}, None)],
    'cumulo': [({}, '3 anos a 6 anos e 6 meses')],
    'lc': [({'a': '6', 'm': '0', 'ini': '2024-03-15'}, '15 de março de 2030'), ({'a': '0', 'm': '0', 'ini': '2024-03-15'}, None), ({'a': '30', 'ini': '2024-03-15', 'desc': '400'}, None)],
    'desp': [({'adm': '2015-02-01', 'fim': '2026-11-20', 'ret': '1200'}, '6608,00'), ({'adm': '2026-11-20', 'fim': '2015-02-01', 'ret': '1200'}, None), ({'adm': '2015-02-01', 'fim': '2026-11-20', 'ret': '999999'}, None)],
    'imt': [({'v': '250000'}, '9042,04'), ({'v': '100000'}, None), ({'v': '2000000'}, None), ({'v': '0'}, None)],
}


async def calculista(b):
    for W, H, movel, nome in ((1440, 900, False, 'computador'), (390, 844, True, 'telemóvel')):
        if RAPIDO and movel:
            continue
        ctx, pg = await nova_pagina(b, W, H, False, movel)
        await ir(pg, 'calculadoras')
        for calc, casos in CASOS_CALC.items():
            onde = f'calculadora {calc} ({nome})'
            if not await pg.locator(f'[data-a="cx-ir"][data-id="{calc}"]').count():
                problema('calculista', onde, 'calculadora em falta', 'não aparece na lista')
                continue
            await pg.locator(f'[data-a="cx-ir"][data-id="{calc}"]').first.click()
            await pg.wait_for_timeout(200)
            for campos, esperado in casos:
                await pg.locator('[data-a="cx-limpar"]').first.click()
                await pg.wait_for_timeout(150)
                for k, val in campos.items():
                    loc = pg.locator(f'#app [data-cx="{k}"], .main [data-cx="{k}"]').first
                    if await loc.count():
                        await loc.fill(val)
                        await loc.dispatch_event('input')
                await pg.wait_for_timeout(150)
                saida = await pg.evaluate("(document.querySelector('#cx-out') || {}).innerText || ''")
                for e in tirar_erros(pg):
                    problema('calculista', onde, 'erro de JavaScript', f'{campos}: {e}')
                if not saida.strip():
                    problema('calculista', onde, 'sem resultado', str(campos))
                for l in LIXO:
                    if l in saida:
                        problema('calculista', onde, 'resultado inválido', f'{campos} → mostra «{l}»')
                if esperado and esperado not in saida:
                    problema('calculista', onde, 'resultado diferente do esperado', f'{campos}: esperava «{esperado}», obteve «{saida[:120]}»')
                sw = await pg.evaluate('document.documentElement.scrollWidth')
                if sw > W + 2:
                    problema('calculista', onde, 'conteúdo sai do ecrã', f'{campos}: {sw}px')
                feito['calculista'] += 1
        await ctx.close()


# ---------------- Robô Estudante ----------------
async def estudante(b):
    ctx, pg = await nova_pagina(b, 1440, 900)
    # simulação de exame completa
    await ir(pg, 'exames')
    if await pg.locator('[data-a="exam-start"]').count():
        await pg.locator('[data-a="exam-start"]').first.click()
        await pg.wait_for_timeout(400)
        for i in range(80):
            if await pg.locator('[data-a="exam-pick"]').count():
                await pg.locator('[data-a="exam-pick"]').first.click()
                await pg.wait_for_timeout(80)
            if await pg.locator('[data-a="exam-confirm"]:not([disabled])').count():
                await pg.locator('[data-a="exam-confirm"]').first.click()
                await pg.wait_for_timeout(80)
            if await pg.locator('[data-a="exam-next"]').count():
                await pg.locator('[data-a="exam-next"]').first.click()
                await pg.wait_for_timeout(80)
                feito['estudante'] += 1
                continue
            if await pg.locator('[data-a="exam-finish"]').count():
                await pg.locator('[data-a="exam-finish"]').last.click()
                await pg.wait_for_timeout(300)
                if await pg.locator('#ov [data-a="exam-finish-ok"], #ov .btn.pri').count():
                    await pg.locator('#ov .btn.pri').last.click()
                    await pg.wait_for_timeout(300)
                break
        txt = await pg.evaluate("(document.querySelector('.main') || {}).innerText || ''")
        if 'Resultado' not in txt:
            problema('estudante', 'simulador de exames', 'exame não chegou ao resultado', txt[:160])
        else:
            feito['estudante'] += 1
    else:
        problema('estudante', 'simulador de exames', 'botão em falta', 'não há botão para iniciar a simulação')
    for e in tirar_erros(pg):
        problema('estudante', 'simulador de exames', 'erro de JavaScript', e)
    # flashcards
    await ir(pg, 'flashcards')
    if await pg.locator('[data-a="fc-ini"]:not([disabled])').count():
        await pg.locator('[data-a="fc-ini"]').first.click()
        await pg.wait_for_timeout(300)
        for _ in range(10):
            if not await pg.locator('[data-a="fc-virar"]').count():
                break
            await pg.locator('[data-a="fc-virar"]').first.click()
            await pg.wait_for_timeout(120)
            if await pg.locator('[data-a="fc-nota"]').count():
                await pg.locator('[data-a="fc-nota"]').last.click()
                await pg.wait_for_timeout(120)
                feito['estudante'] += 1
    for e in tirar_erros(pg):
        problema('estudante', 'flashcards', 'erro de JavaScript', e)
    # casos práticos
    await ir(pg, 'casos')
    ids = await pg.evaluate("[...document.querySelectorAll('[data-a=\"case-open\"]')].map(e => e.dataset.id)")
    for cid in ids[: (5 if RAPIDO else 40)]:
        await ir(pg, 'casos')
        if await pg.locator('[data-a="case-back"]').count():
            await pg.locator('[data-a="case-back"]').first.click()
            await pg.wait_for_timeout(150)
        loc = pg.locator(f'[data-a="case-open"][data-id="{cid}"]')
        if not await loc.count():
            continue
        await loc.first.click()
        await pg.wait_for_timeout(250)
        if await pg.locator('[data-a="case-reveal"]:not([disabled])').count():
            await pg.locator('[data-a="case-reveal"]').first.click()
            await pg.wait_for_timeout(150)
        await verificar_vista(pg, 'estudante', f'caso prático {cid}', 1440)
        feito['estudante'] += 1
    await ctx.close()


async def main():
    global URL
    URL = servir()
    t0 = time.time()
    print(f'Robôs a testar {INDEX}' + (' (modo rápido)' if RAPIDO else ''), flush=True)
    async with async_playwright() as p:
        exe = os.environ.get('CHROME_PATH')
        b = await p.chromium.launch(executable_path=exe, args=['--no-sandbox']) if exe else await p.chromium.launch(args=['--no-sandbox'])
        for nome, f in (('explorador', explorador), ('calculista', calculista), ('estudante', estudante)):
            print(f'— {NOMES[nome]} ({nome})', flush=True)
            try:
                await f(b)
            except Exception as e:
                problema(nome, 'execução', 'o robô parou', repr(e))
            print(f'  {feito[nome]} verificações', flush=True)
        await b.close()
    hoje = datetime.date.today().isoformat()
    por_robo = {r: [p for p in problemas if p['robo'] == r] for r in feito}
    eventos = []
    for r in feito:
        if feito[r] and not any(p['tipo'] == 'o robô parou' for p in por_robo[r]):
            eventos.append({'robo': r, 'tipo': 'teste', 'pontos': 10, 'ref': f'{r}:{hoje}:teste'})
        for i, p in enumerate(por_robo[r][:2]):
            eventos.append({'robo': r, 'tipo': 'erro_encontrado', 'pontos': 10, 'ref': f'{r}:{hoje}:erro:{hashlib.md5((p["onde"] + p["tipo"]).encode()).hexdigest()[:10]}'})
    rel = {'data': hoje, 'segundos': round(time.time() - t0), 'verificacoes': feito, 'problemas': problemas, 'eventos': eventos}
    (pathlib.Path.cwd() / 'robos-relatorio.json').write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding='utf-8')
    md = [f'## Testes automáticos — {hoje}', '', '| Conta | Verificações | Problemas |', '|---|---|---|']
    for r in feito:
        md.append(f'| {NOMES[r]} ({r}) | {feito[r]} | {len(por_robo[r])} |')
    md.append('')
    if problemas:
        md += ['### Problemas encontrados', '', '| Conta | Onde | Tipo | Detalhe |', '|---|---|---|---|']
        md += [f"| {NOMES.get(p['robo'], p['robo'])} | {p['onde']} | {p['tipo']} | {p['detalhe'][:200].replace('|', '/').replace(chr(10), ' ')} |" for p in problemas[:80]]
    else:
        md.append('✅ Nenhum problema encontrado.')
    (pathlib.Path.cwd() / 'robos-relatorio.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'\n{sum(feito.values())} verificações, {len(problemas)} problemas, {round(time.time() - t0)} s')
    sys.exit(1 if problemas else 0)


if __name__ == '__main__':
    asyncio.run(main())
