#!/usr/bin/env python3
import os
import sys
import ssl
import zlib
import base64
import getpass
from typing import Dict, List, Any, Optional

# Load .env BEFORE importing app modules (needed for ENCRYPTION_KEY)
from dotenv import load_dotenv
load_dotenv()

from routeros_api import RouterOsApiPool

# Add app to path for database access
# We need to add the project root (parent of scripts) to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Define DB accessors inside main or usage to avoid circular imports if any, 
# but for this script top-level is fine if path is set.
try:
    from app.db.router_db import get_router_by_host, get_routers_for_backup
    from app.db.aps_db import get_ap_by_host_with_stats, get_all_aps_with_stats, get_ap_credentials
    from app.db.zonas_db import get_all_zonas
    from app.utils.device_clients.adapters.ubiquiti_airmax import UbiquitiAirmaxAdapter
except ImportError as e:
    print(f"⚠ Import Error: {e}")
    print(f"  sys.path: {sys.path}")
    # Allow running without app context for testing (mocking may be needed)
    UbiquitiAirmaxAdapter = None
    # If these are missing, the script will crash later when calling get_devices_from_db
    # We define dummy functions to avoid NameError if import fails, or let it crash with better message
    def get_routers_for_backup(): return []
    def get_all_aps_with_stats(): return []
    def get_ap_by_host_with_stats(h): return None
    def get_ap_credentials(h): return None
    pass


def connect_router(host: str, username: str, password: str, port: int = 8729):
    """Connect to a MikroTik router via API-SSL."""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    pool = RouterOsApiPool(
        host,
        username=username,
        password=password,
        port=port,
        use_ssl=True,
        ssl_context=ssl_context,
        plaintext_login=True,
    )
    return pool.get_api()


def get_router_identity(api) -> str:
    """Get the router's identity (hostname)."""
    try:
        identity = api.get_resource("/system/identity").get()
        return identity[0].get("name", "Unknown") if identity else "Unknown"
    except Exception:
        return "Unknown"


def get_router_info(api) -> Dict[str, Any]:
    """Get basic router info for display."""
    try:
        resource = api.get_resource("/system/resource").get()
        if resource:
            res = resource[0]
            return {
                "board": res.get("board-name", ""),
                "platform": res.get("platform", res.get("architecture-name", "")),
                "version": res.get("version", ""),
            }
    except Exception:
        pass
    return {}


# === DISCOVERY SOURCES ===

def get_neighbors(api) -> List[Dict[str, Any]]:
    """Fetch MNDP/LLDP neighbors."""
    try:
        neighbors_raw = api.get_resource("/ip/neighbor").get()
        neighbors = []
        for n in neighbors_raw:
            neighbors.append({
                "source": "MNDP/LLDP",
                "interface": n.get("interface-name", n.get("interface", "")),
                "mac_address": n.get("mac-address", ""),
                "identity": n.get("identity", ""),
                "ip_address": n.get("address", ""),
                "platform": n.get("platform", ""),
                "board": n.get("board", ""),
            })
        return neighbors
    except Exception as e:
        print(f"  ⚠ Error MNDP/LLDP: {e}")
        return []


def get_arp_table(api) -> List[Dict[str, Any]]:
    """Fetch ARP table entries."""
    try:
        arp_raw = api.get_resource("/ip/arp").get()
        entries = []
        for a in arp_raw:
            if a.get("complete") == "true" or a.get("status") == "reachable":
                entries.append({
                    "source": "ARP",
                    "interface": a.get("interface", ""),
                    "mac_address": a.get("mac-address", ""),
                    "identity": a.get("comment", ""),  # Use comment as identity if set
                    "ip_address": a.get("address", ""),
                    "platform": "",
                    "board": "",
                })
        return entries
    except Exception as e:
        print(f"  ⚠ Error ARP: {e}")
        return []


def get_ospf_neighbors(api) -> List[Dict[str, Any]]:
    """Fetch OSPF neighbors (RouterOS v7 path)."""
    try:
        # Try v7 path first
        try:
            ospf_raw = api.get_resource("/routing/ospf/neighbor").get()
        except:
            # Fallback to v6 path
            ospf_raw = api.get_resource("/routing/ospf/neighbor").get()
        
        neighbors = []
        for o in ospf_raw:
            neighbors.append({
                "source": "OSPF",
                "interface": o.get("interface", ""),
                "mac_address": "",
                "identity": o.get("router-id", o.get("address", "")),
                "ip_address": o.get("address", ""),
                "platform": "OSPF Router",
                "board": "",
            })
        return neighbors
    except Exception as e:
        print(f"  ⚠ Error OSPF: {e}")
        return []


# === RECURSIVE DISCOVERY ===

def get_credentials_for_ip(ip: str) -> Optional[Dict]:
    """Try to find credentials for an IP in the database. Returns dict with vendor info."""
    # Check Routers first
    try:
        router = get_router_by_host(ip)
        if router:
            return {
                "vendor": "mikrotik",
                "username": router["username"],
                "password": router["password"],
                "port": router.get("api_ssl_port") or 8729
            }
    except:
        pass
    
    # Check APs
    try:
        ap = get_ap_by_host_with_stats(ip)
        if ap:
            creds = get_ap_credentials(ip)
            if creds:
                return {
                    "vendor": ap.get("vendor", "ubiquiti"),
                    "username": creds["username"],
                    "password": creds["password"],
                    "port": ap.get("api_port") or 443
                }
    except:
        pass
    
    return None


def discover_from_device(host: str, username: str, password: str, port: int, sources: List[str]) -> tuple:
    """Connect to a MikroTik device and discover its neighbors. Returns (identity, info, neighbors)."""
    try:
        api = connect_router(host, username, password, port)
        identity = get_router_identity(api)
        info = get_router_info(api)
        
        neighbors = []
        if "mndp" in sources:
            neighbors.extend(get_neighbors(api))
        if "arp" in sources:
            neighbors.extend(get_arp_table(api))
        if "ospf" in sources:
            neighbors.extend(get_ospf_neighbors(api))
        
        return identity, info, neighbors
    except Exception as e:
        print(f"    ⚠ Could not connect to {host}: {e}")
        return None, None, []


def discover_from_ubiquiti(host: str, username: str, password: str, port: int = 443) -> tuple:
    """
    Connect to a Ubiquiti AirMAX device and discover its connected stations.
    Returns (identity, info, neighbors).
    """
    if UbiquitiAirmaxAdapter is None:
        print(f"    ⚠ UbiquitiAirmaxAdapter not available")
        return None, None, []
    
    try:
        adapter = UbiquitiAirmaxAdapter(host, username, password, port)
        status = adapter.get_status()
        
        if not status.is_online:
            print(f"    ⚠ Ubiquiti {host}: {status.last_error}")
            return None, None, []
        
        identity = status.hostname or host
        info = {
            "board": status.model,
            "platform": "AirOS",
            "version": status.firmware,
        }
        
        # Convert connected clients to neighbor format
        neighbors = []
        for client in status.clients:
            neighbors.append({
                "source": "Ubiquiti",
                "interface": "wlan",
                "mac_address": client.mac or "",
                "identity": client.hostname or "",
                "ip_address": client.ip_address or "",
                "platform": "CPE",
                "board": "",
            })
        
        adapter.disconnect()
        return identity, info, neighbors
    except Exception as e:
        print(f"    ⚠ Could not connect to Ubiquiti {host}: {e}")
        return None, None, []


def recursive_discover(seed_host: str, seed_user: str, seed_pass: str, seed_port: int, 
                       sources: List[str], max_depth: int = 3, max_nodes: int = 50,
                       seed_vendor: str = "mikrotik") -> Dict:
    """
    BFS recursive discovery with loop protection and deduplication.
    Supports MikroTik and Ubiquiti devices.
    Returns topology dict: {nodes: [...], edges: [...]}
    """
    visited_ips = set()
    visited_identities = {} # map identity -> node_id
    leaf_ips = {}           # map ip -> leaf_node_id
    
    nodes = []  # {id, ip, identity, info, depth, vendor}
    edges = []  # {from_id, to_id, from_iface, to_ip}
    
    # Queue: (ip, username, password, port, depth, parent_id, vendor)
    queue = [(seed_host, seed_user, seed_pass, seed_port, 0, None, seed_vendor)]
    
    print(f"\n🔄 Recursive discovery (max depth: {max_depth}, max nodes: {max_nodes})")
    
    while queue and len(nodes) < max_nodes:
        current_ip, username, password, port, depth, parent_id, vendor = queue.pop(0)
        
        # Normalize IP
        if not current_ip: continue
        
        # Skip if this specific IP was already fully processed as a NODE
        if current_ip in visited_ips:
            # If we have a parent, we might still need to add an edge if it's not already there?
            # But usually we add edge when we queue it.
            # However, if we found a loop via a NEW path, we might want to record it?
            # For simplicity, skip.
            continue
        
        if depth > max_depth:
            continue
        
        print(f"  [Depth {depth}] Scanning {current_ip} ({vendor})...")
        
        # Call vendor-specific discovery
        if vendor == "ubiquiti":
            identity, info, neighbors = discover_from_ubiquiti(current_ip, username, password, port)
        else:
            identity, info, neighbors = discover_from_device(current_ip, username, password, port, sources)
        
        if not identity:
            continue
            
        # Check if we have seen this IDENTITY before (e.g. same router, different IP)
        if identity in visited_identities:
            existing_node_id = visited_identities[identity]
            print(f"    → Loop detected: {identity} is already node {existing_node_id}")
            if parent_id:
                edges.append({
                    "from_id": parent_id,
                    "to_id": existing_node_id,
                    "label": current_ip,
                })
            # Mark this IP as visited so we don't scan it again, but don't add new node
            visited_ips.add(current_ip)
            continue

        visited_ips.add(current_ip)
        
        # Add node
        node_id = f"node_{len(nodes)}"
        visited_identities[identity] = node_id
        
        nodes.append({
            "id": node_id,
            "ip": current_ip,
            "identity": identity,
            "info": info,
            "depth": depth,
            "vendor": vendor,
        })
        
        # Add edge from parent
        if parent_id:
            edges.append({
                "from_id": parent_id,
                "to_id": node_id,
                "label": current_ip,
            })
        
        # Deduplicate neighbors by IP locally
        unique_neighbors_map = {}
        for n in neighbors:
            nip = n.get("ip_address")
            if nip and nip not in unique_neighbors_map:
                unique_neighbors_map[nip] = n
            # If same IP, maybe prioritize one source over another? 
            # MNDP usually has better info than ARP. Existing order is MNDP, ARP, OSPF.
            # So first one wins is usually fine if sources are ordered.
            
        unique_neighbors = list(unique_neighbors_map.values())
        
        # Queue neighbors for next depth
        for neighbor in unique_neighbors:
            neighbor_ip = neighbor.get("ip_address")
            neighbor_identity = neighbor.get("identity")
            
            if not neighbor_ip:
                continue
                
            # Self-loop check (simple IP check)
            if neighbor_ip == current_ip:
                continue

            # Check if neighbor is already a known NODE by IDENTITY
            if neighbor_identity and neighbor_identity in visited_identities:
                 edges.append({
                    "from_id": node_id,
                    "to_id": visited_identities[neighbor_identity],
                    "label": neighbor.get("interface", ""),
                })
                 continue

            # Check if neighbor is already a known NODE by IP
            # (We only track visited_ips for successful scans, but we check here)
            if neighbor_ip in visited_ips:
                 # Find the node that has this IP (scan nodes list?)
                 # Optimized: we could keep a map ip->node_id but visited_ips is just a set.
                 # Let's find it.
                 target_id = None
                 for n in nodes:
                     if n["ip"] == neighbor_ip:
                         target_id = n["id"]
                         break
                 if target_id:
                     edges.append({
                        "from_id": node_id,
                        "to_id": target_id,
                        "label": neighbor.get("interface", ""),
                    })
                 continue
            
            # Try to get credentials from DB
            creds = get_credentials_for_ip(neighbor_ip)
            if creds:
                # Add to queue (BFS)
                # Check if already in queue? BFS handles visited_ips check at pop, 
                # but we can optimize by checking if we already queued it?
                # For now simple logic is fine.
                queue.append((
                    neighbor_ip, 
                    creds["username"], 
                    creds["password"], 
                    creds["port"], 
                    depth + 1, 
                    node_id,
                    creds.get("vendor", "mikrotik")
                ))
            else:
                # It's a LEAF (unreachable or no creds)
                # Check if we already have a leaf for this IP
                if neighbor_ip in leaf_ips:
                    # Link to existing leaf
                    edges.append({
                        "from_id": node_id,
                        "to_id": leaf_ips[neighbor_ip],
                        "label": neighbor.get("interface", ""),
                    })
                else:
                    # Create new leaf
                    leaf_id = f"leaf_{len(nodes)}_{len(leaf_ips)}"
                    leaf_ips[neighbor_ip] = leaf_id
                    
                    nodes.append({
                        "id": leaf_id,
                        "ip": neighbor_ip,
                        "identity": neighbor.get("identity") or neighbor_ip,
                        "info": {"board": neighbor.get("board"), "platform": neighbor.get("platform")},
                        "depth": depth + 1,
                        "is_leaf": True,
                        "vendor": "unknown",
                    })
                    edges.append({
                        "from_id": node_id,
                        "to_id": leaf_id,
                        "label": neighbor.get("interface", ""),
                    })
    
    print(f"✓ Discovered {len(nodes)} nodes, {len(edges)} connections")
    return {"nodes": nodes, "edges": edges}


def generate_d2_recursive(topology: Dict) -> str:
    """Generate D2 code for recursive topology with vendor-aware styling."""
    lines = [
        "# Network Topology - Recursive Discovery",
        "direction: down",
        "",
    ]
    
    # Generate nodes
    for node in topology["nodes"]:
        node_id = node["id"]
        label = node["identity"]
        if node["info"] and node["info"].get("board"):
            label += f" ({node['info']['board']})"
        
        # Style by vendor and depth
        depth = node.get("depth", 0)
        vendor = node.get("vendor", "unknown")
        
        if depth == 0:
            # Seed device (green)
            style = 'style: {fill: "#e8f5e9"; stroke: "#2e7d32"; stroke-width: 2}'
        elif node.get("is_leaf"):
            # Unreachable leaf (red)
            style = 'style: {fill: "#ffebee"; stroke: "#c62828"}'
        elif vendor == "ubiquiti":
            # Ubiquiti device (purple)
            style = 'style: {fill: "#f3e5f5"; stroke: "#7b1fa2"}'
        elif vendor == "mikrotik":
            # MikroTik device (blue)
            style = 'style: {fill: "#e3f2fd"; stroke: "#1565c0"}'
        else:
            # Unknown vendor (gray)
            style = 'style: {fill: "#fafafa"; stroke: "#666"}'
        
        lines.append(f'{node_id}: "{label}" {{')
        lines.append(f"  {style}")
        lines.append("}")
    
    lines.append("")
    
    # Generate edges
    for edge in topology["edges"]:
        label = edge.get("label", "")
        lines.append(f'{edge["from_id"]} -> {edge["to_id"]}: "{label}"')
    
    return "\n".join(lines)

def sanitize_id(name: str) -> str:
    """Convert a name to a valid D2 identifier."""
    safe = "".join(c if c.isalnum() else "_" for c in name)
    if safe and not safe[0].isalpha():
        safe = "n_" + safe
    return safe.lower() or "unknown"


def generate_d2_map(seed_identity: str, seed_info: Dict, devices: List[Dict], source_name: str, seed_device_data: Dict = None) -> str:
    """
    Generate D2 diagram code from discovered topology with Zone grouping.
    """
    lines = [
        f"# Network Topology - {source_name}",
        "direction: right",
        "classes: {",
        "  router: {",
        '    style: {stroke-width: 2; border-radius: 5}',
        "  }",
        "  zone_box: {",
        '    style: {stroke-width: 2; stroke-dash: 3; fill: "transparent"}',
        "  }",
        "}",
        "",
    ]
    
    # Mapping of IP/MAC to their info if found in DB
    # We need to know which discovered devices match DB devices to assign Zones.
    # In a real app, we would cross-reference 'devices' (discovered) with DB data.
    # For this demo, let's assume 'devices' passed here are the DISCOVERED ones.
    # We should probably pass the FULL db list to lookup zones.
    
    db_devices_map = {}
    try:
        all_db = get_devices_from_db()
        for d in all_db:
            # key by IP
            if d.get("host"):
                db_devices_map[d["host"]] = d
            # Also key by MAC if available? (DB might not have MAC always reliable here)
    except:
        pass

    # Determine Zone for Seed
    seed_zone = "Unknown Zone"
    if seed_device_data and seed_device_data.get("zona_nombre"):
        seed_zone = seed_device_data["zona_nombre"]
    
    # Identify unique zones
    zones = set()
    zones.add(seed_zone)
    
    # Augment discovered devices with Zone info
    enhanced_devices = []
    for d in devices:
        # Check if in DB
        ip = d.get("ip_address")
        zone = "Discovered" # Default for unknown
        
        matches = [val for key, val in db_devices_map.items() if key == ip]
        if matches:
            zone = matches[0].get("zona_nombre", "Default")
        else:
            # If not in DB, group with the seed device (attached to discoverer)
            zone = seed_zone
        
        zones.add(zone)
        d["_zone"] = zone
        enhanced_devices.append(d)

    # 1. Create Zone Containers
    for z in sorted(zones):
        z_id = sanitize_id(z)
        lines.append(f"{z_id}: {z} {{")
        lines.append("  class: zone_box")
        lines.append("}")
    
    lines.append("")

    # Helper to track created output IDs
    # seed_id needs to be placed inside its zone
    seed_id = sanitize_id(seed_identity)
    seed_label = seed_identity
    if seed_info.get("board"):
        seed_label += f" ({seed_info['board']})"
        
    seed_zone_id = sanitize_id(seed_zone)
    lines.append(f"{seed_zone_id}.{seed_id}: \"{seed_label}\" {{")
    lines.append('  class: router')
    lines.append('  style: {fill: "#e8f5e9"; stroke: "#2e7d32"}')
    lines.append("}")
    
    # 2. Place devices
    seen_ids = {seed_id}
    
    for device in enhanced_devices:
        identity = device["identity"] or device["ip_address"] or device["mac_address"] or "Unknown"
        device_id = sanitize_id(identity)
        
        # Handle duplicates
        base_id = device_id
        counter = 1
        while device_id in seen_ids:
            device_id = f"{base_id}_{counter}"
            counter += 1
        seen_ids.add(device_id)
        
        label = identity
        if device["board"]:
            label += f" ({device['board']})"
        elif device["platform"]:
            label += f" ({device['platform']})"
            
        # Color by source
        if device["source"] == "MNDP/LLDP":
            style = 'style: {fill: "#e3f2fd"; stroke: "#1565c0"}'
        elif device["source"] == "ARP":
            style = 'style: {fill: "#fff3e0"; stroke: "#ef6c00"}'
        elif device["source"] == "OSPF":
            style = 'style: {fill: "#e0f7fa"; stroke: "#00838f"}'
        else:
            style = 'style: {fill: "#fafafa"; stroke: "#666"}'

        zone_id = sanitize_id(device["_zone"])
        
        # Place inside zone
        lines.append(f'{zone_id}.{device_id}: "{label}" {{')
        lines.append(f"  {style}")
        lines.append("}")
        
        # Connection
        iface = device["interface"]
        conn_label = iface
        if device["ip_address"] and device["ip_address"] != identity:
            conn_label += f" ({device['ip_address']})"
        
        # Link from Seed (fully qualified names)
        lines.append(f'{seed_zone_id}.{seed_id} -> {zone_id}.{device_id}: "{conn_label}"')
        
    return "\n".join(lines)


def generate_html(d2_code: str, title: str) -> str:
    """Generate HTML with Kroki-rendered diagram."""
    compressed = zlib.compress(d2_code.encode('utf-8'), 9)
    encoded = base64.urlsafe_b64encode(compressed).decode()
    img_url = f"https://kroki.io/d2/svg/{encoded}"
    
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: system-ui; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: #16213e; padding: 20px; border-radius: 12px; }}
        h1 {{ color: #4cc9f0; }}
        .legend {{ display: flex; gap: 20px; margin: 15px 0; flex-wrap: wrap; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; }}
        .legend-color {{ width: 20px; height: 20px; border-radius: 4px; }}
        .preview {{ text-align: center; background: #fff; padding: 20px; border-radius: 8px; margin: 20px 0; overflow: auto; }}
        .preview img {{ max-width: 100%; }}
        pre {{ background: #0f0f23; color: #4cc9f0; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 {title}</h1>
        <div class="legend">
            <div class="legend-item"><div class="legend-color" style="background:#e8f5e9;border:2px solid #2e7d32"></div> Seed Router</div>
            <div class="legend-item"><div class="legend-color" style="background:#e3f2fd;border:2px solid #1565c0"></div> MikroTik / MNDP</div>
            <div class="legend-item"><div class="legend-color" style="background:#f3e5f5;border:2px solid #7b1fa2"></div> Ubiquiti</div>
            <div class="legend-item"><div class="legend-color" style="background:#e0f7fa;border:2px solid #00838f"></div> OSPF</div>
            <div class="legend-item"><div class="legend-color" style="background:#fff3e0;border:2px solid #ef6c00"></div> ARP</div>
            <div class="legend-item"><div class="legend-color" style="background:#ffebee;border:2px solid #c62828"></div> Unreachable</div>
            <div class="legend-item"><div class="legend-color" style="background:#fafafa;border:2px solid #666"></div> Unknown</div>
        </div>
        <div class="preview">
            <img src="{img_url}" alt="Network Topology">
        </div>
        <h3 style="color:#7b2cbf">Código D2</h3>
        <pre>{d2_code}</pre>
    </div>
</body>
</html>'''


# === DEVICE SELECTION ===

def get_devices_from_db() -> List[Dict]:
    """Get routers and APs from uManager database with Zone info."""
    devices = []
    try:
        routers = get_routers_for_backup()
        for r in routers:
            devices.append({
                "type": "Router",
                "host": r["host"],
                "hostname": r.get("hostname") or r["host"],
                "model": "RouterOS", # get_routers_for_backup doesn't assume model, maybe add query if needed
                "username": r["username"],
                "password": r["password"],
                "port": 8729, # Default as backup query might not have it
                "zona_nombre": r.get("zona_nombre", "Default")
            })
    except Exception as e:
        print(f"  ⚠ Could not load routers from DB: {e}")
    
    try:
        # filter for Mikrotik APs if needed, or just all
        aps = get_all_aps_with_stats()
        for a in aps:
            if a.get("vendor") == "mikrotik":
                creds = get_ap_by_host_with_stats(a["host"]) # To get credentials
                if not creds: continue
                
                # decrypt if needed (get_ap_by using context might handle it? 
                # actually get_ap_by_host_with_stats returns dict but passwords might be encrypted if not handled)
                # Let's check db logic. 
                # aps_db.get_ap_by_host_with_stats DOES NOT decrypt explicitly in the SQL, 
                # but let's assume we need to handle it or use get_ap_credentials logic.
                from app.utils.security import decrypt_data
                password = creds.get("password")
                try:
                    password = decrypt_data(password)
                except:
                    pass

                devices.append({
                    "type": "AP",
                    "host": a["host"],
                    "hostname": a.get("hostname") or a["host"],
                    "model": a.get("model", ""),
                    "username": creds.get("username"),
                    "password": password,
                    "port": a.get("api_port") or 8729,
                    "zona_nombre": a.get("zona_nombre", "Default")
                })
    except Exception as e:
        print(f"  ⚠ Could not load APs from DB: {e}")
    
    return devices


def select_device() -> Dict:
    """Show device selection menu."""
    print("\n📋 Device Selection")
    print("-" * 40)
    
    devices = get_devices_from_db()
    
    if devices:
        print("\nDevices from uManager database:")
        for i, d in enumerate(devices, 1):
            print(f"  [{i}] {d['type']:6} | {d['hostname']:20} | {d['host']}")
        print(f"  [{len(devices)+1}] Enter IP manually")
        
        choice = input(f"\nSelect [1-{len(devices)+1}]: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(devices):
                return devices[idx]
        except ValueError:
            pass
    
    # Manual entry
    print("\nManual connection:")
    return {
        "host": input("Router IP: ").strip(),
        "username": input("Username: ").strip(),
        "password": getpass.getpass("Password: "),
        "port": int(input("API-SSL Port [8729]: ").strip() or "8729"),
    }


def select_sources() -> List[str]:
    """Show discovery source selection menu."""
    print("\n📡 Discovery Sources")
    print("-" * 40)
    print("  [1] MNDP/LLDP only (neighbors)")
    print("  [2] ARP table only")
    print("  [3] OSPF neighbors only")
    print("  [4] All sources combined")
    print("  [5] RECURSIVE (all sources, follow neighbors)")
    
    choice = input("\nSelect [1-5]: ").strip()
    
    if choice == "1":
        return ["mndp"], False
    elif choice == "2":
        return ["arp"], False
    elif choice == "3":
        return ["ospf"], False
    elif choice == "5":
        return ["mndp", "arp", "ospf"], True  # Recursive mode
    else:
        return ["mndp", "arp", "ospf"], False


# === MAIN ===

def main():
    print("=" * 50)
    print("  Network Discovery & D2 Mapping Tool")
    print("=" * 50)
    
    # Select device
    device = select_device()
    
    # Select sources (returns tuple: sources, is_recursive)
    sources, is_recursive = select_sources()
    
    if is_recursive:
        # === RECURSIVE MODE ===
        max_depth_str = input("\nMax depth [3]: ").strip()
        max_depth = int(max_depth_str) if max_depth_str else 3
        
        max_nodes_str = input("Max nodes [50]: ").strip()
        max_nodes = int(max_nodes_str) if max_nodes_str else 50
        
        topology = recursive_discover(
            device["host"], device["username"], device["password"], device.get("port", 8729),
            sources, max_depth, max_nodes
        )
        
        d2_code = generate_d2_recursive(topology)
        title = f"Network Map (Recursive) - {topology['nodes'][0]['identity'] if topology['nodes'] else 'Unknown'}"
        
    else:
        # === NORMAL MODE ===
        print(f"\n🔌 Connecting to {device['host']}...")
        try:
            api = connect_router(device["host"], device["username"], device["password"], device.get("port", 8729))
            print("✓ Connected")
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return
        
        identity = get_router_identity(api)
        info = get_router_info(api)
        print(f"✓ Identity: {identity} ({info.get('board', 'Unknown')})")
        
        print("\n🔍 Discovering devices...")
        all_devices = []
        
        if "mndp" in sources:
            print("  → MNDP/LLDP...")
            mndp = get_neighbors(api)
            print(f"    Found {len(mndp)} neighbor(s)")
            all_devices.extend(mndp)
        
        if "arp" in sources:
            print("  → ARP table...")
            arp = get_arp_table(api)
            print(f"    Found {len(arp)} entries")
            all_devices.extend(arp)
        
        if "ospf" in sources:
            print("  → OSPF neighbors...")
            ospf = get_ospf_neighbors(api)
            print(f"    Found {len(ospf)} peers")
            all_devices.extend(ospf)
        
        # Remove duplicates by IP
        seen_ips = set()
        unique = []
        for d in all_devices:
            key = d["ip_address"] or d["mac_address"]
            if key and key not in seen_ips:
                seen_ips.add(key)
                unique.append(d)
        
        print(f"\n✓ Total unique devices: {len(unique)}")
        
        source_name = "MNDP/LLDP + ARP + OSPF" if len(sources) > 1 else sources[0].upper()
        d2_code = generate_d2_map(identity, info, unique, source_name, device)
        title = f"Network Map - {identity}"
    
    # Save files
    with open("network_map.d2", "w") as f:
        f.write(d2_code)
    print("✓ Saved: network_map.d2")
    
    html = generate_html(d2_code, title)
    with open("network_discovery_map.html", "w") as f:
        f.write(html)
    print("✓ Saved: network_discovery_map.html")
    
    # Open in browser
    try:
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath('network_discovery_map.html')}")
    except:
        pass
    
    print("\n" + "=" * 50)
    print("D2 Code:")
    print("=" * 50)
    print(d2_code)


if __name__ == "__main__":
    main()
