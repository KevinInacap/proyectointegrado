# Revisión del panel de administración

Fecha: 29 de octubre de 2026.

## Limpieza posterior del panel

- Se eliminaron los tres scripts antiguos de evaluación y chat que habían quedado bloqueados. Los comandos de semillas institucionales que siguen en uso se conservaron.
- El archivo de modales se separó en componentes para vecinos, funcionarios, atenciones, auditoría, roles y catálogos. La vista de reportes se dividió en sus tres sub vistas. Se comparó el HTML renderizado con la versión anterior para las secciones conservadas.
- Se retiraron un panel lateral de delegación sin acceso desde la interfaz, un modal de perfil antiguo que ya había sido sustituido por el menú de cuenta, sus estilos y funciones asociadas, además de una función sin uso que intentaba cambiar el estado de una atención por una ruta no autorizada. El perfil accesible desde el menú de cuenta se mantiene.
- Las comprobaciones de autorización y alcance territorial, la auditoría y el catálogo de permisos se separaron de `organization/views.py` en módulos con responsabilidades definidas. El archivo de vistas aún contiene los endpoints de usuarios, roles, cargos y delegaciones; también `activities/views.py` sigue siendo grande. Separarlos adicionalmente requiere preservar sus dependencias y pruebas, y queda como trabajo de mantenimiento posterior.

## Problemas corregidos

- El código principal del panel concentraba miles de líneas en un solo archivo. Se separó en módulos para vecinos, funcionarios, cargos, roles, delegaciones, atenciones, reportes y edición, conservando el orden de carga y los controles existentes.
- El vínculo entre cargos y roles resultaba confuso. Al crear un cargo se genera un rol base inicialmente sin permisos. Todo rol nuevo o duplicado requiere seleccionar un cargo y la asignación de roles a funcionarios se limita al cargo correspondiente. Se evita asignar permisos por coincidencias ambiguas de nombres y se protegen los roles administrativos. Las modificaciones del cargo mantienen sincronizado su rol base cuando procede.
- En algunas operaciones un error al actualizar el listado después de guardar podía dar la impresión de que no se había guardado. Los flujos revisados distinguen una escritura exitosa de un fallo posterior de actualización y evitan envíos repetidos.
- Un error en la expresión del correo rechazaba direcciones válidas en el formulario de vecinos. Se corrigió y se reforzaron las validaciones de nombre, RUT, dirección, teléfono, correo, estado y límites de longitud en la interfaz y en el servidor. En edición se conservan los valores históricos sin cambios; un valor nuevo o modificado debe cumplir las reglas actuales.
- La importación de vecinos completaba algunos campos con datos inventados. Ahora comunica los errores, no inventa información y limita los archivos a 5 MB y 1000 filas. La exportación a hojas de cálculo protege los datos de fórmulas; el CSV de auditoría también codifica comillas y neutraliza posibles fórmulas.
- Se reforzó la codificación de datos al presentar catálogos, matriz de roles, fichas y tabla de atenciones. Los errores del servidor evitan exponer detalles internos en los flujos revisados. Las solicitudes siguen sujetas a permisos y CSRF del servidor; validar la interfaz por sí sola no concede acceso.
- Se añadieron avisos con SweetAlert para datos requeridos o inválidos y para resultados significativos. Los formularios y resultados disponen de transiciones suaves; los filtros y paginadores dan respuesta visual, respetan la preferencia de movimiento reducido y mejoran las etiquetas y el foco de teclado.
- Se quitaron cifras y horarios fijos de la cabecera de delegaciones que podían no corresponder a los datos reales. Se recuperaron archivos y plantillas necesarios que faltaban en la copia principal para los paneles de delegado, asistencia social, chat y protección de sesión.

## Comprobaciones y límites

- Pasaron once pruebas de scripts administrativos con Node, incluidos los formularios, la relación cargo-rol, el tratamiento de datos peligrosos, el historial, el guardado y los avisos de estado. También pasaron las pruebas de navegación social y protección de sesión, y la comprobación de sintaxis de los módulos JavaScript administrativos.
- Pasaron 242 pruebas con Django 6.1.1. `check` y `makemigrations --check --dry-run` terminaron sin observaciones. Las pruebas se ejecutaron con SQLite de prueba y una clave temporal; la suite completa usa un algoritmo de contraseñas rápido únicamente durante la prueba.
- Las migraciones `organization.0017_position_base_role` y `organization.0018_role_position` deben aplicarse en cada entorno mediante el proceso habitual de despliegue. Las migraciones históricas ya aplicadas no se vuelven a ejecutar. No se dispuso de una base real para comprobar si hay asociaciones antiguas entre cargos y roles que deban revisarse; no se modificaron esas asignaciones a ciegas.
- En Chrome, con datos ficticios y SQLite aislado, se verificó la creación de un cargo, el aviso al intentar guardar un rol sin cargo, la creación de un rol asociado y la edición y persistencia de los permisos del rol base, sin errores JavaScript en estos recorridos. No se verificaron correo, MySQL, AWS, archivos reales de importación ni servicios externos. No se desplegaron cambios.
- Los tres scripts antiguos de datos de evaluación y chat se eliminaron a petición del usuario: alteraban roles, cuentas o contraseñas fuera del flujo administrativo. No se ejecutaron sobre datos reales. Los comandos de semillas vigentes permanecen disponibles.
