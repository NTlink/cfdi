#!/usr/bin/env python3
"""Sesión y modo: login, status, logout, mode."""
import getpass
import os
import sys

import ntlink_api as api


def build(p):
    sub = p.add_subparsers(dest="cmd", required=True)
    login = sub.add_parser("login", help="Iniciar sesión; la contraseña se lee de NTLINK_PASSWORD, stdin o se pide oculta.")
    login.add_argument("--email")
    login.add_argument("--password-stdin", action="store_true")
    sub.add_parser("status", help="Perfil del sistema de la cuenta (GET /api/v2/customer/profile).")
    sub.add_parser("logout", help="Borrar el token guardado del perfil activo.")
    mode = sub.add_parser("mode", help="Ver el modo o cambiar a pruebas.")
    mode.add_argument("environment", nargs="?")


def handle(a):
    if a.cmd == "login":
        email = a.email or input("Correo: ").strip()
        password = sys.stdin.readline().rstrip("\r\n") if a.password_stdin else os.environ.get("NTLINK_PASSWORD") or getpass.getpass("Contraseña: ")
        s = api.login(email, password)
        return {"authenticated": True, "profile": api.profile_name(), "email": s.get("email"), "roles": s.get("roles"), "termsAndConditions": s.get("termsAndConditions")}
    if a.cmd == "status":
        return api.request("GET", "/api/v2/customer/profile")
    if a.cmd == "logout":
        api.update_profile(api.profile_name(), token=None)
        return {"authenticated": False}
    env = (a.environment or "").lower()
    if not env:
        return {"mode": api.profile_name(), "production": "próximamente"}
    if env in ("production", "produccion", "producción", "prod"):
        return {"mode": api.profile_name(), "message": "El modo producción estará disponible próximamente."}
    if env in ("pruebas", "prueba", "test", "testing"):
        api.update_profile("pruebas", baseUrl=api.TEST_BASE_URL)
        store = api.load_store()
        store["active"] = "pruebas"
        api.save_store(store)
        return {"mode": "pruebas", "message": "La cuenta pública de demostración inicia sesión sola al primer comando protegido."}
    raise api.ApiError("Usa: mode pruebas | mode production")


if __name__ == "__main__":
    api.run(build, handle)
