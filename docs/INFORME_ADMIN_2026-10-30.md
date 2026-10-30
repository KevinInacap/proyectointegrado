# Revisión administrativa del 30 de octubre de 2026

## Alcance y correcciones

- Se sincronizaron la duración del contenedor y el fondo de los modales Bootstrap con la transición del diálogo: antes Bootstrap podía ocultar el modal antes de terminar el cierre. Se suavizaron la entrada de los resultados de delegaciones y la selección, y se respeta la preferencia de movimiento reducido.
- Al cerrar una ficha territorial se cancela el desplazamiento pendiente y se limpia la selección. Esto evita que una ficha cerrada vuelva a atraer la pantalla y que quede una tarjeta marcada.
- La generación automática de código de delegación evita un código manual ya ocupado. Se agregó una regresión para ese caso.
- Se precisaron las etiquetas de los indicadores: el conteo territorial es de RUT distintos en casos sociales, no el padrón de vecinos; el agregado suma por sede activa y puede contar un RUT en más de una sede. El cumplimiento es un promedio de los últimos indicadores disponibles por sede activa.
- Se permitió el desplazamiento interno del menú lateral cuando no cabe en la altura de la ventana, para que el pie no tape sus opciones. Se actualizó la versión de caché de los archivos estáticos cambiados.
- Se amplió `EVALUACION_SUMATIVA_III_ADMIN.md` con el contraste de la pauta, el recorrido del código, preguntas para la defensa y sus límites. `CONTEXTO_SGR_ROLES_Y_PERMISOS.md` conserva el material histórico y señala la relación actual entre cargo y rol. Las referencias de revisiones anteriores se conservan.

## Comprobación visual en AWS

Chrome accedió a la sesión existente el 30 de octubre; el rechazo anterior no se reprodujo. Se examinó la instancia antes de desplegar las correcciones de esta revisión; no se comprobó allí el hash exacto desplegado. Por ello esta observación **no verifica visualmente las correcciones nuevas**. No se cambió ningún registro preexistente durante los recorridos.

- Delegaciones: se abrió y cerró el formulario; SweetAlert2 avisó del nombre obligatorio. Se creó `Prueba Codex 20261030`, se abrió su ficha, se editó la dirección y se confirmó su baja. Tras recargar, se vio la dirección editada y el estado inactivo.
- Cargos: se navegó a la página 2, se comprobó la validación del nombre, se creó y editó `Cargo Prueba Codex 20261030` y se confirmó su baja. Después de recargar se observó la reducción del total de cargos activos.
- Roles: se comprobó que el cargo nuevo creó un rol base sin permisos, que aparece asociado a ese cargo; se intentó guardar un rol sin cargo y se vio la validación. Se creó `Rol Prueba Codex 20261030`, asociado al cargo ficticio, se editó su descripción y se comprobó tras recargar. Ambos roles de prueba quedaron sin permisos y sin usuarios. La interfaz de roles no ofrece una baja lógica equivalente a la de vecinos; no se eliminó el rol ficticio.
- Vecinos: se observó la página 2, se combinaron estado y territorio y se comprobó el rango. El formulario vacío mostró SweetAlert2; se creó `Vecino Ficticio Codex` con RUT de prueba, se buscó, se abrió la ficha, se editó su dirección y se confirmó la baja lógica. Después de recargar, la búsqueda ya no lo mostró en el listado. La interfaz informó que se conserva la auditoría.
- En lectura se abrieron Inicio, Usuarios, Metas, Tipo de Atención, Sub Atención, Atenciones, Tipo de Gestión y Solicitudes sociales. En Atenciones se avanzó a la segunda página, donde Siguiente quedó deshabilitado. Se abrieron las tres vistas de Reportes: indican conexión/API pendiente y métricas sin datos. No se probaron operaciones de escritura en esos módulos.

En Chrome local con SQLite aislado y datos ficticios se recorrieron Delegaciones, Cargos y Roles, se abrió y cerró una ficha territorial y formularios, se observaron las transiciones de entrada, apertura y cierre y se crearon un cargo y un rol. Los formularios cerraron sin dejar el fondo bloqueando el panel. La validación de cargo obligatorio y los avisos aparecieron; al editar el rol se precargó su cargo. Una consulta directa a SQLite confirmó el rol base y el vínculo del rol ficticio con su cargo, ambos sin permisos. No se midió objetivamente la fluidez. Con ventana de 1521 × 633 se verificó la corrección del menú: tras desplazarlo se ve completo Reportes y se puede abrir con un clic. Estas observaciones corresponden al código nuevo, no al desplegado en AWS.

## Pruebas automáticas de esta revisión

- Suite Django: **271 pruebas aprobadas** en una base SQLite de pruebas aislada, con Django 6.1.1. Se incluye la regresión del código automático de delegación.
- Los **20 archivos** `scripts/test_*.cjs` terminaron correctamente con Node; se repitió la prueba de ficha de delegación después del ajuste de etiquetas.
- `manage.py check` y `makemigrations --check --dry-run`: sin incidencias ni migraciones nuevas. `git diff --check`: sin errores de espacios.

La persistencia en AWS se comprobó mediante recarga y lectura de la interfaz; no se realizó una consulta directa a MariaDB. Los datos ficticios anteriores permanecen en la instancia: delegación y cargo inactivos, roles sin permisos ni usuarios, y vecino dado de baja lógica. No reutilizar su RUT en una demostración sin comprobar antes la política de duplicados.

## Pendientes y límites

- En AWS se observaron roles históricos con «Cargo pendiente de asignación». El modelo admite esa situación por compatibilidad histórica; altas y duplicados nuevos exigen cargo. Antes de regularizarlos, respaldar y revisar individualmente permisos, funcionarios y cargos; no asignar por coincidencia de nombre. Los roles administrativos protegidos requieren tratamiento específico. La exigencia de que **todos** los roles históricos tengan cargo aún no está cumplida.
- No se ha comprobado visualmente cada operación de todos los módulos, cada tamaño de pantalla, todos los filtros, paginadores o combinaciones de validación. El despliegue y la inspección en AWS de los cambios nuevos quedan pendientes. Las pruebas automáticas no demuestran la percepción visual del movimiento.
- La pauta exige defensa individual y local. Preparar al menos once vecinos ficticios coincidentes para mostrar dos páginas con el mismo filtro; la semilla de presentación aporta tres. Consultar al docente si acepta baja lógica como eliminación y si exige una clase `forms.Form`; este CRUD utiliza formulario HTML y validaciones JavaScript y del servidor.
- Las verificaciones automatizadas locales usan SQLite de pruebas; no certifican MariaDB, correo ni servicios externos. Para próximos cambios conservar las referencias en `REFERENCIAS_ANIMACIONES_Y_AUDITORIA_ADMIN.md` y los informes anteriores.
