"""Exercise supported OpenAPI 3.2 contracts through the public CLI and MCP."""

import http.server
import json
import os
import pathlib
import subprocess
import sys
import threading

sys.dont_write_bytecode = True

from media_projection_probe import Mcp, Recorder


def probe(binary, entrypoint):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Recorder)
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    environment = {**os.environ, "DIALECT_BASE_URL": f"http://127.0.0.1:{server.server_port}", "DIALECT_SERVER_NAME": ""}
    input_file = entrypoint.parent / "dialect-input.json"
    reached = {"cli": 0, "mcp": 0}
    refused = {"cli": 0, "mcp": 0}
    cases = [
        ("search_json", {"criteria": {"label": "a + b"}}, "/query/json?%7B%22label%22%3A%22a%20%2B%20b%22%7D"),
        ("search_form", {"criteria": {"term": "a + b", "tags": ["x", "y"]}}, "/query/form?tags=x&tags=y&term=a+%2B+b"),
        ("search_optional", {}, "/query/optional"),
    ]
    mcp = None
    try:
        mcp = Mcp(binary, entrypoint, environment)
        initialized = mcp.call("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "dialect-probe", "version": "1"}})
        assert "result" in initialized, initialized
        mcp.notify("notifications/initialized")
        catalog = mcp.call("tools/list", {})
        assert {tool["name"] for tool in catalog["result"]["tools"]} == {case[0] for case in cases}, catalog
        for surface in ["cli", "mcp"]:
            for name, arguments, path in cases:
                before = len(Recorder.records)
                if surface == "cli":
                    input_file.write_text(json.dumps(arguments))
                    result = subprocess.run([binary, "tool", "run", str(entrypoint), name, "--harn-input", "@" + str(input_file), "--json"], env=environment, capture_output=True, text=True, timeout=30)
                    assert result.returncode == 0, (name, result.stdout, result.stderr)
                    assert json.loads(result.stdout) is None
                else:
                    result = mcp.call("tools/call", {"name": name, "arguments": arguments})
                    assert "error" not in result and not result["result"].get("isError"), result
                    assert result["result"].get("structuredContent") == {"result": None}, result
                assert len(Recorder.records) == before + 1, "one registry call must produce one HTTP request"
                record = Recorder.records[-1]
                assert record["method"] == "GET", record
                assert record["path"] == path, record
                assert record["body"] == b"", record
                assert record["headers"].get("content-type") is None, record
                assert record["headers"].get("accept") == "*/*", record
                reached[surface] += 1
            before = len(Recorder.records)
            invalid = {"criteria": {"label": "secret-sentinel"}}
            if surface == "cli":
                input_file.write_text(json.dumps(invalid))
                result = subprocess.run([binary, "tool", "run", str(entrypoint), "search_json", "--harn-input", "@" + str(input_file), "--json"], env=environment, capture_output=True, text=True, timeout=30)
                assert result.returncode != 0
                assert "secret-sentinel" not in result.stdout + result.stderr
            else:
                result = mcp.call("tools/call", {"name": "search_json", "arguments": invalid})
                assert "error" in result or result["result"].get("isError"), result
                assert "secret-sentinel" not in json.dumps(result)
            assert len(Recorder.records) == before, "referenced schema rejection must precede HTTP"
            refused[surface] += 1
        assert reached == {"cli": 3, "mcp": 3}
        assert refused == {"cli": 1, "mcp": 1}
        assert not Recorder.errors, Recorder.errors
        print(json.dumps({"reached": reached, "refused": refused, "http_requests": len(Recorder.records), "pending": 0, "measurement_errors": Recorder.errors}))
    finally:
        try:
            if mcp:
                mcp.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join()


if __name__ == "__main__":
    probe(sys.argv[1], pathlib.Path(sys.argv[2]))
