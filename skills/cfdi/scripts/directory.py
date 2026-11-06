#!/usr/bin/env python3
"""Cuenta, empresas (emisores) y clientes (receptores)."""
import ntlink_api as api


def build(p):
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("account", help="Datos del sistema/cuenta (GET /api/v2/customer/profile).")
    sub.add_parser("balance", help="Saldo de timbres (GET /api/v2/customer/balances).")
    sub.add_parser("companies", help="Listar empresas emisoras (GET /api/v2/customer/companies).")
    sub.add_parser("company", help="Detalle de una empresa.").add_argument("id")
    sub.add_parser("customers", help="Listar clientes de todas las empresas (GET /api/v2/customer/clients).")
    sub.add_parser("customer", help="Detalle de un cliente.").add_argument("id")
    sub.add_parser("create-customer", help="Crear un cliente desde JSON. Escritura: confirma antes.").add_argument("file")
    u = sub.add_parser("update-customer", help="Actualizar un cliente desde JSON. Escritura: confirma antes.")
    u.add_argument("id")
    u.add_argument("file")
    sub.add_parser("delete-customer", help="Eliminar un cliente sin comprobantes. Escritura: confirma antes.").add_argument("id")
    sub.add_parser("blacklist", help="Consultar un RFC en la lista negra del SAT (69/69-B).").add_argument("rfc")


def handle(a):
    base = "/api/v2/customer/"
    simple = {"account": "profile", "balance": "balances", "companies": "companies", "customers": "clients"}
    if a.cmd in simple:
        return api.request("GET", base + simple[a.cmd])
    if a.cmd == "company":
        return api.request("GET", base + "companies/" + api.q(a.id))
    if a.cmd == "customer":
        return api.request("GET", base + "clients/" + api.q(a.id))
    if a.cmd == "create-customer":
        return api.request("POST", base + "clients", json_body=api.read_json(a.file))
    if a.cmd == "update-customer":
        return api.request("PUT", base + "clients/" + api.q(a.id), json_body=api.read_json(a.file))
    if a.cmd == "delete-customer":
        api.request("DELETE", base + "clients/" + api.q(a.id))
        return {"deleted": True, "customerId": a.id}
    return api.request("GET", base + "blacklist", query=[("rfc", a.rfc)])


if __name__ == "__main__":
    api.run(build, handle)
