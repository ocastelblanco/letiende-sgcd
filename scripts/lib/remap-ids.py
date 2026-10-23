#!/usr/bin/env python3
"""Sustituye en un workflow los IDs de dev por los de producción (mapa n8n-workflows/id-map.json).

Uso: remap-ids.py <workflow.json> [--check]
  sin flag: imprime el JSON remapeado (IDs de producción aún sin asignar quedan como PENDIENTE:<archivo>)
  --check : imprime un resumen y sale con 1 si queda algún ID de dev en el resultado
"""
import json, sys

wf_path = sys.argv[1]
mapa = json.load(open('n8n-workflows/id-map.json'))
texto = open(wf_path).read()
sustitutos = {}
for archivo, dev_id in mapa['dev'].items():
    sustitutos[dev_id] = mapa['prod'].get(archivo) or f'PENDIENTE:{archivo}'
cambios = 0
for dev_id, prod_id in sustitutos.items():
    if dev_id in texto:
        cambios += texto.count(dev_id)
        texto = texto.replace(dev_id, prod_id)
restos = [d for d in sustitutos if d in texto]
# Todo Execute Workflow debe apuntar a un ID de producción conocido (o pendiente de crear): un ID desconocido es de dev
conocidos = {v for v in mapa['prod'].values() if v} | {v for v in sustitutos.values() if v.startswith('PENDIENTE:')}
for nodo in json.loads(texto)['nodes']:
    if nodo['type'] == 'n8n-nodes-base.executeWorkflow':
        wid = nodo['parameters'].get('workflowId')
        wid = wid.get('value') if isinstance(wid, dict) else wid
        if wid not in conocidos:
            restos.append(f'{nodo["name"]} -> {wid}')
if '--check' in sys.argv:
    pendientes = sorted({p for p in sustitutos.values() if p.startswith('PENDIENTE:') and p in texto})
    print(f'{cambios} ID(s) remapeados' + (f', pendientes de crear: {", ".join(p.split(":")[1] for p in pendientes)}' if pendientes else ''))
    sys.exit(1 if restos else 0)
if restos:
    sys.exit(f'quedan IDs de dev: {restos}')
print(texto, end='')
