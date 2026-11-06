"""Cliente mínimo del backend NTLink (/api/v2 y /api/v1/catalogs).

Solo usa la biblioteca estándar de Python 3.8+. Comparte el perfil y el token
con el CLI `nt` en ~/.ntlink-invoice/config.json, así que una sesión iniciada con
cualquiera de los dos sirve para el otro.
"""
import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

TEST_BASE_URL = "http://pruebas.ntlink.com.mx:8092"
TEST_ACCOUNT = {"email": "URE180429TM6@ntlink.com.mx", "password": "NTPruebas.2021*?"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class ApiError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def config_file():
    base = os.environ.get("NTLINK_INVOICE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".ntlink-invoice")
    return os.path.join(base, "config.json")


def load_store():
    try:
        with open(config_file(), encoding="utf-8-sig") as f:
            store = json.load(f)
        if not store.get("profiles") or not store.get("active"):
            raise ApiError("Configuración inválida en " + config_file())
        return store
    except FileNotFoundError:
        return {"active": "pruebas", "profiles": {"pruebas": {"baseUrl": TEST_BASE_URL, "timeout": 120}}}


def save_store(store):
    path = config_file()
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)
        f.write("\n")
    os.chmod(temp, 0o600)
    os.replace(temp, path)


def profile_name():
    return os.environ.get("NTLINK_PROFILE") or load_store()["active"]


def update_profile(name, **changes):
    store = load_store()
    profile = store["profiles"].get(name) or {"baseUrl": TEST_BASE_URL, "timeout": 120}
    profile.update({k: v for k, v in changes.items() if v is not None})
    for key in [k for k, v in changes.items() if v is None]:
        profile.pop(key, None)
    store["profiles"][name] = profile
    save_store(store)


def settings():
    name = profile_name()
    saved = load_store()["profiles"].get(name)
    base_url = (os.environ.get("NTLINK_BASE_URL") or (saved or {}).get("baseUrl") or TEST_BASE_URL).rstrip("/")
    if not saved and not os.environ.get("NTLINK_BASE_URL"):
        raise ApiError("Perfil desconocido: " + name)
    # A stored token never follows an override to a different backend.
    token = os.environ.get("NTLINK_TOKEN") or ((saved or {}).get("token") if (saved or {}).get("baseUrl", "").rstrip("/") == base_url else None)
    timeout = float(os.environ.get("NTLINK_TIMEOUT") or (saved or {}).get("timeout") or 120)
    host = urllib.parse.urlsplit(base_url).hostname or ""
    if base_url.startswith("http://") and base_url != TEST_BASE_URL and host not in LOCAL_HOSTS and os.environ.get("NTLINK_ALLOW_INSECURE_HTTP") != "1":
        raise ApiError("HTTP remoto sin cifrar bloqueado. Usa HTTPS o define NTLINK_ALLOW_INSECURE_HTTP=1 conscientemente.")
    return name, base_url, token, timeout


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def _send(method, url, body, headers, timeout):
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with _opener.open(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        message = "HTTP %d" % e.code
        try:
            data = json.loads(raw)
            message = data if isinstance(data, str) else str(data.get("message") or data.get("error") or message)
        except (ValueError, AttributeError):
            pass  # Do not print a possibly sensitive HTML body.
        if e.code == 401:
            message += " Inicia sesión otra vez con: python scripts/auth.py login"
        raise ApiError(message, e.code)
    except urllib.error.URLError as e:
        raise ApiError("No se pudo conectar con el backend: %s" % e.reason)


def login(email, password):
    name, base_url, _, timeout = settings()
    _, raw = _send("POST", base_url + "/api/v2/auth/login", json.dumps({"email": email, "password": password}).encode(), {"Content-Type": "application/json"}, timeout)
    session = json.loads(raw)
    if not session.get("token"):
        raise ApiError("El backend no devolvió token.")
    update_profile(name, baseUrl=base_url, token=session["token"])
    return session


def request(method, path, query=None, json_body=None, raw_body=None, content_type=None, anonymous=False, output=None, force=False):
    """Call the backend. Returns parsed JSON, text, or {path, bytes} when output is set."""
    name, base_url, token, timeout = settings()
    if not path.startswith("/") or path.startswith("//"):
        raise ApiError("La ruta debe ser relativa al backend, por ejemplo /api/v2/cfdis.")
    url = base_url + path
    if query:
        url += "?" + urllib.parse.urlencode([(k, v) for k, v in query if v is not None])
    headers = {}
    if not anonymous:
        if not token and base_url == TEST_BASE_URL and name == "pruebas":
            token = login(TEST_ACCOUNT["email"], TEST_ACCOUNT["password"])["token"]
        if not token:
            raise ApiError("Sin sesión. Ejecuta: python scripts/auth.py login")
        headers["Authorization"] = "Bearer " + token
    body = raw_body
    if json_body is not None:
        body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif content_type:
        headers["Content-Type"] = content_type
    _, data = _send(method, url, body, headers, timeout)
    if output:
        with open(output, "wb" if force else "xb") as f:
            f.write(data)
        return {"path": os.path.abspath(output), "bytes": len(data)}
    if not data:
        return None
    text = data.decode("utf-8", "replace")
    try:
        result = json.loads(text)
    except ValueError:
        return text
    if isinstance(result, dict) and result.get("exito") is False:
        raise ApiError("La operación devolvió exito:false. Revisa los datos de entrada.")
    return result


def read_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def print_json(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def q(value):
    return urllib.parse.quote(str(value), safe="")


def add_list_options(parser):
    parser.add_argument("--page", help="Página base cero.")
    parser.add_argument("--size", help="Tamaño de página, máximo 200.")
    parser.add_argument("--company", help="ID de empresa (companyId).")
    parser.add_argument("--customer", help="ID de cliente (customerId).")
    parser.add_argument("--search", help="Texto de búsqueda.")
    parser.add_argument("--from", dest="date_from", help="Fecha inicial YYYY-MM-DD.")
    parser.add_argument("--to", dest="date_to", help="Fecha final YYYY-MM-DD.")
    parser.add_argument("--filter", action="append", default=[], metavar="KEY=VALUE", help="Filtro adicional repetible.")


def list_query(args):
    pairs = [("page", args.page), ("size", args.size), ("companyId", args.company), ("customerId", args.customer),
             ("search", args.search), ("from", args.date_from), ("to", args.date_to)]
    for item in args.filter:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise ApiError("Se esperaba KEY=VALUE: " + item)
        pairs.append((key, value))
    return pairs


def run(build, handle):
    """Shared entry point: argparse + JSON output + JSON errors on stderr."""
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy code page.
    parser = argparse.ArgumentParser()
    build(parser)
    args = parser.parse_args()
    try:
        result = handle(args)
        if result is not None:
            print_json(result)
    except (ApiError, OSError, ValueError) as e:
        error = {"error": str(e)}
        if isinstance(e, ApiError) and e.status:
            error["status"] = e.status
        sys.stderr.write(json.dumps(error, ensure_ascii=False) + "\n")
        sys.exit(1)
