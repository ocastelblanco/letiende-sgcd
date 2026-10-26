#!/usr/bin/env python3
"""Prueba de review_actions (T-0035): cada botón y cada respuesta de edición deja su fila con el actor.

Manda updates sintéticos al router (por defecto el de dev, http://127.0.0.1:5678) con un `from` falso, sobre items creados
directamente en Supabase en `ready_for_review` con una imagen real de Telegram. Comprueba las filas de review_actions, las
vistas de indicadores y que `anon` no puede leer la tabla. Siempre borra lo que crea. Llega un mensaje por acción al chat de administración.
Los secretos se leen de credentials.env; nunca se pasan como argumento ni se imprimen.

Uso: python3 scripts/prueba-review-actions-t0035.py [URL_DEL_ROUTER]
"""
import json, os, subprocess, sys, time, urllib.error, urllib.request

for linea in open('credentials.env'):
    linea = linea.strip()
    if linea and not linea.startswith('#') and '=' in linea:
        k, v = linea.split('=', 1)
        os.environ.setdefault(k, v.strip().strip('"\''))

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:5678/webhook/sgcd-telegram'
SECRETO = os.environ['TELEGRAM_WEBHOOK_SECRET']
ADMIN = int(os.environ['TELEGRAM_ADMIN_CHAT_ID'])
KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
SB = os.environ['SUPABASE_URL'] + '/rest/v1/'
SB_H = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
IMAGEN = 'golden-set/synthetic/images/libro-laberinto.png'
ACTOR, NOMBRE = 777000111, 'Ana Prueba T0035'


def sb(metodo, ruta, cuerpo=None, cab=SB_H):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    crudo = urllib.request.urlopen(urllib.request.Request(SB + ruta, data=datos, headers=cab, method=metodo), timeout=60).read()
    return json.loads(crudo) if crudo else None


def post(cuerpo):
    req = urllib.request.Request(URL, data=json.dumps(cuerpo).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'x-telegram-bot-api-secret-token': SECRETO})
    try:
        return urllib.request.urlopen(req, timeout=120).status
    except urllib.error.HTTPError as e:
        return e.code


resultados = []
def chequea(nombre, ok, detalle=''):
    resultados.append(ok)
    print(('✓' if ok else '✗'), nombre, detalle)


n = int(time.time())
def boton(data):
    global n; n += 1
    return {'update_id': n, 'callback_query': {'id': f'prueba{n}', 'from': {'id': ACTOR, 'first_name': 'Ana', 'last_name': 'Prueba T0035'}, 'data': data,
                                              'message': {'message_id': n, 'chat': {'id': ADMIN}}}}

def respuesta(item, texto):
    global n; n += 1
    return {'update_id': n, 'message': {'message_id': n, 'chat': {'id': ADMIN}, 'from': {'id': ACTOR, 'first_name': 'Ana', 'last_name': 'Prueba T0035'}, 'text': texto,
                                        'reply_to_message': {'from': {'is_bot': True}, 'text': f'✏️ Escribe el nuevo caption\n\nContenido: {item}'}}}

def filas(item):
    return sb('GET', f'review_actions?select=action,outcome,actor_telegram_id,actor_name,detail&content_item_id=eq.{item}&order=id')

inicio = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
creados = []
try:
    subida = subprocess.run(['curl', '-s', '-F', f'chat_id={ADMIN}', '-F', 'caption=Prueba T-0035 (imagen sintética, puedes ignorar)', '-F', f'photo=@{IMAGEN}',
                             f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendPhoto"], capture_output=True, text=True).stdout
    try:
        file_id = json.loads(subida)['result']['photo'][-1]['file_id']
    except (KeyError, ValueError):
        sys.exit('✗ no pude subir la imagen de prueba a Telegram')

    def nuevo():
        r = sb('POST', 'content_items', {'asset_type': 'image', 'raw_asset_url': 'telegram:' + file_id, 'status': 'ready_for_review', 'notes': 'T0035 prueba',
                                         'caption_instagram': 'Caption de prueba', 'hashtags_instagram': ['#prueba'], 'caption_youtube': 'x', 'title_youtube': 'x',
                                         'caption_tiktok': 'x', 'hashtags_tiktok': ['#prueba']})[0]['id']
        creados.append(r); return r
    a, b, c, d = nuevo(), nuevo(), nuevo(), nuevo()
    esperas = lambda s=10: time.sleep(s)

    # A: aprobar, y repetir el botón (estado viejo → ignorada)
    chequea('A aprobar → 200', post(boton(f'approve_{a}')) == 200); esperas()
    chequea('A repetir aprobar → 200', post(boton(f'approve_{a}')) == 200); esperas()
    fa = filas(a)
    chequea('A: approve aplicada con actor, luego approve ignorada con motivo',
            [(f['action'], f['outcome']) for f in fa] == [('approve', 'applied'), ('approve', 'ignored')]
            and all(f['actor_telegram_id'] == ACTOR and f['actor_name'] == NOMBRE for f in fa) and fa[1]['detail'] == 'estado actual: approved', str(fa))

    # B: botón Editar, texto nuevo (detail) y aprobar
    chequea('B editar → 200', post(boton(f'edit_{b}')) == 200); esperas(6)
    chequea('B respuesta con el caption → 200', post(respuesta(b, 'Caption nuevo del aprobador')) == 200); esperas(25)
    chequea('B aprobar → 200', post(boton(f'approve_{b}')) == 200); esperas()
    fb = filas(b)
    chequea('B: edit, editreply con el texto y approve, todas aplicadas',
            [(f['action'], f['outcome']) for f in fb] == [('edit', 'applied'), ('editreply', 'applied'), ('approve', 'applied')]
            and fb[1]['detail'] == 'Caption nuevo del aprobador' and all(f['actor_telegram_id'] == ACTOR for f in fb), str(fb))

    # C: descartar
    chequea('C descartar → 200', post(boton(f'discard_{c}')) == 200); esperas()
    fc = filas(c)
    chequea('C: discard aplicada', [(f['action'], f['outcome']) for f in fc] == [('discard', 'applied')], str(fc))

    # D: regenerar (corre WF20 con Gemini real) y luego aprobar
    chequea('D regenerar → 200', post(boton(f'regenerate_{d}')) == 200)
    for _ in range(30):
        time.sleep(6)
        if sb('GET', f'content_items?select=status&id=eq.{d}')[0]['status'] != 'processing' and filas(d):
            break
    fd = filas(d)
    chequea('D: regenerate aplicada', [(f['action'], f['outcome']) for f in fd] == [('regenerate', 'applied')], str(fd))

    # E: callback mal formado → error_log y ninguna fila
    antes = len(sb('GET', 'review_actions?select=id'))
    chequea('callback mal formado → 200', post(boton('approve_no-es-uuid')) == 200); esperas(6)
    chequea('callback mal formado no escribe fila', len(sb('GET', 'review_actions?select=id')) == antes)

    # Indicadores sobre estas cuatro piezas
    ids = ','.join([a, b, c, d])
    st = {r['content_item_id']: r for r in sb('GET', f'review_item_stats?select=*&content_item_id=in.({ids})')}
    chequea('vista por pieza: A aprobada sin edición', st[a]['approved'] and st[a]['approved_without_edit'] and st[a]['ignored'] == 1, str(st[a]))
    chequea('vista por pieza: B aprobada con 1 edición', st[b]['approved'] and not st[b]['approved_without_edit'] and st[b]['edits'] == 1, str(st[b]))
    chequea('vista por pieza: C descartada', st[c]['discarded'] and not st[c]['approved'], str(st[c]))
    chequea('vista por pieza: D con 1 regeneración', st[d]['regenerations'] == 1, str(st[d]))
    resumen = sb('GET', 'review_summary?select=*')[0]
    chequea('resumen devuelve valores', resumen['pieces_reviewed'] >= 4 and resumen['approved_without_edit_rate'] is not None, str(resumen))

    # RLS: anon no lee la tabla ni las vistas
    anon = {'apikey': os.environ.get('SUPABASE_ANON_KEY', ''), 'Authorization': 'Bearer ' + os.environ.get('SUPABASE_ANON_KEY', '')}
    if anon['apikey']:
        for t in ('review_actions', 'review_item_stats', 'review_summary'):
            try:
                sb('GET', t + '?select=*', cab=anon); chequea(f'anon rechazado en {t}', False)
            except urllib.error.HTTPError as e:
                chequea(f'anon rechazado en {t}', e.code in (401, 403), str(e.code))
    else:
        print('· SUPABASE_ANON_KEY no está en credentials.env: la comprobación de anon se hace aparte')
finally:
    for item in creados:
        sb('DELETE', f'error_log?content_item_id=eq.{item}')
        sb('DELETE', f'content_items?id=eq.{item}')  # review_actions y pipeline_steps caen en cascada
    sb('DELETE', f'error_log?workflow=eq.31-atender-revision&occurred_at=gte.{inicio}')
    quedan = len(sb('GET', f'review_actions?select=id&content_item_id=in.({",".join(creados)})')) if creados else 0
    print(f'datos de prueba borrados: {len(creados)} item(s); filas de review_actions que quedan: {quedan}')
print('RESULTADO:', 'todo bien' if resultados and all(resultados) else 'HAY FALLOS')
