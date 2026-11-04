"""Borra del grupo de revisión las propuestas que mandó WF32 para items de prueba.

Los scripts de prueba borran sus items de la base, pero las propuestas seguían en el grupo con botones vivos («No encontré ese
contenido», 2026-11-04). Cada `review_send` guarda su `n8n_execution_id`; la salida del nodo «Enviar propuesta» de esa ejecución
trae `chat_id` y `message_ids`. Llamar ANTES de borrar los items: `pipeline_steps` cae en cascada con ellos.
Telegram solo deja borrar mensajes de menos de 48 h. Los secretos se leen del entorno y nunca se imprimen.

Uso: from limpiar_propuestas import borrar_propuestas
     borrar_propuestas(ids_de_items, url_del_router_o_host)
"""
import json, os, urllib.parse, urllib.request


def _get(url, headers):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60).read())


def borrar_propuestas(items, url):
    """Devuelve cuántos mensajes borró. Nunca lanza excepciones: la limpieza no debe tapar el resultado de la prueba."""
    items = [i for i in items if i]
    if not items:
        return 0
    dev = '127.0.0.1' in url or 'localhost' in url
    host = 'http://127.0.0.1:5678' if dev else 'https://n8n.letiende.co'
    n8n_h = {'X-N8N-API-KEY': os.environ['N8N_DEV_API_KEY' if dev else 'N8N_API_KEY']}
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    sb_h = {'apikey': key, 'Authorization': 'Bearer ' + key}
    borrados = 0
    try:
        pasos = _get(os.environ['SUPABASE_URL'] + '/rest/v1/pipeline_steps?select=n8n_execution_id&step=eq.review_send'
                     f'&content_item_id=in.({",".join(items)})', sb_h)
    except Exception:  # noqa: BLE001
        return 0
    for ex in {p['n8n_execution_id'] for p in pasos if p.get('n8n_execution_id')}:
        try:
            run = _get(f'{host}/api/v1/executions/{urllib.parse.quote(ex)}?includeData=true', n8n_h)['data']['resultData']['runData']
            salida = run['Enviar propuesta'][0]['data']['main'][0][0]['json']
        except Exception:  # noqa: BLE001 - ejecución ya purgada o de una versión de WF32 sin message_ids
            continue
        for mid in salida.get('message_ids') or []:
            cuerpo = json.dumps({'chat_id': salida['chat_id'], 'message_id': mid}).encode()
            req = urllib.request.Request(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/deleteMessage", data=cuerpo,
                                         headers={'Content-Type': 'application/json'}, method='POST')
            try:
                borrados += bool(json.loads(urllib.request.urlopen(req, timeout=30).read()).get('ok'))
            except Exception:  # noqa: BLE001
                pass
    return borrados
