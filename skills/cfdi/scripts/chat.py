"""Upload source documents and send them to the shared backend assistant."""
import argparse
import os
import uuid
from ntlink_api import request, q, run


def attach(path):
    if os.path.getsize(path) > 5 * 1024 * 1024:
        raise ValueError("El archivo supera 5 MB.")
    with open(path, "rb") as source:
        data = source.read(5 * 1024 * 1024 + 1)
    return request("POST", "/api/v2/chat/attachments", raw_body=data,
                   content_type="application/octet-stream", file_name=path)


def build(parser):
    sub = parser.add_subparsers(dest="command", required=True)
    upload = sub.add_parser("attach", help="Leer PDF, Excel, CSV, XML, JSON o JPG/PNG sin guardar borradores.")
    upload.add_argument("file")
    sub.add_parser("create-session")
    send = sub.add_parser("send")
    send.add_argument("session")
    send.add_argument("message")
    send.add_argument("--attach", action="append", default=[])
    send.add_argument("--request-id", default=None)
    events = sub.add_parser("events")
    events.add_argument("run")


def handle(args):
    if args.command == "attach":
        return attach(args.file)
    if args.command == "create-session":
        return request("POST", "/api/v2/chat/sessions", json_body={})
    if args.command == "events":
        return request("GET", "/api/v2/chat/runs/" + q(args.run) + "/events")
    if len(args.attach) > 3:
        raise ValueError("MÃ¡ximo tres adjuntos por mensaje.")
    return request("POST", "/api/v2/chat/sessions/" + q(args.session) + "/messages", json_body={
        "message": args.message, "requestId": args.request_id or str(uuid.uuid4()),
        "attachments": [attach(path) for path in args.attach]})


if __name__ == "__main__":
    run(build, handle)
