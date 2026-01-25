# Gestión de Cortes y Suspensión

uManager automatiza el proceso de suspensión de servicio por falta de pago, ayudándote a mantener tu cartera al día.

### Configuración de Reglas de Corte

Para que el sistema corte automáticamente el servicio, debes definir las reglas en **Settings > Facturación**:

1. **Día de Corte**: Día del mes en que se ejecuta el corte (Ej: día 15).
2. **Días de Gracia**: Días adicionales después del vencimiento antes de cortar.
3. **Acción de Corte**:
    - **Drop**: Bloquea todo el tráfico.
    - **Redirect**: Redirige al cliente a un portal cautivo de "Pago Pendiente".
