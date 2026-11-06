# Cfdi — NTLink agent skill

Facturación electrónica mexicana (CFDI 4.0) con el backend de NTLink desde cualquier agente: Codex, Claude Code, OpenCode, Cursor o Hermes. La skill trae scripts de Python que llaman directamente a la API: listar empresas, clientes, catálogos SAT y facturas; crear clientes; preparar PRE-CFDI; descargar PDF/XML, y timbrar o cancelar con aprobación explícita.

Solo requiere **Python 3.8 o posterior**. No hay `pip install`, Node ni CLI adicional.

```
skills/cfdi/
├── SKILL.md              # instrucciones para el agente
├── scripts/
│   ├── ntlink_api.py     # cliente HTTP común (biblioteca estándar)
│   ├── auth.py           # login, status, logout, mode
│   ├── directory.py      # cuenta, empresas, clientes
│   ├── catalogs.py       # catálogos SAT
│   ├── cfdi.py           # facturas timbradas: list, download, prepare, stamp, cancel
│   └── drafts.py         # PRE-CFDI y folios
└── references/
    ├── api.md            # rutas HTTP y script de cada una
    ├── cfdi40/           # 20 ejemplos CFDI 4.0 (JSON + XML)
    ├── ingreso-pue.json
    └── cliente.json
```

## Instalar

Con el instalador de skills:

```bash
npx skills add NTlink/Cfdi --skill cfdi --global
```

Elige los agentes durante la instalación, o pásalos con `--agent` (por ejemplo `--agent codex`).

O copia `skills/cfdi/` en la carpeta de skills de tu agente:

| Agente | Carpeta |
|---|---|
| Claude Code | `~/.claude/skills/cfdi` |
| Codex | `~/.codex/skills/cfdi` |
| OpenCode | `~/.config/opencode/skills/cfdi` |
| Cursor | `~/.cursor/skills/cfdi` |
| Hermes | `~/.hermes/skills/cfdi` |

## Probar

```bash
python skills/cfdi/scripts/auth.py mode
python skills/cfdi/scripts/directory.py companies
python skills/cfdi/scripts/cfdi.py prepare skills/cfdi/references/ingreso-pue.json
```

En el entorno de pruebas la primera llamada inicia sesión sola con la cuenta pública de demostración. Para otra cuenta: `python skills/cfdi/scripts/auth.py login --email CORREO`.

## Actualizar

```bash
npx skills update cfdi --global
```

Antes de cada timbrado la skill exige mostrar la factura completa y esperar la aprobación explícita de esa versión exacta. Para entregar comprobantes por WhatsApp desde Hermes existe la skill aparte `cfdi-whatsapp`.
