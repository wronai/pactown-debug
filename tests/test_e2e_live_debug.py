import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_for_http_ok(url: str, timeout_s: float = 10.0) -> None:
    deadline = time.time() + timeout_s
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1.0) as resp:
                if 200 <= resp.status < 500:
                    return
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.15)
    raise AssertionError(f"Timeout waiting for {url}. Last error: {last_err}")


class LiveDebugE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.port = _pick_free_port()

        env = os.environ.copy()
        env["PORT"] = str(cls.port)
        env["PYTHONUNBUFFERED"] = "1"

        cls.proc = subprocess.Popen(
            [sys.executable, str(cls.repo_root / "server.py")],
            cwd=str(cls.repo_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        _wait_for_http_ok(f"http://127.0.0.1:{cls.port}/api/health", timeout_s=10.0)

    @classmethod
    def tearDownClass(cls) -> None:
        if getattr(cls, "proc", None) is None:
            return

        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
            cls.proc.wait(timeout=5)

    def test_serves_frontend_index(self) -> None:
        with urlopen(f"http://127.0.0.1:{self.port}/", timeout=2.0) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8", errors="replace")

        self.assertIn("Pactown Live Debug", html)
        self.assertIn('id="codeInput"', html)
        self.assertIn('id="codeOutput"', html)

    def test_api_health(self) -> None:
        with urlopen(f"http://127.0.0.1:{self.port}/api/health", timeout=2.0) as resp:
            self.assertEqual(resp.status, 200)
            payload = json.loads(resp.read().decode("utf-8"))

        self.assertEqual(payload.get("status"), "healthy")
        self.assertIn("features", payload)

    def test_api_analyze_applies_known_fix(self) -> None:
        code = """#!/usr/bin/bash
OUTPUT=/home/student/output-

for HOST in server{a,b}; do
    echo \"$(ssh student@${HOST} hostname -f\") >> ${OUTPUT}${HOST}
done
"""

        req = Request(
            f"http://127.0.0.1:{self.port}/api/analyze",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"code": code}).encode("utf-8"),
        )

        try:
            with urlopen(req, timeout=5.0) as resp:
                self.assertEqual(resp.status, 200)
                result = json.loads(resp.read().decode("utf-8"))
        except URLError as e:
            out = ""
            if getattr(self, "proc", None) and self.proc.stdout:
                try:
                    out = "\n".join(self.proc.stdout.readlines()[-50:])
                except Exception:  # noqa: BLE001
                    out = ""
            raise AssertionError(f"Request failed: {e}\nServer output tail:\n{out}") from e

        self.assertEqual(result.get("originalCode"), code)
        fixed = result.get("fixedCode", "")
        self.assertIn("hostname -f)\"", fixed)
        self.assertIn("# ✅ NAPRAWIONO", fixed)

        errors = result.get("errors") or []
        self.assertTrue(any(e.get("code") == "SC1073" for e in errors))

    def test_api_batch_analyze_scans_directory(self) -> None:
        fixture_dir = self.repo_root / "tests" / "_batch_fixture"
        fixture_dir.mkdir(parents=True, exist_ok=True)

        try:
            (fixture_dir / "faulty.py").write_text('print "hello"\n', encoding="utf-8")
            (fixture_dir / "ok.py").write_text('print("ok")\n', encoding="utf-8")

            req = Request(
                f"http://127.0.0.1:{self.port}/api/batch_analyze",
                method="POST",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "root": "tests/_batch_fixture",
                        "max_files": 20,
                        "max_bytes": 50_000,
                    }
                ).encode("utf-8"),
            )

            with urlopen(req, timeout=10.0) as resp:
                self.assertEqual(resp.status, 200)
                payload = json.loads(resp.read().decode("utf-8"))

            self.assertIn("totals", payload)
            totals = payload["totals"]
            self.assertGreaterEqual(int(totals.get("filesListed") or 0), 2)
            self.assertGreaterEqual(int(totals.get("filesAnalyzed") or 0), 2)
            self.assertGreaterEqual(int(totals.get("errors") or 0), 1)

            files = payload.get("files") or []
            self.assertTrue(any(f.get("path") == "tests/_batch_fixture/faulty.py" for f in files))
            self.assertTrue(any(f.get("path") == "tests/_batch_fixture/ok.py" for f in files))
            faulty = next(f for f in files if f.get("path") == "tests/_batch_fixture/faulty.py")
            self.assertGreaterEqual(int(faulty.get("errors") or 0), 1)
        finally:
            for p in fixture_dir.glob("*"):
                try:
                    p.unlink()
                except Exception:
                    pass
            try:
                fixture_dir.rmdir()
            except Exception:
                pass
