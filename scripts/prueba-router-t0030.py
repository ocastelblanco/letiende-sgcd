#!/usr/bin/env python3
"""Prueba del router de Telegram y del flujo completo en producción, llamando a su URL directamente (T-0030 y T-0033).

No registra ningún webhook en Telegram. Hace POST a https://n8n.letiende.co/webhook/sgcd-telegram con updates sintéticos:
  1. seguridad: token incorrecto o ausente → 403; chat ajeno y tipo no soportado → 200 y fila en error_log;
  2. de punta a punta: sube una imagen sintética al chat de administración (sendPhoto) para obtener un file_id real, la manda
     al router como foto del administrador, espera a que llegue a ready_for_review con su propuesta enviada (paso review_send)
     y pulsa «Aprobar» con un botón sintético.
Siempre borra lo que crea (items, pasos y filas de error_log). Aparecerá una propuesta de prueba en el chat de revisión.
Los secretos se leen de credentials.env; nunca se pasan como argumento ni se imprimen.

Uso: python3 scripts/prueba-router-t0030.py
"""
import json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

for linea in open('credentials.env'):
    linea = linea.strip()
    if linea and not linea.startswith('#') and '=' in linea:
        k, v = linea.split('=', 1)
        os.environ.setdefault(k, v.strip().strip('"\''))

URL = 'https://n8n.letiende.co/webhook/sgcd-telegram'
SECRETO = os.environ['TELEGRAM_WEBHOOK_SECRET']
ADMIN = int(os.environ['TELEGRAM_ADMIN_CHAT_ID'])
KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
SB = os.environ['SUPABASE_URL'] + '/rest/v1/'
SB_H = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
IMAGEN = 'golden-set/synthetic/images/libro-laberinto.png'
ETIQUETA = 'T0033 prueba'


def sb(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    crudo = urllib.request.urlopen(urllib.request.Request(SB + ruta, data=datos, headers=SB_H, method=metodo), timeout=60).read()
    return json.loads(crudo) if crudo else None


def post(cuerpo, secreto=SECRETO):
    cab = {'Content-Type': 'application/json'}
    if secreto is not None:
        cab['x-telegram-bot-api-secret-token'] = secreto
    req = urllib.request.Request(URL, data=json.dumps(cuerpo).encode(), headers=cab, method='POST')
    try:
        return urllib.request.urlopen(req, timeout=60).status
    except urllib.error.HTTPError as e:
        return e.code


resultados = []
def chequea(nombre, ok, detalle=''):
    resultados.append(ok)
    print(('✓' if ok else '✗'), nombre, detalle)


base = int(time.time())
inicio = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
creados = []
try:
    # 1. Seguridad
    chequea('token incorrecto → 403', post({'update_id': base}, 'incorrecto') == 403)
    chequea('sin cabecera → 403', post({'update_id': base}, None) == 403)
    chequea('chat ajeno → 200', post({'update_id': base + 1, 'message': {'message_id': 1, 'chat': {'id': 123456789}, 'photo': [{'file_id': 'a' * 20}]}}) == 200)
    chequea('tipo no soportado → 200', post({'update_id': base + 2, 'edited_message': {'message_id': 2, 'chat': {'id': ADMIN}}}) == 200)
    time.sleep(8)
    filas = sb('GET', f'error_log?select=id,error_type&workflow=eq.00-router-telegram&occurred_at=gte.{inicio}')
    tipos = sorted(f['error_type'] for f in filas)
    chequea('chat ajeno y tipo no soportado quedaron en error_log', tipos == ['unauthorized_chat', 'unsupported_update'], str(tipos))

    # 2. De punta a punta con una imagen real de Telegram. El token va en la URL de la API: no se imprime
    subida = subprocess.run(['curl', '-s', '-F', f'chat_id={ADMIN}', '-F', 'caption=Prueba T-0033 (imagen sintética, puedes ignorar)', '-F', f'photo=@{IMAGEN}',
                             f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendPhoto"], capture_output=True, text=True).stdout
    try:
        file_id = json.loads(subida)['result']['photo'][-1]['file_id']
    except (KeyError, ValueError):
        sys.exit('✗ no pude subir la imagen de prueba a Telegram')
    foto = {'update_id': base + 3, 'message': {'message_id': 3, 'chat': {'id': ADMIN}, 'caption': f'{ETIQUETA} Libros: El laberinto de las palabras, de Marta Quintero', 'photo': [{'file_id': file_id}]}}
    chequea('foto del administrador → 200', post(foto) == 200)
    item = None
    for _ in range(40):
        time.sleep(6)
        filas = sb('GET', f'content_items?select=id,status&notes=like.{urllib.parse.quote(ETIQUETA)}*')
        if filas:
            item = filas[0]['id']
            pasos = [(p['step'], p['status']) for p in sb('GET', f'pipeline_steps?select=step,status&content_item_id=eq.{item}')]
            if ('review_send', 'succeeded') in pasos or filas[0]['status'] == 'error':
                break
    if item:
        creados.append(item)
        estado = sb('GET', f'content_items?select=status,raw_asset_url&id=eq.{item}')[0]
        pasos = [(p['step'], p['status']) for p in sb('GET', f'pipeline_steps?select=step,status&content_item_id=eq.{item}&order=started_at,id')]
        chequea('la foto llegó a ready_for_review', estado['status'] == 'ready_for_review', estado['status'])
        chequea('pasos ingest → review_send con éxito', [p[0] for p in pasos] == ['ingest', 'extract_visual', 'write_captions', 'validate_captions', 'review_send'] and all(p[1] == 'succeeded' for p in pasos), str(pasos))
        chequea('la base guarda la referencia y no una URL con token', estado['raw_asset_url'].startswith('telegram:'))
        boton = {'update_id': base + 4, 'callback_query': {'id': 'prueba', 'from': {'id': ADMIN}, 'data': f'approve_{item}', 'message': {'message_id': 4, 'chat': {'id': ADMIN}}}}
        chequea('botón Aprobar → 200', post(boton) == 200)
        time.sleep(8)
        chequea('Aprobar deja el item en approved', sb('GET', f'content_items?select=status&id=eq.{item}')[0]['status'] == 'approved')
    else:
        chequea('la foto creó un content_item', False)
finally:
    borradas = 0
    for item in creados:
        sb('DELETE', f'error_log?content_item_id=eq.{item}')
        sb('DELETE', f'content_items?id=eq.{item}')
        borradas += 1
    sb('DELETE', f'error_log?workflow=eq.00-router-telegram&occurred_at=gte.{inicio}')
    print(f'datos de prueba borrados: {borradas} item(s) y las filas de error_log del router')
print('RESULTADO:', 'todo bien' if resultados and all(resultados) else 'HAY FALLOS')
