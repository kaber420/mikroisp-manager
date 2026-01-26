# app/db/init_db.py
import sqlite3

from .base import get_db_connection, get_stats_db_file


def setup_databases():
    print("Configurando la base de datos de inventario (inventory.sqlite)...")
    _setup_inventory_db()
    print("Configurando la base de datos de estadísticas mensuales...")
    _setup_stats_db()
    print("Configuración de bases de datos completada.")


def _setup_inventory_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Tabla de Configuración ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """
    )

    default_settings = [
        ("company_name", "Mi ISP"),
        ("notification_email", "isp@example.com"),
        ("billing_alert_days", "3"),
        ("currency_symbol", "$"),
        ("telegram_bot_token", ""),
        ("telegram_chat_id", ""),
        ("client_bot_token", ""),
        ("days_before_due", "5"),
        ("default_monitor_interval", "300"),
        ("dashboard_refresh_interval", "5"),
        ("suspension_run_hour", "02:00"),
        ("db_backup_run_hour", "04:00"),
        ("cpe_stale_cycles", "3"),  # Number of cycles to wait before marking CPE offline
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", default_settings
    )

    # --- Tablas de Usuarios ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, hashed_password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'admin',
        telegram_chat_id TEXT, receive_alerts BOOLEAN NOT NULL DEFAULT FALSE,
        receive_device_down_alerts BOOLEAN NOT NULL DEFAULT FALSE,
        receive_announcements BOOLEAN NOT NULL DEFAULT FALSE, disabled BOOLEAN NOT NULL DEFAULT FALSE
    )
    """
    )

    # --- MIGRACIÓN DE USUARIOS (CORRECCIÓN) ---
    # Verifica si faltan columnas en la tabla users y las agrega si es necesario
    user_columns = [col[1] for col in cursor.execute("PRAGMA table_info(users)").fetchall()]

    if "telegram_chat_id" not in user_columns:
        print("Migrando users: Agregando telegram_chat_id...")
        cursor.execute("ALTER TABLE users ADD COLUMN telegram_chat_id TEXT;")

    if "receive_alerts" not in user_columns:
        print("Migrando users: Agregando receive_alerts...")
        cursor.execute(
            "ALTER TABLE users ADD COLUMN receive_alerts BOOLEAN NOT NULL DEFAULT FALSE;"
        )

    if "receive_device_down_alerts" not in user_columns:
        print("Migrando users: Agregando receive_device_down_alerts...")
        cursor.execute(
            "ALTER TABLE users ADD COLUMN receive_device_down_alerts BOOLEAN NOT NULL DEFAULT FALSE;"
        )

    if "receive_announcements" not in user_columns:
        print("Migrando users: Agregando receive_announcements...")
        cursor.execute(
            "ALTER TABLE users ADD COLUMN receive_announcements BOOLEAN NOT NULL DEFAULT FALSE;"
        )

    if "disabled" not in user_columns:
        print("Migrando users: Agregando disabled...")
        cursor.execute("ALTER TABLE users ADD COLUMN disabled BOOLEAN NOT NULL DEFAULT FALSE;")

    # --- Tablas de Zonas ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS zonas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        rack_layout TEXT
    )
    """
    )

    zona_columns = [col[1] for col in cursor.execute("PRAGMA table_info(zonas)").fetchall()]
    if "direccion" not in zona_columns:
        cursor.execute("ALTER TABLE zonas ADD COLUMN direccion TEXT;")
    if "coordenadas_gps" not in zona_columns:
        cursor.execute("ALTER TABLE zonas ADD COLUMN coordenadas_gps TEXT;")
    if "notas_generales" not in zona_columns:
        cursor.execute("ALTER TABLE zonas ADD COLUMN notas_generales TEXT;")
    if "notas_sensibles" not in zona_columns:
        cursor.execute("ALTER TABLE zonas ADD COLUMN notas_sensibles TEXT;")

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS zona_documentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, zona_id INTEGER NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN ('image', 'document', 'diagram')),
        nombre_original TEXT NOT NULL, nombre_guardado TEXT NOT NULL UNIQUE,
        descripcion TEXT, creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (zona_id) REFERENCES zonas(id) ON DELETE CASCADE
    );
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS zona_infraestructura (
        id INTEGER PRIMARY KEY AUTOINCREMENT, zona_id INTEGER NOT NULL UNIQUE,
        direccion_ip_gestion TEXT, gateway_predeterminado TEXT, servidores_dns TEXT,
        vlans_utilizadas TEXT, equipos_criticos TEXT, proximo_mantenimiento DATE,
        FOREIGN KEY (zona_id) REFERENCES zonas(id) ON DELETE CASCADE
    );
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS zona_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        zona_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT,
        is_encrypted BOOLEAN NOT NULL DEFAULT FALSE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (zona_id) REFERENCES zonas(id) ON DELETE CASCADE
    );
    """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_zona_notes_zona_id ON zona_notes (zona_id);")

    # --- Tablas de Routers y Planes ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS routers (
        host TEXT PRIMARY KEY, api_port INTEGER DEFAULT 8728, api_ssl_port INTEGER DEFAULT 8729,
        username TEXT NOT NULL, password TEXT NOT NULL, zona_id INTEGER, is_enabled BOOLEAN DEFAULT TRUE,
        hostname TEXT, model TEXT, firmware TEXT, last_status TEXT, last_checked DATETIME,
        FOREIGN KEY (zona_id) REFERENCES zonas (id) ON DELETE SET NULL
    )
    """
    )

    # --- Tabla de Switches ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS switches (
        host TEXT PRIMARY KEY, 
        api_port INTEGER DEFAULT 8728, 
        api_ssl_port INTEGER DEFAULT 8729,
        username TEXT NOT NULL, 
        password TEXT NOT NULL, 
        zona_id INTEGER, 
        is_enabled BOOLEAN DEFAULT TRUE,
        is_provisioned BOOLEAN DEFAULT FALSE,
        hostname TEXT, 
        model TEXT, 
        firmware TEXT, 
        mac_address TEXT,
        location TEXT,
        notes TEXT,
        last_status TEXT, 
        last_checked DATETIME,
        FOREIGN KEY (zona_id) REFERENCES zonas (id) ON DELETE SET NULL
    )
    """
    )

    # --- Migration: Add is_provisioned column to switches table ---
    switch_columns = [col[1] for col in cursor.execute("PRAGMA table_info(switches)").fetchall()]
    if "is_provisioned" not in switch_columns:
        print("Migrando switches: Agregando is_provisioned...")
        cursor.execute("ALTER TABLE switches ADD COLUMN is_provisioned BOOLEAN DEFAULT FALSE;")
        # Smart default: Mark switches where api_port == api_ssl_port as already provisioned
        cursor.execute("UPDATE switches SET is_provisioned = TRUE WHERE api_port = api_ssl_port;")
        print("  -> Switches con api_port == api_ssl_port marcados como aprovisionados.")

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        router_host TEXT NOT NULL,
        name TEXT NOT NULL,
        max_limit TEXT NOT NULL,
        parent_queue TEXT,
        comment TEXT,
        FOREIGN KEY (router_host) REFERENCES routers (host) ON DELETE CASCADE,
        UNIQUE(router_host, name)
    )
    """
    )

    # --- Dispositivos y Clientes ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS aps (
        host TEXT PRIMARY KEY, username TEXT NOT NULL, password TEXT NOT NULL, zona_id INTEGER,
        is_enabled BOOLEAN DEFAULT TRUE, monitor_interval INTEGER, mac TEXT, hostname TEXT, model TEXT, 
        firmware TEXT, last_status TEXT, first_seen DATETIME, last_seen DATETIME, last_checked DATETIME,
        FOREIGN KEY (zona_id) REFERENCES zonas (id) ON DELETE SET NULL
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, address TEXT, phone_number TEXT,
        whatsapp_number TEXT, email TEXT, telegram_contact TEXT, coordinates TEXT, notes TEXT,
        service_status TEXT NOT NULL DEFAULT 'active', billing_day INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS cpes (
        mac TEXT PRIMARY KEY, hostname TEXT, model TEXT, firmware TEXT, ip_address TEXT, client_id INTEGER,
        first_seen DATETIME, last_seen DATETIME, status TEXT DEFAULT 'offline',
        FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE SET NULL
    )
    """
    )

    # --- Migration: Add status column to cpes table ---
    cpe_columns = [col[1] for col in cursor.execute("PRAGMA table_info(cpes)").fetchall()]
    if "status" not in cpe_columns:
        print("Migrando cpes: Agregando status...")
        cursor.execute("ALTER TABLE cpes ADD COLUMN status TEXT DEFAULT 'offline';")

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS client_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, router_host TEXT NOT NULL,
        service_type TEXT NOT NULL DEFAULT 'pppoe', pppoe_username TEXT UNIQUE, router_secret_id TEXT,
        profile_name TEXT, suspension_method TEXT NOT NULL, 
        plan_id INTEGER, ip_address TEXT, 
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
        FOREIGN KEY (router_host) REFERENCES routers(host) ON DELETE SET NULL

    )
    """
    )

    service_columns = [
        col[1] for col in cursor.execute("PRAGMA table_info(client_services)").fetchall()
    ]
    if "plan_id" not in service_columns:
        cursor.execute("ALTER TABLE client_services ADD COLUMN plan_id INTEGER;")
    if "ip_address" not in service_columns:
        cursor.execute("ALTER TABLE client_services ADD COLUMN ip_address TEXT;")

    # --- Migración de Plans: nuevos campos para unificar PPPoE y Simple Queue ---
    plan_columns = [col[1] for col in cursor.execute("PRAGMA table_info(plans)").fetchall()]
    if "plan_type" not in plan_columns:
        print("Migrando plans: Agregando plan_type...")
        cursor.execute("ALTER TABLE plans ADD COLUMN plan_type TEXT DEFAULT 'simple_queue';")
    if "profile_name" not in plan_columns:
        print("Migrando plans: Agregando profile_name...")
        cursor.execute("ALTER TABLE plans ADD COLUMN profile_name TEXT;")
    if "suspension_method" not in plan_columns:
        print("Migrando plans: Agregando suspension_method...")
        cursor.execute("ALTER TABLE plans ADD COLUMN suspension_method TEXT DEFAULT 'queue_limit';")
    if "address_list_strategy" not in plan_columns:
        print("Migrando plans: Agregando address_list_strategy...")
        cursor.execute(
            "ALTER TABLE plans ADD COLUMN address_list_strategy TEXT DEFAULT 'blacklist';"
        )
    if "address_list_name" not in plan_columns:
        print("Migrando plans: Agregando address_list_name...")
        cursor.execute("ALTER TABLE plans ADD COLUMN address_list_name TEXT DEFAULT 'morosos';")

    # --- Migration: Add wan_interface column to routers table ---
    router_columns = [col[1] for col in cursor.execute("PRAGMA table_info(routers)").fetchall()]
    if "wan_interface" not in router_columns:
        print("Migrando routers: Agregando wan_interface...")
        cursor.execute("ALTER TABLE routers ADD COLUMN wan_interface TEXT;")

    # --- Migration: Add is_provisioned column to routers table ---
    if "is_provisioned" not in router_columns:
        print("Migrando routers: Agregando is_provisioned...")
        cursor.execute("ALTER TABLE routers ADD COLUMN is_provisioned BOOLEAN DEFAULT FALSE;")
        # Smart default: Mark routers where api_port == api_ssl_port as already provisioned
        cursor.execute("UPDATE routers SET is_provisioned = TRUE WHERE api_port = api_ssl_port;")
        print("  -> Routers con api_port == api_ssl_port marcados como aprovisionados.")

    # --- Migration: Add provisioning fields to aps table ---
    ap_columns = [col[1] for col in cursor.execute("PRAGMA table_info(aps)").fetchall()]

    if "is_provisioned" not in ap_columns:
        print("Migrando aps: Agregando is_provisioned...")
        cursor.execute("ALTER TABLE aps ADD COLUMN is_provisioned BOOLEAN DEFAULT FALSE;")

    if "api_ssl_port" not in ap_columns:
        print("Migrando aps: Agregando api_ssl_port...")
        cursor.execute("ALTER TABLE aps ADD COLUMN api_ssl_port INTEGER DEFAULT 8729;")

    if "last_provision_attempt" not in ap_columns:
        print("Migrando aps: Agregando last_provision_attempt...")
        cursor.execute("ALTER TABLE aps ADD COLUMN last_provision_attempt DATETIME;")

    if "last_provision_error" not in ap_columns:
        print("Migrando aps: Agregando last_provision_error...")
        cursor.execute("ALTER TABLE aps ADD COLUMN last_provision_error TEXT;")

    # Smart default: Mark MikroTik APs already using SSL port (8729) as provisioned
    cursor.execute("""
        UPDATE aps SET is_provisioned = TRUE 
        WHERE vendor = 'mikrotik' AND api_port = 8729;
    """)
    # Note: This update runs on each startup but is idempotent

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, monto REAL NOT NULL,
        fecha_pago DATETIME DEFAULT CURRENT_TIMESTAMP, mes_correspondiente TEXT NOT NULL,
        metodo_pago TEXT, notas TEXT,
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
    )
    """
    )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_aps_zona ON aps (zona_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpes_ip ON cpes (ip_address);")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_services_client_id ON client_services (client_id);"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pagos_client_id ON pagos (client_id);")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_pagos_mes ON pagos (client_id, mes_correspondiente);"
    )

    conn.commit()
    conn.close()


def _setup_stats_db():
    stats_db_file = get_stats_db_file()
    stats_conn = sqlite3.connect(stats_db_file)
    stats_conn.row_factory = sqlite3.Row
    cursor = stats_conn.cursor()

    # --- HISTORIAL DE APs ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS ap_stats_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME NOT NULL, ap_host TEXT, uptime INTEGER,
        cpuload REAL, freeram INTEGER, client_count INTEGER, noise_floor INTEGER,
        total_throughput_tx INTEGER, total_throughput_rx INTEGER, airtime_total_usage INTEGER,
        airtime_tx_usage INTEGER, airtime_rx_usage INTEGER, frequency INTEGER, chanbw INTEGER,
        essid TEXT, total_tx_bytes INTEGER, total_rx_bytes INTEGER, gps_lat REAL, gps_lon REAL,
        gps_sats INTEGER
    )
    """
    )

    # --- HISTORIAL DE CPEs ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS cpe_stats_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME, ap_host TEXT, cpe_mac TEXT,
        cpe_hostname TEXT, ip_address TEXT, signal INTEGER, signal_chain0 INTEGER, signal_chain1 INTEGER,
        noisefloor INTEGER, cpe_tx_power INTEGER, distance INTEGER, dl_capacity INTEGER, ul_capacity INTEGER,
        airmax_cinr_rx REAL, airmax_usage_rx REAL, airmax_cinr_tx REAL, airmax_usage_tx REAL,
        throughput_rx_kbps INTEGER, throughput_tx_kbps INTEGER, total_rx_bytes INTEGER,
        total_tx_bytes INTEGER, cpe_uptime INTEGER, eth_plugged BOOLEAN, eth_speed INTEGER, eth_cable_len INTEGER
    )
    """
    )

    # --- DESCONEXIONES ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS disconnection_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME, ap_host TEXT, cpe_mac TEXT,
        cpe_hostname TEXT, reason_code INTEGER, connection_duration INTEGER
    )
    """
    )

    # --- NUEVA TABLA: LOGS DE EVENTOS (ROUTERS/APS CAIDOS) ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS event_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_host TEXT NOT NULL,
        device_type TEXT NOT NULL, -- 'router' o 'ap'
        event_type TEXT NOT NULL, -- 'danger', 'success', 'info'
        message TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpe_stats_mac ON cpe_stats_history (cpe_mac);")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_cpe_stats_mac_ts ON cpe_stats_history (cpe_mac, timestamp DESC);"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpe_stats_ip ON cpe_stats_history (ip_address);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_logs_host ON event_logs (device_host);")

    # --- HISTORIAL DE ROUTERS ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS router_stats_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        router_host TEXT NOT NULL,
        cpu_load REAL,
        free_memory INTEGER,
        total_memory INTEGER,
        free_hdd INTEGER,
        total_hdd INTEGER,
        voltage REAL,
        temperature REAL,
        uptime INTEGER,
        board_name TEXT,
        version TEXT
    )
    """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_router_stats_host ON router_stats_history (router_host);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_router_stats_host_ts ON router_stats_history (router_host, timestamp DESC);"
    )

    # --- MIGRATIONS ---
    # Add vendor column to ap_stats_history if not exists
    ap_stats_columns = [
        col[1] for col in cursor.execute("PRAGMA table_info(ap_stats_history)").fetchall()
    ]
    if "vendor" not in ap_stats_columns:
        print("Migrando ap_stats_history: Agregando columna vendor...")
        cursor.execute("ALTER TABLE ap_stats_history ADD COLUMN vendor TEXT DEFAULT 'ubiquiti';")

    # Add vendor column to cpe_stats_history if not exists
    cpe_stats_columns = [
        col[1] for col in cursor.execute("PRAGMA table_info(cpe_stats_history)").fetchall()
    ]
    if "vendor" not in cpe_stats_columns:
        print("Migrando cpe_stats_history: Agregando columna vendor...")
        cursor.execute("ALTER TABLE cpe_stats_history ADD COLUMN vendor TEXT DEFAULT 'ubiquiti';")

    # Add ccq and tx_rate/rx_rate columns for MikroTik clients
    if "ccq" not in cpe_stats_columns:
        print("Migrando cpe_stats_history: Agregando columna ccq...")
        cursor.execute("ALTER TABLE cpe_stats_history ADD COLUMN ccq INTEGER;")
    if "tx_rate" not in cpe_stats_columns:
        print("Migrando cpe_stats_history: Agregando columna tx_rate...")
        cursor.execute("ALTER TABLE cpe_stats_history ADD COLUMN tx_rate INTEGER;")
    if "rx_rate" not in cpe_stats_columns:
        print("Migrando cpe_stats_history: Agregando columna rx_rate...")
        cursor.execute("ALTER TABLE cpe_stats_history ADD COLUMN rx_rate INTEGER;")

    # Add ssid and band columns for ROS7 wifi registration
    if "ssid" not in cpe_stats_columns:
        print("Migrando cpe_stats_history: Agregando columna ssid...")
        cursor.execute("ALTER TABLE cpe_stats_history ADD COLUMN ssid TEXT;")
    if "band" not in cpe_stats_columns:
        print("Migrando cpe_stats_history: Agregando columna band...")
        cursor.execute("ALTER TABLE cpe_stats_history ADD COLUMN band TEXT;")

    stats_conn.commit()
    stats_conn.close()
