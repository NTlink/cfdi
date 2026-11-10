# API del backend NTLink

Las rutas que usan los scripts. Todas, salvo `auth/login`, requieren `Authorization: Bearer <token>`. Las respuestas son JSON salvo las descargas. Un error devuelve `{"message": "..."}` con su código HTTP.

Base de pruebas: `http://pruebas.ntlink.com.mx:8092`. Producción todavía no existe.

Timbrado `/api/v2/cfdis/stamp` y `/api/v2/pre-cfdis/{id}/stamp`: fecha inválida
o futura y folio distinto del siguiente de la emisora devuelven 400 con mensaje
específico antes del PAC y del diario. Usa la hora local de la sucursal (zona de su estado; `GET /api/v2/pre-cfdis/zona-expedicion?cp=CP`) sin Z/offset y consulta
`GET /api/v2/pre-cfdis/folios/next?companyId=ID` con
`drafts.py next-folio --company ID`. Omitir companyId usa la empresa de sesión.
La consulta valida alcance y no reserva ni incrementa. Folios BOR, vacíos,
personalizados, atrasados o adelantados no se timbran; actualiza el mismo
borrador y revisa otra vez. No se sustituyen datos revisados silenciosamente.

## Sesión

| Método | Ruta | Script | Notas |
|---|---|---|---|
| POST | `/api/v2/auth/login` | `auth.py login` | Cuerpo `{"email","password"}` → `{"token","email","roles","termsAndConditions"}`. No hay refresh token: un 401 exige nuevo login. |
| GET | `/api/v2/customer/profile` | `auth.py status`, `directory.py account` | Datos del sistema: RFC, razón social, régimen, timbres. |

## Cuenta, empresas y clientes

| Método | Ruta | Script | Notas |
|---|---|---|---|
| GET | `/api/v2/customer/balances` | `directory.py balance` | Timbres disponibles por sistema. |
| GET | `/api/v2/customer/companies` | `directory.py companies` | Empresas emisoras: `companyId`, `rfc`, `legalName`, `inactive`, `locked`, `assignable`. |
| GET | `/api/v2/customer/companies/{id}` | `directory.py company ID` | Detalle con domicilio y régimen. |
| GET | `/api/v2/customer/clients` | `directory.py customers` | Clientes de todas las empresas: `customerId`, `companyId`, `rfc`, `legalName`. |
| GET | `/api/v2/customer/clients/{id}` | `directory.py customer ID` | Detalle del cliente. |
| POST | `/api/v2/customer/clients` | `directory.py create-customer FILE` | Crea y devuelve el cliente guardado. |
| PUT | `/api/v2/customer/clients/{id}` | `directory.py update-customer ID FILE` | Actualiza el mismo cliente. |
| DELETE | `/api/v2/customer/clients/{id}` | `directory.py delete-customer ID` | 409 si el cliente tiene comprobantes. |
| GET | `/api/v2/customer/blacklist?rfc=` | `directory.py blacklist RFC` | `{"enListaNegra", "situacion"}` (art. 69/69-B). |

Campos del cliente (JSON): `companyId` (empresa a la que pertenece; por defecto la de la sesión), `rfc`, `legalName`, `taxRegime`, `postalCode`, `email`, `phone`, `contact`, `curp`, `address`, `exteriorNumber`, `interiorNumber`, `neighborhood`, `city`, `locality`, `state`, `reference`, `country`, `foreignTaxId`, `nationality`, `bcc`, `website`, `reviewDays`, `paymentAccount`.

Reglas del alta:

- El RFC se normaliza en mayúsculas y no puede repetirse dentro de la misma empresa, salvo `XAXX010101000` y `XEXX010101000`.
- Un cliente extranjero requiere `foreignTaxId` (NumRegIdTrib) y un `country` distinto de México.
- El código postal se valida contra el catálogo del SAT solo para clientes de México.

## Catálogos SAT

| Método | Ruta | Script | Notas |
|---|---|---|---|
| GET | `/api/v1/catalogs/{nombre}?q=&id=` | `catalogs.py get NOMBRE` | `[{"id","descripcion"}]`, máximo 100 filas. `q` busca en clave y descripción; `id` es la clave exacta. |

Catálogos: `ClaveProdServ`, `ClaveUnidad`, `RegimenFiscal`, `UsoCFDI`, `FormaPago`, `MetodoPago`, `TipoDeComprobante`, `Exportacion`, `Moneda`, `ObjetoImp`, `Impuesto`, `TipoFactor`, `Periodicidad`, `Meses`, `TipoRelacion`.

## CFDI timbrados

| Método | Ruta | Script | Notas |
|---|---|---|---|
| GET | `/api/v2/cfdis` | `cfdi.py list` | Paginado: `{"content": [...], ...}`. Filtros `page`, `size` (≤200), `companyId`, `customerId`, `from`, `to`, `rfcEmisor`, `rfcReceptor`, `uuid`, `tipoComprobante`, `status`, `search` (texto libre; no busca en el RFC). Fila: `uuid`, `idTimbre`, `fechaFactura`, `rfcEmisor`, `rfcReceptor`, `status`, `tipoComprobante`, `total`, `moneda`. |
| GET | `/api/v2/cfdis/{uuid}` | `cfdi.py get UUID` | Detalle. |
| GET | `/api/v2/cfdis/{uuid}/status` | `cfdi.py status UUID` | Estatus ante el SAT. Hoy responde 503 «pendiente de validación y habilitación». |
| GET | `/api/v2/cfdis/{uuid}/xml` · `/pdf` | `cfdi.py download UUID --format xml\|pdf` | Bytes del archivo. |
| GET | `/api/v2/cfdis/{uuid}/acuse` | `cfdi.py download UUID --format acuse` | PDF del acuse de cancelación. 400 si no está cancelado; 409 si el receptor rechazó la solicitud (el CFDI volvió a vigente). |
| GET | `/api/v2/cfdis/{uuid}/credit-note` | `cfdi.py credit-note UUID` | Egreso sin guardar: TipoRelacion 01 al UUID, G02 si el régimen del receptor lo admite (si no, el uso del ingreso), PUE y FormaPago del ingreso (sin ella si era 99). 400 si el origen no es ingreso; 409 si está cancelado. |
| POST | `/api/v2/cfdis/validate` | `cfdi.py validate FILE.xml` | Cuerpo XML (`application/xml`) → `{"valido": "SI"|"NO", "detalles": [...]}`. |
| POST | `/api/v2/cfdis/prepare` | `cfdi.py prepare FILE.json` | Valida y recalcula; no guarda ni emite. |
| POST | `/api/v2/cfdis/stamp` | `cfdi.py stamp FILE.json` | **Timbra.** Efecto fiscal real. → `{"uuid","folio","idVenta","pdfGenerado","xmlRespaldadoS3","draftUpdated"}`. |
| POST | `/api/v2/cfdis/cancel` | `cfdi.py cancel UUID --reason 01..04` | **Cancela.** Cuerpo `{"uuid","motivo","folioSustituto"}`. Sin acuse del SAT responde 500 «Error al cancelar: motivo del PAC/SAT» y el CFDI sigue vigente. |
| POST | `/api/v2/customer/retentions/{id}/cancel` | `cfdi.py retention-cancel ID --reason 01..04` | **Cancela una retención.** Cuerpo `{"motivo","folioSustituto"}`. |
| GET | `/api/v2/customer/retentions/{id}/acuse` | `cfdi.py retention-acuse ID` | PDF del acuse de una retención cancelada. |
| POST | `/api/v2/cfdis/{uuid}/send-email` | `cfdi.py email UUID --to …` | **Envía correo.** Cuerpo: arreglo de correos. En pruebas responde hoy 503 (SMTP sin configurar). |

## PRE-CFDI (borradores)

| Método | Ruta | Script | Notas |
|---|---|---|---|
| GET | `/api/v2/pre-cfdis` | `drafts.py list` | Paginado; `estado=sin-timbrar` oculta los ya timbrados. Fila: `id`, `folio`, `createdDate`, `metodoPago`, `formaPago`, totales. |
| GET | `/api/v2/pre-cfdis/{id}` | `drafts.py get ID` | `{"metadata", "cfdi", "companyId"}`: `cfdi` es el comprobante editable; `metadata` trae `id`, `folio`, RFC/razón social de emisor y receptor y totales. |
| POST | `/api/v2/pre-cfdis` | `drafts.py create FILE` | Cuerpo: el comprobante. Responde `{"metadata", "cfdi", "companyId"}`; el script descarga además el PDF y añade `pdf`. |
| PUT | `/api/v2/pre-cfdis/{id}` | `drafts.py update ID FILE` | Cuerpo: el comprobante completo (el objeto `cfdi`, no la respuesta entera). Reemplaza el mismo borrador. |
| GET | `/api/v2/pre-cfdis/{id}/pdf` · `/xml` | `drafts.py download ID` | PDF "PRE-CFDI / BORRADOR" o XML sin sello. |
| GET | `/api/v2/pre-cfdis/folios/next` | `drafts.py next-folio` | `{"folio"}` siguiente fiscal; no reserva. |
| POST | `/api/v2/pre-cfdis/folios/reserve` | `drafts.py reserve-folio` | Folio provisional `BOR-…`; nunca se timbra. |
| POST | `/api/v2/pre-cfdis/{id}/stamp` | `drafts.py stamp ID FILE` | **Timbra** el borrador; misma respuesta que `cfdis/stamp` y liga el UUID en `metadata.uuid`. |

## Forma del JSON del comprobante

Claves en camelCase, como en [`ingreso-pue.json`](ingreso-pue.json) y [`cfdi40/`](cfdi40/README.md): `version`, `serie`, `folio`, `fecha` (`YYYY-MM-DDTHH:mm:ss`, hora local de Ciudad de México, sin zona), `formaPago`, `metodoPago`, `moneda`, `tipoCambio`, `tipoDeComprobante`, `exportacion`, `lugarExpedicion`, `subtotal`, `descuento`, `total`, `emisor{rfc,nombre,regimenFiscal}`, `receptor{rfc,nombre,domicilioFiscalReceptor,regimenFiscalReceptor,usoCfdi}`, `conceptos[]{claveProdServ,cantidad,claveUnidad,unidad,descripcion,valorUnitario,importe,descuento,objetoImp,impuestos{traslados[],retenciones[]}}`, `impuestos{traslados[],retenciones[],totalImpuestosTrasladados,totalImpuestosRetenidos}`, `informacionGlobal{periodicidad,meses,anio}`, `cfdiRelacionados{tipoRelacion,cfdiRelacionado[{uuid}]}` (un solo grupo, como objeto).

### Egresos y cancelaciones en las superficies

El PRE-CFDI tipo E usa `cfdiRelacionados` como objeto con `tipoRelacion` y
`cfdiRelacionado` como arreglo de objetos `uuid`. Se conserva en borradores
y en el XML; no modifica automáticamente el saldo del documento relacionado.
El chat ofrece `invoice.creditNote` (UUID) para abrir en el editor la nota de
crédito prellenada desde `GET /api/v2/cfdis/{uuid}/credit-note`, sin guardarla.
También ofrece `invoice.cancel` (UUID, from, to) para revisar en la interfaz;
la mutación sigue en `POST /api/v2/cfdis/cancel` con uuid, motivo y
folioSustituto para motivo 01. No se consulta estatus SAT desde esa navegación.
