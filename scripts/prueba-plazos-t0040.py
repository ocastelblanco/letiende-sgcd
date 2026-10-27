#!/usr/bin/env python3
"""Prueba de los plazos de revisión (T-0040): recordatorio a las 24 h, stalled a las 48 h y reabrir.

Crea un workflow temporal «zz - Prueba plazos» (Webhook → Execute Workflow del WF22), tres items en `ready_for_review` con su
`review_send` fechado hace 25 h, 49 h y 5 h, y comprueba lo que hace el WF22 en cada uno, que una segunda vuelta no repite nada
y que «Reabrir» (botón enviado al router) devuelve la pieza a revisión y reenvía la propuesta. Siempre borra el workflow temporal,
los items y sus filas. Llegan unos 3 mensajes de prueba al grupo de revisión.
Los secretos se leen de credentials.env; nunca se pasan como argumento ni se imprimen.

Uso: python3 scripts/prueba-plazos-t0040.py            contra dev (http://127.0.0.1:5678)
     python3 scripts/prueba-plazos-t0040.py --prod     contra producción (https://n8n.letiende.co)
"""
import json, os, pathlib, subprocess, sys, time, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
os.chdir(ROOT)
for linea in open('credentials.env'):
    linea = linea.strip()
    if linea and not linea.startswith('#') and '=' in linea:
        k, v = linea.split('=', 1)
        os.environ.setdefault(k, v.strip().strip('"\''))

PROD = '--prod' in sys.argv
HOST = 'https://n8n.letiende.co' if PROD else 'http://127.0.0.1:5678'
APIKEY = os.environ['N8N_API_KEY' if PROD else 'N8N_DEV_API_KEY']
MAPA = json.load(open('n8n-workflows/id-map.json'))['prod' if PROD else 'dev']
WF22 = MAPA['22-revisar-plazos']
SECRETO = os.environ['TELEGRAM_WEBHOOK_SECRET']
ADMIN = int(os.environ['TELEGRAM_ADMIN_CHAT_ID'])
AUTORIZADO = int(os.environ['TELEGRAM_ALLOWED_USER_IDS'].split(',')[0])
SUBIDA = next((int(x) for x in os.environ.get('TELEGRAM_ALLOWED_CHAT_IDS', '').split(',') if x.strip().isdigit()), ADMIN)
KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
SB = os.environ['SUPABASE_URL'] + '/rest/v1/'
SB_H = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
PATH = 'zz-prueba-plazos-t0040'


def http(metodo, url, cuerpo=None, cab=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    try:
        crudo = urllib.request.urlopen(urllib.request.Request(url, data=datos, headers=cab, method=metodo), timeout=180).read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f'✗ {metodo} {url.split("//")[1].split("/", 1)[1][:60]} → {e.code}: {e.read()[:300].decode(errors="replace")}')
    return json.loads(crudo) if crudo else None


sb = lambda m, r, c=None: http(m, SB + r, c, SB_H)
n8n = lambda m, r, c=None: http(m, f'{HOST}/api/v1/{r}', c, {'X-N8N-API-KEY': APIKEY, 'Content-Type': 'application/json'})
resultados = []
def chequea(nombre, ok, detalle=''):
    resultados.append(ok)
    print(('✓' if ok else '✗'), nombre, detalle)


def hace(horas):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() - horas * 3600))


def pasos(item, step):
    return sb('GET', f'pipeline_steps?select=attempt,status&content_item_id=eq.{item}&step=eq.{step}&order=attempt')


def vuelta():
    # El webhook corre el WF22 y devuelve su resumen
    return http('POST', f'{HOST}/webhook/{PATH}', {}, {'Content-Type': 'application/json'})


temporal, creados = None, []
activo_antes = None  # el workflow temporal solo se puede activar si el WF22 lo está: se restaura al terminar
inicio = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
try:
    wf = {'name': 'zz - Prueba plazos T-0040', 'settings': {'executionOrder': 'v1'}, 'nodes': [
        {'id': 'd1000000-0000-4000-8000-000000000001', 'name': 'Webhook', 'type': 'n8n-nodes-base.webhook', 'typeVersion': 2, 'position': [100, 300],
         'webhookId': 'd1000000-0000-4000-8000-0000000000a1', 'parameters': {'httpMethod': 'POST', 'path': PATH, 'responseMode': 'lastNode'}},
        {'id': 'd1000000-0000-4000-8000-000000000002', 'name': 'Correr 22', 'type': 'n8n-nodes-base.executeWorkflow', 'typeVersion': 1.2, 'position': [350, 300],
         'parameters': {'source': 'database', 'workflowId': {'__rl': True, 'mode': 'id', 'value': WF22}, 'mode': 'once', 'options': {'waitForSubWorkflow': True}}}],
        'connections': {'Webhook': {'main': [[{'node': 'Correr 22', 'type': 'main', 'index': 0}]]}}}
    activo_antes = n8n('GET', f'workflows/{WF22}')['active']
    if not activo_antes:
        n8n('POST', f'workflows/{WF22}/activate')
    temporal = n8n('POST', 'workflows', wf)['id']
    n8n('POST', f'workflows/{temporal}/activate')

    subida = subprocess.run(['curl', '-s', '-F', f'chat_id={SUBIDA}', '-F', 'caption=Prueba T-0040 (imagen sintética, puedes ignorar)', '-F', 'photo=@golden-set/synthetic/images/libro-laberinto.png',
                             f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendPhoto"], capture_output=True, text=True).stdout
    try:
        file_id = json.loads(subida)['result']['photo'][-1]['file_id']
    except (KeyError, ValueError):
        sys.exit('✗ no pude subir la imagen de prueba a Telegram')

    def nuevo(h):
        i = sb('POST', 'content_items', {'asset_type': 'image', 'raw_asset_url': 'telegram:' + file_id, 'status': 'ready_for_review', 'notes': 'T0040 prueba',
                                         'caption_instagram': f'Caption de prueba de {h} h', 'title_youtube': f'Pieza de prueba de {h} h', 'hashtags_instagram': ['#prueba'],
                                         'caption_youtube': 'x', 'caption_tiktok': 'x', 'hashtags_tiktok': ['#prueba']})[0]['id']
        creados.append(i)
        sb('POST', 'pipeline_steps', {'content_item_id': i, 'step': 'review_send', 'attempt': 1, 'status': 'succeeded', 'started_at': hace(h), 'finished_at': hace(h)})
        return i
    a, b, c = nuevo(25), nuevo(49), nuevo(5)
    estado = lambda i: sb('GET', f'content_items?select=status&id=eq.{i}')[0]['status']

    r1 = vuelta()
    chequea('WF22 responde con su resumen', isinstance(r1, dict) or (isinstance(r1, list) and r1), str(r1)[:120])
    chequea('A (25 h): recordatorio registrado y sigue en revisión', pasos(a, 'review_reminder') == [{'attempt': 1, 'status': 'succeeded'}] and estado(a) == 'ready_for_review')
    chequea('B (49 h): detenida y con su paso review_stalled', estado(b) == 'stalled' and pasos(b, 'review_stalled') == [{'attempt': 1, 'status': 'succeeded'}])
    chequea('C (5 h): sin cambios', estado(c) == 'ready_for_review' and not pasos(c, 'review_reminder') and not pasos(c, 'review_stalled'))

    vuelta()
    chequea('segunda vuelta: el recordatorio no se repite', pasos(a, 'review_reminder') == [{'attempt': 1, 'status': 'succeeded'}])
    chequea('segunda vuelta: B sigue detenida con una sola fila', estado(b) == 'stalled' and len(pasos(b, 'review_stalled')) == 1)

    # Reabrir con el botón
    update = {'update_id': int(time.time()), 'callback_query': {'id': 'prueba-reabrir', 'from': {'id': AUTORIZADO, 'first_name': 'Prueba'}, 'data': f'reopen_{b}',
                                                              'message': {'message_id': 1, 'chat': {'id': ADMIN}}}}
    req = urllib.request.Request(f'{HOST}/webhook/sgcd-telegram', data=json.dumps(update).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'x-telegram-bot-api-secret-token': SECRETO})
    chequea('botón Reabrir → 200', urllib.request.urlopen(req, timeout=120).status == 200)
    for _ in range(15):
        time.sleep(4)
        if len(pasos(b, 'review_send')) == 2:
            break
    chequea('B vuelve a ready_for_review', estado(b) == 'ready_for_review', estado(b))
    acc = [(f['action'], f['outcome']) for f in sb('GET', f'review_actions?select=action,outcome&content_item_id=eq.{b}')]
    chequea('queda la acción reopen en review_actions', acc == [('reopen', 'applied')], str(acc))
    chequea('se reenvió la propuesta (review_send intento 2)', [p['attempt'] for p in pasos(b, 'review_send')] == [1, 2], str(pasos(b, 'review_send')))
    vuelta()
    chequea('tras reabrir, B arranca con el plazo en cero', estado(b) == 'ready_for_review' and not pasos(b, 'review_reminder') and len(pasos(b, 'review_stalled')) == 1)
finally:
    # Primero los datos (lo que más importa), después los workflows: n8n tarda en despublicar y el DELETE puede dar 409
    for i in creados:
        sb('DELETE', f'error_log?content_item_id=eq.{i}')
        sb('DELETE', f'content_items?id=eq.{i}')  # pipeline_steps y review_actions caen en cascada
    sb('DELETE', f'error_log?occurred_at=gte.{inicio}&workflow=in.(22-revisar-plazos,00-router-telegram,31-atender-revision,32-enviar-revision)')
    if temporal:
        for _ in range(6):
            try:
                n8n('POST', f'workflows/{temporal}/deactivate')
            except SystemExit:
                pass
            time.sleep(3)
            try:
                n8n('DELETE', f'workflows/{temporal}'); break
            except SystemExit:
                continue
        else:
            print('⚠ no pude borrar el workflow temporal', temporal)
    if activo_antes is False:
        try:
            n8n('POST', f'workflows/{WF22}/deactivate')
        except SystemExit:
            print('⚠ no pude desactivar el WF22 de dev')
    print(f'datos de prueba borrados: {len(creados)} item(s) y el workflow temporal')
print('RESULTADO:', 'todo bien' if resultados and all(resultados) else 'HAY FALLOS')
