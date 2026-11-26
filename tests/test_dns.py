import importlib.util, json, socket, struct, threading, unittest, urllib.request, urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
spec=importlib.util.spec_from_file_location("observer",Path(__file__).resolve().parents[1]/"optional-dns/server.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class DNSObserverTests(unittest.TestCase):
    def test_expiry_and_global_budget(self):
        clock=[0];o=mod.Observations(lambda:clock[0]);token=o.create();o.observe(token,"192.0.2.3")
        self.assertEqual(o.result(token),["192.0.2.3"])
        clock[0]=121;self.assertIsNone(o.result(token))
        self.assertTrue(all(o.create() for _ in range(60)));self.assertIsNone(o.create())
    def packet(self,name,kind=1):
        return struct.pack("!6H",7,0x100,1,0,0,0)+mod.name_wire(name)+struct.pack("!2H",kind,1)
    def test_authoritative_only_and_actual_observation(self):
        o=mod.Observations();token=o.create();a=mod.Authority("probe.example.com","ns.example.com","192.0.2.1",o)
        answer=a.answer(self.packet(token+".probe.example.com"),"192.0.2.8")
        flags=struct.unpack("!6H",answer[:12])[1]
        self.assertTrue(flags&0x400);self.assertFalse(flags&0x80)
        self.assertEqual(o.result(token),["192.0.2.8"])
        refused=a.answer(self.packet("outside.example"),"192.0.2.8")
        self.assertEqual(refused[3]&15,5)
        self.assertIsNone(a.answer(b"short","192.0.2.8"))
        self.assertIsNone(a.answer(struct.pack("!6H",7,0,1,0,0,0)+b"\xc0\x0c"+b"\x00\x01\x00\x01","192.0.2.8"))
    def test_dns_no_data_and_ns(self):
        a=mod.Authority("probe.example.com","ns.example.com","192.0.2.1",mod.Observations())
        ns=a.answer(self.packet("probe.example.com",2),"192.0.2.8")
        self.assertIn(mod.name_wire("ns.example.com"),ns)
        no=a.answer(self.packet("a"*32+".probe.example.com",28),"192.0.2.8")
        header=struct.unpack("!6H",no[:12]);self.assertEqual(header[3],0);self.assertEqual(header[4],1)
    def test_api_origin_no_store_and_no_request_body(self):
        o=mod.Observations();server=ThreadingHTTPServer(("127.0.0.1",0),mod.handler(o,"probe.example.com","https://coolcode.ca"))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        url="http://127.0.0.1:"+str(server.server_port)
        with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(urllib.request.Request(url+"/challenge",method="POST"))
        self.assertEqual(cm.exception.code,403)
        r=urllib.request.urlopen(urllib.request.Request(url+"/challenge",method="POST",headers={"Origin":"https://coolcode.ca"}))
        self.assertEqual(r.headers["Cache-Control"],"no-store");data=json.load(r);self.assertRegex(data["token"],r"^[a-f0-9]{32}$")
        o.observe(data["token"],"192.0.2.9")
        result=json.load(urllib.request.urlopen(urllib.request.Request(url+"/result/"+data["token"],headers={"Origin":"https://coolcode.ca"})))
        self.assertEqual(result["resolvers"],["192.0.2.9"])
        with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(urllib.request.Request(url+"/challenge",data=b"private",headers={"Origin":"https://coolcode.ca"}))
        self.assertEqual(cm.exception.code,400)
