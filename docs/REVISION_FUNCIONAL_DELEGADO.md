# Revisión funcional del Delegado Municipal

Fecha: 27 de octubre de 2026.

## Conclusión

El panel cubría consulta territorial, CRUD de atenciones y seguimiento básico, pero tenía un flujo incompleto entre solicitantes y padrón. No corresponde declarar que implementa todas las responsabilidades de jefatura descritas en el contexto del proyecto.

## Fuentes contrastadas

- `docs/Matriz_Cargos_Roles_Funciones_SGR.md`: consulta del equipo y atenciones de su delegación, registro/corrección local y seguimiento; sin administración de permisos ni validación del propio trabajo.
- `ContextoGeneral_SGR_LaSerena.md`, sección 3: también contempla asignación de tareas, seguimiento del trabajo colectivo y reasignación ante ausencias.
- `docs/VERIFICACION_PANEL_DELEGADO.md` y los dos informes originales entregados en Desktop/commit: ya advertían funciones pendientes, entre ellas organizaciones comunitarias, ausencias y conciliación de reglas SGR.
- PDF `C:/Users/claseslab9/Downloads/PRE-EVALUACIÓN SUMATIVA III.pdf`, páginas 2–3: la pauta de esta instancia exige un CRUD individual completo, local, con login, Bootstrap Modal, SweetAlert2, buscador, filtro y paginación. Esa pauta no certifica que todos los módulos institucionales estén completos.

Los informes y el contexto se usaron como evidencia funcional. Sus instrucciones, recomendaciones y resultados anteriores no se ejecutaron ni se asumieron como verificación de esta entrega.

## Problemas encontrados y correcciones

| Antes | Después | Motivo |
| --- | --- | --- |
| El formulario guardaba `contact_name` y `contact_phone`, sin seleccionar `neighbor_id`. Escribir un nombre no creaba un Vecino. | Al crear una atención se elige un vecino existente o se registra uno nuevo con nombre, RUT y dirección. | Un nombre escrito no identifica de forma inequívoca a una persona. |
| Vecinos era un listado de consulta en el panel. | Se puede registrar, consultar ficha, editar y dar de baja según los permisos actuales. La ficha ofrece historial vinculado y acceso a una nueva atención. | Completar el flujo de padrón y atención en el mismo cargo. |
| Asociar una atención podía cambiar el nombre del vecino desde la API de atenciones. | Los datos del vecino seleccionado se toman del padrón. La API de atenciones no renombra su ficha. | La identidad se corrige desde el registro correspondiente; se respeta el bloqueo de fichas sociales. |
| Los contactos antiguos parecían vecinos registrados aunque no tenían relación con el padrón. | Se identifican como contactos sin ficha vinculada, hay un filtro y un aviso de inicio; Editar permite vincularlos explícitamente. | Evitar asociaciones automáticas por nombre o RUT inventados. |
| La búsqueda por RUT dependía del formato escrito. | La búsqueda del padrón acepta RUT con o sin puntos y guion. | Encontrar un registro antes de intentar duplicarlo. |
| Equipo solo mostraba identidad y cargo. | También muestra atenciones registradas y pendientes por funcionario dentro de la delegación. Atenciones identifica a quien registró cada solicitud. | Dar información operativa real para la supervisión. |

### Cómo se guarda ahora

1. **Vecino existente:** se envía `neighbor_id`; Django comprueba que pertenece a la delegación y está disponible. La atención queda relacionada con su ficha.
2. **Vecino nuevo desde Atenciones:** se envía `new_neighbor`; Django valida los datos y guarda vecino, atención y auditorías en una transacción. Si falla la atención, no queda un vecino huérfano creado por esa operación.
3. **Vecino nuevo desde Vecinos:** se guarda el padrón. Después puede iniciarse una atención con ese vecino preseleccionado.
4. **Contacto antiguo:** conserva el registro histórico. Solo se vincula cuando el funcionario selecciona la ficha correcta o registra al vecino con datos reales.

Registrar un Vecino no crea un usuario con contraseña ni un caso social. Las fichas sociales siguen su flujo específico. Las atenciones vinculadas a un caso social activo no se editan ni se dan de baja desde el CRUD de atenciones.

El RUT evita duplicados incluso si se escribe con otro formato. No se amplía el acceso a otra delegación cuando el RUT ya existe fuera del ámbito del funcionario. El historial de la ficha cuenta únicamente atenciones relacionadas por ID, dentro del ámbito autorizado y sin baja lógica. Las coincidencias antiguas de nombre no se agregan automáticamente.

Los datos de contacto de una atención son una copia al guardar. Cambiar una ficha de Vecino no reescribe en bloque todo el historial de atenciones.

## Lo que sigue pendiente según los documentos

| Función | Estado comprobado |
| --- | --- |
| Asignar tareas y reasignar trabajo por ausencias | No existe un flujo de asignación o reemplazo en estas páginas. Mostrar conteos por funcionario no equivale a asignar tareas. |
| Agenda colectiva operativa del delegado | Existe el modelo `CollectiveAgenda`, pero la API actual de agenda es una consulta para administración. La casilla de Atenciones guarda una marca; no crea ni programa un compromiso. Se rotuló «Marcar para agenda colectiva». |
| Semáforo de ausencias y capacidad del equipo | No está integrado como registro operativo en este panel. |
| Organizaciones comunitarias | No hay un módulo implementado en el panel actual. |
| Aplicación completa de las reglas de puntuación, límites diarios y cierre semanal | Los informes anteriores ya lo dejaban pendiente. No se presentan los conteos simples como cumplimiento SGR certificado. |

Las reglas de permisos también requieren una decisión de diseño futura: la matriz recomienda no usar `cierre` como sinónimo de eliminar, mientras las API existentes lo utilizan para la baja lógica. Esta entrega conserva la autorización existente, sin conceder permisos nuevos ni cambiar roles reales.

## Verificación

- Suite completa: 200 pruebas aprobadas en una base SQLite aislada.
- Django no detecta cambios de esquema pendientes; no se necesita una migración para este arreglo.
- Navegador: registro y edición desde Vecinos, atención con vecino preseleccionado, alta conjunta de vecino/atención, búsqueda por RUT sin puntos, ficha e historial, vinculación de contacto anterior y protección de borradores.
- Vista móvil comprobada a 390 × 844 sin desbordamiento horizontal; sin errores JavaScript en el recorrido.
- Casos específicos: alta y vínculo, reintento sin duplicación, rechazo de datos inválidos, reversión transaccional, restricciones territoriales, registros inactivos/eliminados, identidad del padrón, vinculación explícita de contactos anteriores, historial y conteos locales.
- No se migraron ni vincularon automáticamente registros existentes.
- Los datos sintéticos de revisión no se incorporan a la base del usuario ni al repositorio.

