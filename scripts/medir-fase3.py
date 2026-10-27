#!/usr/bin/env python3
"""Medición de salida de la Fase 3 (T-0037): 20 corridas punta a punta, % de éxito y p50/p95 de la ingesta a la revisión.

Sube cada imagen del set dorado (golden-set/pieces, fuera de git) a Telegram para obtener un file_id real, la manda al router
como foto del administrador y espera a que el flujo la lleve a `ready_for_review` con el paso `review_send` exitoso. De una en una,
con 3 s entre piezas (regla del proyecto) y un máximo de TIMEOUT_S por pieza. Mide con `pipeline_steps`, no con relojes propios.

  éxito  = el item queda en `ready_for_review` y su paso `review_send` terminó `succeeded`
  tiempo = de `ingest.started_at` a `review_send.finished_at`
  criterio de la Fase 3 (plan §4): éxito ≥ 95 % y p95 < 120 s

Cada pieza que llega manda al grupo de revisión una propuesta de prueba (avisar al equipo antes). Las fotos se suben al chat
privado de la primera id de TELEGRAM_ALLOWED_CHAT_IDS (sin ruido en el grupo); si no hay, al chat de administración.
Al terminar borra los items de prueba (con sus pasos y acciones) y las filas de error_log de la corrida; el resumen queda en
golden-set/results/fase3-<fecha>.json. Los secretos se leen de credentials.env y nunca se imprimen.

Uso:
  python3 scripts/medir-fase3.py                      simulación: lista las piezas y no toca nada
  python3 scripts/medir-fase3.py --run                20 piezas contra el router de producción
  python3 scripts/medir-fase3.py --run --limit 3 --url http://127.0.0.1:5678/webhook/sgcd-telegram   prueba corta en dev
  opciones: --keep (no borra los datos de prueba)
"""
import argparse, json, math, os, pathlib, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
for linea in (ROOT / 'credentials.env').read_text().splitlines():
    linea = linea.strip()
    if linea and not linea.startswith('#') and '=' in linea:
        k, v = linea.split('=', 1)
        os.environ.setdefault(k, v.strip().strip('"\''))

ap = argparse.ArgumentParser()
ap.add_argument('--run', action='store_true')
ap.add_argument('--limit', type=int, default=20)
ap.add_argument('--url', default='https://n8n.letiende.co/webhook/sgcd-telegram')
ap.add_argument('--keep', action='store_true')
args = ap.parse_args()

TIMEOUT_S = 300   # por pieza; pasado este tiempo cuenta como fallo y se sigue con la siguiente
PAUSA_S = 3       # entre piezas (regla del proyecto entre llamadas a Gemini)
UMBRAL_EXITO, UMBRAL_P95_S = 0.95, 120
ETIQUETA = 'T0037'
SECRETO = os.environ['TELEGRAM_WEBHOOK_SECRET']
ADMIN = int(os.environ['TELEGRAM_ADMIN_CHAT_ID'])
SUBIDA = next((int(x) for x in os.environ.get('TELEGRAM_ALLOWED_CHAT_IDS', '').split(',') if x.strip().isdigit()), ADMIN)
TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
SB = os.environ['SUPABASE_URL'] + '/rest/v1/'
SB_H = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json', 'Prefer': 'return=representation'}

piezas = sorted((ROOT / 'golden-set' / 'pieces').glob('*.json'))[:args.limit]
if not piezas:
    sys.exit('✗ no hay piezas en golden-set/pieces')
if not args.run:
    print(f'Simulación: {len(piezas)} piezas hacia {args.url} (fotos subidas al chat {SUBIDA}).')
    for p in piezas:
        d = json.loads(p.read_text())
        print(f"  {d['id']:45s} {d['theme']:14s} {d['image']}")
    print('Para medir: python3 scripts/medir-fase3.py --run')
    sys.exit(0)


def sb(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    crudo = urllib.request.urlopen(urllib.request.Request(SB + ruta, data=datos, headers=SB_H, method=metodo), timeout=60).read()
    return json.loads(crudo) if crudo else None


def post(cuerpo):
    req = urllib.request.Request(args.url, data=json.dumps(cuerpo).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'x-telegram-bot-api-secret-token': SECRETO})
    try:
        return urllib.request.urlopen(req, timeout=120).status
    except urllib.error.HTTPError as e:
        return e.code


def a_jpeg(ruta, tmp):
    """Telegram acepta mejor JPEG/PNG que WebP en sendPhoto: se convierte con sips (macOS)."""
    if ruta.suffix.lower() in ('.jpg', '.jpeg', '.png'):
        return ruta
    destino = pathlib.Path(tmp) / (ruta.stem + '.jpg')
    subprocess.run(['sips', '-s', 'format', 'jpeg', str(ruta), '--out', str(destino)], capture_output=True, check=True)
    return destino


def subir(ruta):
    # El token va en la URL de la API: no se imprime
    out = subprocess.run(['curl', '-s', '-F', f'chat_id={SUBIDA}', '-F', f'caption={ETIQUETA} (medición de la Fase 3, puedes ignorar)', '-F', f'photo=@{ruta}',
                          f'https://api.telegram.org/bot{TOKEN}/sendPhoto'], capture_output=True, text=True).stdout
    return json.loads(out)['result']['photo'][-1]['file_id']


def iso(s):
    return time.mktime(time.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')) + (float('0.' + s[20:26].split('+')[0].split('Z')[0]) if len(s) > 20 and s[19] == '.' else 0)


def pasos(item):
    return sb('GET', f'pipeline_steps?select=step,attempt,status,started_at,finished_at,error_type,model&content_item_id=eq.{item}&order=started_at,id')


def percentil(valores, p):
    v = sorted(valores)
    if not v:
        return None
    k = (len(v) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return round(v[lo] + (v[hi] - v[lo]) * (k - lo), 1)


resultados, items, inicio = [], [], time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
base = int(time.time())
tmp = tempfile.mkdtemp(prefix='fase3-')
try:
    for n, p in enumerate(piezas, 1):
        d = json.loads(p.read_text())
        r = {'pieza': d['id'], 'tema': d['theme'], 'ok': False, 'causa': None, 'segundos': None, 'pasos': []}
        resultados.append(r)
        t0 = time.time()
        try:
            file_id = subir(a_jpeg((p.parent / d['image']).resolve(), tmp))
        except Exception as e:  # noqa: BLE001 - la subida falla antes de entrar al flujo: se anota y se sigue
            r['causa'] = f'subida a Telegram: {type(e).__name__}'
            print(f'[{n:2d}/{len(piezas)}] ✗ {d["id"]}: {r["causa"]}')
            continue
        marca = f'{ETIQUETA}-{base}-{n:02d}'
        update = {'update_id': base + n, 'message': {'message_id': base + n, 'chat': {'id': ADMIN}, 'photo': [{'file_id': file_id}],
                                                    'caption': f'{marca} {d.get("notes", "")}'[:1024]}}
        estado = post(update)
        if estado != 200:
            r['causa'] = f'router respondió {estado}'
            print(f'[{n:2d}/{len(piezas)}] ✗ {d["id"]}: {r["causa"]}')
            continue
        item, ps = None, []
        while time.time() - t0 < TIMEOUT_S:
            time.sleep(4)
            filas = sb('GET', f'content_items?select=id,status&notes=like.{urllib.parse.quote(marca)}*')
            if not filas:
                continue
            item = filas[0]['id']
            if item not in items:
                items.append(item)
            ps = pasos(item)
            envio = [x for x in ps if x['step'] == 'review_send']
            if filas[0]['status'] == 'error' or (envio and envio[-1]['status'] in ('succeeded', 'failed')):
                break
        r['pasos'] = [{k: x[k] for k in ('step', 'attempt', 'status', 'error_type', 'model')} for x in ps]
        if item is None:
            r['causa'] = 'el flujo no creó el item (WF30 no llegó a la ingesta)'
        else:
            estado_item = sb('GET', f'content_items?select=status&id=eq.{item}')[0]['status']
            envio = [x for x in ps if x['step'] == 'review_send' and x['status'] == 'succeeded']
            ingest = [x for x in ps if x['step'] == 'ingest']
            if estado_item == 'ready_for_review' and envio and ingest:
                r['ok'] = True
                r['segundos'] = round(iso(envio[-1]['finished_at']) - iso(ingest[0]['started_at']), 1)
            else:
                malo = [x for x in ps if x['status'] in ('failed', 'waiting_quota')]
                r['causa'] = (f"estado {estado_item}; " + (f"{malo[-1]['step']} {malo[-1]['status']} {malo[-1]['error_type'] or ''}".strip() if malo else 'sin llegar a review_send (tiempo agotado)'))
        print(f'[{n:2d}/{len(piezas)}] {"✓" if r["ok"] else "✗"} {d["id"]:45s} {r["segundos"] if r["ok"] else r["causa"]}')
        time.sleep(PAUSA_S)

    # Resumen
    total = len(resultados)
    oks = [r for r in resultados if r['ok']]
    tiempos = [r['segundos'] for r in oks]
    reintentos = [(r['pieza'], x['step'], x['attempt'], x['status'], x['error_type']) for r in resultados for x in r['pasos'] if x['attempt'] > 1 or x['status'] in ('waiting_quota',) or x['error_type'] in ('gemini_http',)]
    tasa = len(oks) / total
    resumen = {'fecha': inicio, 'url': args.url, 'piezas': total, 'exitos': len(oks), 'tasa_exito': round(tasa, 4), 'p50_s': percentil(tiempos, 0.5), 'p95_s': percentil(tiempos, 0.95),
               'max_s': max(tiempos) if tiempos else None, 'reintentos_o_cuota': reintentos,
               'criterio': {'exito_minimo': UMBRAL_EXITO, 'p95_maximo_s': UMBRAL_P95_S},
               'cumple': bool(tasa >= UMBRAL_EXITO and (percentil(tiempos, 0.95) or 1e9) < UMBRAL_P95_S), 'detalle': resultados}
    sal = ROOT / 'golden-set' / 'results' / f'fase3-{time.strftime("%Y%m%d-%H%M%S")}.json'
    sal.parent.mkdir(parents=True, exist_ok=True)
    sal.write_text(json.dumps(resumen, ensure_ascii=False, indent=2))
    print(f'\nÉxito: {len(oks)}/{total} ({tasa:.0%}) · p50 {resumen["p50_s"]} s · p95 {resumen["p95_s"]} s · máx {resumen["max_s"]} s')
    print(f'Reintentos o cuota: {len(reintentos)} {reintentos[:6]}')
    for r in resultados:
        if not r['ok']:
            print(f'  ✗ {r["pieza"]}: {r["causa"]}')
    print(f'Criterio de la Fase 3 (≥ {UMBRAL_EXITO:.0%} y p95 < {UMBRAL_P95_S} s): {"CUMPLE" if resumen["cumple"] else "NO CUMPLE"}')
    print(f'Detalle en {sal.relative_to(ROOT)}')
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    if args.keep:
        print(f'--keep: {len(items)} item(s) de prueba conservados')
    else:
        for i in items:
            sb('DELETE', f'error_log?content_item_id=eq.{i}')
            sb('DELETE', f'content_items?id=eq.{i}')  # pipeline_steps y review_actions caen en cascada
        sb('DELETE', f'error_log?occurred_at=gte.{inicio}&workflow=in.(00-router-telegram,30-recibir-pieza,20-procesar-pieza,32-enviar-revision)')
        print(f'datos de prueba borrados: {len(items)} item(s)')
