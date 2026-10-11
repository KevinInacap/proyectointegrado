# Verificación local · segunda evaluación SGR

**Fecha:** 11 de octubre de 2026  
**Entorno:** Windows, servidor local `127.0.0.1:8000`, MySQL `sgr_municipal`  
**Alcance:** lógica de la aplicación, interfaces y base local. Django Admin y AWS quedan fuera de esta ronda.

Este registro distingue evidencia comprobada de trabajo pendiente. Los datos `@pnk.cl` son **ficticios**: no representan personal municipal ni autorizan enviarles mensajes. La carga `seed_academic_users` crea cinco cuentas por delegación, treinta en total, sin contraseñas utilizables. Una segunda ejecución no creó duplicados. La cuenta y el rol temporales usados para probar la interfaz se retiraron al terminar; no se modificaron las credenciales del administrador existente.

## Matriz de comprobación

| Requisito | Precondición y prueba | Resultado esperado y obtenido | Estado |
|---|---|---|---|
| Acceso y recuperación | Pruebas automatizadas de RUT/correo, credenciales, cuenta inactiva, códigos, caducidad, reenvío, intentos y cambio de contraseña. | Se aceptan solo sesiones y códigos válidos; la clave nueva queda verificada y la anterior deja de servir. Las pruebas pasaron. El envío SMTP real no se repitió en esta ronda. | Local verificado; SMTP externo pendiente de nueva prueba |
| Delegaciones | Crear, editar, consultar, validar código único y comuna; revisar formulario y listado en navegador. | Código estable aunque cambie el nombre; comuna persistida en MySQL; rechaza duplicado o comuna vacía. Pasó. | Verificado |
| Roles y permisos | Alternar `edicion` en un rol temporal desde la interfaz, consultar el valor guardado y volver al estado anterior. | El interruptor cambia la base y los accesos dependen del permiso persistido. Pasó. Los roles del sistema se protegen. | Verificado |
| Usuarios | Crear/editar, reasignar rol, cargo y delegación, resetear contraseña, activar/desactivar y proteger cuentas privilegiadas; selección por lote en navegador. | Los cambios de acceso se aplican desde MySQL; el lote de prueba desactivó y reactivó una cuenta ficticia. Pasó. | Verificado |
| Ítems y metas | CRUD, búsqueda, filtros y validación de relaciones; formulario de meta inspeccionado en navegador. | El período se selecciona por nombre, no por ID técnico. API protegida y prueba de regresión aprobada. | Verificado localmente |
| Tipo y Sub Atención | CRUD y relación de subtipo con tipo, incluida restricción de eliminación cuando hay dependencias. | Rechaza combinaciones inválidas y muestra los registros asociados. Pruebas pasadas. | Verificado |
| Ingreso de atención | Pruebas de contexto territorial, solicitante, tipo/subtipo, registro, doble envío y acceso fuera de delegación. | Se conserva responsable y delegación en el servidor; se rechaza la otra sede para usuarios limitados. Pasó. | Verificado localmente |
| Navegación y claridad | Se abrieron las doce secciones del panel; búsqueda, tabla de usuarios, ficha, formulario de delegaciones y formulario de metas se comprobaron en navegador. | Sin error de consola en las interacciones revisadas. Se agregó indicador de fila/columna y listado tabular de delegaciones. | Verificado en la vista local revisada |
| Carga local acotada | 60 lecturas autenticadas a `/api/users/`, seis trabajadores, sin escrituras; umbral exploratorio: cero errores y p95 menor a 500 ms. | 60 respuestas HTTP 200; 0,95 s total; 63,07 solicitudes/s; media 89,5 ms; p95 133,4 ms. | Cumplió en local; **no certifica AWS** |

La suite completa obtuvo **119 pruebas aprobadas**, incluidos el nuevo selector de períodos y la comuna de Delegaciones. `manage.py check`, la revisión de migraciones y la sintaxis de JavaScript no reportaron defectos en esta ronda.

## Correcciones detectadas durante la prueba

- Un script antiguo reemplazaba funciones de acciones por lote y podía mostrar éxito sin guardar cambios. Se retiró; ahora la selección de usuarios llama a la API y comunica fallos parciales. Se confirmó el cambio y su reversión en MySQL.
- La API de catálogos rechazaba por error a la cuenta administradora funcional que no era personal técnico de Django. Se ajustó la autorización al rol institucional y se agregó regresión.
- La ficha de usuarios mostraba una hora fija de último acceso. Ahora utiliza el dato real o indica que no hay ingreso registrado.
- El formulario de metas pedía un ID de período sin ofrecer catálogo. Ahora muestra períodos existentes por nombre.
- Los nombres y correos insertados en la tabla/ficha de usuarios se escapan antes de componer HTML; las acciones ya no interpolan nombres en atributos de JavaScript.
- La búsqueda de usuarios reaccionaba al teclado, pero no siempre al pegado. Ahora escucha cualquier cambio del campo.

## Pendiente antes de declarar lista la entrega

1. Registrar capturas y casos manuales de los seis CRUD, recuperación real por correo, permisos por cargo y rechazo de delegación ajena. Las pruebas automáticas no sustituyen esa evidencia de evaluación.
2. Definir un escenario de carga para AWS con datos, umbrales, CPU/memoria y recuperación; el resultado local anterior es solo una referencia inicial.
3. Revisar configuración de producción, secretos, respaldo, servicio MySQL y correo; desplegar, comprobar URL/versión y después publicar un commit o etiqueta inequívoca en Git.

No se puede garantizar una nota: la rúbrica incluye demostración, evidencia y despliegue que todavía no se han realizado. Este documento se actualizará con sus resultados, sin marcar pruebas pendientes como aprobadas.
