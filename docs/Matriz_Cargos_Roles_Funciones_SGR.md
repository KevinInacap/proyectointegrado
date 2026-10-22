# Matriz de cargos, roles y funciones del SGR

## Regla de acceso

- **Cargo:** define el dashboard y el flujo de trabajo que se presenta al funcionario.
- **Rol:** define las operaciones autorizadas (consultar, registrar, editar, derivar o revisar).
- **Delegación autorizada:** delimita los registros que el funcionario puede consultar o modificar.
- La asignación de un cargo agrega el rol base correspondiente. Los roles complementarios requieren una necesidad aprobada y no sustituyen el control de delegación.
- La ausencia de perfil, rol o delegación autorizada reduce el acceso; nunca concede acceso global.

## Matriz recomendada

| Cargo | Rol base | Acciones y límites recomendados |
|---|---|---|
| SuperAdministrador | SuperAdministrador | Administración global y recuperación de acceso institucional. Reservado a la cuenta designada. No equivale a convertir a cada administrador en superusuario técnico de Django. |
| Administrador General | Administrador | Gestionar usuarios, cargos, roles, delegaciones, catálogos y parámetros; asignar permisos, corregir perfiles y revisar solicitudes. Acceso transversal a la aplicación. |
| Coordinador del Sistema | Coordinador del Sistema | Consultar indicadores e informes de delegaciones autorizadas; coordinar derivaciones y administrar metas o períodos operativos. Sin administración general de cuentas o roles. |
| Delegado Municipal | Delegado Municipal | Consultar el equipo y las atenciones de su delegación; registrar o corregir información local y realizar seguimiento. No valida su propio trabajo ni administra permisos. |
| Gestor Territorial | Gestor Territorial | Registrar actividades y compromisos de terreno, asociar evidencia y actualizar el avance de sus registros; derivar los que requieran otra unidad. No aprueba su propia evidencia. |
| Asistente Social | Asistente Social | Consultar casos sociales de su delegación, registrar atenciones y gestiones, actualizar los datos permitidos y avanzar o derivar el caso. Puede pedir revisión o corrección a administración. No aprueba su propio registro ni elimina definitivamente casos. |
| Verificador Técnico | Verificador Técnico | Revisar registros y evidencia asignados; aprobar, rechazar o solicitar corrección con observación y trazabilidad. No altera el contenido original ni valida su propio trabajo. |
| Auditor Municipal | Auditor Municipal | Consultar bitácoras e informes en modo lectura dentro del alcance autorizado. No modifica registros ni permisos; solo accede a datos personales cuando son necesarios para la auditoría. |
| Usuario de Consulta | Usuario de Consulta | Consultar indicadores e informes expresamente autorizados. Sin creación, edición, derivación, validación o eliminación. |

## Flujo de revisión social

1. Al registrar un caso o una nueva gestión, se conserva el registro en la base de datos y se genera una solicitud de revisión pendiente para administración.
2. Administración recibe una notificación interna con nombre del trabajador, cargo, delegación, tipo de solicitud y referencia del caso.
3. Para corregir un caso existente, el Asistente Social envía el motivo y los cambios propuestos. La ficha original no cambia hasta que administración apruebe la solicitud.
4. Administración puede aprobar o rechazar la solicitud, dejar una respuesta y queda registrada la persona revisora y la fecha.
5. Los resultados se limitan a los roles autorizados y la bitácora registra las operaciones críticas.

## Permisos base orientativos

| Permiso | Significado |
|---|---|
| `lectura` | Consultar datos dentro del ámbito asignado. |
| `edicion` | Crear o modificar datos operativos permitidos. No otorga administración de roles. |
| `derivacion` | Enviar un registro al siguiente actor o etapa autorizada. |
| `validar_evidencia` | Aprobar, rechazar o devolver una evidencia; debe ser independiente de editar el registro. |
| `cierre` | Cerrar un proceso cuando corresponda. No debe usarse como sinónimo de eliminar. |

## Alcance territorial

Funcionarios de atención, trabajo territorial y jefatura operan en su delegación asignada. Coordinación y auditoría pueden tener un ámbito transversal solo si administración les autoriza expresamente las delegaciones necesarias. Un nombre de rol por sí solo nunca debe ampliar el queryset a todas las sedes.

## Criterios de diseño

La matriz sigue los actores y responsabilidades del proyecto SGR, el principio de menor privilegio y la separación entre permisos de operación y scoping territorial. La validación de evidencias debe ser una capacidad separada de la edición de datos fuente.
