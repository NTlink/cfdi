---
name: cfdi
description: Facturación electrónica mexicana (CFDI 4.0) con el backend de NTLink desde cualquier agente (Codex, Claude Code, OpenCode, Cursor, Hermes). Incluye scripts de Python sin dependencias para listar empresas, clientes, catálogos SAT y facturas; crear clientes; preparar PRE-CFDI; descargar PDF/XML, y timbrar o cancelar con aprobación explícita. Úsala cuando el usuario quiera crear, revisar, buscar, descargar, timbrar o cancelar una factura, o consultar datos fiscales de su cuenta NTLink.
---

# Cfdi — facturación CFDI con NTLink

Scripts de Python que llaman directamente a la API de NTLink. Solo necesitan Python 3.8 o posterior: sin `pip install`, sin Node y sin CLI adicional.

Los scripts están en la carpeta `scripts/` **de esta skill**. Ejecútalos con su ruta completa, por ejemplo `python <carpeta-de-la-skill>/scripts/cfdi.py list`. Si `python` no existe, usa `py` en Windows o `python3` en Linux y macOS. Todos devuelven JSON por stdout; los errores salen por stderr como `{"error": "...", "status": N}` y terminan con código 1.

## Primer uso

1. Comprueba el entorno con `python scripts/auth.py mode`. Las instalaciones nuevas están en modo `pruebas`.
2. En pruebas no hace falta iniciar sesión: el primer comando protegido entra solo con la cuenta pública de demostración (`URE180429TM6@ntlink.com.mx` / `NTPruebas.2021*?`). Esa cuenta es de administrador y sus datos son compartidos: úsala solo para pruebas. El entorno de pruebas usa HTTP sin TLS; nunca envíes ahí contraseñas reales.
3. Para entrar con otra cuenta usa `python scripts/auth.py login --email CORREO`. La contraseña se pide oculta, o se lee de `NTLINK_PASSWORD` o de stdin con `--password-stdin`. No la escribas en la línea de comandos.
4. Producción todavía no existe: `auth.py mode production` solo responde «próximamente». No inventes una URL de producción.

El token se guarda en `~/.ntlink-invoice/config.json` (Windows: `%USERPROFILE%\.ntlink-invoice\config.json`), el mismo archivo que usa el CLI `nt`. No muestres el token. Variables opcionales: `NTLINK_TOKEN`, `NTLINK_BASE_URL`, `NTLINK_PROFILE`, `NTLINK_TIMEOUT` (segundos).

## Reglas de seguridad

- **Lecturas** (listar, consultar, descargar, `prepare`, `validate`): ejecútalas sin pedir permiso.
- **Escrituras** (crear o modificar clientes y PRE-CFDI): confirma con el usuario qué vas a guardar.
- **Efectos fiscales o externos** (`stamp`, `cancel`, `email`): solo después de revisión y aprobación explícita (ver «Timbrar»). Comprueba antes `auth.py mode`; el nombre del perfil no demuestra que el PAC sea sandbox.
- Si una escritura falla con 401 o se corta, no la repitas a ciegas: consulta primero si ya tuvo efecto (`drafts.py list`, `cfdi.py list`).
- Leer un PDF o XML no autoriza guardarlo, convertirlo en borrador ni emitirlo. Analízalo tú mismo, presenta el resultado y pregunta antes de persistir. Si una lectura es dudosa (OCR, importes que no cuadran), dilo y pregunta los datos faltantes.

## Cuenta y empresas

```sh
python scripts/directory.py account        # datos del sistema y timbres
python scripts/directory.py balance        # saldo de timbres
python scripts/directory.py companies      # empresas emisoras (companyId, rfc, legalName)
python scripts/directory.py company 7975   # detalle de una empresa
```

Usa `companies` para elegir el emisor: el `rfc` va en `emisor.rfc` del comprobante y el `companyId` sirve para filtrar listas o asignar clientes.

## Clientes

```sh
python scripts/directory.py customers                    # todos los clientes (customerId, companyId, rfc, legalName)
python scripts/directory.py customer 6942                # detalle
python scripts/directory.py blacklist RFC                # ¿está en la lista 69/69-B del SAT?
python scripts/directory.py create-customer cliente.json
python scripts/directory.py update-customer 6942 cliente.json
python scripts/directory.py delete-customer 6942         # 409 si tiene comprobantes
```

Para crear un cliente:

1. Busca primero en `customers` si el RFC ya existe en esa empresa; si existe, ofrece actualizarlo en lugar de duplicarlo.
2. Pide los datos fiscales que exige CFDI 4.0: RFC, razón social exacta de la constancia, régimen fiscal (`catalogs.py get RegimenFiscal`) y código postal del domicilio fiscal. Correo y domicilio son opcionales.
3. Escribe el JSON con la forma de [`references/cliente.json`](references/cliente.json). `companyId` indica a qué empresa pertenece el cliente; si falta, se usa la de la sesión.
4. Muestra los datos, confirma y ejecuta `create-customer`. La respuesta trae el `customerId` guardado. Si el RFC ya existe en la empresa o el código postal no está en el catálogo del SAT, el backend responde 400 con el motivo: corrígelo con el usuario, no lo fuerces.

Cliente extranjero: RFC `XEXX010101000`, `foreignTaxId` (NumRegIdTrib) y `country` distinto de México. Público en general: `XAXX010101000`. Los campos completos y las reglas de validación están en [`references/api.md`](references/api.md#cuenta-empresas-y-clientes).

## Catálogos SAT

```sh
python scripts/catalogs.py list                           # nombres disponibles
python scripts/catalogs.py get UsoCFDI                    # primeras 100 filas
python scripts/catalogs.py get ClaveProdServ --q tornillo # busca en clave y descripción
python scripts/catalogs.py get FormaPago --id 03          # clave exacta
```

Catálogos: `ClaveProdServ`, `ClaveUnidad`, `RegimenFiscal`, `UsoCFDI`, `FormaPago`, `MetodoPago`, `TipoDeComprobante`, `Exportacion`, `Moneda`, `ObjetoImp`, `Impuesto`, `TipoFactor`, `Periodicidad`, `Meses`, `TipoRelacion`. Devuelven `[{"id", "descripcion"}]`. Confirma cada clave en el catálogo antes de usarla; no la deduzcas de memoria.

## Facturas timbradas

```sh
python scripts/cfdi.py list --from 2026-10-01 --to 2026-10-31 --page 0 --size 20
python scripts/cfdi.py list --company 7975 --filter rfcReceptor=GOFB8210255F4
python scripts/cfdi.py get UUID
python scripts/cfdi.py status UUID
python scripts/cfdi.py validate factura.xml
```

`list` devuelve `{"content": [...]}` con `uuid`, `fechaFactura`, `rfcEmisor`, `rfcReceptor`, `status`, `tipoComprobante`, `total` y `moneda`. Filtros: `--page`, `--size` (máx. 200), `--company`, `--customer`, `--from`, `--to` y, con `--filter KEY=VALUE`, `rfcEmisor`, `rfcReceptor`, `uuid`, `tipoComprobante` (`I`, `E`, `T`, `P`, `N`) y `status`. Para buscar por RFC usa `--filter rfcReceptor=RFC`; `--search` no busca en el RFC.

`status` (consulta de estatus ante el SAT) responde 503 mientras el backend no la habilite; dilo así y no lo interpretes como un CFDI cancelado. `validate` revisa estructura, certificado y sello: los XML de `references/cfdi40/` son muestras y su sello no es válido.

## Descargar PDF y XML

```sh
python scripts/cfdi.py download UUID --format pdf --output factura.pdf
python scripts/cfdi.py download UUID --format xml --output factura.xml
python scripts/drafts.py download BORRADOR_ID --format pdf --output precfdi.pdf
python scripts/drafts.py download BORRADOR_ID --format xml --output precfdi.xml
```

Responden `{"path": "<ruta absoluta>", "bytes": N}`. No sobrescriben un archivo existente salvo con `--force`. Antes de entregarlo comprueba que el PDF empieza con `%PDF` y que no pesa casi nada: un archivo vacío o un HTML de error no es un comprobante. Entrega la ruta real; no inventes rutas ni digas que adjuntaste algo que no descargaste.

## PRE-CFDI (borradores)

```sh
python scripts/drafts.py list --filter estado=sin-timbrar
python scripts/drafts.py get BORRADOR_ID
python scripts/drafts.py create cfdi.json                 # guarda y descarga PRE-CFDI-ID.pdf
python scripts/drafts.py create cfdi.json --pdf-output precfdi.pdf
python scripts/drafts.py update BORRADOR_ID cfdi.json
python scripts/drafts.py next-folio
python scripts/drafts.py reserve-folio
```

- `create` guarda el borrador y descarga su PDF de revisión. La salida conserva `metadata.id` y añade `pdf.path`. Si aparece `pdfError`, el borrador **ya quedó guardado**: recupera el PDF con `drafts.py download` y no repitas la creación.
- Entrega el PDF cada vez que crees o actualices un PRE-CFDI, aunque no lo pidan, salvo que el usuario diga que no lo quiere. El XML es adicional y no lo sustituye.
- El PDF dice PRE-CFDI / BORRADOR: no está timbrado ni tiene validez fiscal. El XML es de revisión, sin sello ni timbre.
- `get`, `create` y `update` responden `{"metadata", "cfdi", "companyId"}`. Para editar, guarda el objeto `cfdi` en un archivo, cámbialo y envíalo con `update`; `metadata` (ID, folio, totales) no se envía.
- Al editar, conserva el ID y actualiza el mismo borrador; no crees otro para reemplazarlo. La API no tiene ruta para borrar borradores.

### Folios

| Script | Devuelve | ¿Se timbra? |
|---|---|---|
| `drafts.py next-folio` | El siguiente folio fiscal real de la empresa (ej. `000009135`). Solo consulta: no reserva ni incrementa. | **Sí**, es el folio para emitir. |
| `drafts.py reserve-folio` | Un folio provisional `BOR-…` de captura, con su propio contador. | **Nunca.** |

- Antes de timbrar un borrador, consulta `next-folio`, ponlo en `folio` en lugar de `BOR-…`, guarda con `drafts.py update`, descarga el PDF actualizado y preséntalo para revisión.
- `serie` y `folio` son campos independientes. No inventes folios (fechas, incrementos propios) ni reutilices el de otra factura.
- Si el usuario pide un folio distinto de `next-folio`, confírmalo. Si el sistema rechaza el folio, informa el error; no lo trunques.

## Preparar un comprobante

1. Elige el ejemplo más cercano en [`references/cfdi40/`](references/cfdi40/README.md) (20 casos: ingreso, egreso, traslado, IVA 0/8/16%, exento, retenciones, RESICO, factura global, extranjero, a cuenta de terceros, objetoImp 01–08) o [`references/ingreso-pue.json`](references/ingreso-pue.json).
2. Ajusta emisor (de `companies`), receptor (de `customers`), conceptos y claves verificadas en los catálogos. Si el usuario no da fecha, usa la hora local de Ciudad de México con el formato `YYYY-MM-DDTHH:mm:ss`, sin `Z` ni zona.
3. Ejecuta `python scripts/cfdi.py prepare cfdi.json`: valida y recalcula importes sin guardar. Usa los totales que devuelve.
4. Para guardarlo como borrador usa `drafts.py create`.

La forma completa del JSON está en [`references/api.md`](references/api.md#forma-del-json-del-comprobante).

## Timbrar

`cfdi.py stamp cfdi.json` y `drafts.py stamp ID cfdi.json` emiten un CFDI real si el entorno y los permisos lo permiten.

- **Revisión obligatoria:** antes de timbrar presenta la factura completa: emisor, receptor, conceptos, cantidades, impuestos, totales, forma y método de pago, fecha, serie y folio, tal como quedó después de `prepare`. Señala cualquier valor inferido o corregido y espera que el usuario apruebe esa versión exacta. Un pedido inicial como «créala y timbrala» no sustituye la revisión.
- **Una sola confirmación por versión:** si el usuario ya vio el resumen y responde «timbra», «sí» o algo equivalente, timbra de inmediato, sin repetir el resumen. Vuelve a pedir revisión solo si cambió algún dato.
- La respuesta es `{"uuid", "folio", "idVenta", "pdfGenerado", "xmlRespaldadoS3", "draftUpdated"}`. Informa el UUID y entrega el PDF (`cfdi.py download`). Después de timbrar, consulta otra vez `next-folio` para la siguiente factura; no sumes uno por tu cuenta.
- Al timbrar un PRE-CFDI, el borrador queda ligado al UUID (`metadata.uuid`) y deja de aparecer con `estado=sin-timbrar`.
- Informa el resultado tal como llegó. Si el resultado no es claro, consulta `cfdi.py list` antes de reintentar.

### Ejemplo: factura de ingreso PUE

Petición: «Créame una factura con estos datos y timbrala», con [`references/ingreso-pue.json`](references/ingreso-pue.json).

1. `python scripts/auth.py mode` y `python scripts/cfdi.py prepare references/ingreso-pue.json`.
2. Presenta la factura: subtotal $250,456.00 MXN, IVA 16% $40,072.96 MXN, total $290,528.96 MXN. Para el folio, `drafts.py next-folio`.
3. Espera la aprobación. Si piden cambios, aplícalos y vuelve a presentarla completa.
4. `python scripts/cfdi.py stamp references/ingreso-pue.json` e informa el UUID.

El JSON es una muestra para preparar y revisar; nunca lo presentes como factura emitida.

## Cancelar y enviar por correo

```sh
python scripts/cfdi.py cancel UUID --reason 02
python scripts/cfdi.py cancel UUID --reason 01 --replacement UUID_SUSTITUTO
python scripts/cfdi.py email UUID --to cliente@example.com
```

Motivos SAT: `01` con errores y relación (requiere `--replacement`), `02` con errores sin relación, `03` no se llevó a cabo la operación, `04` operación nominativa en factura global. Ambas acciones son efectos reales: confirma UUID, receptor y total con el usuario antes de ejecutarlas.

## Referencia

- [`references/api.md`](references/api.md): todas las rutas HTTP, sus parámetros y respuestas, y el script que usa cada una.
- [`references/cfdi40/`](references/cfdi40/README.md): 20 ejemplos CFDI 4.0 en JSON y XML, con el resultado de `prepare` de cada uno.
- [`references/cliente.json`](references/cliente.json): alta de cliente.
- Ayuda de cada script: `python scripts/<script>.py --help` y `python scripts/<script>.py <comando> --help`.

Scripts: `auth.py` (sesión y modo), `directory.py` (cuenta, empresas, clientes), `catalogs.py` (catálogos SAT), `cfdi.py` (facturas timbradas), `drafts.py` (PRE-CFDI y folios). `ntlink_api.py` es el cliente HTTP común.

## Problemas frecuentes

- `401`: la sesión venció. Ejecuta `auth.py login` (en pruebas, `auth.py logout` y el siguiente comando vuelve a entrar con la cuenta de demostración). Revisa si la acción anterior tuvo efecto antes de repetirla.
- `exito:false` o `400`: el backend rechazó los datos; lee el mensaje, corrige el JSON y vuelve a ejecutar `prepare`.
- `cfdiRelacionados debe ser un objeto`: la API acepta un solo grupo, `{"tipoRelacion", "cfdiRelacionado": [{"uuid"}]}`.
- `File exists`: el archivo de salida ya existe; elige otra ruta o usa `--force`.
- `email` → 503 «Configura SMTP…»: el servidor no tiene correo configurado (así está hoy el entorno de pruebas). Entrega el PDF/XML descargado en su lugar.
- `cancel` → 500 «El certificador no devolvió un acuse de cancelación»: el PAC no confirmó la cancelación y el CFDI sigue vigente. Hoy ocurre siempre en el entorno de pruebas. Comprueba con `cfdi.py list --filter uuid=UUID` (`fechaCancelacion`) y no digas que se canceló.
- `validate` de un CFDI timbrado en pruebas marca «Verificacion del sello del PAC: NO» porque el PAC de pruebas usa un certificado de prueba; el resto de las validaciones deben salir «SI».
- `python` no encontrado: usa `py` (Windows) o `python3` (Linux/macOS).

El CLI de Node `nt` (`npm install --global @ntlinkmx/nt`) es una alternativa opcional que usa la misma API y el mismo archivo de sesión. Los scripts no lo necesitan.
