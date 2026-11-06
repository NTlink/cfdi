#!/usr/bin/env python3
"""CFDI timbrados: list, get, status, download, validate, prepare, stamp, cancel, email."""
import ntlink_api as api


def build(p):
    sub = p.add_subparsers(dest="cmd", required=True)
    api.add_list_options(sub.add_parser("list", help="Listar facturas timbradas (GET /api/v2/cfdis)."))
    for name in ("get", "status"):
        sub.add_parser(name).add_argument("uuid")
    d = sub.add_parser("download", help="Descargar XML o PDF de un CFDI timbrado.")
    d.add_argument("uuid")
    d.add_argument("--format", choices=["xml", "pdf"], default="xml")
    d.add_argument("--output")
    d.add_argument("--force", action="store_true", help="Sobrescribir el archivo de salida.")
    sub.add_parser("validate", help="Validar un XML CFDI.").add_argument("file")
    sub.add_parser("prepare", help="Validar y recalcular un JSON sin guardar ni emitir.").add_argument("file")
    sub.add_parser("stamp", help="TIMBRAR un JSON. Efecto fiscal real: requiere aprobación explícita.").add_argument("file")
    c = sub.add_parser("cancel", help="CANCELAR un CFDI. Efecto fiscal real: requiere aprobación explícita.")
    c.add_argument("uuid")
    c.add_argument("--reason", required=True, choices=["01", "02", "03", "04"])
    c.add_argument("--replacement", help="UUID sustituto (motivo 01).")
    e = sub.add_parser("email", help="Enviar el CFDI por correo. Efecto externo: confirma antes.")
    e.add_argument("uuid")
    e.add_argument("--to", action="append", required=True)


def handle(a):
    if a.cmd == "list":
        return api.request("GET", "/api/v2/cfdis", query=api.list_query(a))
    if a.cmd == "get":
        return api.request("GET", "/api/v2/cfdis/" + api.q(a.uuid))
    if a.cmd == "status":
        return api.request("GET", "/api/v2/cfdis/%s/status" % api.q(a.uuid))
    if a.cmd == "download":
        return api.request("GET", "/api/v2/cfdis/%s/%s" % (api.q(a.uuid), a.format), output=a.output or "%s.%s" % (a.uuid, a.format), force=a.force)
    if a.cmd == "validate":
        with open(a.file, "rb") as f:
            return api.request("POST", "/api/v2/cfdis/validate", raw_body=f.read(), content_type="application/xml")
    if a.cmd in ("prepare", "stamp"):
        return api.request("POST", "/api/v2/cfdis/" + a.cmd, json_body=api.read_json(a.file))
    if a.cmd == "cancel":
        return api.request("POST", "/api/v2/cfdis/cancel", json_body={"uuid": a.uuid, "motivo": a.reason, "folioSustituto": a.replacement})
    return api.request("POST", "/api/v2/cfdis/%s/send-email" % api.q(a.uuid), json_body=a.to)


if __name__ == "__main__":
    api.run(build, handle)
