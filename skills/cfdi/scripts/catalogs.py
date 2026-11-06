#!/usr/bin/env python3
"""Catálogos SAT: list, get NAME [--q TEXTO | --id CLAVE]."""
import ntlink_api as api

NAMES = ["ClaveProdServ", "ClaveUnidad", "RegimenFiscal", "UsoCFDI", "FormaPago", "MetodoPago", "TipoDeComprobante",
         "Exportacion", "Moneda", "ObjetoImp", "Impuesto", "TipoFactor", "Periodicidad", "Meses", "TipoRelacion"]


def build(p):
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="Nombres de catálogos disponibles.")
    g = sub.add_parser("get", help="Consultar un catálogo; máximo 100 filas por respuesta.")
    g.add_argument("name")
    g.add_argument("--q", help="Buscar en clave o descripción.")
    g.add_argument("--id", help="Clave exacta.")


def handle(a):
    if a.cmd == "list":
        return NAMES
    name = next((n for n in NAMES if n.lower() == a.name.lower()), None)
    if not name:
        raise api.ApiError("Catálogo desconocido. Disponibles: " + ", ".join(NAMES))
    return api.request("GET", "/api/v1/catalogs/" + name, query=[("id", a.id), ("q", a.q)])


if __name__ == "__main__":
    api.run(build, handle)
