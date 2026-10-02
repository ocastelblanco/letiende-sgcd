# Skills de Claude Code del proyecto

El repositorio es público, así que solo versiona las skills de autoría propia.
Las de terceros se instalan localmente desde su fuente y quedan fuera de git (`.gitignore`),
lo que evita redistribuirlas sin licencia y las mantiene actualizadas.

## Propias (versionadas, licencia MIT)

| Skill | Ruta |
|---|---|
| `ai-effort-tracking` | `.claude/skills/ai-effort-tracking/` |
| `project-docs-bootstrap` | `.claude/skills/project-docs-bootstrap/` |

## De terceros (instalar en `.claude/skills/`)

| Skills | Fuente | Licencia |
|---|---|---|
| `supabase`, `supabase-postgres-best-practices` | https://github.com/supabase/agent-skills — `npx skills add supabase/agent-skills` | MIT (declarada en el SKILL.md) |
| `gemini-api-dev`, `gemini-live-api-dev`, `gemini-omni-flash-api` | https://github.com/google-gemini/gemini-skills | Por verificar en la fuente |
| `using-n8n-mcp-skills` y las `n8n-*` (pack n8n-mcp-skills) | Autor de https://github.com/czlonkowski/n8n-mcp — URL exacta del pack por verificar | Por verificar en la fuente |
| `slim-readme`, `slim-badges` | Proyecto SLIM — URL por verificar | Por verificar en la fuente |

Antes de versionar cualquier skill de terceros, confirmar que su licencia permite redistribuirla
y conservar su archivo LICENSE y aviso de copyright.
