# app/services/monitoring/autodoc_service.py
import logging
import hashlib
import json
from datetime import datetime
from typing import Any, Optional
from sqlmodel import Session, select

from app.models.zona import Zona, ZonaAutodoc
from app.models.router import Router
from app.models.switch import Switch
from app.utils.security import decrypt_data
from app.services.network.router_service import RouterService
from app.services.network.infrastructure_service import get_device_infrastructure_data
from app.utils.cache import cache_manager

logger = logging.getLogger("AutodocService")


async def sync_zona_autodoc(zona_id: int, session: Session) -> dict[str, Any]:
    """
    Sincroniza y consolida la autodocumentación física y lógica de una Zona (PoP).
    1. Obtiene routers y switches asignados a la zona.
    2. Conecta a los dispositivos para extraer interfaces, VLANs y bridges (estáticos).
    3. Recupera estadísticas dinámicas desde la caché de Redict (CPU, uptime, etc.).
    4. Genera una ficha técnica premium consolidada en Markdown.
    5. Guarda el JSON unificado de puertos y el Markdown en base de datos, optimizando escrituras mediante hashes SHA256.
    """
    logger.info(f"🔄 Iniciando sincronización de autodocumentación para Zona {zona_id}...")
    
    zona = session.get(Zona, zona_id)
    if not zona:
        raise ValueError(f"Zona con id {zona_id} no encontrada.")

    # 1. Obtener routers y switches activos asignados a la zona
    routers = session.exec(
        select(Router).where(Router.zona_id == zona_id).where(Router.is_enabled == True)
    ).all()
    
    switches = session.exec(
        select(Switch).where(Switch.zona_id == zona_id).where(Switch.is_enabled == True)
    ).all()

    ports_layout = []

    # 2. Conectar a los Routers y extraer estructura + fusionar caché
    for r in routers:
        device_data = {
            "host": r.host,
            "hostname": r.hostname or r.host,
            "model": r.model or "Router MikroTik",
            "type": "router",
            "status": "offline",
            "ports": []
        }
        
        # Recuperar estadísticas en tiempo real desde Redict
        stats_store = cache_manager.get_store("router_stats")
        cached_stats = await stats_store.get_async(r.host) if stats_store else None

        # Sincronización de puertos en vivo mediante API-SSL
        if r.is_provisioned and r.api_port == r.api_ssl_port:
            try:
                decrypted_password = decrypt_data(r.password)
                service = RouterService(r.host, r, decrypted_password)
                try:
                    # Ejecutar la llamada MikroTik de forma síncrona/hilo para no bloquear
                    import asyncio
                    def do_mikrotik_call():
                        api = service.get_api_client()
                        return get_device_infrastructure_data(
                            api=api,
                            host=r.host,
                            hostname=r.hostname or r.host,
                            model=r.model or "MikroTik"
                        )
                    
                    infra = await asyncio.to_thread(do_mikrotik_call)
                    device_data["ports"] = infra.get("ports", [])
                    device_data["status"] = "online"
                finally:
                    service.disconnect()
            except Exception as e:
                logger.error(f"⚠️ Error extrayendo estructura del Router {r.host}: {e}")

        # Integrar métricas dinámicas de Redict
        if cached_stats:
            device_data["uptime"] = cached_stats.get("uptime", "N/A")
            device_data["cpu_load"] = cached_stats.get("cpu_load", "N/A")
            device_data["temperature"] = cached_stats.get("temperature")
            device_data["voltage"] = cached_stats.get("voltage")
            device_data["free_memory"] = cached_stats.get("free_memory")
            device_data["total_memory"] = cached_stats.get("total_memory")
            
            # Si el monitor tiene datos de uptime recientes, marcar online si falló API estructural
            if device_data["status"] == "offline" and cached_stats.get("uptime"):
                device_data["status"] = "online"

        ports_layout.append(device_data)

    # 3. Conectar a los Switches y extraer estructura + fusionar caché
    for s in switches:
        device_data = {
            "host": s.host,
            "hostname": s.hostname or s.host,
            "model": s.model or "Switch MikroTik",
            "type": "switch",
            "status": "offline",
            "ports": []
        }
        
        # Recuperar estadísticas en tiempo real desde Redict
        stats_store = cache_manager.get_store("switch_stats")
        cached_stats = await stats_store.get_async(s.host) if stats_store else None

        if s.is_provisioned:
            try:
                from app.services.network.switch_service import get_switch_service
                service = get_switch_service(s.host)
                try:
                    import asyncio
                    def do_switch_call():
                        api = service.get_api_client()
                        return get_device_infrastructure_data(
                            api=api,
                            host=s.host,
                            hostname=s.hostname or s.host,
                            model=s.model or "MikroTik"
                        )
                    
                    infra = await asyncio.to_thread(do_switch_call)
                    device_data["ports"] = infra.get("ports", [])
                    device_data["status"] = "online"
                finally:
                    service.disconnect()
            except Exception as e:
                logger.error(f"⚠️ Error extrayendo estructura del Switch {s.host}: {e}")

        # Integrar métricas dinámicas de Redict
        if cached_stats:
            device_data["uptime"] = cached_stats.get("uptime", "N/A")
            device_data["cpu_load"] = cached_stats.get("cpu_load", "N/A")
            device_data["temperature"] = cached_stats.get("temperature")
            device_data["voltage"] = cached_stats.get("voltage")
            
            if device_data["status"] == "offline" and cached_stats.get("uptime"):
                device_data["status"] = "online"

        ports_layout.append(device_data)

    # 4. Autogeneración de Ficha Técnica en Markdown
    md = []
    md.append(f"# 🗄️ Ficha Técnica Autogenerada de PoP: {zona.nombre}")
    md.append(f"*Sincronizado el:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    md.append("---")
    
    md.append("\n## 🌐 Información General del PoP")
    if zona.direccion:
        md.append(f"- **📍 Dirección:** {zona.direccion}")
    if zona.coordenadas_gps:
        md.append(f"- **🧭 Coordenadas GPS:** `{zona.coordenadas_gps}`")
    md.append(f"- **🖥️ Equipos de Red Habilitados:** {len(routers) + len(switches)}")
    
    # Detallar puertos por dispositivo
    for device in ports_layout:
        md.append(f"\n## 🔌 Dispositivo: {device['hostname']} ({device['host']})")
        md.append(f"- **Tipo:** {device['type'].upper()}")
        md.append(f"- **Modelo:** {device['model']}")
        status_str = "🟢 ONLINE" if device["status"] == "online" else "🔴 OFFLINE"
        md.append(f"- **Estado de Enlace:** {status_str}")
        
        if "uptime" in device:
            md.append(f"- **Tiempo de Actividad:** `{device['uptime']}`")
        if "cpu_load" in device and device["cpu_load"] != "N/A":
            md.append(f"- **Carga de CPU:** `{device['cpu_load']}%`")
        if device.get("temperature"):
            md.append(f"- **Temperatura:** `{device['temperature']} °C`")
        if device.get("voltage"):
            md.append(f"- **Voltaje:** `{device['voltage']} V`")

        if device["ports"]:
            md.append("\n### 📋 Cuadrícula de Interfaces Físicas")
            md.append("\n| Puerto | Estado | Velocidad | PoE | VLANs | Comentario |")
            md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for p in device["ports"]:
                p_status = "🟢 UP" if p.get("running") else "⚪ DOWN"
                if p.get("disabled"):
                    p_status = "❌ DESHABILITADO"
                
                speed = p.get("speed") or "—"
                poe = p.get("poe") or "off"
                vlans_str = ", ".join([f"{v.get('id')}" for v in p.get("vlans", [])]) or "—"
                comment = p.get("comment") or "—"
                
                md.append(f"| **{p['name']}** | {p_status} | {speed} | {poe} | {vlans_str} | {comment} |")
        else:
            md.append("\n*⚠️ No se pudo obtener la estructura física del dispositivo (fuera de línea o sin aprovisionar).*")
        md.append("\n---")
        
    content_markdown = "\n".join(md)

    # 5. Calcular Hash SHA256 para redundancia y control de escrituras
    payload = {
        "markdown": content_markdown,
        "ports": ports_layout
    }
    serialized_payload = json.dumps(payload, sort_keys=True, default=str)
    content_hash = hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()

    # 6. Guardar en Base de Datos (Insert / Update)
    autodoc = session.exec(
        select(ZonaAutodoc).where(ZonaAutodoc.zona_id == zona_id)
    ).first()

    if autodoc:
        if autodoc.content_hash != content_hash:
            autodoc.content_markdown = content_markdown
            autodoc.ports_layout = ports_layout
            autodoc.last_updated = datetime.utcnow()
            autodoc.content_hash = content_hash
            session.add(autodoc)
            session.commit()
            logger.info(f"✅ Autodocumentación de Zona {zona_id} actualizada por cambios.")
        else:
            logger.info(f"ℹ️ Autodocumentación de Zona {zona_id} sin cambios (hash idéntico).")
    else:
        autodoc = ZonaAutodoc(
            zona_id=zona_id,
            content_markdown=content_markdown,
            ports_layout=ports_layout,
            last_updated=datetime.utcnow(),
            content_hash=content_hash
        )
        session.add(autodoc)
        session.commit()
        logger.info(f"✅ Autodocumentación de Zona {zona_id} creada exitosamente.")

    return {
        "zona_id": zona_id,
        "last_updated": autodoc.last_updated,
        "markdown": content_markdown,
        "ports": ports_layout
    }
