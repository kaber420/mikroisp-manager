# 🤝 Contribuyendo a OmniWISP

¡Gracias por interesarte en mejorar OmniWISP! Para mantener el proyecto organizado y profesional, seguimos estos estándares.

## 🚀 Flujo de Trabajo (Git)

1.  **Ramas (Branches)**:
    - `main`: Código estable y probado (Producción).
    - `develop`: Integración de nuevas funcionalidades.
    - `feat/nombre-mejora`: Para nuevas características.
    - `fix/nombre-error`: Para corrección de errores.
2.  **Pull Requests**: Siempre realizar PRs hacia `develop` antes de pasar a `main`.

## 📜 Estándares de Código

### Python (Backend)
- Usar **Python 3.10+**.
- **Estilo**: Seguir PEP 8.
- **Tipado**: Usar *Type Hints* en todas las funciones.
- **Async**: OmniWISP es asíncrono; usa `async/await` siempre que sea posible (FastAPI, SQLModel, Redis).
- **Linter**: Se recomienda usar `ruff`.

### Frontend
- Framework: **SvelteKit**.
- CSS: **TailwindCSS** + **DaisyUI**.
- Evitar usar estilos en línea; preferir clases de utilidad de Tailwind.

## 🧪 Pruebas y Calidad
- Ejecutar pruebas con `pytest`.
- Las nuevas funciones deben incluir tests en la carpeta `/tests`.
- Documentar funciones complejas usando docstrings estilo **Google**.

## 📦 Gestión de Dependencias
- Usar `pyproject.toml` para la configuración general.
- Para añadir una librería:
  1. Instalarla en el venv.
  2. Actualizar la sección `dependencies` en `pyproject.toml`.
  3. Ejecutar `pip install -e .` para refrescar.

---
OmniWISP se construye con ❤️ y colaboración.
