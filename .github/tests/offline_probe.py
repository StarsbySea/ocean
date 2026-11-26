"""Acceptance test: positive controls outside the namespace, negative inside."""
import asyncio
import errno
import os
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

WRAPPER = Path(__file__).resolve().parents[1] / "scripts" / "offline.sh"

def request(kind, port):
    with socket.socket(socket.AF_INET, kind) as conn:
        conn.settimeout(2)
        conn.connect(("127.0.0.1", port))
        if kind == socket.SOCK_DGRAM:
            conn.send(b"ping")
            assert conn.recv(4) == b"pong"

def denied(kind, port):
    try:
        request(kind, port)
    except OSError as exc:
        assert exc.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EACCES, errno.EPERM, errno.ECONNREFUSED), repr(exc)
    else:
        raise AssertionError("original namespace still reachable")

def inside(tcp, udp, child=False):
    denied(socket.SOCK_STREAM, tcp)
    denied(socket.SOCK_DGRAM, udp)
    with socket.socket() as conn:
        conn.settimeout(2)
        try:
            conn.connect(("1.1.1.1", 443))
        except OSError as exc:
            assert exc.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EACCES, errno.EPERM), repr(exc)
        else:
            raise AssertionError("external TCP reachable")
    async def task():
        return 42
    assert asyncio.run(task()) == 42
    a, b = socket.socketpair()
    with a, b:
        a.sendall(b"x")
        assert b.recv(1) == b"x"
    with tempfile.TemporaryDirectory() as path:
        file = Path(path) / "test"
        file.write_text("ok")
        assert file.read_text() == "ok"
    if not child:
        subprocess.run([sys.executable, __file__, "child", str(tcp), str(udp)], check=True)
    print("PASS: TCP/UDP isolation, external TCP, asyncio, socketpair, filesystem and descendant probe", flush=True)

def main():
    with socket.socket() as tcp, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        tcp.bind(("127.0.0.1", 0))
        tcp.listen()
        udp.bind(("127.0.0.1", 0))
        def echo():
            data, peer = udp.recvfrom(4)
            assert data == b"ping"
            udp.sendto(b"pong", peer)
        threading.Thread(target=echo, daemon=True).start()
        tp, up = tcp.getsockname()[1], udp.getsockname()[1]
        request(socket.SOCK_STREAM, tp)
        request(socket.SOCK_DGRAM, up)
        with socket.create_connection(("1.1.1.1", 443), timeout=5):
            pass
        subprocess.run(["bash", str(WRAPPER), sys.executable, __file__, "inside", str(tp), str(up)], check=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("PASS: live positive controls, network isolation and descendant compatibility.\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inside(int(sys.argv[2]), int(sys.argv[3]), child=sys.argv[1] == "child")
    else:
        main()
