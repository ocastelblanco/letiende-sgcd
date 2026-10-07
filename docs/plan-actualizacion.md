# Plan de actualización y mejora — SGCD Le Tiende

> Plan vigente desde 2026-10-02. Reemplaza las fases "Semana 1–4" del plan original.
> Las tareas activas salen de aquí hacia `docs/TODO.md` (motor JIT, 2 tareas a la vez).

---

## 1. Diagnóstico de partida (2026-10-02)

| Hallazgo | Evidencia | Impacto |
|---|---|---|
| Sistema caído | Certificado SSL de `n8n.letiende.co` vencido el 2026-06-18. Certbot está en el host, pero nginx corre en Docker y la renovación nunca funcionó | Telegram no entrega nada al bot desde junio |
| Ningún contenido completó el ciclo | 26 registros en `content_items`: 8 `ingested`, 7 `processing`, 11 `ready_for_review`, 0 aprobados | El flujo nunca funcionó de punta a punta |
| **Gemini no veía las imágenes** | Con la URL en el texto del prompt (método de ADR-007), tres corridas describieron un Listerine, un vino y un portátil. Con la imagen enviada como datos describió correctamente *La clase de griego* de Han Kang | Captions inventados: causa raíz de la mala calidad |
| Dos workflows pelean por el bot | WF01 y WF03 tienen cada uno un Telegram Trigger; Telegram admite un solo webhook por bot. El webhook vivo solo acepta `message` | Los botones de aprobación no llegaban a ningún flujo |
| Encadenamiento frágil | Los workflows se llaman entre sí por HTTP a la URL pública | Depende de SSL, DNS y nginx; los fallos a mitad de camino dejan items atascados sin rastro |
| El manejo de errores también falla | El INSERT en `error_log` usa una columna inexistente (`created_at`) | Los errores no se registraban |
| Plataforma desactualizada | n8n 2.12.3 sobre la imagen `latest` sin fijar (hoy existe la 2.41.6). JSON escritos a mano con versiones de nodo viejas | Parte de los "bugs de n8n" vienen de esa configuración |
| VM justa | E2.1.Micro: 2 vCPU, 954 MB de RAM y 455 MB de swap en uso | Poco margen para un n8n más nuevo |

## 2. Principios del plan

1. **Medir antes de cambiar.** Cada paso del flujo deja un registro (Fase 2); cada cambio se compara contra una línea base.
2. **Costo cercano a USD 0 garantizado por diseño**, no por vigilancia: el proyecto de Gemini va **sin facturación** (`letiende-sgcd`); el de pago, con tope prepago, queda solo como respaldo (ADR-013, 2026-10-07). Al agotar la cuota la API responde 429 y no cobra; el flujo encola y reintenta después del reinicio diario.
3. **Un cambio a la vez, verificable.** Cada fase tiene un criterio de salida numérico.
4. **Nunca editar producción directamente con IA.** Los workflows se construyen y validan con n8n-mcp en la instancia de desarrollo local y luego se despliegan.
5. **Equipo de 3 a 5 personas.** Todo el equipo ve las propuestas en un grupo de Telegram y cualquiera puede objetar.

## 3. Capacidad semanal sin costo en Gemini

Google ya no publica los límites de la capa gratuita: cada proyecto los ve en AI Studio
(<https://aistudio.google.com/rate-limit>). Se aplican **por proyecto y por modelo**, y la cuota diaria (RPD)
se reinicia a medianoche del Pacífico, es decir, 02:00 en Bogotá con horario de verano en EE. UU. y 03:00 sin él.
Por eso la capacidad se calcula con una fórmula alimentada con los límites reales del proyecto (tabla del 2026-10-07 en ADR-013) y con las llamadas por pieza medidas en la Fase 2.

**Llamadas a Gemini por pieza en el flujo rediseñado (Fase 3):**

| Paso | Imagen | Video corto (≤ 90 s) | Modelo |
|---|---|---|---|
| Extracción visual estructurada | 1 | 1 (más carga en tokens) | Modelo A (ligero) |
| Redacción por plataforma | 1 | 1 | Modelo B |
| Reintento por validación fallida | `r` (medido) | `r` (medido) | B |
| Regeneración pedida por el equipo | `g` × 2 (medido) | `g` × 2 (medido) | A y B |

**Fórmula:**

```
capacidad_semanal = min sobre cada modelo m de  ⌊ RPD_m × 7 × 0,8  ÷  llamadas_m_por_pieza ⌋
```

- `0,8` deja un 20 % de margen para pruebas manuales y picos.
- Repartir los dos pasos entre modelos distintos suma cuotas independientes, porque los límites son por modelo.
- También hay que comprobar RPM y TPM: varias piezas enviadas a la vez no pueden pasar del límite por minuto (el flujo serializa con una cola), y los videos consumen muchos más tokens por llamada.
- Las evaluaciones del set dorado consumen cuota. Se programan fuera del horario de operación, y su consumo se descuenta antes de calcular la capacidad.
- No se crean proyectos adicionales para multiplicar la cuota de producción: hay que revisar los términos de la API de Gemini antes de considerar cualquier separación de proyectos.

**Entregable:** tabla de capacidad (piezas/semana por tipo) en `docs/MEMORY.md`, recalculada al cambiar de modelo.
El mismo ejercicio se hace para Cloudinary (25 créditos/mes), R2 (10 GB) y Supabase, para saber cuál es el cuello de botella real.

## 4. Fases

### Fase 0 — Restablecer, respaldar y asegurar

- Respaldo completo: workflows vivos (API de n8n), base de n8n (`pg_dump` en la VM) y Supabase.
- Rotar las credenciales expuestas en `.claude/settings.local.json` y limpiar el archivo.
- Restablecer HTTPS con renovación automática. Propuesta: reemplazar nginx + certbot por **Caddy**, que gestiona sus certificados.
- Definir la estrategia de costo de Gemini (T-0011): la cuenta actual ya tiene facturación. Anotar RPM, TPM y RPD de los modelos candidatos del proyecto elegido.

**Salida:** `/healthz` responde 200 con certificado válido; renovación probada (`caddy` o simulación de certbot); respaldo restaurable; límites de Gemini anotados.

### Fase 1 — Plataforma al día

- n8n 2.12.3 → 2.41.x **con la versión fijada** (nunca `latest`).
- `docker-compose.yml`:
  - quitar `N8N_BASIC_AUTH_*`, que no tienen efecto desde n8n 1.x (la protección es la cuenta owner con 2FA);
  - quitar `version`;
  - publicar el 5678 solo en `127.0.0.1`.
- Medir RAM y CPU. Si no alcanza, intentar la VM ARM A1.Flex gratuita (4 OCPU, 24 GB).
  - **Cerrada el 2026-10-07 (T-0019):** 72 h estables, 333–405 MB disponibles y CPU en reposo: se mantiene la E2.1.Micro. Salvedad: hubo que añadir `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` para que los workflows ejecutaran.
- PostgreSQL 15 se mantiene; cambiar de versión mayor no aporta valor ahora.
- **Instancia de desarrollo local:** `infrastructure/docker-compose.dev.yml` con n8n (misma versión fijada) y PostgreSQL en el Mac. Todo workflow se construye y valida ahí con n8n-mcp (`N8N_MCP_TARGET=dev`), y solo se despliega a producción ya probado (ADR-014).

**Salida:** n8n 2.41.x estable 72 h en producción, uso de memoria registrado e instancia de desarrollo con la misma versión.

### Fase 2 — Instrumentación y banco de pruebas

- Tabla `pipeline_steps` en Supabase: `content_item_id`, paso, inicio, fin, estado, error, modelo, tokens y costo. Cada subworkflow escribe su fila.
- Vista de tablero: duración por paso (p50 y p95), tasa de fallo por paso, items atascados y consumo de cuota diario.
- **Set dorado a partir de publicaciones reales de Instagram**:
  - Origen: la exportación oficial de Instagram (*Configuración → Tu actividad → Descargar tu información*, formato JSON), que trae imágenes, videos y captions sin necesidad de app ni token.
  - Selección: 15–20 publicaciones representativas (libros, café, bar, teatro, vinilos, eventos).
  - Por pieza se anotan los **hechos esperados** (tema, título, autor, evento, fecha) y el caption original como **referencia de estilo**.
  - Los captions reales también sirven como ejemplos de tono (*few-shot*) en el prompt de redacción.
  - El set vive fuera del repositorio público (carpeta local ignorada o bucket R2); en git solo van los resultados agregados.
- Script de evaluación que corre la generación sobre el set y califica de forma automática:
  - tema correcto;
  - hechos mencionados;
  - cero voseo;
  - hashtags dentro de la lista permitida;
  - longitudes por plataforma;
  - JSON válido.

**Salida:** línea base medida del flujo actual y tablero operativo.

### Fase 3 — Rediseño del flujo de imagen

- **Una sola entrada de Telegram:** un workflow `00 - Router Telegram` recibe `message` y `callback_query` y despacha. El webhook queda registrado con `allowed_updates` y `secret_token` (OWASP A01).
- **Subworkflows** (`Execute Workflow`) en lugar de llamadas HTTP a sí mismo: ingesta → extracción → redacción → revisión.
- **Visión real:** la imagen viaja a Gemini como datos. En un Code node, `this.helpers.getBinaryDataBuffer()` da los bytes, que se convierten a base64 para `inline_data`.
- **Generación en dos pasos con salida estructurada** (`responseMimeType: application/json` y `responseSchema`):
  1. Extracción: qué hay en la imagen, texto legible y entidades.
  2. Redacción por plataforma: usa la extracción, el tema que escribió quien envió la pieza y ejemplos de estilo.
- **Validadores deterministas** antes de la revisión: longitudes, voseo, lista de hashtags y hechos obligatorios. Si falla, un reintento con la causa del fallo.
- **Selección de modelo con evidencia:** comparar 3–4 candidatos de capa gratuita (familia 3.x Flash y Flash-Lite, Gemma 4) en el set dorado; gana el que pase los umbrales con menor consumo de cuota.
- **Máquina de estados con guardas, cola y reintentos:**
  - estado `waiting_quota` ante un 429;
  - reproceso automático de items atascados;
  - manejo de errores que sí registra en `error_log`.
- Se borran todos los datos de prueba (Supabase y ejecuciones de n8n).

**Salida:**
- Set dorado: tema correcto ≥ 90 %, salida válida 100 %, voseo 0 %.
- Punta a punta: ≥ 95 % de éxito en 20 corridas y p95 de la ingesta a la revisión < 2 min.

### Fase 4 — Revisión en equipo

- Grupo de Telegram con todo el equipo. El bot publica cada propuesta en el grupo con los botones: ✅ Aprobar · ✏️ Editar · 🔄 Regenerar · 💬 Objetar · ❌ Descartar.
- **Lista de usuarios autorizados** (`TELEGRAM_ALLOWED_USER_IDS`): las acciones de cualquier otra persona se ignoran y se registran.
- Tabla `review_actions`: quién hizo qué y cuándo, con el texto de la objeción o de la edición.
- Política propuesta (a confirmar al iniciar la fase):
  - una aprobación de alguien distinto a quien envió la pieza;
  - una objeción abierta bloquea la aprobación hasta resolverse;
  - recordatorio a las 24 h y estado `stalled` a las 48 h.
- Para que el bot lea las fotos enviadas al grupo hay que desactivar el modo privacidad (BotFather `/setprivacy`) o hacerlo administrador.
- Indicadores de calidad que salen solos: % aprobado sin edición, ediciones y regeneraciones por pieza, objeciones por pieza.

**Salida:** 20 piezas revisadas por el equipo con su trazabilidad completa en `review_actions`.

### Fase 5 — Publicación automática en Instagram

- La cuenta es Creator y está vinculada a una página de Facebook; la API de publicación de contenido de Instagram admite cuentas profesionales (Business y Creator). Se verifican los permisos vigentes al iniciar la fase.
- Flujo: aprobación → contenedor de medios → `media_publish` → guardar `instagram_post_id` → estado `published`.
- Tokens de larga duración con alerta antes de vencer (OWASP A07).
- El paquete manual por Telegram queda como respaldo y sigue siendo el canal para TikTok y YouTube.

**Salida:** 10 publicaciones reales automáticas sin intervención y cero tokens vencidos sin alerta.

### Fase 6 — Video

- Decidir con datos dónde se procesa: Lambda con Node 24 (Node 20 ya no tiene soporte), FFmpeg en la VM (solo si se consigue la A1) o transformaciones de Cloudinary.
- Gemini analiza el video corto subido por la File API.

### Fase 7 — Métricas y monitor de cuotas

- WF05 cobra sentido cuando existen IDs de publicación (Fase 5).
- Monitor diario: cuota de Gemini, créditos de Cloudinary y almacenamiento de R2, con alerta al 80 %.

## 5. Costos esperados

| Servicio | Plan | Costo |
|---|---|---|
| Oracle Cloud VM | Always Free | 0 |
| Supabase | Free (los crons evitan la pausa por inactividad) | 0 |
| Gemini API | Capa gratuita, proyecto sin facturación | 0 (al agotar cuota: 429, no cobro) |
| Cloudinary | Free, 25 créditos/mes | 0 |
| Cloudflare R2 | Free, 10 GB | 0 |
| Telegram Bot API | — | 0 |
| Instagram API | — | 0 |
| AWS Lambda (Fase 6, si se elige) | Capa gratuita | 0; ECR cobra almacenamiento del orden de centavos |
| Route 53 | Zona DNS de `letiende.co` | USD 0,50/mes, compartido con el sitio |

En la capa gratuita de Gemini, Google puede usar el contenido para mejorar sus productos. Se aceptó porque el contenido es material de marketing que igual se publica.

## 6. Decisiones abiertas

| Decisión | Cuándo se resuelve |
|---|---|
| ~~Caddy vs. reparar certbot~~ | Resuelta el 2026-10-03: Caddy (ADR-015) |
| VM E2.1.Micro vs. A1.Flex | Final de la Fase 1, con mediciones |
| Modelos A y B de Gemini | Fase 3, con el set dorado |
| Política de aprobación del equipo | Inicio de la Fase 4 |
| Procesamiento de video | Inicio de la Fase 6 |
