#!/usr/bin/env python3
"""
代理节点链接生成器（统一版）
合并 Hysteria2 / NaiveProxy / VLESS(Xray) 三个脚本为一个。

运行后生成：
  1. proxy_links.html  — 自包含单页 HTML，参照样品.html 样式
  2. proxy_links.txt    — 纯链接订阅文件（所有协议）
"""

from __future__ import annotations

import json
import os
import sys
import base64
import urllib.request
import urllib.parse
import re
import ssl
from datetime import datetime

# ─── Windows console UTF-8 fix ───────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass

_SSL_CTX = ssl.create_default_context()

# ═══════════════════════════════════════════════════════════════════
#  Config URLs
# ═══════════════════════════════════════════════════════════════════

HY2_CONFIG_URLS = [
    "https://gitlab.com/free9999/ipupdate/-/raw/master/backup/img/1/2/ipp/hysteria2/1/config.json",
    "https://gitlab.com/free9999/ipupdate/-/raw/master/backup/img/1/2/ipp/hysteria2/2/config.json",
    "https://gitlab.com/free9999/ipupdate/-/raw/master/backup/img/1/2/ipp/hysteria2/3/config.json",
    "https://gitlab.com/free9999/ipupdate/-/raw/master/backup/img/1/2/ipp/hysteria2/4/config.json",
]
HY2_NODE_NAMES = ["节点1", "节点2", "节点3", "节点4"]

NAIVE_PRIMARY_URLS = [
    "https://gitlab.com/free9999/ipupdate/-/raw/master/backup/img/1/2/ipp/naiveproxy/1/config.json",
    "https://gitlab.com/free9999/ipupdate/-/raw/master/backup/img/1/2/ipp/naiveproxy/2/config.json",
]
NAIVE_FALLBACK_URLS = [
    "https://www.67867867.xyz/Alvin9999/PAC/refs/heads/master/backup/img/1/2/ipp/naiveproxy/1/config.json",
    "https://www.67867867.xyz/Alvin9999/PAC/refs/heads/master/backup/img/1/2/ipp/naiveproxy/2/config.json",
]
NAIVE_NODE_NAMES = ["节点1", "节点2"]

VLESS_CONFIG_URLS = {
    "节点1": "https://gitlab.com/free9999/ipupdate/-/raw/master/backup/img/1/2/ipp/xray/1/config.json",
    "节点2": "https://gitlab.com/free9999/ipupdate/-/raw/master/backup/img/1/2/ipp/xray/2/config.json",
    "节点3": "https://gitlab.com/free9999/ipupdate/-/raw/master/backup/img/1/2/ipp/xray/3/config.json",
    "节点4": "https://gitlab.com/free9999/ipupdate/-/raw/master/backup/img/1/2/ipp/xray/4/config.json",
}

# ═══════════════════════════════════════════════════════════════════
#  Shared utilities
# ═══════════════════════════════════════════════════════════════════


def fetch_url(url: str, timeout: int = 15) -> dict:
    """Fetch and parse JSON from a single URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_config_with_fallback(primary_url: str, fallback_url: str) -> tuple[dict, str]:
    """Fetch JSON from primary URL with fallback. Returns (config, source_label)."""
    try:
        return fetch_url(primary_url), "GitLab"
    except Exception as e:
        print(f"    [WARN] Primary URL failed: {e}")
        print(f"    [INFO] Trying fallback URL...")
    try:
        return fetch_url(fallback_url), "Backup"
    except Exception:
        raise Exception(f"Both URLs failed. Primary: {primary_url}, Fallback: {fallback_url}")


def parse_server(server_str: str) -> tuple[str, str]:
    """Parse host and port from server field. Supports host:port, [ipv6]:port, host."""
    server_str = server_str.strip()
    m = re.match(r"^\[(.+)\]:(\d+)$", server_str)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"^(.+):(\d+)$", server_str)
    if m:
        return m.group(1), m.group(2)
    return server_str, "443"


def is_ipv6(host: str) -> bool:
    return ":" in host


def bracket_host(host: str) -> str:
    if is_ipv6(host) and not host.startswith("["):
        return f"[{host}]"
    return host


def _truncate(s: str, limit: int = 30) -> str:
    return s if len(s) <= limit else s[:limit] + "…"


# ═══════════════════════════════════════════════════════════════════
#  1. Hysteria2
# ═══════════════════════════════════════════════════════════════════


def build_hy2_link(config: dict, name: str) -> str | None:
    """Generate hy2:// share link from Hysteria2 config.json. Returns None on error."""
    try:
        server_str = config.get("server", "")
        auth = config.get("auth", "")
        host, port = parse_server(server_str)

        auth_encoded = urllib.parse.quote(auth, safe="")
        if is_ipv6(host):
            authority = f"{auth_encoded}@[{host}]:{port}"
        else:
            authority = f"{auth_encoded}@{host}:{port}"

        params = []
        tls = config.get("tls", {})
        sni = tls.get("sni", "")
        if sni:
            params.append(("sni", sni))
        if tls.get("insecure", False):
            params.append(("insecure", "1"))
        pin = tls.get("pinSHA256", "")
        if pin:
            params.append(("pinSHA256", pin))

        obfs = config.get("obfs", {})
        transport_obfs = config.get("transport", {}).get("obfs", {})
        obfs_type = obfs.get("type", "") or transport_obfs.get("type", "")
        obfs_password = obfs.get("password", "") or transport_obfs.get("password", "")
        if obfs_type:
            params.append(("obfs", obfs_type))
        if obfs_password:
            params.append(("obfs-password", obfs_password))

        qs = urllib.parse.urlencode(params) if params else ""
        uri = f"hy2://{authority}"
        if qs:
            uri += f"/?{qs}"
        uri += f"#{urllib.parse.quote(name)}"
        return uri
    except Exception:
        return None


def fetch_hysteria2() -> list[dict]:
    """Fetch all Hysteria2 configs and return node dicts for HTML."""
    nodes = []
    print("[*] Fetching Hysteria2 configs...")
    for i, (url, name) in enumerate(zip(HY2_CONFIG_URLS, HY2_NODE_NAMES)):
        print(f"    #{i+1}: {url}")
        try:
            config = fetch_url(url)
        except Exception as e:
            print(f"    [FAIL] {e}")
            continue

        server = config.get("server", "")
        host, port_str = parse_server(server)
        port = int(port_str)
        auth = config.get("auth", "")
        tls = config.get("tls", {})
        sni = tls.get("sni", "")
        insecure = tls.get("insecure", False)
        obfs = config.get("obfs", {})
        transport_obfs = config.get("transport", {}).get("obfs", {})
        obfs_type = obfs.get("type", "") or transport_obfs.get("type", "")
        obfs_password = obfs.get("password", "") or transport_obfs.get("password", "")

        link = build_hy2_link(config, name)
        if not link:
            continue

        details = {
            "协议": "Hysteria2",
            "认证": _truncate(auth),
            "SNI": sni or "(none)",
            "Obfs": obfs_type or "(none)",
            "Insecure": insecure,
        }
        nodes.append({"name": name, "host": host, "port": port, "link": link, "details": details})
        print(f"    [OK] {host}:{port}")
    print(f"    → Hysteria2: {len(nodes)} nodes\n")
    return nodes


# ═══════════════════════════════════════════════════════════════════
#  2. NaiveProxy
# ═══════════════════════════════════════════════════════════════════


def parse_proxy_url(proxy_url: str) -> tuple[str, str, str, str, str]:
    """Parse proxy URL -> (scheme, username, password, host, port)."""
    parsed = urllib.parse.urlparse(proxy_url)
    return (
        parsed.scheme,
        urllib.parse.unquote(parsed.username) if parsed.username else "",
        urllib.parse.unquote(parsed.password) if parsed.password else "",
        parsed.hostname or "",
        str(parsed.port) if parsed.port else "443",
    )


def build_naive_link(config: dict, name: str) -> str | None:
    """Generate naive+https:// or naive+quic:// share link."""
    try:
        proxy_url = config.get("proxy", "")
        if not proxy_url:
            return None
        scheme, username, password, host, port = parse_proxy_url(proxy_url)
        link_scheme = "naive+quic" if scheme == "quic" else "naive+https"
        username_encoded = urllib.parse.quote(username, safe="")
        password_encoded = urllib.parse.quote(password, safe="")
        userinfo = f"{username_encoded}:{password_encoded}" if username else ""
        hostport = f"[{host}]:{port}" if is_ipv6(host) else f"{host}:{port}"
        if userinfo:
            uri = f"{link_scheme}://{userinfo}@{hostport}"
        else:
            uri = f"{link_scheme}://{hostport}"
        uri += f"#{urllib.parse.quote(name)}"
        return uri
    except Exception:
        return None


def fetch_naiveproxy() -> list[dict]:
    """Fetch all NaiveProxy configs and return node dicts for HTML."""
    nodes = []
    print("[*] Fetching NaiveProxy configs...")
    for i, (primary, fallback, name) in enumerate(zip(NAIVE_PRIMARY_URLS, NAIVE_FALLBACK_URLS, NAIVE_NODE_NAMES)):
        print(f"    #{i+1}: {primary}")
        try:
            config, source = fetch_config_with_fallback(primary, fallback)
        except Exception as e:
            print(f"    [FAIL] {e}")
            continue

        proxy_url = config.get("proxy", "")
        scheme, username, password, host, port = parse_proxy_url(proxy_url)

        link = build_naive_link(config, name)
        if not link:
            continue

        details = {
            "协议": "NaiveProxy",
            "服务器": _truncate(host),
            "端口": port,
            "用户名": _truncate(username),
            "密码": _truncate(password),
        }
        nodes.append({"name": name, "host": host, "port": int(port), "link": link, "details": details})
        print(f"    [OK] {source} → {host}:{port}")
    print(f"    → NaiveProxy: {len(nodes)} nodes\n")
    return nodes


# ═══════════════════════════════════════════════════════════════════
#  3. VLESS (Xray)
# ═══════════════════════════════════════════════════════════════════


def find_vless_outbound(config: dict) -> dict | None:
    for ob in config.get("outbounds", []):
        if ob.get("protocol") == "vless":
            return ob
    return None


def extract_vless_node_info(outbound: dict) -> dict:
    vnext = outbound["settings"]["vnext"][0]
    user = vnext["users"][0]
    stream = outbound.get("streamSettings", {})
    reality = stream.get("realitySettings", {})
    xhttp = stream.get("xhttpSettings", {})
    return {
        "uuid": user["id"],
        "address": vnext["address"],
        "port": vnext["port"],
        "encryption": user.get("encryption", "none"),
        "flow": user.get("flow", ""),
        "network": stream.get("network", "tcp"),
        "security": stream.get("security", "tls"),
        "sni": reality.get("serverName", ""),
        "fingerprint": reality.get("fingerprint", ""),
        "publicKey": reality.get("publicKey", ""),
        "shortId": reality.get("shortId", ""),
        "path": xhttp.get("path", ""),
        "xhttpMode": xhttp.get("mode", ""),
        "serviceName": stream.get("grpcSettings", {}).get("serviceName", ""),
        "host": stream.get("wsSettings", {}).get("headers", {}).get("Host", ""),
    }


def build_vless_link(info: dict, tag: str = "") -> str:
    addr = bracket_host(info["address"])
    params = {}
    enc = info["encryption"]
    params["encryption"] = enc if enc and enc != "none" else "none"
    if info["flow"]:
        params["flow"] = info["flow"]
    params["type"] = info["network"]
    params["security"] = info["security"]
    if info["security"] == "reality":
        if info["sni"]:
            params["sni"] = info["sni"]
        if info["fingerprint"]:
            params["fp"] = info["fingerprint"]
        if info["publicKey"]:
            params["pbk"] = info["publicKey"]
        if info["shortId"]:
            params["sid"] = info["shortId"]
    if info["network"] == "xhttp":
        if info["path"]:
            params["path"] = info["path"]
        if info["xhttpMode"]:
            params["xhttpMode"] = info["xhttpMode"]
    elif info["network"] == "ws":
        if info["path"]:
            params["path"] = info["path"]
        if info["host"]:
            params["host"] = info["host"]
    elif info["network"] == "grpc":
        if info["serviceName"]:
            params["serviceName"] = info["serviceName"]
    query = urllib.parse.urlencode(params)
    fragment = urllib.parse.quote(tag) if tag else ""
    link = f"vless://{info['uuid']}@{addr}:{info['port']}?{query}"
    if fragment:
        link += f"#{fragment}"
    return link


def fetch_vless() -> list[dict]:
    """Fetch all VLESS (Xray) configs and return node dicts for HTML."""
    nodes = []
    print("[*] Fetching VLESS (Xray) configs...")
    for name, url in VLESS_CONFIG_URLS.items():
        print(f"    {name}: {url}")
        try:
            config = fetch_url(url)
            outbound = find_vless_outbound(config)
            if not outbound:
                print(f"    [SKIP] No vless outbound")
                continue
            info = extract_vless_node_info(outbound)
            link = build_vless_link(info, tag=name)
        except Exception as e:
            print(f"    [FAIL] {e}")
            continue

        host = info["address"]
        port = info["port"]
        details = {
            "协议": "vless",
            "加密": _truncate(info["encryption"]),
            "传输": info["network"],
            "安全": info["security"],
            "SNI": info["sni"],
            "Fingerprint": info["fingerprint"],
            "PublicKey": _truncate(info["publicKey"]),
            "ShortID": info["shortId"],
            "Path": info["path"],
            "Mode": info["xhttpMode"],
        }
        nodes.append({"name": name, "host": host, "port": port, "link": link, "details": details})
        print(f"    [OK] {host}:{port}")
    print(f"    → VLESS: {len(nodes)} nodes\n")
    return nodes


# ═══════════════════════════════════════════════════════════════════
#  HTML generation (参照 样品.html)
# ═══════════════════════════════════════════════════════════════════

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>代理节点链接生成器</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;background:#0f1117;color:#e0e0e0;min-height:100vh;padding:20px}
h1{text-align:center;font-size:24px;margin-bottom:6px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.subtitle{text-align:center;color:#888;font-size:13px;margin-bottom:20px}
.controls{text-align:center;margin-bottom:20px}
.btn{padding:10px 24px;border:none;border-radius:8px;font-size:14px;cursor:pointer;transition:transform .15s,box-shadow .15s}
.btn:hover{transform:translateY(-1px)}.btn:active{transform:translateY(0)}
.btn-primary{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff}
.btn-primary:hover{box-shadow:0 4px 16px rgba(102,126,234,.4)}
.btn-secondary{background:#2d2d3d;color:#aaa;border:1px solid #444}
.btn-secondary:hover{color:#fff;border-color:#667eea}
.status{text-align:center;color:#888;font-size:13px;margin-bottom:14px}
.tip{background:#1a1b26;border:1px solid #333;border-radius:10px;padding:14px 16px;margin-bottom:20px;font-size:13px;color:#888;line-height:1.6}
.tip strong{color:#aaa}
.tip code{background:#0f1117;padding:1px 6px;border-radius:4px;color:#667eea;font-size:12px}
.group-title{font-size:17px;font-weight:600;margin:24px 0 10px;padding-bottom:6px;border-bottom:2px solid #333;display:flex;align-items:center;gap:8px}
.badge{font-size:11px;padding:2px 8px;border-radius:4px;color:#fff;font-weight:500}
.badge-vless{background:#4263eb}.badge-hy{background:#e67700}.badge-np{background:#0ca678}
.node-card{background:#1a1b26;border:1px solid #2d2d3d;border-radius:12px;padding:14px 16px;margin-bottom:10px;transition:border-color .2s}
.node-card:hover{border-color:#444}
.node-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.node-name{font-size:15px;font-weight:600;color:#c8c8d0}
.node-addr{font-size:12px;color:#888;font-family:"Cascadia Code","Fira Code",monospace}
.node-details{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:4px 14px;margin-bottom:10px;font-size:12px}
.detail-item{display:flex;gap:6px}
.detail-label{color:#666;min-width:56px}
.detail-value{color:#aaa;font-family:"Cascadia Code","Fira Code",monospace;word-break:break-all}
.link-row{display:flex;align-items:stretch;gap:8px}
.link-box{flex:1;background:#0f1117;border:1px solid #2d2d3d;border-radius:8px;padding:8px 12px;font-size:11px;font-family:"Cascadia Code","Fira Code",monospace;color:#667eea;word-break:break-all;line-height:1.5;user-select:all;max-height:72px;overflow-y:auto}
.btn-copy{background:#2d2d3d;color:#ccc;border:1px solid #444;border-radius:8px;padding:8px 14px;cursor:pointer;font-size:13px;white-space:nowrap;transition:all .2s;align-self:center}
.btn-copy:hover{background:#4263eb;color:#fff;border-color:#4263eb}
.btn-copy.copied{background:#2b8a3e;color:#fff;border-color:#2b8a3e}
.toast{position:fixed;top:20px;right:20px;background:#2b8a3e;color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;opacity:0;transform:translateY(-10px);transition:all .3s;z-index:1000;pointer-events:none}
.toast.show{opacity:1;transform:translateY(0)}
footer{text-align:center;color:#555;font-size:12px;margin-top:36px;padding-top:14px;border-top:1px solid #222}
</style>
</head>
<body>
<h1>🔗 代理节点链接生成器</h1>
<p class="subtitle">从远程配置自动提取节点信息，生成可导入客户端的分享链接</p>
<div class="controls">
  <button class="btn btn-secondary" onclick="copyAllLinks()">📋 复制全部链接</button>
</div>
<div class="status" id="status"></div>
<div class="tip">
  <strong>💡 使用说明：</strong><br>
  • 页面数据已嵌入，双击 HTML 文件即可查看所有节点链接<br>
  • 每个节点旁有「复制」按钮，可单独复制链接<br>
  • 点击「复制全部」可一次性复制所有链接到剪贴板<br>
  • VLESS 链接可导入 <strong>v2rayN / v2rayNG / Clash Verge / NekoBox</strong><br>
  • Hysteria2 链接需导入 <strong>Clash Verge / sing-box</strong>（v2rayN 不支持）<br>
  • NaiveProxy 链接可导入 <strong>Clash Verge / NaiveProxy</strong><br>
  • 如需更新数据，请重新运行 <code>python gen_links.py</code>
</div>
<div id="content"></div>
<div class="toast" id="toast"></div>
<footer>生成时间: __TIMESTAMP__ &nbsp;|&nbsp; 如数据过期请重新运行脚本</footer>
<script>
const NODES = __NODES_JSON__;
let allLinks = [];

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

function render(){
  const c=document.getElementById('content');
  let html='';
  let idx=0;
  for(const src of NODES){
    html+=`<div class="group-title"><span class="badge ${src.badge}">${src.group}</span> <span style="color:#666;font-size:13px">(${src.nodes.length} 个节点)</span></div>`;
    for(const node of src.nodes){
      idx++;
      const nid='lnk-'+idx;
      const detHtml=Object.entries(node.details).map(([k,v])=>`<div class="detail-item"><span class="detail-label">${esc(k)}</span><span class="detail-value">${esc(v)}</span></div>`).join('');
      html+=`<div class="node-card">
        <div class="node-header">
          <span class="node-name">${esc(src.group)} - ${esc(node.name)}</span>
          <span class="node-addr">${esc(node.host)}:${node.port}</span>
        </div>
        <div class="node-details">${detHtml}</div>
        <div class="link-row">
          <div class="link-box" id="${nid}">${esc(node.link)}</div>
          <button class="btn-copy" onclick="copyLink('${nid}',this)">📋 复制</button>
        </div>
      </div>`;
      allLinks.push(node.link);
    }
  }
  c.innerHTML=html;
  document.getElementById('status').textContent=`共 ${allLinks.length} 个节点链接，已嵌入页面`;
}

function copyLink(id,btn){
  const el=document.getElementById(id);if(!el)return;
  navigator.clipboard.writeText(el.textContent.trim()).then(()=>{
    btn.textContent='✅ 已复制';btn.classList.add('copied');showToast('✅ 已复制到剪贴板');
    setTimeout(()=>{btn.textContent='📋 复制';btn.classList.remove('copied')},2000);
  }).catch(()=>{
    const r=document.createRange();r.selectNodeContents(el);const s=window.getSelection();s.removeAllRanges();s.addRange(r);
    try{document.execCommand('copy');showToast('✅ 已复制')}catch(e){showToast('❌ 复制失败，请手动选择复制')}
    s.removeAllRanges();
  });
}

function copyAllLinks(){
  navigator.clipboard.writeText(allLinks.join('\n')).then(()=>showToast(`✅ 已复制全部 ${allLinks.length} 个链接`)).catch(()=>showToast('❌ 复制失败'));
}

function showToast(msg){
  const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2000);
}

window.addEventListener('DOMContentLoaded',render);
</script>
</body>
</html>'''


def generate_html(groups: list[dict], output_path: str) -> None:
    """Generate self-contained HTML file from node groups."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nodes_json = json.dumps(groups, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("__NODES_JSON__", nodes_json).replace("__TIMESTAMP__", timestamp)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[SAVED] HTML: {output_path}")


# ═══════════════════════════════════════════════════════════════════
#  TXT subscription file
# ═══════════════════════════════════════════════════════════════════


def generate_txt(groups: list[dict], output_path: str) -> None:
    """Generate plain-text subscription file with all links grouped by protocol."""
    lines = []
    total = 0
    for g in groups:
        lines.append(f"# {g['group']}")
        for node in g["nodes"]:
            lines.append(node["link"])
            total += 1
        lines.append("")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[SAVED] TXT:  {output_path} ({total} links)")


# ═══════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════


def main() -> int:
    ci_mode = "--ci" in sys.argv

    sep = "=" * 60
    print(sep)
    print("  代理节点链接生成器（统一版）")
    print("  Hysteria2 + NaiveProxy + VLESS(Xray)")
    print(sep)
    print()

    # Determine output directory (same as script location, or CWD in CI)
    if ci_mode:
        output_dir = os.getcwd()
    else:
        output_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(output_dir, "proxy_links.html")
    txt_path = os.path.join(output_dir, "proxy_links.txt")

    # Fetch all protocols
    hy2_nodes = fetch_hysteria2()
    naive_nodes = fetch_naiveproxy()
    vless_nodes = fetch_vless()

    # Assemble groups (order: VLESS first, then Hysteria2, then NaiveProxy)
    groups = []
    if vless_nodes:
        groups.append({"group": "Xray VLESS", "badge": "badge-vless", "nodes": vless_nodes})
    if hy2_nodes:
        groups.append({"group": "Hysteria2", "badge": "badge-hy", "nodes": hy2_nodes})
    if naive_nodes:
        groups.append({"group": "NaiveProxy", "badge": "badge-np", "nodes": naive_nodes})

    total = sum(len(g["nodes"]) for g in groups)
    print(sep)
    print(f"  Total: {total} nodes from {len(groups)} protocol groups")
    print(sep)
    print()

    if total == 0:
        print("[WARN] No nodes fetched. Check network and try again.")
        return 1

    # Generate outputs
    generate_html(groups, html_path)
    generate_txt(groups, txt_path)

    print()
    print("[DONE] All done!")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        if "--ci" not in sys.argv:
            print("\n")
            input("Press Enter to exit...")
