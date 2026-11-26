#!/usr/bin/env python3
"""Bounded authoritative DNS observation service. No recursion, logs or disk state."""
import collections, ipaddress, json, os, re, secrets, socket, socketserver, struct, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

TOKEN = re.compile(r"^[a-f0-9]{32}$")
TTL = 120
MAX_ACTIVE = 1000

class Observations:
    def __init__(self, clock=time.monotonic):
        self.clock, self.lock = clock, threading.RLock()
        self.items = {}
        self.issued = collections.deque()
    def prune(self):
        now = self.clock()
        self.items = {k:v for k,v in self.items.items() if now-v["created"] < TTL}
        while self.issued and now-self.issued[0] >= 60: self.issued.popleft()
    def create(self):
        with self.lock:
            self.prune()
            if len(self.issued) >= 60 or len(self.items) >= MAX_ACTIVE: return None
            token = secrets.token_hex(16)
            self.items[token] = {"created":self.clock(),"resolvers":set()}
            self.issued.append(self.clock())
            return token
    def observe(self, token, address):
        with self.lock:
            self.prune()
            item = self.items.get(token)
            if item and len(item["resolvers"]) < 16:
                item["resolvers"].add(str(ipaddress.ip_address(address)))
    def result(self, token):
        with self.lock:
            self.prune()
            item = self.items.get(token)
            return None if item is None else sorted(item["resolvers"])

def name_wire(name):
    return b"".join(bytes([len(s)])+s.encode("ascii") for s in name.rstrip(".").split("."))+b"\x00"

def read_name(data, offset=12):
    labels = []
    for _ in range(128):
        if offset >= len(data): raise ValueError("name bounds")
        size = data[offset]; offset += 1
        if not size: return ".".join(labels).lower(), offset
        if size > 63 or offset+size > len(data): raise ValueError("compressed or oversized question")
        labels.append(data[offset:offset+size].decode("ascii")); offset += size
        if sum(len(x)+1 for x in labels) > 254: raise ValueError("name too long")
    raise ValueError("label count")

class Authority:
    def __init__(self, zone, nameserver, ipv4, observations):
        self.zone, self.nameserver = zone.rstrip(".").lower(), nameserver.rstrip(".").lower()
        self.ip = ipaddress.IPv4Address(ipv4).packed
        self.observations = observations
    def answer(self, packet, peer):
        if len(packet)<12 or len(packet)>512: return None
        ident, flags, qd, an, ns, ar = struct.unpack("!6H",packet[:12])
        if flags & 0x8000 or flags & 0x7800 or qd != 1: return None
        try:
            name, end = read_name(packet)
            if end+4>len(packet): return None
            qtype,qclass = struct.unpack("!2H",packet[end:end+4]); question=packet[12:end+4]
        except (ValueError,UnicodeError): return None
        def response(code=0, answer=b"", authority=b"", authoritative=True):
            return struct.pack("!6H",ident,0x8000|(0x0400 if authoritative else 0)|(flags&0x0100)|code,1,bool(answer),bool(authority),0)+question+answer+authority
        if qclass!=1 or not (name==self.zone or name.endswith("."+self.zone)): return response(5,authoritative=False)
        token=name[:-(len(self.zone)+1)] if name!=self.zone else ""
        if TOKEN.fullmatch(token): self.observations.observe(token,peer)
        def rr(owner,kind,data,ttl=0): return owner+struct.pack("!HHIH",kind,1,ttl,len(data))+data
        owner=b"\xc0\x0c"
        if name==self.zone and qtype==2: return response(answer=rr(owner,2,name_wire(self.nameserver),60))
        soa=name_wire(self.nameserver)+name_wire("hostmaster."+self.zone)+struct.pack("!5I",1,60,60,300,0)
        if name==self.zone and qtype==6: return response(answer=rr(owner,6,soa,60))
        if TOKEN.fullmatch(token) and qtype==1: return response(answer=rr(owner,1,self.ip))
        # AAAA and modern HTTPS/SVCB receive authoritative NODATA, with no recursion.
        return response(authority=rr(name_wire(self.zone),6,soa,0))

class UDP(socketserver.UDPServer):
    allow_reuse_address=True
class DNSUDP(socketserver.BaseRequestHandler):
    def handle(self):
        data,sock=self.request
        answer=self.server.authority.answer(data,self.client_address[0])
        if answer: sock.sendto(answer,self.client_address)
class DNSTCP(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(2)
        try:
            def read_exact(size):
                buf=b""
                while len(buf)<size:
                    part=self.request.recv(size-len(buf))
                    if not part: raise ValueError("closed")
                    buf+=part
                return buf
            length=struct.unpack("!H",read_exact(2))[0]
            if length>512:return
            answer=self.server.authority.answer(read_exact(length),self.client_address[0])
            if answer:self.request.sendall(struct.pack("!H",len(answer))+answer)
        except (OSError,ValueError): pass
class TCP(socketserver.TCPServer):
    allow_reuse_address=True

def handler(observations, zone, allowed_origin):
    class API(BaseHTTPRequestHandler):
        server_version="DNSObserver"
        def log_message(self,*args): pass
        def reply(self,status,data):
            body=json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type","application/json")
            self.send_header("Cache-Control","no-store")
            self.send_header("Access-Control-Allow-Origin",allowed_origin)
            self.send_header("Vary","Origin")
            self.send_header("Referrer-Policy","no-referrer")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers();self.wfile.write(body)
        def origin_ok(self):
            return self.headers.get("Origin")==allowed_origin
        def do_OPTIONS(self):
            if not self.origin_ok():return self.reply(403,{"error":"origin"})
            self.send_response(204);self.send_header("Access-Control-Allow-Origin",allowed_origin)
            self.send_header("Access-Control-Allow-Methods","GET, POST, OPTIONS")
            self.send_header("Content-Length","0");self.end_headers()
        def do_POST(self):
            if not self.origin_ok():return self.reply(403,{"error":"origin"})
            if self.path!="/challenge":return self.reply(404,{"error":"path"})
            # No request body is accepted or stored.
            if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Length","0")!="0":
                self.close_connection=True;return self.reply(400,{"error":"body_not_allowed"})
            token=observations.create()
            if not token:return self.reply(429,{"error":"busy"})
            self.reply(201,{"token":token,"hostname":token+"."+zone,"expires_in":TTL})
        def do_GET(self):
            if self.path=="/health":return self.reply(200,{"status":"ok"})
            if not self.origin_ok():return self.reply(403,{"error":"origin"})
            token=self.path.removeprefix("/result/")
            if not self.path.startswith("/result/") or not TOKEN.fullmatch(token):return self.reply(404,{"error":"path"})
            result=observations.result(token)
            self.reply(404 if result is None else 200,{"error":"expired"} if result is None else {"resolvers":result,"retention_seconds":TTL})
    return API

def main():
    zone=os.environ["OBSERVER_ZONE"].lower().rstrip(".")
    ns=os.environ["OBSERVER_NS"].lower().rstrip(".")
    if not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+",zone) or not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+",ns):raise SystemExit("Invalid DNS names")
    origin=os.environ.get("OBSERVER_ORIGIN","https://coolcode.ca")
    parsed=urlsplit(origin)
    if parsed.scheme!="https" or not parsed.netloc or parsed.path:raise SystemExit("OBSERVER_ORIGIN must be an HTTPS origin")
    observations=Observations()
    def expire():
        while True:
            time.sleep(1)
            with observations.lock: observations.prune()
    threading.Thread(target=expire,daemon=True).start()
    authority=Authority(zone,ns,os.environ["OBSERVER_IPV4"],observations)
    port=int(os.environ.get("DNS_PORT","5353")); bind=os.environ.get("DNS_BIND","0.0.0.0")
    servers=[UDP((bind,port),DNSUDP),TCP((bind,port),DNSTCP),ThreadingHTTPServer(("127.0.0.1",int(os.environ.get("HTTP_PORT","8098"))),handler(observations,zone,origin))]
    for server in servers:server.authority=authority
    for server in servers[:-1]:threading.Thread(target=server.serve_forever,daemon=True).start()
    try:servers[-1].serve_forever()
    finally:
        for server in servers:server.server_close()
if __name__=="__main__":main()
