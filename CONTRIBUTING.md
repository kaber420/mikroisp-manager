# 📜 Manifiesto de Consistencia y Calidad

Este documento establece las reglas de convivencia técnica para el proyecto. Nuestra prioridad no es solo que el código funcione, sino que sea sostenible.

## 1. El Principio de Invisibilidad
El código debe ser escrito de tal forma que sea imposible adivinar quién lo programó. No buscamos "estilos personales" ni "sellos de autor". Buscamos una sola voz técnica en todo el repositorio.

## 2. Mimetismo Arquitectónico
Antes de escribir una sola línea, observa el código circundante.

* Si el proyecto usa Pattern A, tú usas Pattern A.
* Si el manejo de errores es X, tú usas X.

La consistencia es superior a la preferencia personal. Incluso si crees que hay una forma "mejor" de escribirlo, mantén el estándar actual para evitar la fragmentación.

## 3. Prohibición de "Módulos Frankenstein"
No permitiremos parches de lógica que rompan la cohesión del módulo. Si una funcionalidad nueva requiere un cambio de estilo, este debe discutirse primero. No se aceptarán soluciones que se sientan como "un cuerpo extraño" dentro del sistema.

## 4. La Regla del Boy Scout (Con Límites)
Siempre deja el código un poco mejor de como lo encontraste, pero dentro de los márgenes del estilo establecido. Limpiar código no es excusa para cambiar la arquitectura o la nomenclatura base del proyecto.

## 5. Prioridad en la Revisión (Code Review)
Cualquier Pull Request que introduzca patrones inconsistentes o lógica que genere carga cognitiva innecesaria será rechazado, independientemente de si la funcionalidad es correcta. La deuda técnica no es una opción.

> "Escribimos código para humanos primero y para máquinas después. Si un humano no puede saltar de un módulo a otro sin sentir que cambió de proyecto, hemos fallado."

---

## 6. Reglas de Oro Prácticas

### 6.1. El Idioma del Código
El código (variables, funciones, clases) y los comentarios técnicos se escriben exclusivamente en **Inglés**. La interfaz de usuario y los logs de negocio se manejan según la localización definida (i18n).

### 6.2. Comentarios: El "Por Qué", no el "Qué"
No comentes lo que el código ya dice. Usa comentarios solo para explicar decisiones arquitectónicas o lógica compleja que no sea evidente. Si el código es difícil de leer, refactoriza antes de comentar.

### 6.3. Prohibición de Código Muerto
No se permite código comentado ("dead code"). Si algo no se usa, se borra. El historial de Git es el lugar para recuperar versiones anteriores, no el código fuente actual.

### 6.4. Gestión de Dependencias
Antes de añadir una librería externa, justifica por qué no puede resolverse con las herramientas nativas del framework. Menos dependencias equivalen a menos deuda técnica y menores riesgos de seguridad.

### 6.5. Estándar de Commits (Conventional Commits)
Usa mensajes de commit claros y estructurados. Ejemplo: `feat: add ssl indicator`, `fix: router timeout`. Esto permite entender el progreso y generar changelogs automáticos.
