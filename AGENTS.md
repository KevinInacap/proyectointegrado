# Reglas para dashboards

- Autorizar en el servidor cada lectura y cambio por acción, rol y ámbito; nunca confiar solo en controles ocultos de la interfaz. Usar CSRF en acciones con sesión y auditar cambios sensibles sin registrar contraseñas ni códigos de recuperación.
- Definir límites, obligatoriedad y formatos acordes al modelo y a la operación. Validarlos en el servidor, tanto en creación como en edición, incluso cuando el navegador ya los valide. Responder con mensajes claros sin exponer detalles internos.
- Aplicar los mismos límites a los formularios, asociar etiquetas y errores a sus campos y evitar descartar datos ante errores. No truncar silenciosamente información existente.
- Presentar datos no confiables como texto con textContent o codificación adecuada al contexto; no interpolarlos en HTML, atributos, estilos o JavaScript. Validar direcciones antes de usarlas como enlaces o imágenes.
- Usar SweetAlert para confirmar bajas, cambios sensibles y avisar errores o resultados significativos; no confirmar cada acción inocua. Prevenir envíos duplicados y comunicar resultados parciales con precisión.
- Crear transiciones breves y coherentes para cambios de vista y diálogos, sin bloquear la interacción; respetar prefers-reduced-motion, el teclado y la gestión de foco.
- Separar responsabilidades por módulo cuando aporte claridad, reutilizar funciones existentes y evitar archivos innecesarios o cambios ajenos a la tarea.
- Probar permisos, entradas inválidas, límites, persistencia y flujos importantes; no declarar verificados servicios, dispositivos o despliegues que no se hayan probado.
