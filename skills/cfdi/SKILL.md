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
- **PRE-CFDI** (`drafts.py create` / `update`): no tiene validez fiscal. Si la petición ya trae todos los datos (o un documento que los contiene), créalo de inmediato y entrega el PDF, sin pedir confirmación ni preguntar por datos que el documento ya dice.
- **Clientes** (`create-customer`, `update-customer`): confirma con el usuario antes de guardar.
- **Efectos fiscales o externos** (`stamp`, `cancel`, `email`): solo después de revisión y aprobación explícita (ver «Timbrar»). Comprueba antes `auth.py mode`; el nombre del perfil no demuestra que el PAC sea sandbox.
- Si una escritura falla con 401 o se corta, no la repitas a ciegas: consulta primero si ya tuvo efecto (`drafts.py list`, `cfdi.py list`).
- Leer un documento (PDF, XLSX, XML) para convertirlo en factura sí autoriza crear el PRE-CFDI, pero nunca timbrar ni cancelar. Si el documento ya indica el tratamiento de impuestos (IVA sí/no, retención), sigue lo que dice sin preguntar.
- Si una lectura es dudosa (OCR, celdas con valores ocultos), di qué valor usaste y por qué.

## Prioridad: entregar el PRE-CFDI cuanto antes

El camino normal es: leer los datos → completar lo que falte con los valores por defecto de abajo → `prepare` → revisar → `drafts.py create` → entregar el PDF. Pregunta solo si, después de intentar completar, falta un dato que no se puede inferir (por ejemplo, el RFC del receptor o los conceptos). En ese caso di exactamente qué falta, por qué no se puede deducir y si el usuario puede proporcionarlo; si no puede, indícalo y no inventes el dato.

No pidas datos que ya están en la cuenta o en el documento, ni confirmes decisiones que tienen un valor por defecto razonable: aplícalas, decláralas en la respuesta final y deja que el usuario las corrija.

## Cuenta y empresas

```sh
python scripts/directory.py account        # datos del sistema y timbres
python scripts/directory.py balance        # saldo de timbres
python scripts/directory.py companies      # empresas emisoras (companyId, rfc, legalName)
python scripts/directory.py company 7975   # detalle de una empresa
```

**Emisor por defecto:** el emisor es la cuenta con la que estás conectado, no algo que se pregunte. `directory.py account` devuelve su `rfc` y `razonSocial`; `directory.py companies` da el `companyId` cuyo `rfc` coincide. En pruebas la cuenta es URE (`URE180429TM6`, companyId 7975), así que todo comprobante de prueba sale a nombre de UNIVERSIDAD ROBOTICA ESPAÑOLA SA DE CV. En producción será la empresa del cliente que usa la skill; el mismo procedimiento aplica. Solo pregunta por otro emisor si el usuario lo pide explícitamente.

El `rfc` va en `emisor.rfc` del comprobante. La clave de `emisor.regimenFiscal` sale del catálogo `RegimenFiscal` (en la cuenta de pruebas: `601`).

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
2. Completa RFC, razón social, régimen fiscal (`catalogs.py get RegimenFiscal`) y código postal del domicilio fiscal con lo disponible. Si falta el régimen del receptor, aplica 601 provisional y avisa que queda pendiente de revisión, sin preguntar ese campo. Pregunta solo por otros datos obligatorios ausentes. Correo y domicilio son opcionales.
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

En `list`, los valores de `status` que se ven en pruebas son `PAGADO` y `PENDIENTE`: son estados locales del listado, no el estatus ante el SAT. `--filter status=VIGENTE` no devuelve filas.

Si `download` responde 404 «Archivo no encontrado en Azure», el backend no tiene guardado el PDF o XML de ese CFDI. No hay otra fuente: dilo y no inventes el archivo.

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

**Antes de emitir:** consulta `drafts.py next-folio --company COMPANY_ID` para
la emisora y usa exactamente el valor recibido. No reserva: si otra emisión
lo consume, vuelve a consultar, actualiza el mismo borrador y revisa de nuevo.
El portal rechaza con 400 folios vacíos, BOR, personalizados, atrasados o
adelantados. No inventes incrementos, fechas como folio ni trunques el valor.

**Fecha:** hora local de la sucursal emisora, `YYYY-MM-DDTHH:mm:ss`, sin Z ni
offset. La zona es la de su estado, no siempre CDMX: `python scripts/drafts.py zone --cp CP`
devuelve `timeZone` (p. ej. `America/Tijuana` para Baja California). Úsala con
`datetime.now(ZoneInfo(timeZone)).strftime('%Y-%m-%dT%H:%M:%S')`, con
`from datetime import datetime; from zoneinfo import ZoneInfo`. No uses `utcnow()`,
`toISOString()` ni borres la Z de una hora UTC: quitar la zona no convierte la hora.
Si el servidor no conoce la zona, usa `America/Mexico_City`. Si `zone` responde 404, ese backend no tiene la ruta desplegada: usa `America/Mexico_City` solo para sucursales de CDMX o Aguascalientes, y dilo en la respuesta. Si faltan zonas
horarias, resuélvelo antes de emitir; no adivines la hora. No reutilices fechas
de ejemplos antiguos. El backend rechaza fechas inválidas o futuras
antes del PAC. Corrige el mismo borrador y vuelve a revisar; un 409 de
conciliación no autoriza borrar candados ni reintentar a ciegas.

| Script | Devuelve | ¿Se timbra? |
|---|---|---|
| `drafts.py next-folio` | El siguiente folio fiscal real de la empresa (ej. `000009135`). Solo consulta: no reserva ni incrementa. | **Sí**, es el folio para emitir. |
| `drafts.py reserve-folio` | Un folio provisional `BOR-…` de captura, con su propio contador. | **Nunca.** |

- Antes de timbrar un borrador, consulta `next-folio`, ponlo en `folio` en lugar de `BOR-…`, guarda con `drafts.py update`, descarga el PDF actualizado y preséntalo para revisión.
- `serie` y `folio` son campos independientes. No inventes folios (fechas, incrementos propios) ni reutilices el de otra factura.
- Si el usuario pide otro folio, explica que el portal exige el siguiente de la empresa. No intentes saltarte la validación.

## Preparar un comprobante

1. Elige el ejemplo más cercano en [`references/cfdi40/`](references/cfdi40/README.md) (20 casos: ingreso, egreso, traslado, IVA 0/8/16%, exento, retenciones, RESICO, factura global, extranjero, a cuenta de terceros, objetoImp 01–08) o [`references/ingreso-pue.json`](references/ingreso-pue.json).
2. Completa los datos sin preguntar:
   - **Emisor:** la cuenta por defecto (ver «Cuenta y empresas»).
   - **Receptor:** de `customers` si existe. Si no, usa los datos del documento o de la petición directamente en `receptor` (RFC, nombre, C.P. como `domicilioFiscalReceptor`, régimen y uso). No des de alta el cliente salvo que lo pidan.
   - **Régimen del receptor:** conserva el que aporte el usuario, el documento o el directorio. Si no está disponible, captura `601` por defecto, intenta preparar y guardar el PRE-CFDI y no preguntes ese régimen al usuario. Declara siempre: «Régimen fiscal del receptor: 601 aplicado por defecto; pendiente de revisión». No lo presentes como verificado ante SAT ni deducido del RFC; es una captura provisional autorizada. Si el backend rechaza esa combinación, informa el error concreto y deja pendiente la preparación, sin inventar otra clave ni repetir la pregunta por el régimen. No timbres ni omitas la revisión por haber aplicado el valor por defecto.
   - **Uso de CFDI:** el que diga el documento, traducido a su clave del catálogo `UsoCFDI` (p. ej. «adquisición de mercancías» → `G01`, «gastos en general» → `G03`). Confirma la clave en el catálogo.
   - **Claves SAT y unidad:** verificadas en los catálogos; el `ClaveProdServ` y `ClaveUnidad` que diga el documento son válidos si existen en el catálogo.
   - **Fecha:** hora local de la sucursal emisora (ver «Folios»); si el documento trae fecha, úsala.
   - **Folio:** `drafts.py next-folio --company COMPANY_ID`.
3. Aplica el tratamiento de impuestos (ver «Cuadrar impuestos con un total») y ejecuta `python scripts/cfdi.py prepare cfdi.json`. Usa los totales que devuelve.
4. **Revisión antes de guardar** (sin preguntar al usuario). Guardar un PRE-CFDI lo deja en la base de datos, así que esta revisión va antes de `drafts.py create`:
   - Compara el JSON preparado con lo que pidió el usuario: emisor (la cuenta), receptor, conceptos, cantidades, claves, fecha, folio y forma/método de pago.
   - Verifica la aritmética: subtotal − retenciones + traslados = total, y cada impuesto = base × tasa, redondeado a centavos.
   - Comprueba que las claves SAT existen en su catálogo y que el folio es el que devolvió `next-folio`.
   - Si hay un error claro (un redondeo, un campo mal copiado), corrígelo en el JSON y vuelve a ejecutar `prepare`. Si el error necesita una decisión del usuario, no guardes: pregunta solo ese punto.
5. Guarda el PRE-CFDI con `drafts.py create` y entrega el PDF. Tras guardar, confirma que el PDF empieza con `%PDF` y no está vacío.
6. En la respuesta final di en una línea qué revisaste y el resultado.

**Estilo para usuarios finales:** respuestas simples y cortas. Si falta un dato, pregunta en una o dos frases, sin explicaciones largas ni listas de posibilidades.

### Cuadrar impuestos con un total

Si el documento o la petición dan un total, los impuestos deben cuadrar con él. Orden de decisión:

1. **El documento dice el tratamiento** (p. ej. «sin IVA», «IVA 16%», «retención ISR 1.25%»): aplícalo tal cual, aunque no cuadre con el total de la hoja. Si el total no cuadra, muestra el total calculado y la diferencia, no lo fuerces.
2. **El documento solo da un total y un subtotal:** prueba, en este orden, IVA 16% sobre el subtotal, IVA incluido en el precio (base = total / 1.16) y sin IVA; quédate con el que cuadre con el total, y si hay retención (`ObjetoImp 02`, `001`, `0.0125` para ISR 1.25%) inclúyela solo si el total lo exige. Declara el que elegiste.
3. **Sin total ni tratamiento:** IVA 16% sobre el subtotal, sin retenciones.

Redondea IVA y retenciones a centavos antes de comparar. Si el total calculado difiere del documento por centavos, usa el calculado y dilo.

En el JSON, la retención va en `conceptos[].impuestos.retenciones` (con `objetoImp` `02`) y en `impuestos.retenciones` con `totalImpuestosRetenidos`. Un concepto sin IVA ni retención lleva `objetoImp` `01`; si tiene retención o traslado, `02`.

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
python scripts/cfdi.py download UUID --format acuse --output acuse.pdf
python scripts/cfdi.py retention-cancel ID_RETENCION --reason 02
python scripts/cfdi.py retention-acuse ID_RETENCION --output acuse-retencion.pdf
python scripts/cfdi.py email UUID --to cliente@example.com
```

El acuse PDF solo existe para un comprobante ya cancelado. Si responde 409, el receptor rechazó la solicitud y el backend regresó el CFDI a vigente: dilo así y no lo presentes como cancelado. El id de una retención es el campo `id` de `reports retentions` / `GET /api/v2/customer/retentions`.

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
- `cancel` → 500 «Error al cancelar: …»: el texto que sigue es el motivo del PAC o del SAT (en el entorno de pruebas siempre ocurre: el SAT no conoce sus CFDI y el PAC responde que no pudo consultar su estatus). El CFDI sigue vigente; compruébalo con `cfdi.py list --filter uuid=UUID` (`fechaCancelacion`) y no digas que se canceló.
- `validate` de un CFDI timbrado en pruebas marca «Verificacion del sello del PAC: NO» porque el PAC de pruebas usa un certificado de prueba; el resto de las validaciones deben salir «SI».
- `404 «Ruta de portal no encontrada»` o `405` en `credit-note`, `download --format acuse`, `retention-acuse` o `drafts.py zone`: el backend no tiene desplegada esa ruta. Con la versión de pruebas del 9/nov/2026 ocurre así. Dilo tal cual, no reintentes en bucle y no simules el resultado.
- `python` no encontrado: usa `py` (Windows) o `python3` (Linux/macOS).

El CLI de Node `nt` (`npm install --global @ntlinkmx/nt`) es una alternativa opcional que usa la misma API y el mismo archivo de sesión. Los scripts no lo necesitan.

## Notas de crédito y acceso desde el chat

Parte de la factura de ingreso: `cfdi.py credit-note UUID --output nota.json`
devuelve, sin guardar, un egreso con los datos del XML real, `TipoRelacion` 01
al UUID de origen, `UsoCFDI` G02 si el régimen del receptor lo admite (si
no, conserva el uso del ingreso), `MetodoPago` PUE y la misma `FormaPago` del
ingreso (Anexo 20). Si el ingreso tenía `99`, la nota llega sin `formaPago`:
pide la forma real. Ajusta conceptos e importes al monto de la devolución o
descuento (importes positivos); el ejemplo `references/cfdi40/06-egresos.json`
muestra la forma. Ejecuta `cfdi.py prepare nota.json` y `drafts.py create
nota.json` tras la petición de guardado. Revisa antes de `stamp`; no hay
descuento automático del saldo de origen. En la interfaz, Reportes de
facturas ofrece «Crear nota de crédito» en cada ingreso vigente.
El chat prepara ese borrador y ofrece un enlace a Cancelaciones con UUID y
fechas; el usuario confirma allí. Los scripts y CLI pueden cancelar con
aprobación explícita usando sus comandos existentes.


## Leer documentos y analizarlos por chat

Usa el backend para extraer PDF, Excel XLSX/XLS, CSV UTF-8, XML, JSON y JPG/PNG. No instales lectores ni conviertas estos archivos localmente.

```sh
python scripts/chat.py attach factura.xlsx
python scripts/chat.py create-session
python scripts/chat.py send SESSION_ID "Analiza discrepancias sin guardar" --attach factura.xlsx
python scripts/chat.py events RUN_ID
```

`attach` devuelve el adjunto JSON, sin guardar borradores. `send` acepta hasta tres `--attach`, devuelve el run y admite `--request-id UUID` para conservar identidad ante reintentos. `events` devuelve el SSE como texto JSON; espera hasta finalizar. Revisa la sesión y sus borradores antes de repetir una intención con otro UUID tras un fallo. Excel/CSV conservan hojas, celdas, valores originales y formato visible en `text` (JSON). Revisa advertencias: fórmulas sin recalcular, valores ausentes, errores y contenido oculto. Aclara hojas/tablas ambiguas. Adjuntar o pedir análisis no autoriza guardar; preparar un borrador requiere petición expresa. No timbra ni cancela.

Límites: 5 MB por archivo, XML/JSON 1 MB; tablas hasta 20 hojas, 2000 filas y 100 columnas por hoja, 10000 celdas y 120000 bytes de texto; imágenes 20 megapíxeles. Los libros grandes se rechazan sin recortar. Detalle en `references/api.md`.

Al preparar desde Excel, revisa el domicilio completo antes de pedir el CP. Conserva los resultados guardados de fórmulas con advertencia; no pidas reconfirmación solo por contener fórmulas. Pregunta ante discrepancias, errores o resultados ausentes. Si el régimen fiscal del receptor no está en el documento, petición ni directorio, usa 601 provisional con el aviso de revisión, sin preguntarlo. Al usar chat o CLI desde esta skill, incluye el 601 por defecto autorizado y su aviso en la instrucción al backend; no esperes a que lo infiera ni traslades al usuario una pregunta por ese régimen.

CLI 0.2.3: lectura de adjuntos mediante el backend, incluidos Excel y XML; en Hermes usa la skill autónoma `cfdi-whatsapp` con `nt`. La instalación privada del CLI en el VPS no implica publicación npm. Los JSON de entrada admiten BOM UTF-8 tanto en los scripts Python como en los adjuntos de Go. Verificado en la API de pruebas tras el despliegue bda877b del 10/nov/2026.
