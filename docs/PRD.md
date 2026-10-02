# PRD.md — Sistema SGCD Le Tiende

## 1. Visión del producto

| Campo | Valor |
|---|---|
| Nombre | SGCD — Sistema de Gestión de Contenidos Digitales |
| Tipo | Sistema autónomo de orquestación de contenido para redes sociales |
| Público objetivo | Equipo de Le Tiende: 3 personas (5 a corto plazo) que envían y revisan contenido |
| Idioma del sistema | Español colombiano |
| URL principal | https://n8n.letiende.co |

---

## 2. Contexto y problema que resuelve

Le Tiende es un centro cultural colombiano que reúne librería, café, bar, teatro y próximamente una tienda de discos de vinilo. El nombre "Le Tiende" es una modificación humorística y de género neutro de "La Tienda". Publica contenido en Instagram, YouTube y TikTok sobre su programación cultural. El proceso actual es completamente manual: el equipo captura activos (imágenes o videos), redacta textos para cada plataforma, coordina aprobaciones y publica manualmente.

**Problemas que resuelve el SGCD:**
- Publicar en 3 plataformas exige adaptar cada texto manualmente (formatos y límites distintos)
- Sin sistema de aprobación, el contenido puede publicarse sin revisión
- No hay visibilidad consolidada del rendimiento entre plataformas
- El proceso tarda 30–60 minutos por pieza de contenido

**Solución:** Un flujo automático que va desde la recepción del activo hasta la publicación, con una única intervención humana en el punto de aprobación.

---

## 3. Usuarios y audiencias

| Perfil | Rol | Necesidades |
|---|---|---|
| Integrante del equipo (3, pronto 5) | Envía imágenes y videos por Telegram **y** revisa las propuestas de los demás | Enviar sin fricción; ver todas las propuestas en el grupo; aprobar, editar, regenerar u **objetar** |
| Admin técnico | Monitorea el sistema | Alertas de errores, cuotas, contenidos bloqueados |

---

## 4. Objetivos

| Métrica de éxito | Objetivo | Estado |
|---|---|---|
| Tiempo de la ingesta a la revisión | p95 < 2 minutos | ❌ Sin medir (flujo caído) |
| Fidelidad del texto a la imagen | ≥ 90 % de tema correcto en el set dorado; 0 % voseo | ❌ Línea base pendiente (Fase 2) |
| Calidad percibida por el equipo | % de propuestas aprobadas sin edición, en aumento | ❌ Pendiente (Fase 4) |
| Éxito de punta a punta | ≥ 95 % de piezas llegan a revisión sin intervención técnica | ❌ 0 de 26 en las pruebas de 2026 |
| Costo del sistema | Cercano a USD 0/mes; Gemini sin facturación | ✅ Infraestructura gratuita; capacidad sin costo por calcular |
| Capacidad sin costo | Piezas/semana máximas sin pagar Gemini, conocidas y vigiladas | ❌ Pendiente (plan §3) |
| Publicación automática en Instagram | Una aprobación → publicado | ❌ Fase 5 (hoy: paquete manual por Telegram) |
| Reporte semanal de rendimiento | Cada domingo | ❌ Fase 7 |

---

## 5. Funcionalidades actuales

> **Estado real (2026-10-02):** las funcionalidades 5.1–5.4 están construidas pero el flujo nunca completó un ciclo. Ver `docs/plan-actualizacion.md` §1.

### 5.1 Ingesta de activos (⚠️ Construido, en rediseño)

```
Operador → envía foto o video por Telegram
                ↓
         Valida formato y tamaño
         ├── Imagen (JPG, PNG, WebP, GIF ≤ 20 MB) → se guarda en el repositorio de imágenes
         └── Video (MP4, MOV, AVI ≤ 200 MB)      → se guarda en el repositorio de videos
                ↓
         El sistema registra el activo y responde: "✅ Recibido. Procesando…"
                ↓
         Dispara la etapa de generación automáticamente
```

### 5.2 Generación con IA (⚠️ Construido, en rediseño — la IA no recibía la imagen)

El sistema genera automáticamente para cada activo:
- Texto para Instagram (máx 2,000 caracteres + llamada a la acción)
- 10–15 hashtags para Instagram
- Texto para TikTok (máx 150 caracteres, muy directo)
- 5–7 hashtags para TikTok
- Título para YouTube (máx 80 caracteres, con la palabra clave al inicio)
- Descripción completa para YouTube (con snippet de búsqueda y timestamps si aplica)
- Hasta 15 etiquetas para YouTube
- Horario sugerido de publicación

La IA escribe en el tono de Le Tiende: cercano, moderno, aspiracional, en español colombiano.

### 5.3 Revisión y aprobación humana (⚠️ Construido, en rediseño — pasa a revisión en equipo)

El aprobador recibe en Telegram:
- Miniatura del activo (imagen o frame del video)
- Textos generados para cada plataforma
- Horario sugerido de publicación
- 4 botones de acción:

| Botón | Efecto |
|---|---|
| ✅ Aprobar | El contenido pasa a la etapa de publicación |
| ✏️ Editar | El aprobador puede reescribir el texto antes de aprobar |
| 🔄 Regenerar | La IA genera textos nuevos para el mismo activo |
| ❌ Descartar | El activo se archiva sin publicar |

**Recordatorios automáticos:**
- 24 horas sin respuesta → primer recordatorio al aprobador
- 48 horas sin respuesta → alerta al canal del equipo, activo marcado como bloqueado

### 5.4 Empaquetado y entrega (⚠️ Construido, sin probar de punta a punta)

Cuando el aprobador aprueba, el sistema arma el paquete completo y lo entrega por Telegram:
- Texto + hashtags formateados para Instagram con el enlace a la imagen en el tamaño correcto
- Título + descripción + etiquetas + enlace a la miniatura para YouTube
- Texto + hashtags para TikTok
- El equipo publica manualmente con el paquete recibido

---

## 6. Roadmap

Detalle por fases con criterios de salida: `docs/plan-actualizacion.md`.

| Feature | Fase | Prioridad |
|---|---|---|
| Restablecer servicio, respaldo y seguridad | 0 | Crítica |
| Plataforma actualizada (n8n 2.41.x) | 1 | Alta |
| Medición por paso y set dorado con publicaciones reales de Instagram | 2 | Alta |
| Flujo de imagen confiable (visión real, salida estructurada, validadores) | 3 | Alta |
| Revisión en equipo en grupo de Telegram, con objeciones | 4 | Alta |
| Publicación automática en Instagram | 5 | Alta |
| Procesamiento y análisis de video | 6 | Media |
| Reporte semanal y monitor de cuotas | 7 | Media |
| YouTube, TikTok (API), Canva, imágenes generadas por IA, carruseles | — | Baja / sin fecha |

---

## 6.1 Requisitos de calidad de contenido generado por IA

| Requisito | Especificación |
|---|---|
| Idioma | Español de Colombia, específicamente de Bogotá. Solo tuteo ("tú"), nunca voseo ("vos"). Ejemplo: "Descubre", no "Descubrí". |
| Hashtags | Precisos para el tema detectado. No mezclar hashtags de otros temas. Genéricos permitidos: `#LeTiende`, `#CulturaBogota`, `#CafeCultural`, `#PuntoDeEncuentro`, `#AgendaCultural`, `#BarCultural`, `#BogotaCultura`, `#DondeIrEnBogota` |
| Visión | Gemini debe saber qué contiene la imagen para generar contenido relevante. Si inlineData no es viable, implementar descripción manual o File API. |
| Revisión | El mensaje de aprobación en Telegram debe mostrar captions completos de YouTube y TikTok, no truncados. |

---

## 7. Casos de uso

| Actor | Acción | Resultado esperado |
|---|---|---|
| Operador | Envía foto al bot de Telegram | Bot confirma; foto guardada; textos listos en < 2 min |
| Operador | Envía video al bot de Telegram | Bot confirma; video guardado; textos listos para revisión |
| Aprobador | Presiona "✅ Aprobar" | Recibe paquete completo por Telegram para publicar |
| Aprobador | Presiona "✏️ Editar" | Bot solicita nuevo texto; se actualiza antes de publicar |
| Aprobador | Presiona "🔄 Regenerar" | La IA genera textos nuevos con el mismo activo |
| Aprobador | Presiona "❌ Descartar" | Activo archivado, no se publica |
| Admin | No responde en 48h | Sistema envía alerta de activo bloqueado al canal del equipo |
| Admin | Domingo 6pm Colombia | Recibe reporte semanal de rendimiento (cuando Flujo 5 esté listo) |

---

## 8. Requisitos no funcionales

| Categoría | Requisito |
|---|---|
| Costo | Cercano a USD 0/mes — condición de viabilidad. Gemini opera sin facturación: al agotar la cuota, el contenido espera al día siguiente en vez de generar cobro |
| Disponibilidad | > 99% — servicios con reinicio automático ante fallos |
| Seguridad | Credenciales solo en variables de entorno, nunca en el código; webhooks con validación de origen |
| Límites externos | Respetar cuotas: Gemini según el límite del proyecto en AI Studio (Google ya no los publica), Cloudinary 25 créditos/mes, R2 10 GB, YouTube 10K unidades/día |
| Idioma | Español colombiano en todos los textos generados y comunicaciones del bot |
| Escalabilidad | Base de datos PostgreSQL para soporte de múltiples ejecuciones concurrentes |

---

## 9. Restricciones y decisiones de diseño

| Restricción | Razón |
|---|---|
| Infraestructura en Oracle Cloud Free Tier | Costo cero — requisito de viabilidad del proyecto |
| Repositorio separado: imágenes en Cloudinary, videos en Cloudflare R2 | El plan gratuito de Cloudinary (25 créditos/mes) se agotaría rápido con videos de gran tamaño; R2 es más económico para archivos grandes |
| TikTok: entrega manual mientras no se aprueba la API | La API de TikTok requiere aprobación de Meta que no está garantizada; el equipo publica manualmente con el paquete entregado |
| Una sola etapa humana en el flujo | El sistema genera y entrega; el equipo solo revisa (aprueba, edita, regenera, objeta o descarta) |
| Sin publicación directa en redes sociales (fase actual) | El sistema empaqueta y entrega; la integración directa con Instagram y YouTube es el siguiente paso del roadmap |

---

## 10. Glosario de negocio

| Término | Definición |
|---|---|
| SGCD | Sistema de Gestión de Contenidos Digitales — nombre del sistema |
| Activo | Imagen o video que se va a publicar en redes sociales |
| Texto / Caption | El texto descriptivo que acompaña un activo en cada plataforma |
| HITL | Revisión humana antes de publicar — el momento en que el aprobador decide |
| Bloqueado / Stalled | Activo que lleva más de 48h esperando aprobación |
| Objeción | Reparo de un integrante del equipo a una propuesta; bloquea la aprobación hasta resolverse |
| Set dorado | Conjunto de publicaciones reales de Instagram con lo esperado anotado, usado para medir la calidad de la IA |
| Ingesta | El proceso de recibir y registrar un activo en el sistema |
| Flujo | Una secuencia automatizada que ejecuta una parte del proceso |
| Paquete de publicación | El conjunto de textos, hashtags y enlaces listos para publicar en las tres plataformas |
| Cuota | Límite de uso de un servicio externo (YouTube, Gemini, Cloudinary) |
