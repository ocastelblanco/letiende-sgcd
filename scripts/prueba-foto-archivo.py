#!/usr/bin/env python3
"""Prueba de la propuesta de revisión cuando la imagen llegó como archivo (documento) y no como foto.

Sube una imagen sintética con sendDocument para obtener un file_id de documento real, crea una pieza detenida con ese file_id y
pulsa «Reabrir» (botón enviado al router de dev): WF31 reenvía la propuesta con WF32, que antes fallaba con 400 al usar sendPhoto.
Despliega antes el WF32 y el WF30 del repositorio en dev. Siempre borra lo que crea; llega una propuesta de prueba al grupo de revisión.
Los secretos se leen de credentials.env; nunca se pasan como argumento ni se imprimen.

Uso: python3 scripts/prueba-foto-archivo.py
"""
import json, os, pathlib, subprocess, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
os.chdir(ROOT)
for linea in open('credentials.env'):
    linea = linea.strip()
    if linea and not linea.startswith('#') and '=' in linea:
        k, v = linea.split('=', 1)
        os.environ.setdefault(k, v.strip().strip('"\''))

HOST = 'http://127.0.0.1:5678'
APIKEY = os.environ['N8N_DEV_API_KEY']
MAPA = json.load(open('n8n-workflows/id-map.json'))['dev']
ADMIN = int(os.environ['TELEGRAM_ADMIN_CHAT_ID'])
AUTORIZADO = int(os.environ['TELEGRAM_ALLOWED_USER_IDS'].split(',')[0])
KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
SB = os.environ['SUPABASE_URL'] + '/rest/v1/'
SB_H = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
N8N_H = {'X-N8N-API-KEY': APIKEY, 'Content-Type': 'application/json'}


def http(metodo, url, cuerpo=None, cab=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    crudo = urllib.request.urlopen(urllib.request.Request(url, data=datos, headers=cab, method=metodo), timeout=120).read()
    return json.loads(crudo) if crudo else None


sb = lambda m, r, c=None: http(m, SB + r, c, SB_H)


def desplegar(nombre):
    wf = json.load(open(f'n8n-workflows/{nombre}.json'))
    cuerpo = {k: wf[k] for k in ('name', 'nodes', 'connections', 'settings')}
    http('PUT', f'{HOST}/api/v1/workflows/{MAPA[nombre]}', cuerpo, N8N_H)
    http('POST', f'{HOST}/api/v1/workflows/{MAPA[nombre]}/activate', None, N8N_H)


resultados = []
def chequea(nombre, ok, detalle=''):
    resultados.append(ok)
    print(('✓' if ok else '✗'), nombre, detalle)


item = None
try:
    for n in ('32-enviar-revision', '30-recibir-pieza'):
        desplegar(n)
    subida = subprocess.run(['curl', '-s', '-F', f'chat_id={ADMIN}', '-F', 'caption=Prueba de imagen como archivo (puedes ignorar)', '-F', 'document=@golden-set/synthetic/images/libro-laberinto.png',
                             f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendDocument"], capture_output=True, text=True).stdout
    try:
        file_id = json.loads(subida)['result']['document']['file_id']
    except (KeyError, ValueError):
        sys.exit('✗ no pude subir la imagen de prueba como documento')
    item = sb('POST', 'content_items', {'asset_type': 'image', 'raw_asset_url': 'telegram:' + file_id, 'status': 'stalled', 'notes': 'Prueba foto como archivo',
                                         'caption_instagram': 'Caption de prueba', 'title_youtube': 'Pieza de prueba', 'hashtags_instagram': ['#prueba'],
                                         'caption_youtube': 'x', 'caption_tiktok': 'x', 'hashtags_tiktok': ['#prueba']})[0]['id']
    update = {'update_id': int(time.time()), 'callback_query': {'id': 'prueba-archivo', 'from': {'id': AUTORIZADO, 'first_name': 'Prueba'}, 'data': f'reopen_{item}',
                                                              'message': {'message_id': 1, 'chat': {'id': ADMIN}}}}
    req = urllib.request.Request(f'{HOST}/webhook/sgcd-telegram', data=json.dumps(update).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'x-telegram-bot-api-secret-token': os.environ['TELEGRAM_WEBHOOK_SECRET']})
    chequea('botón Reabrir → 200', urllib.request.urlopen(req, timeout=120).status == 200)
    pasos = []
    for _ in range(15):
        time.sleep(4)
        pasos = sb('GET', f'pipeline_steps?select=attempt,status,error_type&content_item_id=eq.{item}&step=eq.review_send&order=attempt')
        if pasos:
            break
    chequea('la propuesta de la imagen-archivo se envió sin error 400', pasos and pasos[-1]['status'] == 'succeeded', str(pasos))
finally:
    if item:
        sb('DELETE', f'error_log?content_item_id=eq.{item}')
        sb('DELETE', f'content_items?id=eq.{item}')
    print('datos de prueba borrados')
print('RESULTADO:', 'todo bien' if resultados and all(resultados) else 'HAY FALLOS')
