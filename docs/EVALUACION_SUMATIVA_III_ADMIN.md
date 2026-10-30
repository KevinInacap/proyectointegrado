# Preparación para la preevaluación sumativa III

Fecha de revisión: 30 de octubre de 2026. Fuente: `PRE-EVALUACIÓN SUMATIVA III.pdf`, páginas 1–3, proporcionado por el estudiante. La pauta evalúa una demostración individual y local; AWS no es parte de esta evaluación. El puntaje final depende también de que cada estudiante ejecute y explique su CRUD ante el docente. No es posible garantizar una nota mediante pruebas automatizadas.

## CRUD propuesto: vecinos del panel de administración

| Criterio de la pauta | Dónde verlo y cómo demostrarlo | Evidencia y pendiente |
| --- | --- | --- |
| Ejecución local e inicio de sesión (5 puntos) | Seguir «Ejecutar en local» del README; ingresar con una cuenta autorizada de administrador. | La prueba `activities/test_evaluacion_sumativa.py` envía credenciales al inicio de sesión y comprueba la respuesta del panel. Cada estudiante debe comprobar sus propias credenciales y explicar el acceso en su equipo. |
| Listar, crear, editar y eliminar con persistencia (15 puntos) | Abrir Vecinos; crear una ficha de prueba con RUT válido y único; verificarla en la tabla; editar su dirección; comprobar el cambio; confirmar su baja. | La prueba automatizada consulta la base de pruebas después de crear, editar y dar de baja y revisa el registro de auditoría. La baja es lógica: el registro deja de aparecer en la lista y se conserva para auditoría. Explicar y mostrar rutas, vista, modelo, plantilla y código del formulario durante la presentación. |
| Ventanas modales Bootstrap y confirmación SweetAlert2 (8 puntos) | Usar «Nuevo Vecino», luego «Editar» en su fila y «Baja» para mostrar la confirmación; cancelar una vez y después confirmar. | El formulario de alta y edición está en el modal Bootstrap `modalVecino`; la baja usa SweetAlert2 y solo envía DELETE al confirmar. Falta la demostración visual individual en el navegador del estudiante. |
| Búsqueda, filtros y paginación combinados (12 puntos) | Con suficientes vecinos ficticios que cumplan los mismos filtros, buscar, filtrar por estado y territorio, avanzar a otra página y comprobar el rango y los resultados; limpiar filtros. | `scripts/test_admin_neighbors_pagination.cjs` ejecuta el código de la tabla con 25 registros simulados y comprueba páginas, filtros, búsqueda, recarga y página vacía. Preparar suficientes datos ficticios para demostrar más de una página real. |

## Qué se corrigió en esta revisión

- La tabla de vecinos cortaba los resultados a diez, pero no creaba botones para avanzar a otras páginas. Ahora crea un paginador accesible, limita los números visibles y conserva la página tras recargar cuando sigue siendo válida. Si se elimina el último registro de la última página, retrocede a una página existente.
- Las columnas ocultas volvían a aparecer en las filas al cambiar de página o filtrar. Ahora se mantiene la selección al dibujar la tabla.
- Las búsquedas de vecinos, atenciones y auditoría se ejecutaban solo al soltar una tecla; ahora también reaccionan a pegar, cortar o borrar texto.
- Se retiró del listado un contador inicial de cuatro registros que no correspondía a datos cargados.

## Dónde está el código para explicar

- Rutas: `activities/urls.py`, nombres `api_vecinos` y `api_vecino_detail`, y ruta del panel de administración.
- Vista: `activities/views.py`, funciones `dashboard_admin_view`, `api_vecinos` y `api_vecino_detail`; validan acceso y datos, consultan y modifican la base y registran auditoría.
- Modelo: `activities/models.py`, clase `Vecino`; auditoría en `core/models.py`, clase `AuditLog`.
- Plantilla de la lista: `templates/activities/admin/views/vecinos.html`.
- Modal y campos: `templates/activities/admin/components/modals/neighbor_forms.html`.
- Interacciones: `static/js/admin/neighbors.js`, funciones `abrirModalVecino`, `guardarVecino`, `eliminarVecino`, `ejecutarFiltroCompletoVecinos`, `renderTablaVecinos` y `actualizarPaginadorVecinos`.
- Las validaciones son específicas del proyecto y se aplican en JavaScript y en el servidor. Este CRUD usa JSON y validación del servidor, no una clase Django `forms.Form`: explicar el formulario HTML y esas validaciones con honestidad.
- Referencias de animación y revisión anterior: `docs/REFERENCIAS_ANIMACIONES_Y_AUDITORIA_ADMIN.md`.

## Ensayo sugerido

1. Ejecutar el servidor local, iniciar sesión y navegar a Vecinos. Tener una cuenta autorizada y datos ficticios con RUT válidos; nunca usar datos personales reales para una demostración improvisada.
2. Crear un vecino, buscarlo, modificar su dirección y recargar la sección para verificar que quedó guardada. Mostrar qué ocurre con campos vacíos, correo o RUT inválidos y RUT duplicado.
3. Con más de diez vecinos que coincidan, combinar búsqueda y filtros, navegar a la página 2, volver y limpiar los filtros. Verificar el contador.
4. Mostrar la ventana de confirmación de baja, cancelar, volver a abrir y confirmar; explicar que la ficha conserva auditoría aunque desaparezca del listado.
5. Abrir los archivos indicados y explicar el recorrido: botón y modal → JavaScript → ruta → vista y validaciones → modelo/base de datos → respuesta JSON → actualización de la tabla. Practicar este recorrido individualmente.

## Preparación de la defensa individual

La pauta permite que el docente pida localizar, explicar o modificar brevemente código durante la revisión. Cada integrante debe defender un CRUD propio sin intervención de otro integrante. Antes de la evaluación, comprobar que el entorno local inicia, que la cuenta autorizada tiene acceso y permisos suficientes para las cuatro operaciones, y que los datos de demostración no corresponden a personas reales. La carga `seed_presentation` aporta solo tres vecinos ficticios: para enseñar dos páginas con el mismo filtro hacen falta al menos once fichas ficticias coincidentes y con RUT válidos y únicos. Prepararlas en una base local de ensayo, no en la instancia compartida.

Preguntas útiles para ensayar en voz alta y comprobar en el código:

1. **¿Cómo entra un usuario?** `core/views.py`, `login_view`, localiza el perfil, usa `authenticate` y establece la sesión; la ruta del panel y las API vuelven a comprobar los permisos. Mostrar el inicio de sesión real con una cuenta autorizada, sin exponer su contraseña.
2. **¿Qué pasa al guardar?** El formulario HTML está en `neighbor_forms.html`; `guardarVecino` valida, envía JSON por `fetch` con el token CSRF a la ruta de alta o detalle, y luego actualiza la tabla. La vista repite la validación, guarda el modelo `Vecino` y devuelve JSON. En edición el navegador usa POST al detalle; la API también acepta PUT.
3. **¿Cómo se demuestra la persistencia?** Tras crear y editar, recargar la página o sección y consultar la ficha por nombre/RUT; explicar que las pruebas de Django consultan el modelo en la base temporal después de cada operación. Un aviso de éxito por sí solo no prueba que la información persista.
4. **¿Qué significa eliminar?** SweetAlert2 solicita confirmación antes del DELETE; cancelar no debe cambiar la ficha. Al confirmar se registra una baja lógica (`deleted_at`) y auditoría, por lo que el vecino desaparece del listado, pero sigue en la base. Explicar esta decisión y verificar con el docente que acepta baja lógica como eliminación. Un vecino vinculado a un caso social activo no puede darse de baja hasta resolver ese vínculo.
5. **¿Dónde se procesan búsqueda, filtros y páginas?** En el panel de administración, `cargarVecinosDesdeDB` pide `/api/vecinos/` y utiliza la lista `vecinos` devuelta. `ejecutarFiltroCompletoVecinos` aplica búsqueda, estado y territorio en JavaScript sobre esa lista; `renderTablaVecinos` calcula el segmento de diez filas y dibuja el paginador. La API también admite parámetros `q`, `estado` y `page` para otros consumidores, pero no se debe afirmar que el panel envía esos parámetros ni que su paginación es una consulta SQL paginada. Explicar esta diferencia y su límite de escalabilidad con muchos registros.
6. **¿Por qué hay validaciones en dos lugares?** El navegador da retroalimentación inmediata; el servidor vuelve a validar y comprueba permisos, CSRF y duplicados porque una solicitud puede llegar sin usar el formulario. Mostrar un caso inválido y después uno válido.

La pauta pide identificar vistas, formularios, rutas y plantilla; este proyecto usa un formulario HTML con validación JavaScript y del servidor, no una clase `forms.Form`. Si el docente exige una clase de formularios Django como interpretación adicional, confirmarlo antes de la evaluación y preparar la adaptación necesaria; no afirmar que ya existe.

## Comprobaciones y límites

En la revisión anterior del commit `476c6e4` se ejecutaron 270 pruebas Django sobre una base temporal aislada, 20 archivos de pruebas JavaScript y `makemigrations --check --dry-run`, sin fallos. Esos resultados corresponden a esa revisión y no sustituyen las pruebas de cambios posteriores. Las pruebas JavaScript usan un DOM simulado y no sustituyen la revisión visual de Bootstrap, SweetAlert2, animaciones o clics en un navegador real. El 30 de octubre de 2026 se accedió al panel AWS y se hizo una comprobación visual parcial antes de desplegar las correcciones nuevas; no se comprobó el hash exacto de esa instancia. El detalle está en `INFORME_ADMIN_2026-10-30.md`. Quedan pendientes el ensayo visual local completo del CRUD de vecinos y la explicación individual. Las pruebas no constituyen garantía de ausencia total de errores ni de la calificación.
