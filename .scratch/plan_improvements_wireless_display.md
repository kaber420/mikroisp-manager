# Plan de Mejoras: Visualización de Datos Inalámbricos (MikroTik)

Este documento detalla la propuesta para integrar y visualizar los datos extendidos que extraemos de los equipos MikroTik (v6 y v7).

## 1. Datos Disponibles (Backend)

El sistema ya extrae los siguientes datos directamente del `registration-table`:

| Campo | Origen API | Ejemplo | Estado |
|-------|-----------|---------|--------|
| **Uptime** | `uptime` | `"1h"`, `"52m2s"` | ✅ Extraído |
| **IP Cliente** | `last-ip` + fallback ARP | `192.168.77.253` | ✅ Extraído |
| **Bytes TX/RX** | `bytes` (formato `tx,rx`) | `"370030975,74220760"` | ✅ Extraído y parseado |
| **SNR** | `signal-to-noise` | `"60"`, `"39"` | ✅ Extraído directamente (NO calculado) |
| **Cadenas** | `signal-strength-ch0/ch1` | `"-50"`, `"-40"` | ✅ Extraído |
| **Noise Floor** | `noise-floor` | `"-95"` | ✅ Extraído |
| **CCQ** | `tx-ccq` | `"93"` | ✅ Ya visible en UI |
| **TX/RX Rate** | `tx-rate`, `rx-rate` | `"150Mbps-40MHz/1S/SGI"` | ✅ Ya visible en UI |

> **Nota:** El SNR viene directamente del dispositivo (`signal-to-noise`), no se calcula.

## 2. Propuesta de Visualización (Frontend)

### A. Mejoras en la Tarjeta de Cliente

**Actual:**

```
Signal / Chains: -40 dBm
Noise Floor: N/A dBm
```

**Propuesto:**

```
Señal: -40 dBm (Ch0: -50 / Ch1: -40)
SNR: 60 dB | Ruido: -100 dBm
Uptime: 1h | Bytes: ↓350 MB / ↑70 MB
```

### B. Datos a Agregar en UI

| Dato | Ubicación Propuesta | Prioridad |
|------|---------------------|-----------|
| **SNR** | Junto a la señal o en fila propia | Alta |
| **Cadenas (Ch0/Ch1)** | Paréntesis junto a señal principal | Media |
| **Uptime de conexión** | Nueva fila o badge en esquina | Media |
| **Bytes TX/RX** | Ya existe, solo formatear mejor | Baja |

## 3. Cambios Técnicos

### Backend (Estado Actual)

- [x] `wireless.py`: Extrae `snr` directamente de `signal-to-noise`
- [x] `wireless.py`: Extrae `signal_chain0`, `signal_chain1`
- [x] `wireless.py`: Extrae `noise_floor`
- [x] Adapter: Pasa estos campos a `ConnectedClient`
- [x] API Model: Campo `extra` agregado a `CPEDetail`

### Frontend (Pendiente)

- [ ] `ap_details_mikrotik.js`: Mostrar SNR en `renderCPEExtra()`
- [ ] `ap_details_core.js`: Mostrar cadenas junto a señal
- [ ] Formatear uptime amigable (ej: "2d 4h" en vez de segundos)

## 4. Preguntas Pendientes

1. ¿Mostrar SNR siempre visible o solo en hover/tooltip?
2. ¿Resaltar en rojo clientes con uptime muy bajo (< 5 min) para detectar flapping?
3. ¿Preferencia de diseño para las cadenas: `(Ch0/Ch1)` o iconos?
