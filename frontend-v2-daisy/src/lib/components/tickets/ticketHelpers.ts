import type { Ticket } from "$lib/types/ticket";

// ── Etiquetas de estado ────────────────────────────────────────────────────
export function statusLabel(s: string): string {
    return (
        {
            open: "Abierto",
            pending: "Pendiente",
            resolved: "Resuelto",
            closed: "Cerrado",
        }[s] ?? s
    );
}

export function statusClass(s: string): string {
    return (
        {
            open: "badge-success",
            pending: "badge-warning",
            resolved: "badge-primary",
            closed: "badge-ghost",
        }[s] ?? "badge-ghost"
    );
}

// ── Etiquetas de prioridad ─────────────────────────────────────────────────
export function priorityLabel(p: string): string {
    return (
        { urgent: "Urgente", high: "Alta", normal: "Normal", low: "Baja" }[
            p
        ] ?? p
    );
}

export function priorityClass(p: string): string {
    return (
        {
            urgent: "badge-error",
            high: "badge-warning",
            normal: "badge-info",
            low: "badge-ghost",
        }[p] ?? "badge-ghost"
    );
}

// ── Identificador legible ──────────────────────────────────────────────────
export function getDisplayId(t: Ticket): string {
    if (t.ticket_id && t.ticket_id > 0) return "#" + t.ticket_id;
    return "#" + t.id.slice(-6);
}

// ── Formato de fecha ───────────────────────────────────────────────────────
export function fmtDate(s: string, withTime = false): string {
    if (!s) return "—";
    return new Date(s).toLocaleString("es-MX", withTime
        ? { dateStyle: "medium", timeStyle: "short" }
        : { year: "numeric", month: "short", day: "numeric" }
    );
}
