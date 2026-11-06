#!/usr/bin/env python3
"""PRE-CFDI (borradores): list, get, create, update, download, next-folio, reserve-folio, zone, stamp."""
import ntlink_api as api


def build(p):
    sub = p.add_subparsers(dest="cmd", required=True)
    api.add_list_options(sub.add_parser("list", help="Listar PRE-CFDI (GET /api/v2/pre-cfdis)."))
    sub.add_parser("get").add_argument("id")
    c = sub.add_parser("create", help="Guardar un PRE-CFDI y descargar su PDF de revisión.")
    c.add_argument("file")
    c.add_argument("--pdf-output", help="Destino del PDF; por defecto PRE-CFDI-ID.pdf.")
    c.add_argument("--no-pdf", action="store_true", help="Guardar sin descargar el PDF.")
    c.add_argument("--force", action="store_true", help="Sobrescribir el PDF de destino.")
    u = sub.add_parser("update", help="Reemplazar el contenido del mismo PRE-CFDI.")
    u.add_argument("id")
    u.add_argument("file")
    d = sub.add_parser("download", help="Descargar el PDF o XML (sin timbre) de un PRE-CFDI.")
    d.add_argument("id")
    d.add_argument("--format", choices=["xml", "pdf"], default="pdf")
    d.add_argument("--output")
    d.add_argument("--force", action="store_true")
    sub.add_parser("next-folio", help="Siguiente folio fiscal de la empresa; solo consulta, no reserva.").add_argument("--company", type=int, help="ID de la empresa emisora; omitir usa la empresa de sesión.")
    sub.add_parser("reserve-folio", help="Reservar un folio provisional BOR-… (nunca se timbra).")
    z = sub.add_parser("zone", help="Zona horaria de la sucursal por código postal; úsala para la fecha de expedición.")
    z.add_argument("--cp", required=True, help="Código postal de la sucursal (LugarExpedicion).")
    s = sub.add_parser("stamp", help="TIMBRAR un PRE-CFDI. Efecto fiscal real: requiere aprobación explícita.")
    s.add_argument("id")
    s.add_argument("file")


def handle(a):
    base = "/api/v2/pre-cfdis"
    if a.cmd == "list":
        return api.request("GET", base, query=api.list_query(a))
    if a.cmd == "get":
        return api.request("GET", "%s/%s" % (base, api.q(a.id)))
    if a.cmd == "create":
        draft = api.request("POST", base, json_body=api.read_json(a.file))
        if a.no_pdf:
            return draft
        key = ((draft or {}).get("metadata") or {}).get("id")
        if not key:
            return dict(draft or {}, pdfError="Borrador guardado, pero sin ID en la respuesta. No repitas la creación.")
        try:
            pdf = api.request("GET", "%s/%s/pdf" % (base, api.q(key)), output=a.pdf_output or "PRE-CFDI-%s.pdf" % key, force=a.force)
            return dict(draft, pdf=pdf)
        except (api.ApiError, OSError) as e:
            return dict(draft, pdfError="Borrador guardado. %s. Recupera el PDF con drafts.py download; no repitas la creación." % e)
    if a.cmd == "update":
        return api.request("PUT", "%s/%s" % (base, api.q(a.id)), json_body=api.read_json(a.file))
    if a.cmd == "download":
        return api.request("GET", "%s/%s/%s" % (base, api.q(a.id), a.format), output=a.output or "PRE-CFDI-%s.%s" % (a.id, a.format), force=a.force)
    if a.cmd == "next-folio":
        return api.request("GET", base + "/folios/next", query=[("companyId", a.company)] if a.company else None)
    if a.cmd == "zone":
        return api.request("GET", base + "/zona-expedicion", query=[("cp", a.cp)])
    if a.cmd == "reserve-folio":
        return api.request("POST", base + "/folios/reserve")
    return api.request("POST", "%s/%s/stamp" % (base, api.q(a.id)), json_body=api.read_json(a.file))


if __name__ == "__main__":
    api.run(build, handle)
