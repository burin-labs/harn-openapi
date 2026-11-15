"""Independent HTTP byte recorder for the generated CLI and stdio MCP paths."""

import base64
import email.parser
import email.policy
import http.server
import json
import os
import pathlib
import queue
import subprocess
import sys
import threading


BINARY = b"\x00\xffHello\n"
WIRE_BINARY = {"$bytes_b64": base64.b64encode(BINARY).decode("ascii")}
LITERAL = "${1 + 1}"


class Recorder(http.server.BaseHTTPRequestHandler):
    records = []
    errors = []
    multiple = 0

    def log_message(self, *_args):
        pass

    def do_POST(self):
        self.respond()

    def do_GET(self):
        self.respond()

    def respond(self):
        try:
            body = self.rfile.read(int(self.headers.get("content-length", "0")))
            record = {
                "method": self.command,
                "path": self.path,
                "headers": {key.lower(): value for key, value in self.headers.items()},
                "body": body,
            }
            self.records.append(record)
            status, content_type, payload = 204, None, b""
            if self.path == "/response/json":
                status, content_type, payload = 200, "application/problem+json", b'{"ok":true}'
            elif self.path == "/response/text":
                status, content_type, payload = 200, "text/plain; charset=utf-8", "plain Δ response".encode()
            elif self.path == "/response/bytes":
                status, content_type, payload = 200, "application/octet-stream", BINARY
            elif self.path == "/response/multiple":
                type(self).multiple += 1
                if self.multiple % 2:
                    status, content_type, payload = 200, "text/plain", b"selected text"
                else:
                    status, content_type, payload = 200, "application/octet-stream", BINARY
            elif self.path == "/response/oversized":
                status, content_type = 200, "application/octet-stream"
            self.send_response(status)
            if content_type:
                self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(16777217 if self.path == "/response/oversized" else len(payload)))
            self.end_headers()
            if payload:
                self.wfile.write(payload)
        except Exception as error:
            self.errors.append(type(error).__name__)
            raise


class Mcp:
    def __init__(self, binary, entrypoint, environment):
        self.process = subprocess.Popen(
            [binary, "serve", "mcp", str(entrypoint)],
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.messages = queue.Queue()
        self.errors = []
        self.reader = threading.Thread(target=self.read_stdout)
        self.error_reader = threading.Thread(target=self.read_stderr)
        self.reader.start()
        self.error_reader.start()
        self.next_id = 0

    def read_stdout(self):
        try:
            for line in self.process.stdout:
                self.messages.put(json.loads(line))
        except Exception as error:
            self.messages.put(error)
        finally:
            self.messages.put(None)

    def read_stderr(self):
        self.errors.append(self.process.stderr.read())

    def notify(self, method):
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method, "params": {}}) + "\n")
        self.process.stdin.flush()

    def call(self, method, params):
        self.next_id += 1
        request_id = self.next_id
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}) + "\n")
        self.process.stdin.flush()
        while True:
            message = self.messages.get(timeout=30)
            assert message is not None, (method, "MCP exited", self.errors)
            assert not isinstance(message, Exception), message
            if "id" in message:
                assert message["id"] == request_id, message
                return message

    def close(self):
        try:
            self.process.stdin.close()
            self.process.wait(timeout=30)
            assert self.process.returncode == 0, self.errors
        finally:
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait(timeout=10)
            self.reader.join(timeout=10)
            self.error_reader.join(timeout=10)
            assert not self.reader.is_alive() and not self.error_reader.is_alive()


def multipart_parts(record):
    content_type = record["headers"]["content-type"]
    assert content_type.startswith("multipart/form-data; boundary="), content_type
    message = email.parser.BytesParser(policy=email.policy.default).parsebytes(
        b"Content-Type: " + content_type.encode("ascii") + b"\r\nMIME-Version: 1.0\r\n\r\n" + record["body"]
    )
    assert not message.defects, message.defects
    parts = list(message.iter_parts())
    assert [part.get_param("name", header="content-disposition") for part in parts] == ["file", "tags", "tags", "title"]
    assert [part.get_payload(decode=True) for part in parts] == [BINARY, b"a", b"b", b"title"]
    assert parts[0].get_filename() == "proof.bin"
    assert [part.get_content_type() for part in parts] == ["application/octet-stream", "text/plain", "text/plain", "text/plain"]
    assert parts[0]["X-Part"] == "present"
    assert parts[0]["X-Count"] == "7"
    assert all(not part.defects for part in parts)
    boundary = message.get_boundary().encode("ascii")
    assert record["body"].startswith(b"--" + boundary + b"\r\n")
    assert record["body"].endswith(b"--" + boundary + b"--\r\n")


def verify_record(record, path, content_type, body, accept=""):
    assert record["path"] == path, record["path"]
    assert record["method"] == ("GET" if path.startswith("/response/") else "POST")
    assert record["headers"].get("x-media-literal") == LITERAL
    assert record["headers"].get("accept", "") == (accept or "*/*"), (path, record["headers"])
    if content_type == "multipart/form-data":
        multipart_parts(record)
    else:
        assert record["headers"].get("content-type") == content_type, record["headers"]
        assert record["body"] == body, (path, record["body"], body)


def probe(binary, entrypoint):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Recorder)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    environment = {**os.environ, "MEDIA_BASE_URL": f"http://127.0.0.1:{server.server_port}"}
    cases = [
        ("send_json", {"body": {"value": "sentinel"}}, "/json", "application/json", b'{"value":"sentinel"}', "", None),
        ("send_text", {"body": "plain Δ text"}, "/text", "text/plain; charset=utf-8", "plain Δ text".encode(), "", None),
        ("send_form", {"body": {"title": "a + b", "tags": ["one", "two"], "packed": ["a", "b"], "metadata": {"ok": True}}}, "/form", "application/x-www-form-urlencoded", b"metadata=%7B%22ok%22%3Atrue%7D&packed=a%7Cb&tags=one&tags=two&title=a+%2B+b", "", None),
        ("send_multipart", {"body": {"file": {"value": WIRE_BINARY, "filename": "proof.bin", "headers": {"X-Part": "present", "X-Count": 7}}, "title": {"value": "title"}, "tags": [{"value": "a"}, {"value": "b"}]}}, "/multipart", "multipart/form-data", None, "", None),
        ("send_bytes", {"body": WIRE_BINARY}, "/bytes", "application/octet-stream", BINARY, "", None),
        ("send_multiple", {"body": {"content_type": "application/problem+json", "value": {"value": "json"}}}, "/multiple", "application/problem+json", b'{"value":"json"}', "", None),
        ("send_multiple", {"body": {"content_type": "text/plain", "value": "text"}}, "/multiple", "text/plain", b"text", "", None),
        ("send_optional", {}, "/optional", None, b"", "", None),
        ("send_optional", {"body": None}, "/optional", "application/json", b"null", "", None),
        ("receive_json", {}, "/response/json", None, b"", "application/problem+json", {"ok": True}),
        ("receive_text", {}, "/response/text", None, b"", "text/plain", "plain Δ response"),
        ("receive_bytes", {}, "/response/bytes", None, b"", "application/octet-stream", WIRE_BINARY),
        ("receive_multiple", {}, "/response/multiple", None, b"", "application/octet-stream, text/plain", "selected text"),
        ("receive_multiple", {}, "/response/multiple", None, b"", "application/octet-stream, text/plain", WIRE_BINARY),
    ]
    input_file = entrypoint.parent / "projection-input.json"
    mcp = None
    reached = {"cli": 0, "mcp": 0}
    refused = {"cli": 0, "mcp": 0}
    try:
        mcp = Mcp(binary, entrypoint, environment)
        initialized = mcp.call("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "media-byte-probe", "version": "1"}})
        assert "result" in initialized, initialized
        mcp.notify("notifications/initialized")
        catalog = mcp.call("tools/list", {})
        assert len(catalog["result"]["tools"]) == 12, catalog
        for surface in ["cli", "mcp"]:
            for tool, arguments, path, content_type, body, accept, expected in cases:
                before = len(Recorder.records)
                if surface == "cli":
                    input_file.write_text(json.dumps(arguments))
                    result = subprocess.run([binary, "tool", "run", str(entrypoint), tool, "--harn-input", "@" + str(input_file), "--json"], env=environment, capture_output=True, text=True, timeout=30)
                    assert result.returncode == 0, (tool, result.stdout, result.stderr)
                    assert json.loads(result.stdout) == expected, (tool, result.stdout)
                else:
                    result = mcp.call("tools/call", {"name": tool, "arguments": arguments})
                    assert "error" not in result and not result["result"].get("isError"), result
                    structured = expected if tool in {"receive_json", "receive_bytes"} else {"result": expected}
                    assert result["result"].get("structuredContent") == structured, (tool, result)
                assert len(Recorder.records) == before + 1, (tool, "missing or duplicate request")
                verify_record(Recorder.records[-1], path, content_type, body, accept)
                reached[surface] += 1
            before = len(Recorder.records)
            invalid = {"body": {"content_type": "secret-body-value", "value": "secret-body-value"}}
            if surface == "cli":
                input_file.write_text(json.dumps(invalid))
                result = subprocess.run([binary, "tool", "run", str(entrypoint), "send_multiple", "--harn-input", "@" + str(input_file), "--json"], env=environment, capture_output=True, text=True, timeout=30)
                assert result.returncode != 0
                assert "secret-body-value" not in result.stdout + result.stderr
            else:
                result = mcp.call("tools/call", {"name": "send_multiple", "arguments": invalid})
                assert "error" in result or result["result"].get("isError"), result
                assert "secret-body-value" not in json.dumps(result)
            assert len(Recorder.records) == before, "invalid selection must refuse before HTTP"
            refused[surface] += 1
            if surface == "cli":
                input_file.write_text("{}")
                result = subprocess.run([binary, "tool", "run", str(entrypoint), "receive_oversized", "--harn-input", "@" + str(input_file), "--json"], env=environment, capture_output=True, text=True, timeout=30)
                assert result.returncode != 0
            else:
                result = mcp.call("tools/call", {"name": "receive_oversized", "arguments": {}})
                assert "error" in result or result["result"].get("isError"), result
                assert not result.get("result", {}).get("structuredContent"), result
            assert len(Recorder.records) == before + 1
            refused[surface] += 1
        assert not Recorder.errors, Recorder.errors
        assert reached == {"cli": 14, "mcp": 14}
        assert refused == {"cli": 2, "mcp": 2}
        print(json.dumps({"reached": reached, "refused": refused, "http_requests": len(Recorder.records), "pending": 0, "measurement_errors": Recorder.errors}))
    finally:
        try:
            if mcp:
                mcp.close()
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=10)
            assert not server_thread.is_alive()


if __name__ == "__main__":
    probe(sys.argv[1], pathlib.Path(sys.argv[2]).resolve())
