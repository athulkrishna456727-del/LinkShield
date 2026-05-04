"""
Real network scanner using nmap, smbclient, and ssh-audit subprocesses.
Produces a lateral-movement graph (nodes = hosts, edges = exploitable services).
"""
import asyncio
import ipaddress
import logging
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Lateral movement risk weights
EDGE_RISK = {
    "smb_guest": {"score": 90, "level": "high", "label": "SMB Anonymous Login",
                  "remediation": "Disable guest SMB via GPO: 'EnableGuestAuth' and 'RestrictAnonymous'."},
    "rdp_open": {"score": 60, "level": "medium", "label": "RDP Exposed",
                 "remediation": "Restrict RDP to VPN/jump-host. Enforce NLA + MFA."},
    "winrm_open": {"score": 70, "level": "medium", "label": "WinRM Exposed",
                   "remediation": "Disable WinRM HTTP (5985); use HTTPS (5986) with cert auth only."},
    "ssh_weak": {"score": 65, "level": "medium", "label": "SSH Weak Crypto",
                 "remediation": "Disable CBC ciphers, MD5/SHA1 MACs, weak kex algorithms."},
    "ssh_open": {"score": 25, "level": "low", "label": "SSH Reachable",
                 "remediation": "Restrict source IPs and enforce key-only auth."},
    "smb_open": {"score": 30, "level": "low", "label": "SMB Reachable",
                 "remediation": "Block 445/tcp at perimeter; segment workstation subnets."},
}

DEFAULT_PORTS = "22,445,3389,5985,5986"


def _validate_targets(ip_ranges: list[str]) -> list[str]:
    """Sanitize and validate IP ranges to prevent command injection."""
    valid = []
    for r in ip_ranges:
        r = r.strip()
        if not r:
            continue
        # Allow CIDR, single IP, or hyphenated range like 10.0.0.1-10.0.0.50
        if not re.match(r"^[0-9a-fA-F:./\-]+$", r):
            continue
        try:
            if "/" in r:
                ipaddress.ip_network(r, strict=False)
            elif "-" in r:
                start, end = r.split("-", 1)
                ipaddress.ip_address(start.strip())
                # nmap accepts "10.0.0.1-50" or full
            else:
                ipaddress.ip_address(r)
            valid.append(r)
        except ValueError:
            continue
    return valid


async def _run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """Run subprocess and capture output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return -1, "", "timeout"
    except FileNotFoundError:
        return -2, "", "tool_not_installed"
    except Exception as e:
        return -3, "", str(e)


async def nmap_discover(targets: list[str], ports: str = DEFAULT_PORTS) -> dict:
    """Run nmap host discovery + service detection. Returns dict[ip] -> info."""
    if not targets:
        return {}
    if not shutil.which("nmap"):
        return {}

    # -sn for ping sweep alternative; we use combined: -Pn -sS not allowed without root.
    # Use -sT (TCP connect) which works without root and -sV light service detection.
    cmd = [
        "nmap", "-T4", "-Pn", "-sT",
        "-p", ports,
        "--max-retries", "1",
        "--host-timeout", "60s",
        "-oX", "-",  # XML to stdout
        *targets,
    ]
    rc, stdout, stderr = await _run(cmd, timeout=600)
    if rc < 0 or not stdout:
        logger.warning("nmap failed rc=%s err=%s", rc, stderr[:200])
        return {}

    hosts = {}
    try:
        root = ET.fromstring(stdout)
        for host in root.findall("host"):
            status = host.find("status")
            if status is None or status.get("state") not in ("up",):
                continue
            addr_el = host.find("address")
            ip = addr_el.get("addr") if addr_el is not None else None
            if not ip:
                continue
            hostname_el = host.find("hostnames/hostname")
            hostname = hostname_el.get("name") if hostname_el is not None else ip

            os_match_el = host.find("os/osmatch")
            os_name = os_match_el.get("name") if os_match_el is not None else None

            open_ports = []
            for port in host.findall("ports/port"):
                state_el = port.find("state")
                if state_el is None or state_el.get("state") != "open":
                    continue
                portid = int(port.get("portid"))
                service_el = port.find("service")
                svc_name = service_el.get("name") if service_el is not None else ""
                product = service_el.get("product") if service_el is not None else ""
                open_ports.append({"port": portid, "service": svc_name, "product": product or ""})

            hosts[ip] = {
                "ip": ip,
                "hostname": hostname,
                "os": os_name,
                "open_ports": open_ports,
            }
    except ET.ParseError as e:
        logger.warning("nmap XML parse error: %s", e)
    return hosts


async def smb_guest_check(ip: str) -> dict:
    """smbclient -L //ip -N -- guest/anonymous share enumeration."""
    if not shutil.which("smbclient"):
        return {"checked": False, "reason": "tool_missing"}
    rc, stdout, stderr = await _run(
        ["smbclient", "-L", f"//{ip}", "-N", "-t", "10"], timeout=20
    )
    out = (stdout + stderr).lower()
    if "session setup failed" in out or "nt_status_access_denied" in out or "logon_failure" in out:
        return {"checked": True, "guest_allowed": False, "shares": []}
    if "sharename" in out and "type" in out:
        # parse share names
        shares = []
        for line in stdout.splitlines():
            m = re.match(r"\s+(\S+)\s+(Disk|IPC|Printer)\s*", line)
            if m:
                shares.append({"name": m.group(1), "type": m.group(2)})
        return {"checked": True, "guest_allowed": True, "shares": shares[:20]}
    return {"checked": True, "guest_allowed": False, "shares": [], "raw": out[:200]}


async def ssh_audit_check(ip: str) -> dict:
    """ssh-audit IP -- detect weak crypto."""
    ssh_audit = shutil.which("ssh-audit") or "/root/.venv/bin/ssh-audit"
    rc, stdout, stderr = await _run([ssh_audit, "-n", ip], timeout=25)
    if rc < 0 and rc != 1:
        return {"checked": False, "reason": "tool_error"}
    text = stdout + stderr
    weak_findings = []
    for line in text.splitlines():
        # ssh-audit prefixes findings with [fail], [warn], [info]
        if re.match(r"\s*\(?\[?(fail|warn)\]?\)?", line, re.I):
            weak_findings.append(line.strip()[:160])
    return {
        "checked": True,
        "weak_crypto": len([f for f in weak_findings if "[fail]" in f.lower() or "(fail)" in f.lower()]) > 0,
        "warnings": weak_findings[:15],
    }


async def winrm_test(ip: str, port: int) -> dict:
    """Quick WinRM banner / availability test via curl."""
    rc, stdout, stderr = await _run(
        ["curl", "-sk", "-m", "8", "-o", "/dev/null", "-w", "%{http_code}",
         f"http{'s' if port == 5986 else ''}://{ip}:{port}/wsman"],
        timeout=12,
    )
    return {"checked": True, "reachable": stdout.strip() in ("200", "401", "403", "405")}


async def scan_host(ip: str, host_info: dict) -> tuple[dict, list[dict]]:
    """For one host, run service-specific checks and return (node, edges_to_self_finding)."""
    open_port_set = {p["port"] for p in host_info.get("open_ports", [])}
    findings = []

    if 445 in open_port_set:
        smb = await smb_guest_check(ip)
        host_info["smb"] = smb
        if smb.get("guest_allowed"):
            findings.append({"type": "smb_guest", "port": 445, "detail": f"Anonymous SMB shares: {len(smb.get('shares', []))}"})
        else:
            findings.append({"type": "smb_open", "port": 445, "detail": "SMB reachable"})

    if 22 in open_port_set:
        ssh = await ssh_audit_check(ip)
        host_info["ssh"] = ssh
        if ssh.get("weak_crypto"):
            findings.append({"type": "ssh_weak", "port": 22, "detail": "Weak SSH crypto"})
        else:
            findings.append({"type": "ssh_open", "port": 22, "detail": "SSH reachable"})

    if 3389 in open_port_set:
        findings.append({"type": "rdp_open", "port": 3389, "detail": "RDP exposed"})

    if 5985 in open_port_set or 5986 in open_port_set:
        port = 5986 if 5986 in open_port_set else 5985
        winrm = await winrm_test(ip, port)
        host_info["winrm"] = winrm
        if winrm.get("reachable"):
            findings.append({"type": "winrm_open", "port": port, "detail": "WinRM responding"})

    # node-level risk = max edge severity
    max_score = 0
    for f in findings:
        max_score = max(max_score, EDGE_RISK.get(f["type"], {}).get("score", 0))

    host_info["risk_score"] = max_score
    host_info["findings"] = findings
    return host_info, findings


def build_graph(hosts: dict[str, dict]) -> dict:
    """Build vis-network compatible graph: nodes + edges representing lateral-movement paths."""
    nodes = []
    edges = []
    weak_endpoints = []

    for ip, info in hosts.items():
        score = info.get("risk_score", 0)
        if score >= 70:
            level, color = "high", "#ef4444"
        elif score >= 40:
            level, color = "medium", "#f59e0b"
        elif score > 0:
            level, color = "low", "#facc15"
        else:
            level, color = "safe", "#22c55e"

        nodes.append({
            "id": ip,
            "label": info.get("hostname") or ip,
            "title": f"{ip}\nOS: {info.get('os') or 'unknown'}\nRisk: {score}",
            "color": color,
            "risk_score": score,
            "risk_level": level,
            "ip": ip,
            "hostname": info.get("hostname"),
            "os": info.get("os"),
            "open_ports": info.get("open_ports", []),
        })

        for f in info.get("findings", []):
            edge_meta = EDGE_RISK.get(f["type"], {})
            weak_endpoints.append({
                "ip": ip,
                "hostname": info.get("hostname") or ip,
                "type": f["type"],
                "label": edge_meta.get("label", f["type"]),
                "level": edge_meta.get("level", "low"),
                "score": edge_meta.get("score", 0),
                "port": f.get("port"),
                "detail": f.get("detail", ""),
                "remediation": edge_meta.get("remediation", ""),
            })

    # Build lateral movement edges: from each high/medium-risk host to others sharing similar attack surface
    # Heuristic: if host A has SMB guest enabled, edges to every other host with port 445 open (attacker pivot).
    # This represents realistic lateral-movement direction in the graph.
    smb_guest_hosts = [ip for ip, h in hosts.items() if any(f["type"] == "smb_guest" for f in h.get("findings", []))]
    smb_open_hosts = [ip for ip, h in hosts.items() if 445 in {p["port"] for p in h.get("open_ports", [])}]
    rdp_hosts = [ip for ip, h in hosts.items() if 3389 in {p["port"] for p in h.get("open_ports", [])}]
    winrm_hosts = [ip for ip, h in hosts.items() if any(f["type"] == "winrm_open" for f in h.get("findings", []))]

    edge_id = 0
    for src in smb_guest_hosts:
        for dst in smb_open_hosts:
            if src == dst:
                continue
            edge_id += 1
            edges.append({
                "id": f"e{edge_id}", "from": src, "to": dst,
                "label": "SMB pivot", "color": {"color": "#ef4444"}, "width": 3,
                "arrows": "to", "risk_type": "smb_guest", "risk_level": "high",
                "dashes": False,
            })
    for src in winrm_hosts:
        for dst in winrm_hosts:
            if src == dst:
                continue
            edge_id += 1
            edges.append({
                "id": f"e{edge_id}", "from": src, "to": dst,
                "label": "WinRM lateral", "color": {"color": "#f59e0b"}, "width": 2,
                "arrows": "to", "risk_type": "winrm_open", "risk_level": "medium",
                "dashes": True,
            })
    # RDP cluster (less aggressive - only connect adjacent)
    for i, src in enumerate(rdp_hosts):
        for dst in rdp_hosts[i + 1:i + 3]:
            edge_id += 1
            edges.append({
                "id": f"e{edge_id}", "from": src, "to": dst,
                "label": "RDP", "color": {"color": "#facc15"}, "width": 1,
                "arrows": "to", "risk_type": "rdp_open", "risk_level": "medium",
                "dashes": True,
            })

    # Sort weak endpoints by score desc
    weak_endpoints.sort(key=lambda x: x["score"], reverse=True)

    summary = {
        "hosts_total": len(nodes),
        "hosts_high_risk": sum(1 for n in nodes if n["risk_level"] == "high"),
        "hosts_medium_risk": sum(1 for n in nodes if n["risk_level"] == "medium"),
        "edges_total": len(edges),
        "smb_guest_count": len(smb_guest_hosts),
        "rdp_exposed_count": len(rdp_hosts),
        "winrm_exposed_count": len(winrm_hosts),
    }

    return {"nodes": nodes, "edges": edges, "weak_endpoints": weak_endpoints, "summary": summary}


async def run_full_scan(ip_ranges: list[str], ports: str = DEFAULT_PORTS,
                        progress_cb=None) -> dict:
    """Top-level: discover hosts, fingerprint each, build graph."""
    targets = _validate_targets(ip_ranges)
    if not targets:
        return {"error": "No valid IP ranges/addresses provided", "graph": {"nodes": [], "edges": [], "weak_endpoints": [], "summary": {}}}

    if progress_cb:
        await progress_cb("discovering", f"Running nmap on {len(targets)} target(s)…")

    hosts = await nmap_discover(targets, ports=ports)

    if progress_cb:
        await progress_cb("fingerprinting", f"Discovered {len(hosts)} host(s); analyzing services…")

    # Run per-host service checks concurrently (capped)
    sem = asyncio.Semaphore(8)

    async def _wrap(ip, info):
        async with sem:
            return await scan_host(ip, info)

    if hosts:
        await asyncio.gather(*[_wrap(ip, info) for ip, info in hosts.items()])

    if progress_cb:
        await progress_cb("graphing", "Building lateral-movement graph…")

    graph = build_graph(hosts)
    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "targets": targets,
        "ports": ports,
        "hosts": hosts,
        "graph": graph,
    }
