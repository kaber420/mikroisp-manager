# app/db/zonas_db.py
import os
import sqlite3
from typing import Any

from ..utils.security import decrypt_data, encrypt_data  # <-- LÍNEA CAMBIADA
from .base import get_db_connection

# --- Funciones de Zonas (CRUD Básico) ---


def create_zona(nombre: str) -> dict[str, Any]:
    conn = get_db_connection()
    try:
        cursor = conn.execute("INSERT INTO zonas (nombre) VALUES (?)", (nombre,))
        new_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"El nombre de la zona '{nombre}' ya existe.")
    finally:
        conn.close()
    return {"id": new_id, "nombre": nombre}


def get_all_zonas() -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute("SELECT id, nombre FROM zonas ORDER BY nombre")
    zonas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return zonas


_ZONA_ALLOWED_COLUMNS = frozenset(
    ["nombre", "descripcion", "notas_sensibles", "direccion", "contacto"]
)


def update_zona_details(zona_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
    if not updates:
        return get_zona_by_id(zona_id)

    # Validate column names against whitelist to prevent SQL injection
    invalid_keys = set(updates.keys()) - _ZONA_ALLOWED_COLUMNS
    if invalid_keys:
        raise ValueError(f"Invalid column names: {invalid_keys}")

    conn = get_db_connection()

    if "notas_sensibles" in updates and updates["notas_sensibles"] is not None:
        updates["notas_sensibles"] = encrypt_data(updates["notas_sensibles"])

    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])  # nosec B608
    values = list(updates.values())
    values.append(zona_id)

    try:
        cursor = conn.execute(
            f"UPDATE zonas SET {set_clause} WHERE id = ?",
            tuple(values),  # nosec B608
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("El nombre de la zona ya existe.")
    finally:
        conn.close()
    return get_zona_by_id(zona_id)


def delete_zona(zona_id: int) -> int:
    conn = get_db_connection()
    cursor_check_aps = conn.execute("SELECT 1 FROM aps WHERE zona_id = ?", (zona_id,))
    if cursor_check_aps.fetchone():
        conn.close()
        raise ValueError("No se puede eliminar la zona porque contiene APs.")
    cursor_check_routers = conn.execute("SELECT 1 FROM routers WHERE zona_id = ?", (zona_id,))
    if cursor_check_routers.fetchone():
        conn.close()
        raise ValueError("No se puede eliminar la zona porque contiene Routers.")

    cursor_delete = conn.execute("DELETE FROM zonas WHERE id = ?", (zona_id,))
    conn.commit()
    rowcount = cursor_delete.rowcount
    conn.close()
    return rowcount


def get_zona_by_id(zona_id: int) -> dict[str, Any] | None:
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM zonas WHERE id = ?", (zona_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    if data.get("notas_sensibles"):
        data["notas_sensibles"] = decrypt_data(data["notas_sensibles"])
    return data


# --- Funciones de Infraestructura ---


def get_infra_by_zona_id(zona_id: int) -> dict[str, Any] | None:
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM zona_infraestructura WHERE zona_id = ?", (zona_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


_INFRA_ALLOWED_COLUMNS = frozenset(
    [
        "router_principal",
        "router_respaldo",
        "switch_principal",
        "switch_respaldo",
        "ups_modelo",
        "ups_capacidad",
        "panel_solar",
        "bateria_modelo",
        "bateria_capacidad",
        "rack_tipo",
        "rack_unidades",
        "notas",
    ]
)


def update_or_create_infra(zona_id: int, infra_data: dict[str, Any]) -> dict[str, Any]:
    if not infra_data:
        existing = get_infra_by_zona_id(zona_id)
        return existing if existing else {}

    # Validate column names against whitelist to prevent SQL injection
    invalid_keys = set(infra_data.keys()) - _INFRA_ALLOWED_COLUMNS
    if invalid_keys:
        raise ValueError(f"Invalid column names: {invalid_keys}")

    conn = get_db_connection()
    existing_infra = get_infra_by_zona_id(zona_id)

    if existing_infra:
        set_clause = ", ".join([f"{key} = ?" for key in infra_data.keys()])  # nosec B608
        values = list(infra_data.values())
        values.append(zona_id)
        conn.execute(
            f"UPDATE zona_infraestructura SET {set_clause} WHERE zona_id = ?",  # nosec B608
            tuple(values),
        )
    else:
        columns = ", ".join(infra_data.keys())  # nosec B608
        placeholders = ", ".join(["?"] * len(infra_data))
        values = list(infra_data.values())
        conn.execute(
            f"INSERT INTO zona_infraestructura (zona_id, {columns}) VALUES (?, {placeholders})",  # nosec B608
            (zona_id, *values),
        )

    conn.commit()
    conn.close()
    return get_infra_by_zona_id(zona_id)


# --- Funciones de Documentos ---


def get_docs_by_zona_id(zona_id: int) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT * FROM zona_documentos WHERE zona_id = ? ORDER BY creado_en DESC",
        (zona_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def add_document(doc_data: dict[str, Any]) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.execute(
        """INSERT INTO zona_documentos (zona_id, tipo, nombre_original, nombre_guardado, descripcion)
           VALUES (?, ?, ?, ?, ?)""",
        (
            doc_data["zona_id"],
            doc_data["tipo"],
            doc_data["nombre_original"],
            doc_data["nombre_guardado"],
            doc_data["descripcion"],
        ),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    new_doc = get_document_by_id(new_id)
    if not new_doc:
        raise ValueError("No se pudo recuperar el documento después de la creación.")
    return new_doc


def get_document_by_id(doc_id: int) -> dict[str, Any] | None:
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM zona_documentos WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_document(doc_id: int) -> int:
    doc_info = get_document_by_id(doc_id)
    if doc_info:
        file_path = os.path.join(
            "uploads", "zonas", str(doc_info["zona_id"]), doc_info["nombre_guardado"]
        )
        if os.path.exists(file_path):
            os.remove(file_path)

    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM zona_documentos WHERE id = ?", (doc_id,))
    rowcount = cursor.rowcount
    conn.commit()
    conn.close()
    return rowcount


# --- Funciones de Notas ---


def create_note(zona_id: int, title: str, content: str, is_encrypted: bool) -> dict[str, Any]:
    conn = get_db_connection()

    final_content = encrypt_data(content) if is_encrypted else content

    cursor = conn.execute(
        """INSERT INTO zona_notes (zona_id, title, content, is_encrypted)
           VALUES (?, ?, ?, ?)""",
        (zona_id, title, final_content, is_encrypted),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    new_note = get_note_by_id(new_id)
    if not new_note:
        raise ValueError("Could not retrieve note after creation.")
    return new_note


def get_note_by_id(note_id: int) -> dict[str, Any] | None:
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM zona_notes WHERE id = ?", (note_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None

    data = dict(row)
    if data["is_encrypted"] and data["content"]:
        data["content"] = decrypt_data(data["content"])
    return data


def get_notes_by_zona_id(zona_id: int) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT * FROM zona_notes WHERE zona_id = ? ORDER BY updated_at DESC",
        (zona_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    for row in rows:
        if row["is_encrypted"] and row["content"]:
            row["content"] = decrypt_data(row["content"])

    return rows


def update_note(
    note_id: int, title: str, content: str, is_encrypted: bool
) -> dict[str, Any] | None:
    conn = get_db_connection()

    final_content = encrypt_data(content) if is_encrypted else content

    cursor = conn.execute(
        """UPDATE zona_notes SET title = ?, content = ?, is_encrypted = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (title, final_content, is_encrypted, note_id),
    )
    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        return None

    conn.close()
    return get_note_by_id(note_id)


def delete_note(note_id: int) -> int:
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM zona_notes WHERE id = ?", (note_id,))
    rowcount = cursor.rowcount
    conn.commit()
    conn.close()
    return rowcount
