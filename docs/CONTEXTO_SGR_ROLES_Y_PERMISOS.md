# Criterios funcionales del SGR

Este documento conserva las decisiones funcionales que deben mantenerse al ampliar el sistema. La guía y los requisitos de evaluación describen actores, alcance territorial, catálogos y controles; la regla de navegación definida para esta implementación es que el cargo selecciona el panel y el rol concede acciones.

## Identidad, panel y alcance

- **Usuario**: cuenta de acceso e identidad de la persona.
- **Cargo**: función institucional. Determina el panel inicial y puede relacionarse con las funciones e indicadores que se miden.
- **Rol**: conjunto de permisos de lectura, creación, edición, derivación, cierre, validación y administración de módulos. Una persona puede tener más de un rol.
- **Delegación**: ámbito territorial de trabajo y consulta. El acceso ordinario queda restringido a la delegación asignada; el rol Administrador puede operar transversalmente.
- **Perfil**: vincula usuario, cargo, delegación, estado y roles.

Por lo tanto, cargo y rol no son sinónimos ni deben crearse necesariamente en pares. Una misma capacidad puede darse a personas con distintos cargos; personas con el mismo cargo pueden tener roles distintos.

## Administrador

El rol de aplicación **Administrador** concentra la gestión transversal: usuarios y sus credenciales, roles y permisos, cargos, delegaciones, catálogos, atenciones, vecinos, metas, reportes y auditoría. Su matriz no se puede desactivar parcialmente desde los interruptores de la interfaz, porque eso produciría una administración inconsistente.

El cargo **Administrador General** elige el panel administrativo, pero no concede privilegios por sí solo. A la inversa, una persona con rol Administrador y cargo territorial conserva su panel por cargo y obtiene las operaciones autorizadas por el rol. Las cuentas técnicas de Django (`staff`/`superuser`) son una capa separada y no se conceden al crear usuarios ordinarios.

## Catálogos y consistencia

El catálogo de permisos detallados se guarda en `permission_definition`; las asignaciones normalizadas se guardan en la relación entre roles y permisos. Se mantiene `permissions_data` por compatibilidad con código existente y se actualizan ambos formatos juntos. Los permisos base se insertan con una migración repetible y el rol Administrador recibe el catálogo completo.

Los CRUD de **cargos** y **roles** permanecen separados. Al crear o modificar un usuario se asignan de forma independiente su cargo, delegación y uno o más roles. La autorización debe validarse en el servidor en cada operación, además de ocultar o mostrar controles en la interfaz.

## Actores previstos y decisiones pendientes

La documentación contempla administración, coordinación, jefatura/delegación, funcionarios, verificación y consulta. El proyecto incluye roles de Administrador, Coordinador, Delegado, Gestor Territorial/Funcionario, Verificador Técnico y Usuario de Consulta; los cargos se mantienen como catálogo independiente y pueden ser más específicos.

No se agrega automáticamente un rol para cada cargo. Antes de separar, por ejemplo, Auditor o Asistente Social como roles, se debe definir qué operaciones distintas necesitan y qué datos pueden consultar. Tampoco se asigna un cargo a un perfil real incompleto sin validarlo con la persona responsable.

## Fuentes de requisitos

Las reglas anteriores resumen los requisitos de la segunda evaluación, el contexto institucional, la guía del proyecto y las clases de perfiles, scoping, permisos y CRUD protegido. Los documentos originales permanecen como fuentes de referencia fuera del repositorio; este resumen evita duplicarlos y facilita mantener el comportamiento coherente.
