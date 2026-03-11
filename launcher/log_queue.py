# launcher/log_queue.py
import logging
import logging.handlers

def configure_process_logging(queue):
    """
    Configura el logging para un subproceso.
    Redirige todos los logs al QueueHandler para ser procesados por el proceso principal.
    """
    root = logging.getLogger()
    
    # IMPORTANTE: Limpiar handlers existentes para evitar doble log o conflictos
    if root.handlers:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
            
    # Configurar QueueHandler
    queue_handler = logging.handlers.QueueHandler(queue)
    root.addHandler(queue_handler)
    
    # Nivel base (el filtro final lo hace el listener o el logger origen)
    root.setLevel(logging.INFO)

    # Configurar captura de logs de librerías específicas si es necesario
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    # Apscheduler
    logging.getLogger("apscheduler").setLevel(logging.INFO)
