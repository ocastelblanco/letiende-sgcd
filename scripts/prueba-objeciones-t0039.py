#!/usr/bin/env python3
"""Prueba de objeciones (T-0039): una objeción abierta bloquea la aprobación hasta que alguien la resuelve.

Manda al router (por defecto el de dev) botones y respuestas de dos usuarios autorizados (los dos primeros de
TELEGRAM_ALLOWED_USER_IDS) sobre un item creado en `ready_for_review`. Siempre borra lo que crea. Llegan mensajes al chat de administración.
Los secretos se leen de credentials.env; nunca se pasan como argumento ni se imprimen.

Uso: python3 scripts/prueba-objeciones-t0039.py [URL_DEL_ROUTER]
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
U1, U2 = (int(x) for x in os.environ['TELEGRAM_ALLOWED_USER_IDS'].split(',')[:2])
KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
SB = os.environ['SUPABASE_URL'] + '/rest/v1/'
SB_H = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
IMAGEN = 'golden-set/synthetic/images/libro-laberinto.png'


def sb(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    crudo = urllib.request.urlopen(urllib.request.Request(SB + ruta, data=datos, headers=SB_H, method=metodo), timeout=60).read()
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
def boton(uid, data):
    global n; n += 1
    return post({'update_id': n, 'callback_query': {'id': f'prueba{n}', 'from': {'id': uid, 'first_name': f'U{uid % 1000}'}, 'data': data, 'message': {'message_id': n, 'chat': {'id': ADMIN}}}})

def respuesta(uid, item, texto, prompt):
    global n; n += 1
    return post({'update_id': n, 'message': {'message_id': n, 'chat': {'id': ADMIN}, 'from': {'id': uid, 'first_name': f'U{uid % 1000}'}, 'text': texto,
                                             'reply_to_message': {'from': {'is_bot': True}, 'text': f'{prompt}\n\nContenido: {item}'}}})

def estado(item): return sb('GET', f'content_items?select=status&id=eq.{item}')[0]['status']
def acciones(item): return [(f['action'], f['outcome'], f['actor_telegram_id']) for f in sb('GET', f'review_actions?select=action,outcome,actor_telegram_id&content_item_id=eq.{item}&order=id')]

creados = []
inicio = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
try:
    subida = subprocess.run(['curl', '-s', '-F', f'chat_id={ADMIN}', '-F', 'caption=Prueba T-0039 (imagen sintética, puedes ignorar)', '-F', f'photo=@{IMAGEN}',
                             f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendPhoto"], capture_output=True, text=True).stdout
    try:
        file_id = json.loads(subida)['result']['photo'][-1]['file_id']
    except (KeyError, ValueError):
        sys.exit('✗ no pude subir la imagen de prueba a Telegram')
    item = sb('POST', 'content_items', {'asset_type': 'image', 'raw_asset_url': 'telegram:' + file_id, 'status': 'ready_for_review', 'notes': 'T0039 prueba',
                                        'caption_instagram': 'Caption', 'hashtags_instagram': ['#prueba'], 'caption_youtube': 'x', 'title_youtube': 'x',
                                        'caption_tiktok': 'x', 'hashtags_tiktok': ['#prueba']})[0]['id']
    creados.append(item)
    w = lambda s=9: time.sleep(s)

    chequea('Resolver sin objeción → ignorada', boton(U2, f'resolve_{item}') == 200 and (w() or True) and acciones(item)[-1] == ('resolve', 'ignored', U2), str(acciones(item)))
    chequea('U1 pulsa Objetar', boton(U1, f'object_{item}') == 200); w()
    chequea('U1 responde con su objeción', respuesta(U1, item, 'La foto no corresponde al tema', '💬 Escribe tu objeción') == 200); w()
    f = sb('GET', f'review_actions?select=action,detail&content_item_id=eq.{item}&action=eq.objectreply')
    chequea('la objeción queda con su texto (y no como edición)', f == [{'action': 'objectreply', 'detail': 'La foto no corresponde al tema'}], str(f))
    chequea('U2 intenta aprobar → bloqueada', boton(U2, f'approve_{item}') == 200 and (w() or True) and estado(item) == 'ready_for_review' and acciones(item)[-1] == ('approve', 'ignored', U2), str(acciones(item)))
    d = sb('GET', f'review_actions?select=detail&content_item_id=eq.{item}&action=eq.approve')[0]['detail']
    chequea('el motivo es «objeción abierta»', d == 'objeción abierta', str(d))
    chequea('U2 resuelve la objeción', boton(U2, f'resolve_{item}') == 200 and (w() or True) and acciones(item)[-1] == ('resolve', 'applied', U2), str(acciones(item)[-1]))
    chequea('segunda objeción de U2 y nuevo bloqueo', respuesta(U2, item, 'Falta el nombre de la autora', '💬 Escribe tu objeción') == 200 and (w() or True)
            and boton(U1, f'approve_{item}') == 200 and (w() or True) and estado(item) == 'ready_for_review', estado(item))
    chequea('U1 resuelve y aprueba', boton(U1, f'resolve_{item}') == 200 and (w() or True) and boton(U1, f'approve_{item}') == 200 and (w() or True) and estado(item) == 'approved', estado(item))
    st = sb('GET', f'review_item_stats?select=objections,approved&content_item_id=eq.{item}')[0]
    chequea('la vista cuenta 2 objeciones', st == {'objections': 2, 'approved': True}, str(st))
    chequea('el resumen trae objections_per_piece', sb('GET', 'review_summary?select=objections_per_piece')[0]['objections_per_piece'] is not None)
finally:
    for i in creados:
        sb('DELETE', f'error_log?content_item_id=eq.{i}')
        sb('DELETE', f'content_items?id=eq.{i}')
    sb('DELETE', f'error_log?workflow=eq.00-router-telegram&occurred_at=gte.{inicio}')
    print(f'datos de prueba borrados: {len(creados)} item(s)')
print('RESULTADO:', 'todo bien' if resultados and all(resultados) else 'HAY FALLOS')
