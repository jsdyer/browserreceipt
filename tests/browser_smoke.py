from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, os, shutil, tempfile, threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
def main():
    screenshots=ROOT/"browser-checks";screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT/"dist",Path(temporary)/"example-tool")
        server=ThreadingHTTPServer(("127.0.0.1",0),partial(QuietHandler,directory=temporary))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=os.environ.get("CHROMIUM_EXECUTABLE"))
                page=browser.new_page(viewport={"width":1280,"height":1000})
                errors=[];requests=[]
                page.on("pageerror",lambda e:errors.append(str(e)))
                page.on("request",lambda r:requests.append(r.url))
                page.goto(f"http://127.0.0.1:{server.server_port}/example-tool/")
                assert int(page.locator("#count").inner_text())>=30
                assert not any("workers.dev" in u or "probe.example" in u for u in requests)
                page.locator("#save").click()
                assert "0 changed fields" in page.locator("#baseline").inner_text()
                page.set_viewport_size({"width":1100,"height":900})
                page.locator("#capture").click()
                assert "Viewport" in page.locator("#changes").inner_text()
                page.reload()
                assert "Saved" in page.locator("#baseline").inner_text()
                page.route("**/api/browserreceipt/connection",lambda r:r.fulfill(json={"data":{"ip":"192.0.2.17","asn":64501,"organization":"Test network","country":"CA","colo":"YVR","http":"HTTP/2","tls":"TLSv1.3"}}))
                page.locator("#connection").click()
                page.get_by_text("192.0.2.17",exact=True).wait_for()
                with page.expect_download() as event:page.locator("#export").click()
                data=json.loads(Path(event.value.path()).read_text())
                assert not any(k.startswith("Connection ·") for k in data["values"])
                page.locator("#include-network").check()
                with page.expect_download() as event:page.locator("#export").click()
                assert "192.0.2.17" in Path(event.value.path()).read_text()
                page.locator("#forget").click()
                assert "No baseline saved" in page.locator("#baseline").inner_text()
                page.locator("#permissions").click()
                page.get_by_text("Read this site’s permission states. No permission was requested and no device was opened.").wait_for()

                page.screenshot(path=str(screenshots/"desktop.png"),full_page=True)
                page.set_viewport_size({"width":390,"height":844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots/"mobile.png"),full_page=True)
                assert not errors,errors
                browser.close()
            print("Browser checks passed: task flow, privacy, safe rendering and mobile layout")
        finally:server.shutdown()
if __name__=="__main__":main()
