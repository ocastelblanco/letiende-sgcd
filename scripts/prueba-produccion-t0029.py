#!/usr/bin/env python3
"""Prueba T-0029 en producción: una pieza sintética recorre WF20 y todo lo creado se borra al terminar.

Uso: python3 scripts/prueba-produccion-t0029.py <archivo-con-la-url-de-la-imagen>

Crea un content_item de prueba, un workflow temporal «zz - Prueba T-0029 (borrar)» con un webhook de ruta aleatoria que
llama a WF20, lo dispara y comprueba el estado. Siempre borra el workflow, el item y sus filas de pipeline_steps y error_log.
La URL debe ser de api.telegram.org (único host de imágenes permitido en producción) y no se imprime: lleva el token del bot.
Los secretos se leen de credentials.env; nunca se pasan como argumento.
"""
import json, os, secrets, subprocess, sys, time, urllib.request

NOTES = 'Libros: El laberinto de las palabras, de Marta Quintero'  # pieza SINTÉTICA (título y autora ficticios)

for linea in open('credentials.env'):
    linea = linea.strip()
    if linea and not linea.startswith('#') and '=' in linea:
        k, v = linea.split('=', 1)
        os.environ.setdefault(k, v.strip().strip('"\''))

N8N = 'https://n8n.letiende.co/api/v1'
N8N_H = {'X-N8N-API-KEY': os.environ['N8N_API_KEY'], 'Content-Type': 'application/json'}
SB = os.environ['SUPABASE_URL'] + '/rest/v1/'
KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
SB_H = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json', 'Prefer': 'return=representation'}


def call(base, headers, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    raw = urllib.request.urlopen(urllib.request.Request(base + path, data=data, headers=headers, method=method)).read()
    return json.loads(raw) if raw else None


n8n = lambda m, p, b=None: call(N8N, N8N_H, m, p, b)
sb = lambda m, p, b=None: call(SB, SB_H, m, p, b)

url = open(sys.argv[1]).read().strip()
if not url.startswith('https://api.telegram.org/file/bot'):
    sys.exit('la URL debe ser de api.telegram.org/file/bot…')

wid = json.load(open('n8n-workflows/id-map.json'))['prod']['20-procesar-pieza']
if not wid:
    sys.exit('WF20 aún no está en producción (id-map.json)')

item = sb('POST', 'content_items', {'asset_type': 'image', 'raw_asset_url': url, 'notes': NOTES})[0]['id']
print('item de prueba', item)
hid = None
try:
    esquema = [{'id': k, 'displayName': k, 'required': False, 'defaultMatch': False, 'display': True, 'canBeUsedToMatch': True, 'type': 'string'}
               for k in ('content_item_id', 'image_url', 'notes')]
    path = 't0029-' + secrets.token_hex(12)
    wf = {
        'name': 'zz - Prueba T-0029 (borrar)', 'settings': {'executionOrder': 'v1'},
        'nodes': [
            {'id': 'a1', 'name': 'Webhook', 'type': 'n8n-nodes-base.webhook', 'typeVersion': 2, 'position': [0, 0],
             'webhookId': secrets.token_hex(16)[:8] + '-0000-4000-8000-' + secrets.token_hex(6),
             'parameters': {'httpMethod': 'POST', 'path': path, 'responseMode': 'lastNode', 'options': {}}},
            {'id': 'a2', 'name': 'Procesar pieza', 'type': 'n8n-nodes-base.executeWorkflow', 'typeVersion': 1.2, 'position': [250, 0],
             'parameters': {'source': 'database', 'workflowId': {'__rl': True, 'mode': 'id', 'value': wid}, 'mode': 'each',
                            'workflowInputs': {'mappingMode': 'defineBelow', 'matchingColumns': [], 'schema': esquema,
                                               'value': {k: '={{ $json.body.%s }}' % k for k in ('content_item_id', 'image_url', 'notes')},
                                               'attemptToConvertTypes': False, 'convertFieldsToString': False},
                            'options': {'waitForSubWorkflow': True}}},
        ],
        'connections': {'Webhook': {'main': [[{'node': 'Procesar pieza', 'type': 'main', 'index': 0}]]}},
    }
    hid = n8n('POST', '/workflows', wf)['id']
    n8n('POST', f'/workflows/{hid}/activate')
    time.sleep(5)
    cuerpo = json.dumps({'content_item_id': item, 'image_url': url, 'notes': NOTES})
    salida = subprocess.run(['curl', '-s', '-m', '280', '-X', 'POST', f'https://n8n.letiende.co/webhook/{path}',
                             '-H', 'Content-Type: application/json', '-d', cuerpo], capture_output=True, text=True).stdout
    print('respuesta de WF20:', salida[:300].replace(url, '<url>'))
    fila = sb('GET', f'content_items?select=status,caption_instagram&id=eq.{item}')[0]
    pasos = sb('GET', f'pipeline_steps?select=step,status,attempt&content_item_id=eq.{item}&order=started_at')
    print('estado:', fila['status'], '| caption:', (fila['caption_instagram'] or '')[:80], '| pasos:', pasos)
finally:
    if hid:
        n8n('POST', f'/workflows/{hid}/deactivate')
        n8n('DELETE', f'/workflows/{hid}')
        print('workflow temporal borrado')
    for tabla, col in [('error_log', 'content_item_id'), ('pipeline_steps', 'content_item_id'), ('content_items', 'id')]:
        print('borradas', tabla, len(sb('DELETE', f'{tabla}?{col}=eq.{item}') or []))
