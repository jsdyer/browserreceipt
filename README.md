# Browser Receipt

[Open Browser Receipt](https://coolcode.ca/browserreceipt/) — inspect what this browser exposes, save a local baseline, and compare after changing a privacy setting, browser or VPN.

<!-- coolcode:guide -->
Check your public IP and network on demand, or capture browser settings and compare them with a saved local baseline. Network fields are included in saved or exported receipts only when you select them.
<!-- /coolcode:guide -->

[Open the public IP check](https://coolcode.ca/browserreceipt/what-is-my-ip/).

## What works immediately

- Browser, display, locale, hardware estimates, privacy preferences and API/codec capabilities.
- Explicitly saved baseline in `coolcode:browserreceipt:baseline:v1`; imported baseline stays in memory until you choose to save the current receipt.
- Refresh, compare, forget and JSON import/export. Field-level comparison does not imply uniqueness or anonymity.
- A separate **Check public connection** button calls CoolCode's no-store Cloudflare endpoint for this request's IP, ASN/organization, country code, serving edge and transport metadata.
- **Read permission states** asks the Permissions API about this site's current states. It never requests camera, microphone, notification or location access.

Browser values can be reduced, spoofed, unavailable or estimated. Screen sizes are CSS pixels. Hardware concurrency is browser-visible capacity, memory is approximate, online status is not a connection test, and a network organization may be a proxy/VPN rather than an ISP. WebGL availability is checked without reading a renderer fingerprint. No canvas pixel hash, font enumeration, WebRTC address gathering or device probing occurs.

## Privacy and analytics

The application does not upload captured fields, imports, comparison results or saved baselines. Its public-connection request necessarily exposes the requester IP to CoolCode's Cloudflare endpoint but does not send browser-receipt fields. The optional observer sees a public client request and resolver egress addresses. No API key is required.

The ordinary CoolCode pageview counter sends only the tool ID and respects GPC / Do Not Track. Inputs never enter URLs or analytics. Receipt exports may contain sensitive network data only when the explicit checkbox is selected.

## Optional DNS observer

See [optional-dns/README.md](optional-dns/README.md). This is an optional small VPS companion, not a dependency of the browser tool. It requires a delegated DNS subzone, a public server with TCP/UDP 53, and HTTPS for its API. It observes **recursive resolver egress**, never the complete resolver chain. Installation, testing, limits and removal are documented. Nothing is installed automatically.

## Expand or customize

The measured field list and explanation text are in `web/app.mjs`; adding a browser API should also state what it means and whether it prompts, sends network traffic or increases fingerprinting. Keep ordinary capture local and permission-free. The connection API URL is in that file. Its response is validated by `normalizeConnection` in `web/model.mjs`.

No default DNS observer is configured or contacted. Enter your own observer origin in the optional panel. Tune its bounded lifetime and capacity in `optional-dns/server.py` only after reviewing privacy and abuse limits. No schedules or collector watchdog target are needed: all results are produced by the visitor's browser or explicit request.

## Build and publish

```bash
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

The default build is offline and has no production package dependencies. `tests/browser_smoke.py` uses test-only Playwright/Chromium. Pushes to `main` test and publish Pages; manual workflow runs are also available. Keep Pages source set to GitHub Actions. A source edit does not need a new data capture.

## References

- [Browser-reported processor capacity](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/hardwareConcurrency)
- [Memory privacy rounding](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/deviceMemory)
- [Permissions API](https://developer.mozilla.org/en-US/docs/Web/API/Permissions_API)
- [Cloudflare request metadata](https://developers.cloudflare.com/workers/runtime-apis/request/)
