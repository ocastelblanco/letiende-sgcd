#!/usr/bin/env python3
"""Registra (o consulta) el webhook del bot de Telegram apuntando al router de n8n, con secret_token (OWASP A01).

Uso:
  python3 scripts/set-telegram-webhook.py            simulación: muestra el webhook actual y lo que se registraría
  python3 scripts/set-telegram-webhook.py --apply    registra y verifica con getWebhookInfo

Condición: los Telegram Trigger de WF01 y WF03 deben estar desactivados (deploy-workflows.sh --apply --retirar-viejos); si siguen
activos, n8n les devuelve el bot al reiniciarse. El token y el secreto se leen de credentials.env; nunca se imprimen.
"""
import json, os, sys, urllib.parse, urllib.request

for linea in open('credentials.env'):
    linea = linea.strip()
    if linea and not linea.startswith('#') and '=' in linea:
        k, v = linea.split('=', 1)
        os.environ.setdefault(k, v.strip().strip('"\''))

DESTINO = 'https://n8n.letiende.co/webhook/sgcd-telegram'
PERMITIDOS = ['message', 'callback_query']
TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
SECRETO = os.environ.get('TELEGRAM_WEBHOOK_SECRET', '')
apply = '--apply' in sys.argv[1:]
if any(a not in ('--apply',) for a in sys.argv[1:]):
    sys.exit('uso: set-telegram-webhook.py [--apply]')
if len(SECRETO) < 16 or not all(c.isalnum() or c in '_-' for c in SECRETO):
    sys.exit('✗ TELEGRAM_WEBHOOK_SECRET falta, es corto o tiene caracteres que Telegram no admite (A-Z a-z 0-9 _ -)')


def api(metodo, datos=None):
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    req = urllib.request.Request(f'https://api.telegram.org/bot{TOKEN}/{metodo}', data=cuerpo, headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=30))['result']


def resumen(info):
    return {'url': info.get('url') or '(ninguno)', 'pendientes': info.get('pending_update_count'),
            'allowed_updates': info.get('allowed_updates'), 'último error': info.get('last_error_message', 'ninguno')}


antes = api('getWebhookInfo')
print('webhook actual:', resumen(antes))
print('se registraría:', {'url': DESTINO, 'allowed_updates': PERMITIDOS, 'secret_token': '(de credentials.env)'})
if not apply:
    print('✓ Simulación completa. Nada se modificó. Para registrar: python3 scripts/set-telegram-webhook.py --apply')
    sys.exit(0)

api('setWebhook', {'url': DESTINO, 'secret_token': SECRETO, 'allowed_updates': PERMITIDOS, 'drop_pending_updates': False})
despues = api('getWebhookInfo')
print('webhook ahora:', resumen(despues))
ok = despues.get('url') == DESTINO and sorted(despues.get('allowed_updates', [])) == sorted(PERMITIDOS) and not despues.get('last_error_message')
print('✓ Webhook registrado y verificado' if ok else '✗ El webhook no quedó como se esperaba: revisa arriba')
sys.exit(0 if ok else 1)
