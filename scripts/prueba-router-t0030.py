#!/usr/bin/env python3
"""Prueba T-0030: el router de Telegram en producción con updates sintéticos, llamando a su URL directamente.

No registra ningún webhook en Telegram ni envía mensajes: solo hace POST a https://n8n.letiende.co/webhook/sgcd-telegram,
revisa las ejecuciones por la API de n8n y borra las filas de error_log que la propia prueba genera.
Los secretos se leen de credentials.env; nunca se pasan como argumento ni se imprimen.

Uso: python3 scripts/prueba-router-t0030.py
"""
import json, os, time, urllib.error, urllib.parse, urllib.request

for linea in open('credentials.env'):
    linea = linea.strip()
    if linea and not linea.startswith('#') and '=' in linea:
        k, v = linea.split('=', 1)
        os.environ.setdefault(k, v.strip().strip('"\''))

URL = 'https://n8n.letiende.co/webhook/sgcd-telegram'
SECRETO = os.environ['TELEGRAM_WEBHOOK_SECRET']
ADMIN = os.environ['TELEGRAM_ADMIN_CHAT_ID']
IDS = json.load(open('n8n-workflows/id-map.json'))['prod']
H_N8N = {'X-N8N-API-KEY': os.environ['N8N_API_KEY']}
KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
H_SB = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY}
SB = os.environ['SUPABASE_URL'] + '/rest/v1/'


def post(cuerpo, secreto=SECRETO):
    cab = {'Content-Type': 'application/json'}
    if secreto is not None:
        cab['x-telegram-bot-api-secret-token'] = secreto
    req = urllib.request.Request(URL, data=json.dumps(cuerpo).encode(), headers=cab, method='POST')
    try:
        return urllib.request.urlopen(req, timeout=60).status
    except urllib.error.HTTPError as e:
        return e.code


def ejecuciones(clave):
    r = urllib.request.Request(f'https://n8n.letiende.co/api/v1/executions?workflowId={IDS[clave]}&limit=20&includeData=true', headers=H_N8N)
    return json.load(urllib.request.urlopen(r))['data']


def recibido(clave, update_id):
    """Entrada que recibió el subworkflow para ese update, o None."""
    for e in ejecuciones(clave):
        try:
            entrada = e['data']['resultData']['runData']['Confirmar recepción'][0]['data']['main'][0][0]['json']['recibido']
        except (KeyError, IndexError, TypeError):
            continue
        if entrada.get('update_id') == update_id:
            return entrada
    return None


base = int(time.time())
resultados = []
def chequea(nombre, ok, detalle=''):
    resultados.append(ok)
    print(('✓' if ok else '✗'), nombre, detalle)


chequea('token incorrecto → 403', post({'update_id': base}, 'incorrecto') == 403)
chequea('sin cabecera → 403', post({'update_id': base}, None) == 403)
foto = {'update_id': base + 1, 'message': {'message_id': 1, 'chat': {'id': int(ADMIN)}, 'photo': [{'file_id': 'a'}, {'file_id': 'b'}], 'caption': 'Prueba T-0030'}}
chequea('foto del administrador → 200', post(foto) == 200)
boton = {'update_id': base + 2, 'callback_query': {'id': 'cb', 'from': {'id': int(ADMIN)}, 'data': 'approve:x', 'message': {'message_id': 2, 'chat': {'id': int(ADMIN)}}}}
chequea('botón del administrador → 200', post(boton) == 200)
chequea('chat ajeno → 200', post({'update_id': base + 3, 'message': {'message_id': 3, 'chat': {'id': 123456789}, 'photo': [{'file_id': 'a'}]}}) == 200)
chequea('tipo no soportado → 200', post({'update_id': base + 4, 'edited_message': {'message_id': 4, 'chat': {'id': int(ADMIN)}}}) == 200)
time.sleep(8)
e30 = recibido('30-recibir-pieza', base + 1)
chequea('la foto llegó a WF30 con la foto más grande', bool(e30) and e30.get('file_id') == 'b' and e30.get('media_kind') == 'image', str(e30 and {k: e30[k] for k in ('media_kind', 'file_id')}))
e31 = recibido('31-atender-revision', base + 2)
chequea('el botón llegó a WF31', bool(e31) and e31.get('callback_data') == 'approve:x')
chequea('el chat ajeno no llegó a ningún subworkflow', recibido('30-recibir-pieza', base + 3) is None)

filas = json.load(urllib.request.urlopen(urllib.request.Request(
    SB + 'error_log?select=id,error_type,error_message&workflow=eq.00-router-telegram&error_message=like.' + urllib.parse.quote(f'update {base + 3}:*') , headers=H_SB)))
filas += json.load(urllib.request.urlopen(urllib.request.Request(
    SB + 'error_log?select=id,error_type,error_message&workflow=eq.00-router-telegram&error_message=like.' + urllib.parse.quote(f'update {base + 4}:*'), headers=H_SB)))
tipos = sorted(f['error_type'] for f in filas)
chequea('chat ajeno y tipo no soportado quedaron en error_log', tipos == ['unauthorized_chat', 'unsupported_update'], str(tipos))
for f in filas:
    urllib.request.urlopen(urllib.request.Request(SB + f"error_log?id=eq.{f['id']}", headers=H_SB, method='DELETE'))
print('filas de error_log borradas:', len(filas))
print('RESULTADO:', 'todo bien' if all(resultados) else 'HAY FALLOS')
