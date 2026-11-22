#!/usr/bin/env python3
"""A tiny stand-in for a TAK Server's plain TCP input (port 8087) for testing the
PagerMesh mesh <-> TAK bridge without a real server.

Prints every CoT event it gets (contacts and GeoChat) and, a few seconds after a
client connects, sends one GeoChat to "All Chat Rooms" from a demo TAK user, so you
can see it arrive on the mesh. Demo data only.

  python3 tools/fake_takserver.py --port 8087
"""
import argparse
import re
import socket
import threading
import time


def geochat(text, cs="DEMO-ATAK", uid="ANDROID-demo0001"):
    t = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    st = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time() + 86400))
    return ('<event version="2.0" uid="GeoChat.%s.All Chat Rooms.demo%d" type="b-t-f" how="h-g-i-g-o" '
            'time="%s" start="%s" stale="%s"><point lat="0" lon="0" hae="0" ce="9999999" le="9999999"/>'
            '<detail><__chat parent="RootContactGroup" groupOwner="false" messageId="demo%d" chatroom="All Chat Rooms" '
            'id="All Chat Rooms" senderCallsign="%s"><chatgrp uid0="%s" uid1="All Chat Rooms" id="All Chat Rooms"/>'
            '</__chat><link uid="%s" type="a-f-G-U-C" relation="p-p"/><remarks source="BAO.F.ATAK.%s" '
            'to="All Chat Rooms" time="%s">%s</remarks></detail></event>') % (
        uid, int(time.time()), t, t, st, int(time.time()), cs, uid, uid, uid, t, text)


def client(c, addr):
    print("client %s:%d" % addr, flush=True)

    def later():
        time.sleep(4)
        try:
            c.sendall(geochat("Hello mesh, this is TAK").encode())
            print("-> GeoChat from DEMO-ATAK", flush=True)
        except OSError:
            pass
    threading.Thread(target=later, daemon=True).start()
    buf = b""
    while True:
        try:
            d = c.recv(65536)
        except OSError:
            break
        if not d:
            break
        buf += d
        while b"</event>" in buf:
            ev, buf = buf.split(b"</event>", 1)
            ev = ev.decode("utf-8", "replace")
            typ = re.search(r'type="([^"]*)"', ev)
            if typ and typ.group(1) == "b-t-f":
                cs = re.search(r'senderCallsign="([^"]*)"', ev)
                rm = re.search(r"<remarks[^>]*>(.*)", ev, re.S)
                print("<- GeoChat %s: %s" % (cs.group(1) if cs else "?", rm.group(1).split("</remarks>")[0] if rm else ""), flush=True)
            else:
                cs = re.search(r'callsign="([^"]*)"', ev)
                pt = re.search(r'<point lat="([^"]*)" lon="([^"]*)"', ev)
                print("<- %s %s %s" % (typ.group(1) if typ else "?", cs.group(1) if cs else "?",
                                       "%s,%s" % pt.groups() if pt else ""), flush=True)
    print("client gone", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8087)
    ap.add_argument("--bind", default="127.0.0.1")
    a = ap.parse_args()
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((a.bind, a.port))
    s.listen(4)
    print("fake TAK server (TCP) on %s:%d" % (a.bind, a.port), flush=True)
    while True:
        c, addr = s.accept()
        threading.Thread(target=client, args=(c, addr), daemon=True).start()


if __name__ == "__main__":
    main()
