# Ejemplos CFDI 4.0

Casos tomados de `NTlink/ntlink-utils` (`src/test/resources/cfdi40`). Cada número existe en dos formatos:

- `NN-*.json`: entrada para `cfdi.py prepare`, `drafts.py create` o `cfdi.py stamp`. Se quitaron `sello`, `certificado` y `noCertificado`; el backend los genera al timbrar.
- `NN-*.xml`: el XML original del caso, útil para `cfdi.py validate` o para ver cómo queda cada nodo.

Todos usan el emisor `URE180429TM6` (régimen 601) de la cuenta de pruebas. Fuera de pruebas cambia emisor, receptor, `lugarExpedicion`, `fecha` y `folio`. `prepare` recalcula importes: presenta los totales que devuelve, no los del archivo.

| # | Tipo | Método/forma | Impuestos y nodos que muestra | `prepare` |
|---|---|---|---|---|
| 01 `ingreso` | I | PUE/02 | IVA 8% (frontera); retención ISR 10% e IVA 2/3; cuenta predial | OK |
| 02 `ingreso-exento` | I | PUE/01 | IVA exento; retención ISR 10% (honorarios médicos) | OK |
| 03 `ingreso-descuento-aplicado` | I | PUE/02 | Como 01 con `descuento` | OK |
| 04 `retencion-iva-6` | I | PUE/02 | IVA 16%; retención IVA 6% | OK |
| 05 `ingreso-iva-tasa-0` | I | PUE/02 | IVA tasa 0% | OK |
| 06 `egresos` | E | PUE/02 | Nota de crédito con `cfdiRelacionados` (tipo 01) | OK |
| 07 `traslado` | T | — | Traslado de mercancía, sin importes ni impuestos | OK |
| 08 `a-cuenta-de-terceros` | I | PUE/01 | IVA 16%; nodo `aCuentaTerceros` | OK |
| 09 `cfdi-relacionados` | I | PUE/01 | IVA 16%; dos grupos de `cfdiRelacionados` (04 y 01) | **Falla**: la API acepta un solo grupo, como objeto |
| 10 `informacion-global` | I | PUE/01 | Factura global a `XAXX010101000` con `informacionGlobal` | OK |
| 11 `rfc-extranjero-xexx010101000` | I | PUE/02 | Receptor extranjero; USD con `tipoCambio` | OK |
| 12 `ingreso-1` | I | PUE/02 | Concepto no objeto de impuesto (`objetoImp` 01) | OK |
| 13 `marca-de-retencion-2-resico` | I | PUE/03 | IVA 16%; retención ISR RESICO 1.25% | OK |
| 14 `marca-de-retencion-1-…-isr` | I | PUE/01 | IVA 0% y 16% mezclados; retención IVA 4%; descuento | OK |
| 15 `cuenta-predial` | I | PUE/01 | Retención ISR 10%; descuento; uso `CP01` | OK |
| 16 `objimp-06` | I | PUE/28 | `objetoImp` 06; retención ISR 1.25%; factura global | OK |
| 17 `objimp-07` | I | PUE/28 | `objetoImp` 07; IEPS cuota; retención ISR 1.25% | OK |
| 18 `objimp-08` | I | PPD/99 | `objetoImp` 08; retención ISR 1.25%; descuento | OK |
| 19 `resico-servicio-persona-moral` | I | PUE/03 | IVA 16%; retención ISR RESICO 1.25% | OK |
| 20 `resico-producto-a-persona-fisica` | I | PUE/01 | IVA exento; retención ISR RESICO 1.25% | OK |

La columna `prepare` es el resultado de `python scripts/cfdi.py prepare` contra el entorno de pruebas el 5/nov/2026. `06-egresos.json` se convirtió de arreglo a objeto (un solo grupo, mismo contenido). `09` conserva los dos grupos del original; para emitirlo hoy deja uno solo.

Otros ejemplos:

- [`../ingreso-pue.json`](../ingreso-pue.json): ingreso PUE con IVA 16%, usado en el flujo de revisión y timbrado de `SKILL.md`.
- [`../cliente.json`](../cliente.json): alta de un cliente (receptor) con `directory.py create-customer`.
