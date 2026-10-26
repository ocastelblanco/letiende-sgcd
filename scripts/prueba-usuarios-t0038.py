#!/usr/bin/env python3
"""Prueba de la lista de usuarios autorizados (T-0038): solo TELEGRAM_ALLOWED_USER_IDS puede pulsar botones y editar.

Manda al router (por defecto el de dev) un botón y una respuesta de edición de un usuario ajeno, y un botón del primer usuario
autorizado. Comprueba que el ajeno no cambia el estado ni deja fila en review_actions, que queda en error_log como
`unauthorized_user` y que el autorizado sí aprueba. Siempre borra lo que crea. Llega algún mensaje al chat de administración.
Los secretos se leen de credentials.env; nunca se pasan como argumento ni se imprimen.

Uso: python3 scripts/prueba-usuarios-t0038.py [URL_DEL_ROUTER]
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
AUTORIZADO = int(os.environ['TELEGRAM_ALLOWED_USER_IDS'].split(',')[0])
AJENO = 777000222
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
    return {'update_id': n, 'callback_query': {'id': f'prueba{n}', 'from': {'id': uid, 'first_name': 'Prueba'}, 'data': data, 'message': {'message_id': n, 'chat': {'id': ADMIN}}}}

def respuesta(uid, item, texto):
    global n; n += 1
    return {'update_id': n, 'message': {'message_id': n, 'chat': {'id': ADMIN}, 'from': {'id': uid, 'first_name': 'Prueba'}, 'text': texto,
                                        'reply_to_message': {'from': {'is_bot': True}, 'text': f'Contenido: {item}'}}}

inicio = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
creados = []
try:
    subida = subprocess.run(['curl', '-s', '-F', f'chat_id={ADMIN}', '-F', 'caption=Prueba T-0038 (imagen sintética, puedes ignorar)', '-F', f'photo=@{IMAGEN}',
                             f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendPhoto"], capture_output=True, text=True).stdout
    try:
        file_id = json.loads(subida)['result']['photo'][-1]['file_id']
    except (KeyError, ValueError):
        sys.exit('✗ no pude subir la imagen de prueba a Telegram')
    item = sb('POST', 'content_items', {'asset_type': 'image', 'raw_asset_url': 'telegram:' + file_id, 'status': 'ready_for_review', 'notes': 'T0038 prueba',
                                        'caption_instagram': 'Caption original', 'hashtags_instagram': ['#prueba'], 'caption_youtube': 'x', 'title_youtube': 'x',
                                        'caption_tiktok': 'x', 'hashtags_tiktok': ['#prueba']})[0]['id']
    creados.append(item)

    chequea('usuario ajeno: botón Aprobar → 200', post(boton(AJENO, f'approve_{item}')) == 200); time.sleep(8)
    chequea('usuario ajeno: respuesta de edición → 200', post(respuesta(AJENO, item, 'Caption de un ajeno')) == 200); time.sleep(8)
    actual = sb('GET', f'content_items?select=status,caption_instagram&id=eq.{item}')[0]
    chequea('el ajeno no cambió ni el estado ni el caption', actual == {'status': 'ready_for_review', 'caption_instagram': 'Caption original'}, str(actual))
    chequea('el ajeno no dejó fila en review_actions', sb('GET', f'review_actions?select=id&content_item_id=eq.{item}') == [])
    filas = sb('GET', f'error_log?select=error_type,error_message&workflow=eq.00-router-telegram&occurred_at=gte.{inicio}')
    chequea('quedaron 2 filas unauthorized_user en error_log', sorted(f['error_type'] for f in filas) == ['unauthorized_user'] * 2, str(filas))

    chequea('usuario autorizado: botón Aprobar → 200', post(boton(AUTORIZADO, f'approve_{item}')) == 200); time.sleep(10)
    actual = sb('GET', f'content_items?select=status&id=eq.{item}')[0]['status']
    chequea('el autorizado sí aprueba', actual == 'approved', actual)
    acc = sb('GET', f'review_actions?select=action,outcome,actor_telegram_id&content_item_id=eq.{item}')
    chequea('y queda su fila en review_actions', acc == [{'action': 'approve', 'outcome': 'applied', 'actor_telegram_id': AUTORIZADO}], str(acc))
finally:
    for i in creados:
        sb('DELETE', f'error_log?content_item_id=eq.{i}')
        sb('DELETE', f'content_items?id=eq.{i}')
    sb('DELETE', f'error_log?workflow=eq.00-router-telegram&occurred_at=gte.{inicio}')
    print(f'datos de prueba borrados: {len(creados)} item(s) y las filas de error_log del router')
print('RESULTADO:', 'todo bien' if resultados and all(resultados) else 'HAY FALLOS')
