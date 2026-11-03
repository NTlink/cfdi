---
name: cfdi
description: Si buscas interactuar con el timbrado mexicano de CFDI desde una terminal o un agente como Hermes, esta skill te guía con el CLI nt para revisar documentos, preparar facturas y timbrar con aprobación explícita.
---

# Cfdi — NTLink CLI para timbrado mexicano

Si buscas una manera de interactuar con el timbrado mexicano desde una terminal o un agente como Hermes, esta skill te guía para hacerlo con el CLI `nt`, en Windows o Linux.

## Instalar

Requiere Node.js 22.12 o posterior y npm. Instala o actualiza el paquete global así:

```powershell
npm install --global @ntlinkmx/nt
nt --version
nt --help
```

El nombre npm es `@ntlinkmx/nt`; el comando instalado es `nt`.

## Entornos e inicio de sesión

- Las instalaciones nuevas comienzan en modo `pruebas`. `nt mode` informa el modo sin mostrar la dirección del servidor; `nt mode pruebas` vuelve al entorno de pruebas.
- Producción todavía no existe. `nt mode production` solo muestra “próximamente” y deja activo el modo actual. No inventes una URL de producción ni afirmes que ese entorno está disponible.
- El perfil nuevo apunta al servidor remoto de `pruebas`; la primera operación protegida inicia sesión automáticamente con la cuenta pública de demostración. Correo: `URE180429TM6@ntlink.com.mx`; contraseña: `NTPruebas.2021*?`. Usa esta cuenta únicamente para pruebas compartidas.
- Ese entorno de pruebas usa HTTP. El CLI permite automáticamente HTTP solo para su origen de pruebas configurado. Otros orígenes HTTP requieren `nt config set --allow-insecure-http` y generan una advertencia en cada solicitud. Producción todavía no está disponible.
- El token se guarda en `~/.ntlink-invoice/config.json` (Windows: `%USERPROFILE%\.ntlink-invoice\config.json`). No muestres ni compartas el token.

## Qué formatos acepta

| Archivo | Uso en el CLI | Qué permite | Límite del chat |
|---|---|---|---|
| PDF | `nt chat attach archivo.pdf` o `nt chat send ID "Analiza esta factura" --attach archivo.pdf` | Extraer texto/OCR y analizar el documento en el chat. No se timbra directamente desde PDF. | 5 MB y 30 páginas |
| XML | `nt cfdi validate factura.xml`; también puede adjuntarse al chat | Validar, revisar y analizar un XML; consultar o descargar XML de un CFDI existente. No es entrada directa de `nt cfdi stamp`. | Adjuntos de chat hasta 1 MB |
| JSON | `nt cfdi prepare cfdi.json`; `nt drafts create cfdi.json`; `nt cfdi stamp cfdi.json` | Preparar un CFDI, crear/actualizar un borrador y, con autorización explícita, timbrar desde un JSON válido. | Adjuntos de chat hasta 1 MB |

Los límites indicados son para adjuntos del chat; no los extrapoles a otras funciones del CLI. El OCR puede advertir lecturas inciertas: conserva las páginas de origen, comprueba importes y pregunta por los datos faltantes.

## Comandos frecuentes

```sh
nt mode
nt health ready
nt client info
nt client balance
nt cfdi list --from 2026-10-01 --to 2026-10-31 --page 0 --size 20
nt cfdi get UUID
nt cfdi status UUID
nt cfdi validate factura.xml
nt cfdi download UUID --format xml --output factura.xml
nt cfdi download UUID --format pdf --output factura.pdf
nt cfdi prepare cfdi.json
nt drafts create cfdi.json
nt drafts list --filter estado=sin-timbrar
nt chat sessions create
nt chat sessions list
```

Para analizar un documento en el chat:

```sh
nt chat sessions create
nt chat send SESSION_ID "Analiza los campos e importes y señala dudas; no guardes ni emitas" --attach factura.pdf
nt chat events RUN_ID
```

`chat send` devuelve un `runId`; usa ese ID en `chat events`. Se aceptan hasta tres adjuntos. `nt chat attach archivo.pdf` extrae contenido sin enviarlo a un chat. Consulta `nt <grupo> --help` para ver opciones.

## Preparar y timbrar

- `nt cfdi prepare cfdi.json` prepara y valida sin guardar ni emitir.
- `nt drafts create cfdi.json` y `nt drafts update ID cfdi.json` sí guardan cambios.
- `nt cfdi stamp cfdi.json` y `nt drafts stamp ID cfdi.json` pueden timbrar realmente si el entorno y los permisos lo permiten. Aceptan JSON; no timbran directamente un PDF o XML.
- El chat puede consultar y preparar un borrador, pero no timbra, cancela, cobra ni envía correo.
- **Revisión obligatoria antes de timbrar:** presenta al usuario la factura completa que se va a emitir, incluidos emisor, receptor, conceptos, cantidades, impuestos, totales, forma y método de pago, fecha, serie y folio. Muestra los datos finales después de validar/preparar, señala cualquier valor inferido o corregido y espera que el usuario apruebe esa versión exacta antes de ejecutar `stamp`. Una solicitud inicial como «créala y timbrala» no sustituye esta revisión previa.
- Antes de crear/modificar datos, emitir, cancelar, enviar correo/WhatsApp, cobrar o realizar otro efecto externo, confirma con el usuario y comprueba `nt mode`. El nombre del perfil por sí solo no demuestra que el PAC sea sandbox.

### Ejemplo: factura de ingreso PUE

Una petición clara para iniciar el flujo sería: **«Créame una factura con estos datos y timbrala»**. Usa [el JSON de ejemplo de ingreso PUE](references/ingreso-pue.json) como datos de entrada y sigue este orden:

1. Revisa el modo activo con `nt mode` y prepara/valida el JSON con `nt cfdi prepare references/ingreso-pue.json`.
2. Presenta al usuario una vista legible de todos los datos finales de la factura. Comprueba las operaciones: subtotal $250,456.00 MXN, IVA 16% $40,072.96 MXN y total $290,528.96 MXN. Verifica con el usuario el folio y cualquier dato que haya cambiado durante la preparación.
3. Espera aprobación explícita de esa factura revisada. Si el usuario pide cambios, aplícalos y vuelve a mostrar la factura completa para otra revisión.
4. Solo después de la aprobación ejecuta `nt cfdi stamp references/ingreso-pue.json`. Informa el resultado y el UUID devuelto; si el modo o el resultado no son claros, detente y consulta antes de reintentar.

Nunca presentes el ejemplo como una factura ya emitida. El JSON es únicamente una muestra para preparar y revisar.

## Descargar y entregar el comprobante (PDF/XML)

`download` saca del servicio el comprobante ya timbrado y lo deja en disco. Necesita el UUID:

```sh
nt cfdi download UUID --format pdf --output factura.pdf
nt cfdi download UUID --format xml --output factura.xml
```

Responde `{"path": "...", "bytes": N}`. Antes de entregarlo comprueba que el archivo existe, que el PDF empieza con `%PDF` y que pesa más de ~10 KB: un PDF de 0 bytes o un HTML de error no es un comprobante.

### Entrega por WhatsApp (gateway del servidor remoto)

Cuando la petición llegó por WhatsApp, el comprobante se manda como **archivo adjunto**, no como texto, liga ni base64. El gateway convierte la etiqueta `MEDIA:<ruta absoluta>` en un documento nativo:

```
Aquí está tu factura, UUID EE5C1905-2143-47EC-A51C-91D95EE7B552.  MEDIA:/tmp/EE5C1905.pdf
```

- `[[as_document]] MEDIA:/tmp/factura.pdf` fuerza el envío como documento (cuando el archivo podría tratarse como imagen o comprimirse).
- La ruta debe ser absoluta y existir en el mismo host donde corre el agente: en el servidor remoto `/tmp` o `~/.hermes/tmp`; en Windows `%LOCALAPPDATA%\Temp`. Nunca dentro del repositorio.
- Para enviarlo a otro chat o a una persona distinta del interlocutor: `hermes send --to whatsapp:<numero> "Factura UUID … MEDIA:/tmp/factura.pdf"`.
- Un `MEDIA:` por archivo. Si piden PDF y XML, van dos mensajes (o dos etiquetas); el XML se adjunta igual que el PDF.
- Confirma UUID, RFC del receptor y total antes de enviar: es un comprobante fiscal emitido, no una vista previa.
- No borres el archivo hasta que el envío termine; si piden reenviarlo, vuelve a descargarlo con `download` en lugar de confiar en una ruta vieja.
- En modo *bot* del servidor remoto la herramienta `terminal` está restringida: si no puedes descargar el PDF, dilo; no inventes rutas ni adjuntos.

En la CLI local (terminal) `MEDIA:` no se intercepta: ahí se entrega la ruta absoluta y el usuario abre el archivo.

## PRE-CFDI y folios

Al crear un PRE-CFDI, sigue el mismo criterio de captura que la aplicación:

1. Inicia un CFDI 4.0 con los campos por completar, fecha local de Ciudad de México, tipo ingreso, MXN/PUE y conceptos vacíos.
2. Para una creación nueva, sigue el patrón de reserva de folio provisional de la aplicación. Si el CLI no ofrece esa operación, indícalo y no inventes un folio ni una reserva.
3. Al editar un borrador existente, conserva su ID y actualiza ese mismo borrador en lugar de crear otro para reemplazarlo.

Si se trabaja sin la interfaz, conserva estas distinciones:

- El `id` identifica el borrador; la reserva entrega un folio provisional `BOR-…` para capturas. No lo confundas con el folio fiscal.
- `Serie` y `Folio` son campos independientes. No concatentes la serie para inventar la secuencia.
- El folio del borrador puede conservarse al emitir y llegar al XML. No asumas que `BOR-…` será sustituido automáticamente por un consecutivo fiscal. Antes de timbrar, confirma con el usuario el folio que desea usar.
- `BOR-…` identifica provisionalmente una captura; el folio fiscal pertenece al comprobante emitido.
- El ejemplo `PUE…` es solo una muestra, no una reserva ni garantía de unicidad. No lo uses como sustituto de la reserva de folio.
- Si el sistema rechaza el folio por longitud o formato, informa el problema; no lo trunques ni lo cambies silenciosamente.

El borrador se crea/actualiza con `nt drafts create` y `nt drafts update`; consulta `nt drafts --help` para ver el formato exacto. `nt cfdi prepare` valida/prepara sin guardar ni reservar folio.

Leer un PDF no autoriza guardarlo, convertirlo en borrador, emitirlo ni pagar. Para convertirlo en borrador, presenta primero el análisis y pide confirmación antes de persistirlo.

## Actualizar y resolver problemas

- Actualiza con `npm install --global @ntlinkmx/nt`.
- Si PowerShell no encuentra `nt`, revisa `Get-Command nt` y vuelve a abrir la terminal tras instalar. En Linux, asegúrate de que el directorio global de npm está en `PATH`.
- Si aparece un 401 por una sesión vencida, vuelve a autenticar con `nt auth login` y repite solo después de revisar si la acción anterior tuvo efecto.
- Si npm devuelve 404, comprueba que la publicación inicial terminó y que el nombre es `@ntlinkmx/nt`.
