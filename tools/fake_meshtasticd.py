#!/usr/bin/env python3
"""Fake meshtasticd for testing PagerMesh without a radio.

Speaks the Meshtastic TCP API (framing + the protobuf fields PagerMesh uses)
with a handful of demo nodes around a demo location. Nodes move, send chat,
telemetry and positions; direct messages from PagerMesh get an ack.

  python3 tools/fake_meshtasticd.py [--port 4403] [--lat 39.7392 --lon -104.9903]
                                    [--region 1] [--fast]

Everything PagerMesh sends is printed, so you can see what would go on air.
"""
import argparse
import math
import os
import random
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                "library", "user", "general", "PagerMesh", "mesh"))
import meshproto as mp  # noqa: E402

MY_NUM = 0xA1B2C3D4
NODES = [  # num, long, short, bearing deg, distance m, battery
    (0x0BADF00D, "Demo Base Station", "BASE", 40, 2400, 101),
    (0x1CEB00DA, "Demo Hiker", "HIKR", 200, 900, 76),
    (0x2DEC0DE5, "Demo Relay Ridge", "RDGE", 300, 7800, 54),
    (0x3FACADE1, "Demo Truck 2", "TRK2", 120, 4100, 92),
]
CHATTER = ["Radio check", "Copy all", "On scene", "Moving to checkpoint 2", "All clear", "Standing by"]


def frame(b):
    return mp.MAGIC + struct.pack(">H", len(b)) + b


def offset(lat, lon, brg, dist):
    dlat = dist * math.cos(math.radians(brg)) / 111320.0
    dlon = dist * math.sin(math.radians(brg)) / (111320.0 * math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon


def user(num, long_, short):
    return mp.f_bytes(1, mp.node_id(num)) + mp.f_bytes(2, long_) + mp.f_bytes(3, short) + mp.f_varint(5, 43)


def position(lat, lon, t):
    return mp.f_sfixed32(1, int(lat * 1e7)) + mp.f_sfixed32(2, int(lon * 1e7)) + mp.f_varint(3, 300) + mp.f_fixed32(4, t)


def metrics(batt):
    return mp.f_varint(1, batt) + mp.ev((2 << 3) | 5) + struct.pack("<f", 4.05)


def nodeinfo(num, long_, short, lat, lon, batt, snr, heard, hops, mqtt=False):
    b = mp.f_varint(1, num) + mp.f_bytes(2, user(num, long_, short))
    if lat is not None:
        b += mp.f_bytes(3, position(lat, lon, heard))
    b += mp.ev((4 << 3) | 5) + struct.pack("<f", snr) + mp.f_fixed32(5, heard)
    if batt is not None:
        b += mp.f_bytes(6, metrics(batt))
    if hops is not None:
        b += mp.f_varint(9, hops)
    if mqtt:
        b += mp.f_varint(8, 1)
    return mp.f_bytes(4, b)


def packet(frm, to, port, payload, channel=0, snr=6.5, req=None, hop_start=3, hop_limit=2, rssi=None,
           mqtt=False, encrypted=None):
    data = mp.f_varint(1, port) + mp.f_bytes(2, payload)
    if req:
        data += mp.f_fixed32(6, req)
    if rssi is None:
        rssi = int(-60 - (8 - snr) * 6 + random.randint(-4, 4))
    body = mp.f_bytes(5, encrypted) if encrypted else mp.f_bytes(4, data)
    p = (mp.f_fixed32(1, frm) + mp.f_fixed32(2, to) + mp.f_varint(3, channel) + body +
         mp.f_fixed32(6, random.randint(1, 0xFFFFFFFF)) + mp.f_fixed32(7, int(time.time())) +
         mp.ev((8 << 3) | 5) + struct.pack("<f", snr) + mp.f_varint(9, hop_limit) + mp.f_varint(12, rssi) +
         mp.f_varint(15, hop_start))
    if mqtt:
        p += mp.f_varint(14, 1)
    return mp.f_bytes(2, p)


def default_settings(region):
    """Demo radio settings (sent during want_config; admin changes are kept while the simulator runs)."""
    cfg = {
        1: mp.f_varint(1, 0) + mp.f_varint(7, 10800),                                   # device: CLIENT
        2: mp.f_varint(1, 900) + mp.f_varint(2, 1),                                     # position
        3: b"",                                                                         # power
        4: mp.f_varint(1, 1) + mp.f_bytes(3, "DemoNet") + mp.f_bytes(4, "demo-password"),  # network
        5: mp.f_varint(1, 60),                                                          # display
        6: mp.f_varint(1, 1) + mp.f_varint(2, 0) + mp.f_varint(7, region) + mp.f_varint(8, 3) + mp.f_varint(9, 1),
        7: mp.f_varint(1, 1) + mp.f_varint(2, 1),                                       # bluetooth
    }
    mod = {1: mp.f_varint(1, 0) + mp.f_bytes(2, "mqtt.example.org") + mp.f_bytes(4, "demo") + mp.f_varint(5, 1),
           6: mp.f_varint(1, 1800)}
    chans = {0: mp.f_varint(1, 0) + mp.f_bytes(2, mp.f_bytes(2, b"\x01") + mp.f_bytes(3, "")) + mp.f_varint(3, 1),
             1: mp.f_varint(1, 1) + mp.f_bytes(2, mp.f_bytes(2, bytes(range(32))) + mp.f_bytes(3, "Team")) + mp.f_varint(3, 2)}
    return cfg, mod, chans


class Client(threading.Thread):
    def __init__(self, sock, a, world):
        super().__init__(daemon=True)
        self.sock, self.a, self.w = sock, a, world
        self.alive = True
        self.lock = threading.Lock()

    def tx(self, b):
        with self.lock:
            try:
                self.sock.sendall(frame(b))
            except OSError:
                self.alive = False

    def config(self, nonce):
        t = int(time.time())
        w = self.w
        self.tx(mp.f_bytes(3, mp.f_varint(1, MY_NUM)))
        self.tx(mp.f_bytes(13, mp.f_bytes(1, "2.7.15.demo") + mp.f_varint(4, 1) + mp.f_varint(5, 1) + mp.f_varint(9, 43)))
        for sec in sorted(w.cfg):
            self.tx(mp.f_bytes(5, mp.f_bytes(sec, w.cfg[sec])))
        for sec in sorted(w.mod):
            self.tx(mp.f_bytes(9, mp.f_bytes(sec, w.mod[sec])))
        self.tx(nodeinfo(MY_NUM, w.owner[0], w.owner[1], None, None, 101, 0, t, None))
        for n in w.nodes:
            self.tx(nodeinfo(n["num"], n["long"], n["short"], n["lat"], n["lon"], n["batt"], n["snr"],
                             t - random.randint(30, 900), n["hops"], n.get("mqtt")))
        for i in range(8):
            self.tx(mp.f_bytes(10, w.chans.get(i) or mp.f_varint(1, i) + mp.f_varint(3, 0)))
        self.tx(mp.f_varint(7, nonce))

    def on_admin(self, b):
        w = self.w
        for fn, wt, v in mp.fields(b):
            if fn == 32:
                u = dict((f, mp.text(x)) for f, _w, x in mp.fields(v))
                w.owner = (u.get(2) or w.owner[0], u.get(3) or w.owner[1])
                print("<- ADMIN set_owner %s / %s" % w.owner, flush=True)
            elif fn == 34:
                for sec, _w, raw in mp.fields(v):
                    w.cfg[sec] = bytes(raw)
                    print("<- ADMIN set_config section %d (%d bytes)" % (sec, len(raw)), flush=True)
                    w.reboot = True
            elif fn == 35:
                for sec, _w, raw in mp.fields(v):
                    w.mod[sec] = bytes(raw)
                    print("<- ADMIN set_module_config section %d" % sec, flush=True)
                    w.reboot = True
            elif fn == 33:
                c = mp.dec_channel(v)
                w.chans[c["index"]] = bytes(v)
                print("<- ADMIN set_channel %d name=%r role=%d key=%s" % (c["index"], c["name"], c["role"], c["psk_kind"]), flush=True)
            elif fn == 64:
                print("<- ADMIN begin_edit", flush=True)
            elif fn == 65:
                print("<- ADMIN commit_edit", flush=True)
                if w.reboot:
                    self.reboot()
            elif fn == 97:
                print("<- ADMIN reboot", flush=True)
                self.reboot()
            elif fn in (39, 40):
                print("<- ADMIN %s favorite %s" % ("set" if fn == 39 else "remove", mp.node_id(v)), flush=True)
            else:
                print("<- ADMIN field %d" % fn, flush=True)

    def reboot(self):
        """Like a Wi-Fi radio restarting: the TCP connection drops; back in a few seconds."""
        self.w.reboot = False
        self.w.down_until = time.time() + 4
        print("   (radio restarting)", flush=True)
        self.tx(mp.f_varint(8, 1))
        time.sleep(0.3)
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass

    def on_toradio(self, b):
        for fn, wt, v in mp.fields(b):
            if fn == 3:
                print("<- want_config %d" % v, flush=True)
                self.config(v)
            elif fn == 4:
                print("<- disconnect", flush=True)
                self.alive = False
            elif fn == 7:
                print("<- heartbeat", flush=True)
            elif fn == 1:
                p = mp.dec_packet(v)
                d = p.get("decoded", {})
                to = "ALL" if p.get("to") == mp.BROADCAST else mp.node_id(p.get("to"))
                if d.get("portnum") == mp.PORT_TEXT:
                    print("<- TEXT to=%s ch=%s hop=%s: %s" % (to, p.get("channel", 0), p.get("hop_limit"),
                                                            d["payload"].decode("utf-8", "replace")), flush=True)
                    if p.get("to") != mp.BROADCAST:
                        time.sleep(1.5)
                        self.tx(packet(p["to"], MY_NUM, mp.PORT_ROUTING, b"", req=p["id"]))
                        time.sleep(2)
                        self.tx(packet(p["to"], MY_NUM, mp.PORT_TEXT, b"Copy, got your DM"))
                elif d.get("portnum") == mp.PORT_ADMIN and p.get("to") == MY_NUM:
                    self.on_admin(d["payload"])
                elif d.get("portnum") == mp.PORT_TRACEROUTE:
                    print("<- TRACEROUTE to=%s" % to, flush=True)
                    n = self.w.node(p.get("to"))
                    if n:
                        relay = self.w.nodes[0]["num"] if n["num"] != self.w.nodes[0]["num"] else self.w.nodes[1]["num"]
                        rd = (mp.f_bytes(1, struct.pack("<I", relay)) + mp.f_bytes(2, mp.ev(24) + mp.ev(18)) +
                              mp.f_bytes(3, struct.pack("<I", relay)) + mp.f_bytes(4, mp.ev(20) + mp.ev(26)))
                        threading.Timer(3, lambda: self.tx(packet(n["num"], MY_NUM, mp.PORT_TRACEROUTE, rd, req=p["id"]))).start()
                elif d.get("portnum") == mp.PORT_WAYPOINT:
                    wp = mp.dec_waypoint(d["payload"])
                    print("<- WAYPOINT %r %.5f,%.5f expire=%s" % (wp["name"], wp.get("lat", 0), wp.get("lon", 0), wp["expire"]), flush=True)
                elif d.get("portnum") == mp.PORT_POSITION:
                    pos = mp.dec_position(d["payload"])
                    print("<- POSITION to=%s %.5f,%.5f alt=%s want_response=%s" % (
                        to, pos.get("lat", 0), pos.get("lon", 0), pos.get("alt"), d.get("want_response", False)), flush=True)
                    n = self.w.node(p.get("to"))
                    if n and d.get("want_response"):
                        threading.Timer(2, lambda: self.tx(packet(n["num"], MY_NUM, mp.PORT_POSITION,
                                                                  position(n["lat"], n["lon"], int(time.time())), req=p["id"]))).start()
                else:
                    print("<- packet port %s" % d.get("portnum"), flush=True)

    def run(self):
        buf = b""
        self.sock.settimeout(0.5)
        while self.alive:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
            except socket.timeout:
                continue
            except OSError:
                break
            while len(buf) >= 4 and buf[:2] == mp.MAGIC:
                n = struct.unpack(">H", buf[2:4])[0]
                if len(buf) < 4 + n:
                    break
                self.on_toradio(buf[4:4 + n])
                buf = buf[4 + n:]
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass
        print("client gone", flush=True)


class World:
    def __init__(self, a):
        self.a = a
        self.nodes = []
        for num, long_, short, brg, dist, batt in NODES:
            lat, lon = offset(a.lat, a.lon, brg, dist)
            self.nodes.append({"num": num, "long": long_, "short": short, "lat": lat, "lon": lon,
                               "batt": batt, "snr": round(random.uniform(-8, 9), 2), "hops": random.randint(0, 2),
                               "heading": random.randint(0, 359)})
        self.nodes[3]["mqtt"] = True                      # one node heard through MQTT
        self.clients = []
        self.cfg, self.mod, self.chans = default_settings(a.region)
        self.owner = ("Demo Pager", "PGR")
        self.reboot = False
        self.down_until = 0

    def node(self, num):
        return next((n for n in self.nodes if n["num"] == num), None)

    def broadcast(self, b):
        for c in list(self.clients):
            if c.alive:
                c.tx(b)
        self.clients = [c for c in self.clients if c.alive]

    def tick(self):
        n = random.choice(self.nodes)
        r = random.random()
        if n["short"] in ("HIKR", "TRK2"):                # movers
            step = 60 if n["short"] == "HIKR" else 250
            n["heading"] = (n["heading"] + random.randint(-30, 30)) % 360
            n["lat"], n["lon"] = offset(n["lat"], n["lon"], n["heading"], step)
        if r < 0.45:
            self.broadcast(packet(n["num"], mp.BROADCAST, mp.PORT_POSITION, position(n["lat"], n["lon"], int(time.time())),
                                  snr=n["snr"]))
        elif r < 0.65:
            if n["batt"] <= 100:
                n["batt"] = max(5, n["batt"] - 1)
            self.broadcast(packet(n["num"], mp.BROADCAST, mp.PORT_TELEMETRY, mp.f_bytes(2, metrics(n["batt"])), snr=n["snr"]))
        elif r < 0.85:
            ch = 1 if random.random() < 0.3 else 0
            self.broadcast(packet(n["num"], mp.BROADCAST, mp.PORT_TEXT, random.choice(CHATTER).encode(), channel=ch,
                                  snr=n["snr"]))
        elif r < 0.9:
            self.broadcast(packet(n["num"], mp.BROADCAST, mp.PORT_NODEINFO, user(n["num"], n["long"], n["short"]),
                                  snr=n["snr"], mqtt=n.get("mqtt", False)))
        elif r < 0.95:                                   # a channel we have no key for
            self.broadcast(packet(0x4E0D1234, mp.BROADCAST, 1, b"", snr=-3.5, encrypted=os.urandom(random.randint(20, 60))))
        else:
            wp = (mp.f_varint(1, 777) + mp.f_sfixed32(2, int((self.a.lat + 0.01) * 1e7)) +
                  mp.f_sfixed32(3, int((self.a.lon - 0.01) * 1e7)) + mp.f_varint(4, int(time.time()) + 86400) +
                  mp.f_bytes(6, "Rally point") + mp.f_bytes(7, "Demo waypoint"))
            self.broadcast(packet(self.nodes[0]["num"], mp.BROADCAST, mp.PORT_WAYPOINT, wp, snr=self.nodes[0]["snr"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=4403)
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--lat", type=float, default=39.7392)      # demo location (Denver)
    ap.add_argument("--lon", type=float, default=-104.9903)
    ap.add_argument("--region", type=int, default=1)           # 1 = US, 0 = UNSET
    ap.add_argument("--fast", action="store_true", help="an event every 2 s instead of 8 s")
    a = ap.parse_args()
    w = World(a)
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((a.bind, a.port))
    srv.listen(4)
    print("fake meshtasticd on %s:%d" % (a.bind, a.port), flush=True)

    def ticker():
        while True:
            time.sleep(2 if a.fast else 8)
            w.tick()
    threading.Thread(target=ticker, daemon=True).start()
    while True:
        s, addr = srv.accept()
        if time.time() < w.down_until:                  # still "restarting"
            s.close()
            continue
        # like the firmware's API server: a new client replaces the old one
        for c in w.clients:
            c.alive = False
        print("client %s:%d" % addr, flush=True)
        c = Client(s, a, w)
        w.clients = [c]
        c.start()


if __name__ == "__main__":
    main()
