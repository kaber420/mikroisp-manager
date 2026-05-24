# 🗄️ Arquitectura de Autodocumentación y Visualización de PoPs (Híbrida: BD + CSS Grid)

Este documento describe la arquitectura técnica propuesta para el sistema de autodocumentación y visualización física de puertos en los **PoPs (Zonas)** de OmniWISP.

El diseño se fundamenta en un modelo **híbrido y asíncrono**:
* **Persistencia Física en BD:** Almacenamiento local precalculado para respuesta instantánea.
* **Cero Consultas en Vivo:** Evita timeouts y degradación de CPU en MikroTik durante el monitoreo habitual.
* **Visualización Dual:** Ficha técnica estructurada en **Markdown** (para lectura/exportación) y cuadrícula interactiva de puertos en **CSS Grid** (para diagnóstico en la web).

---

## 🎯 1. Principios del Diseño

1. **Eficiencia Extrema:** Toda la recolección de configuraciones pesadas (VLANs, bridges, interfaces) se realiza de forma pasiva y bajo demanda, no en bucles recurrentes de red.
2. **Carga Pasiva Instantánea:** La interfaz de usuario nunca espera a que un router responda; lee directamente un registro plano de la base de datos de OmniWISP.
3. **Fusión en Memoria:** Combina los datos de estructura física (estáticos en la base de datos) con el estado de enlace y uso de red (dinámicos en caché de Redict) al momento de guardar.

---

## 💾 2. Esquema de Base de Datos (SQLModel)

Se propone la creación de una nueva tabla relacional en la base de datos de OmniWISP: **`ZonaAutodoc`** (conectada por clave foránea única de uno a uno con la tabla `Zona`).

```python
# app/models/zona_autodoc.py
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

class ZonaAutodoc(SQLModel, table=True):
    __tablename__ = "zona_autodocumentacion"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relación uno-a-uno única con la Zona
    zona_id: int = Field(foreign_key="zonas.id", unique=True, index=True, nullable=False)
    
    # Campo 1: Ficha Técnica consolidada en Markdown
    content_markdown: str = Field(
        nullable=False, 
        description="Ficha técnica de texto Markdown autogenerada para el PoP"
    )
    
    # Campo 2: Estructura de puertos físicos y VLANs consolidada en JSON
    ports_layout: Optional[list[dict[str, Any]]] = Field(
        default=None, 
        sa_column=Column(JSON),
        description="Lista de puertos con su estado, velocidad, PoE y VLANs"
    )
    
    # Auditoría e integridad
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Fecha y hora de la última actualización"
    )
    content_hash: str = Field(
        nullable=False, 
        description="Hash SHA256 del contenido para control de redundancia"
    )

    # Relación inversa
    # zona: Optional["Zona"] = Relationship(back_populates="autodoc")
```

---

## ⚙️ 3. Flujo de Trabajo y Ciclo de Vida del Dato

El sistema divide la recolección de información en dos categorías de datos:

### A. Datos Estructurales (Frecuencia: Estática / Bajo Demanda)
Se refiere a los puertos físicos, bridges y VLANs asociadas. Esta configuración cambia muy rara vez.
* Se lee **una sola vez** mediante `get_device_infrastructure_data` cuando:
  1. El dispositivo es agregado al sistema.
  2. El dispositivo se aprovisiona exitosamente con API-SSL.
  3. El administrador o técnico hace clic manual en el botón **"🔄 Sincronizar Estructura de Puertos"** tras realizar cambios físicos o lógicos en el router/switch.

### B. Datos Dinámicos (Frecuencia: Cada Verificación de Monitor)
Se refiere al estado de enlace (UP/DOWN), tasas de transferencia actuales, voltajes, temperaturas y tiempo de actividad.
* Se extrae en tiempo real de la RAM a través de los almacenes de caché existentes de Redict (`router_stats`, `ap_stats` y `switch_stats`) actualizados periódicamente por los Schedulers del monitor principal.

### C. Proceso de Consolidación (Worker asíncrono)
Cuando expira el temporizador de ciclo o se detecta un evento de cambio de estado crítico:
1. El backend levanta en memoria la estructura del PoP.
2. Lee los datos en Redict.
3. Fusiona ambos conjuntos.
4. Genera el Markdown y el JSON de puertos.
5. Compara el Hash SHA256 resultante con el campo `content_hash` en la base de datos.
6. **Si el hash es diferente**, ejecuta una escritura `UPDATE`/`INSERT` física en la tabla `zona_autodocumentacion`. Si es idéntico, no hace nada (previniendo el desgaste de I/O en disco).

---

## 🌐 4. Definición de Endpoints en la API (`app/api/zonas/infra.py`)

Con este modelo de base de datos persistente, las APIs se vuelven extremadamente directas, rápidas y seguras:

```python
# En app/api/zonas/infra.py

@router.get("/zonas/{zona_id}/autodoc", response_model=dict[str, Any])
def get_pop_autodocumentation(
    zona_id: int,
    session: Session = Depends(get_sync_session),
    current_user: User = Depends(require_technician)
):
    """
    Retorna la ficha técnica precalculada del PoP en Markdown y JSON.
    Carga instantánea sin queries de red a dispositivos.
    """
    autodoc = session.exec(
        select(ZonaAutodoc).where(ZonaAutodoc.zona_id == zona_id)
    ).first()
    
    if not autodoc:
        raise HTTPException(
            status_code=404, 
            detail="Ficha técnica no encontrada. Presione 'Sincronizar estructura'."
        )
        
    return {
        "zona_id": autodoc.zona_id,
        "last_updated": autodoc.last_updated,
        "markdown": autodoc.content_markdown,
        "ports": autodoc.ports_layout or []
    }

@router.post("/zonas/{zona_id}/autodoc/sync", status_code=202)
def trigger_manual_autodoc_sync(
    zona_id: int,
    current_user: User = Depends(require_technician)
):
    """
    Forzar una sincronización estructural única sobre el dispositivo físico.
    Útil después de cablear un puerto o configurar una VLAN en MikroTik.
    """
    # Llama a la tarea asíncrona para no bloquear el HTTP request del usuario
    from ...services.tasks import task_force_autodoc_sync
    task_force_autodoc_sync.delay(zona_id)
    return {"message": "Sincronización estructural iniciada en segundo plano."}
```

---

## 🎨 5. Estrategia Visual Dual en el Frontend (Svelte)

La interfaz en Svelte utilizará el mismo payload JSON devuelto por la API para renderizar las dos vistas optimizadas:

### Vista A: Pestaña "Notas y Documentación" (Visualización Markdown)
Ideal para imprimir o tener reportes limpios del estado de la zona.
* **Componente:** Renderiza el campo `.markdown` utilizando un parseador HTML ligero en Svelte.

### Vista B: Pestaña "Infraestructura de Red" (Visualización de Puertos CSS)
Renderiza una cuadrícula de puertos interactiva a través de componentes puros en CSS Grid.

#### Ejemplo del JSON devuelto en `.ports` para el Frontend:
```json
[
  {
    "name": "ether1-WAN",
    "status": "up",
    "speed": "1 Gbps",
    "poe": "off",
    "vlans": [{"id": "100", "name": "VLAN_WAN_ISP"}],
    "comment": "Enlace Fibra Principal"
  },
  {
    "name": "ether2-AP-Norte",
    "status": "up",
    "speed": "100 Mbps",
    "poe": "auto-on",
    "vlans": [{"id": "10", "name": "VLAN_Clientes"}],
    "comment": "Sectorial Norte (Cambiar cable!)"
  },
  {
    "name": "ether3-Libre",
    "status": "down",
    "speed": "—",
    "poe": "off",
    "vlans": [],
    "comment": "Disponible para expansión"
  }
]
```

#### Maquetación del CSS Grid Responsivo en el Componente:
* Se define un contenedor flex-box o grid simple con DaisyUI:
  ```html
  <div class="grid grid-cols-4 sm:grid-cols-8 gap-2 bg-base-100 p-4 rounded-box">
    {#each autodoc.ports as port}
      <div class="tooltip" data-tip="{port.name} - {port.comment || 'Sin Comentario'}">
        <div class="flex flex-col items-center justify-center p-2 border rounded-md {getPortColor(port)}">
          <span class="font-bold text-xs uppercase">{port.name.slice(0, 5)}</span>
          <span class="text-[9px] opacity-85">{port.speed}</span>
        </div>
      </div>
    {/each}
  </div>
  ```

---

## 🏆 6. Ventajas Técnicas y de Negocio de este Modelo

1. **Cero Sobrecarga de Servidor:** Las peticiones en el panel web solo ejecutan una lectura secuencial rápida a la base de datos SQLite o PostgreSQL local. El consumo es prácticamente nulo.
2. **Resiliencia ante Caídas:** Si una tormenta o corte eléctrico tumba un PoP entero, la última ficha técnica e inventario de puertos de la zona siguen estando disponibles en OmniWISP. El técnico puede revisar cómo estaba cableada la infraestructura antes del apagón.
3. **Mantenimiento Simplificado:** Al no haber código SVG ni lógica gráfica compleja en el backend, cualquier desarrollador puede entender, modificar o ampliar el sistema en minutos.
