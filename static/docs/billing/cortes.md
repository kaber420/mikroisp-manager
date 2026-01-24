# Gestión de Cortes y Suspensión

uManager automatiza el proceso de suspensión de servicio por falta de pago, ayudándote a mantener tu cartera al día.

## Configuración de Reglas de Corte

Para que el sistema corte automáticamente el servicio, debes definir las reglas en **Settings > Facturación**:

1. **Día de Corte**: Día del mes en que se ejecuta el corte (Ej: día 15).
2. **Días de Gracia**: Días adicionales después del vencimiento antes de cortar.
3. **Acción de Corte**:
    - **Drop**: Bloquea todo el tráfico.
    - **Redirect**: Redirige al cliente a un portal cautivo de "Pago Pendiente".

## Corte Manual

También puedes suspender a un cliente manualmente en cualquier momento:

1. Ve a la ficha del cliente.
2. Haz clic en el botón **"Acciones"**.
3. Selecciona **"Suspender Servicio"**.
4. Confirma la acción.

> [!WARNING]
> Al suspender un servicio manualmente, el cliente no tendrá internet hasta que lo reactives o el sistema detecte un pago (si está configurada la reconexión automática).

## Reactivación

El servicio se reactiva automáticamente cuando:

- Registras un pago que cubre la deuda vencida.
- El cliente paga a través del portal de clientes.

Para reactivar manualmente:

1. Ve a la ficha del cliente.
2. Haz clic en **"Reactivar Servicio"**.
