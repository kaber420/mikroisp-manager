# Análisis: Campos SSID y Banda en CPEs

## Resumen
El usuario quiere ver el **SSID** y la **banda** a la que está conectado cada CPE en la tabla del frontend.

## Confirmación de Disponibilidad (RouterOS v7)
```
/interface/wifi> reg print
#   INTERFACE  SSID       MAC-ADDRESS        SIGNAL  BAND   
0 A wifi2      wifikbr-2  C4:23:60:F8:74:DD  -43     2ghz-ax
1 A wifi2      wifikbr-2  46:73:80:BA:D4:9C  -40     2ghz-ax
```
✅ Los campos `ssid` y `band` están disponibles en la API de MikroTik.

## Problema Identificado
El flujo de datos actual **NO propaga** estos campos al frontend:

| Capa | Archivo | Estado |
|------|---------|--------|
| Extracción | `wireless.py` | `band` en `extra`, `ssid` NO extraído |
| Modelo | `ConnectedClient` | NO tiene `ssid` ni `band` |
| DB Schema | `cpe_stats_history` | NO tiene columnas |
| INSERT | `stats_db.py` | NO inserta estos campos |
| API Model | `CPEGlobalInfo` | NO tiene campos |
| Frontend | `cpes.js` | NO renderiza |

## Solución
Ver `implementation_plan.md` para los cambios detallados en cada capa.
