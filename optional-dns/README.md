# Optional DNS observer for Browser Receipt

This small Python standard-library service lets a visitor see which recursive resolver addresses reach **your authoritative DNS server**. It does not discover the full DNS chain, verify anonymity, identify an ISP with certainty, or offer recursive DNS to the internet.

The browser tool works without it. Start with a test subdomain on your VPS; no paid API or Cloudflare Worker is needed.

## 1. Choose names and DNS records

Example names below are placeholders. Replace them with your own domain and the VPS public IPv4:

| Record in your existing DNS provider | Value |
|---|---|
| `ns1.example.com A` | VPS public IPv4 (DNS-only, not proxied) |
| `dns-observer.example.com A` | VPS public IPv4 |
| `probe.example.com NS` | `ns1.example.com.` |

Use the `probe.example.com` **subzone only**. Do not change nameservers for your main domain. Existing DNS services on the VPS may already occupy port 53; check `sudo ss -luntp` first. This service needs inbound TCP and UDP 53. Its API is loopback-only on 8098 behind your HTTPS reverse proxy. Port 8098 must not be opened publicly.

The DNS server currently listens on IPv4; IPv6 clients can still use recursive resolvers that contact IPv4 authoritative servers. It returns NODATA for AAAA probes and records whichever recursive source addresses actually reach it.

## 2. Install on a systemd VPS

Requires Python 3.10+ and your existing HTTPS reverse proxy. From a checked-out copy of this repository:

```bash
sudo install -d -m 755 /opt/coolcode-dns-observer
sudo install -m 644 optional-dns/server.py /opt/coolcode-dns-observer/server.py
sudo install -m 600 optional-dns/observer.env.example /etc/coolcode-dns-observer.env
sudoedit /etc/coolcode-dns-observer.env
sudo install -m 644 optional-dns/coolcode-dns-observer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now coolcode-dns-observer.service
sudo systemctl status coolcode-dns-observer.service
```

Set `OBSERVER_ZONE`, `OBSERVER_NS` and `OBSERVER_IPV4` to your real values. Keep `OBSERVER_ORIGIN=https://coolcode.ca`. These are public configuration values, not API secrets. The example addresses will not function on the public internet.

Add the example Caddy site from [Caddyfile.example](Caddyfile.example) to your existing configuration, substituting your API hostname. Use Caddy's normal validation and reload procedure. Another HTTPS proxy can forward to `127.0.0.1:8098` instead. Do not replace unrelated proxy configuration. Do not enable access logging for the observer: result paths contain short-lived tokens. Keep TLS verification enabled.

No wildcard TLS certificate is required. The browser triggers a fetch to a unique probe hostname; HTTPS may intentionally fail after the resolver has contacted this DNS server. The UI uses the separate DNS observation, not success of that fetch. Your API hostname still needs a valid normal HTTPS certificate.

## 3. Test before using the browser

```bash
curl --fail https://dns-observer.example.com/health
curl --fail -X POST -H 'Origin: https://coolcode.ca' https://dns-observer.example.com/challenge
```

Copy the returned hostname and token. Query the hostname through your normal recursive resolver:

```bash
dig RETURNED-HOSTNAME A
curl --fail -H 'Origin: https://coolcode.ca' https://dns-observer.example.com/result/RETURNED-TOKEN
```

The result should list the source address seen by the authoritative server. Also test both transports directly with `dig @YOUR-VPS-IP probe.example.com NS` and `dig +tcp @YOUR-VPS-IP probe.example.com NS`. An unrelated query such as `dig @YOUR-VPS-IP example.net A` must return REFUSED and must not recurse.

Open Browser Receipt, expand **Optional: observe DNS resolver egress**, enter your HTTPS API origin, and run the probe. Browser policies, filtering and network failures can produce no observation; no result is not proof of a leak or leak protection.

## Limits, retention and maintenance

- Only the configured subzone is authoritative. No recursion, forwarding, arbitrary DNS lookup endpoint or amplification-oriented ANY response.
- At most 60 challenges per minute globally, 1,000 live challenges and 16 resolver addresses per token.
- Tokens are 128 random bits and expire after 120 seconds; expiry is checked on access and an idle cleanup loop removes expired entries within a second.
- State is in RAM only; no databases, query logs, visitor logs or result persistence.
- CORS admits only the configured HTTPS origin. CORS is not authentication: the global budget also bounds direct clients.
- TCP reads time out after two seconds; packets are bounded to 512 bytes. This is a low-volume experimental observer, not a general DNS hosting service.
- The systemd service uses a dynamic user, a read-only system and only the capability required to bind port 53.
- Watch service health with your VPS monitoring. If included in the CoolCode watchdog later, track service execution separately from individual no-observation probes.

For an update, replace `server.py` using the install command and restart the service. Tests: `python3 -m unittest discover -s tests -p test_dns.py -v` from the repository.

## Remove

```bash
sudo systemctl disable --now coolcode-dns-observer.service
```

Then remove its dedicated service/config/program files, its API reverse-proxy block and the three DNS records you added. Leave all unrelated VPS services and DNS records unchanged.
