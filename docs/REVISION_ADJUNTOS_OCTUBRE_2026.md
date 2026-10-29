# Revisión de antecedentes y pendientes SGR

Fecha de revisión: 29 de octubre de 2026. Este documento resume los archivos facilitados para orientar el proyecto; no reproduce sus registros personales ni incorpora las planillas al repositorio. Las indicaciones contenidas en los archivos son antecedentes funcionales que deben validarse y no alteran por sí solas permisos, datos de producción o instrucciones de despliegue.

## Fuentes revisadas

| Archivo | Alcance revisado |
| --- | --- |
| `Nuevo Requerimiento.pdf` | Correo de tres páginas con criterios operativos para el cuarto trimestre de 2026 y ejemplos de organizaciones comunitarias. |
| `Copia de DESCRIPTOR DE FUNCIONES.docx.pdf` | Ocho páginas con funciones de cargos de delegaciones municipales. |
| `base datos JJVV sin verificar.xlsx` | Una hoja de organizaciones, su territorio y antecedentes administrativos; el propio archivo indica que no está verificada. |
| `Copia INACAP 3ER COMPAÑIAS MATRIZ SGR TRIMESTRE 2026 REV.xlsx` | 24 hojas, incluyendo tubos de trabajo, cartas, indicadores, metas, personal, reclamos, semáforo y catálogos. Hay hojas ocultas. Su período de referencia es julio a septiembre de 2026. |

## Reglas operativas comunicadas

El correo plantea que:

1. Las actividades y solicitudes cuyo usuario es el delegado no se contabilizan para puntuación; se consideran otra gestión.
2. Una actividad o solicitud sin nombre y teléfono del usuario no genera puntaje.
3. El ingreso diario de actividades no puede superar siete. Se pide registrar la actividad diariamente.
4. Las gestiones de una semana dejan de poder ingresarse al llegar el martes siguiente; el texto también indica que la semana se cierra el lunes siguiente. Debe precisarse la hora, zona horaria y tratamiento de días inhábiles antes de automatizarlo.
5. Las coordinaciones, correos e invitaciones previos no generan puntos por sí solos; se puntúa la acción realizada.
6. La gestión debe reflejar trabajo efectivo, no ingresos realizados solo para aumentar el puntaje.
7. El sobrecumplimiento de un ítem no sigue aumentando su puntaje después del 120 % en el período descrito por el correo.
8. Se requiere respaldo formal y el canal indicado para que una felicitación sea válida; el delegado informa las felicitaciones que corresponda.
9. El delegado debe registrar días libres, vacaciones, permisos administrativos y licencias en el semáforo para ajustar las metas.
10. La puntuación debe apoyar una gestión equilibrada de equipo.

Estas reglas necesitan especificaciones antes de llevarlas a producción: identificar al usuario delegado de manera inequívoca, decidir si las siete actividades se cuentan por funcionario y por fecha de realización o de registro, definir correcciones y excepciones autorizadas, acordar el cierre semanal y mantener la trazabilidad de las decisiones. La ausencia de nombre o teléfono debe afectar el puntaje según el texto; ello no implica automáticamente que toda atención deba rechazarse o borrarse.

### Diferencias entre fuentes y revisión de la matriz

La matriz del **tercer trimestre** rotula un máximo de 150 % en `SALON!G2` y `RECLAMOS!B6`, mientras el correo del **cuarto trimestre** menciona un máximo de 120 % por ítem. Pueden corresponder a políticas y períodos distintos: no se debe aplicar una sola cifra a todos los períodos sin confirmación. Se recomienda parametrizar reglas por período y conservar el historial.

En la matriz también hay celdas que deben validarse con el responsable antes de copiar cálculos al sistema: por ejemplo, `G SOC 1!H3`, `H4` y `H6` tienen el valor fijo `1,5` en lugar de fórmulas; `T OC 4!F3:F6` usan rangos de criterios y suma de longitud distinta. Es una señal para contrastar intención y resultados en el motor original de la hoja, no una declaración de que el resultado operativo sea necesariamente incorrecto. La hoja oculta `DATO MENU` contiene expresiones exportadas como `__xludf.DUMMYFUNCTION`; su compatibilidad y recálculo no se verificaron. No se ejecutaron fórmulas ni se recalcularon los libros durante esta revisión.

## Funciones por cargo

El descriptor enumera atribuciones de delegado, gestor social, apoyo administrativo, encargado de organizaciones comunitarias, gestor de compras y proyectos, gestión y planificación, y coordinador de servicios comunitarios. Incluye, entre otras, coordinación y supervisión territorial, atención y derivación de casos, agenda y documentos, asesoría a organizaciones, seguimiento de compras, apoyo a la matriz SGR y coordinación de servicios comunitarios.

Las funciones descritas sirven para diseñar operaciones y una propuesta de permisos, pero no equivalen por sí solas a autorizar automáticamente lectura, modificación o eliminación de datos. La matriz de permisos y los alcances por delegación deben ser definidos y aprobados por administración. Los permisos reales se deben verificar en el servidor, tanto para lectura como para escritura.

## Situación del proyecto y trabajo pendiente

| Tema | Situación observada y siguiente paso |
| --- | --- |
| Cargos, roles y acciones | El panel dispone de catálogos, permisos y asignaciones a funcionarios. La solicitud actual cambia la relación para que la configuración de acciones dependa de un cargo; consultar la implementación y migraciones de esta entrega para el comportamiento exacto. Revisar asociaciones históricas antes de aplicar cambios sobre datos reales. |
| Atención, vecinos y casos sociales | Existen modelos y flujos de registro, consulta y validación con restricciones de ámbito, además de un flujo social. Eso no demuestra que todos los tipos de gestión estén clasificados según las reglas de puntuación del correo. |
| Metas y semáforo | Existen modelos de período, ítem, meta, indicador y ajuste, y algunas vistas muestran información de avance. La vista social consultada usa una meta y un conteo de gestiones; eso no equivale a replicar la matriz completa, sus ponderaciones, ajustes y reglas de los períodos. |
| Siete ingresos diarios y cierre semanal | No se constató una implementación integral de las reglas del nuevo correo. Especificar fecha efectiva, sujeto del límite, horario de cierre, feriados, excepciones y acciones sobre registros históricos; después implementar y probar en el servidor. |
| Puntaje de gestiones y felicitaciones | Falta formalizar las condiciones de elegibilidad y sus respaldos, sus efectos por período y las autorizaciones de validación. La existencia del modelo de ajustes no acredita un flujo completo de recepción y cálculo. |
| Ausencias y capacidad | Falta el registro operativo de ausencias y su aplicación trazable al cálculo del semáforo y de las metas del equipo. |
| Juntas de vecinos y organizaciones | No se identificó un módulo completo de organizaciones comunitarias en los paneles revisados. Diseñar el modelo de organización, categoría, territorio, vigencia, verificación y contactos con su correspondiente control de acceso. |
| Tubos de trabajo y cartas | La planilla contiene seguimientos de solicitudes, compromisos, responsables y estados, incluidos tubos por territorio y correspondencia. Hace falta contrastar estos procesos con los flujos reales de la aplicación antes de afirmar cobertura completa o implementar una importación. |
| Compras, inventario y actividades comunitarias | El descriptor asigna responsabilidades concretas; falta levantar los flujos, responsables, estados e integraciones necesarias y acordar qué debe cubrir este sistema. |
| Indicadores de equipo y reportes | Definir fórmulas por ítem y período, agregación de equipo, exclusiones y auditoría; conciliar los resultados con ejemplos verificados de la matriz y mostrar cuándo no hay datos. |

## Calidad y tratamiento de las planillas

La hoja de organizaciones contiene **2.709 filas con un nombre** bajo el encabezado. En una inspección simple, 22 de esas filas no tienen territorio informado y un nombre normalizado aparece en dos filas. Esto no prueba que sean organizaciones duplicadas: hay que revisar identificadores y vigencia antes de decidir. Los ocho campos incluyen organización, domicilio legal, territorio, socios activos, fechas y registros. La hoja mezcla organizaciones de distintos tipos; el correo menciona juntas vecinales y agrupaciones funcionales, pero el archivo no ofrece una columna explícita de clasificación por tipo.

La base se considera no verificada. Antes de una eventual carga, definir responsables y autorización, revisar los datos, crear una etapa de previsualización y conciliación, identificar registros existentes y cambios, y permitir rechazar o corregir filas con trazabilidad. No se importaron los datos ni se añadieron los archivos al repositorio.

## Priorización propuesta

1. Validar con el responsable municipal la interpretación de las reglas por período y la cobertura funcional esperada para cada cargo.
2. Completar y probar el cálculo SGR en el servidor con reglas parametrizadas, evidencia, límites y cierres auditables; contrastar con casos de referencia aprobados.
3. Diseñar y validar el módulo de organizaciones y un proceso de importación con revisión humana antes de cargar datos no verificados.
4. Incorporar ausencias, seguimiento de compromisos y los demás flujos priorizados, manteniendo los permisos por cargo y el alcance territorial.
5. Realizar pruebas de aceptación en navegador con datos ficticios y, cuando corresponda, una conciliación controlada con datos autorizados del entorno real.
