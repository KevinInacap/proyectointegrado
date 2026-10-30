# Referencias y revisión del panel de administración

Actualizado: 30 de octubre de 2026.

## Referencias para futuras mejoras

| Recurso | Aplicación al proyecto |
| --- | --- |
| [Animate.css, repositorio y documentación](https://github.com/animate-css/animate.css) | Biblioteca conocida de animaciones CSS; sus recomendaciones incluyen conservar la preferencia de movimiento reducido. Útil para estudiar patrones de entrada y salida. |
| [Animate.css: buenas prácticas](https://github.com/animate-css/animate.css/blob/main/docsSource/sections/03-best-practices.md) | Considerar accesibilidad y el estado final de las animaciones. Revisar su licencia antes de incorporar código o distribuir la biblioteca. |
| [Motion, repositorio](https://github.com/motiondivision/motion) | Biblioteca MIT para JavaScript y otros entornos; referencia para transiciones de interfaz y coordinación de estados. |
| [FormKit AutoAnimate](https://auto-animate.formkit.com/) | Referencia para animar adiciones, eliminaciones y desplazamientos de elementos, con soporte para movimiento reducido. |
| [FormKit AutoAnimate en GitHub](https://github.com/formkit/auto-animate) | Código fuente y licencia MIT de la utilidad de transiciones automáticas. |
| [W3C: preferencia de movimiento reducido](https://www.w3.org/WAI/WCAG22/Techniques/css/C39) | Técnica de accesibilidad para respetar `prefers-reduced-motion`. |

En esta entrega se utilizan CSS y las API existentes del navegador; no se añadieron estas bibliotecas como dependencias. Las animaciones son breves y los indicadores de carga acompañan peticiones reales. Los formularios se mantienen utilizables con movimiento reducido.

## Problemas corregidos

- Las pantallas de cargos, roles, delegaciones, vecinos, usuarios y atenciones muestran carga durante consultas reales; abrir un formulario o cambiar una lista tiene una transición breve. El foco entra a un campo visible y la preferencia de movimiento reducido se respeta.
- La vista de delegaciones acumulaba eventos cada vez que se abría y podía conservar resultados anteriores mientras cargaba. Ahora registra los eventos una sola vez e informa cargas y errores.
- Una cuenta con permisos territoriales podía restablecer la contraseña de un administrador funcional de la misma delegación. Se protegieron las cuentas administrativas ante ese acceso.
- Los cambios de estado admiten un estado explícito para que una petición repetida no revierta el cambio. Los botones de roles protegidos se muestran deshabilitados, y se previenen bajas duplicadas. La confirmación de baja de usuario describe su consecuencia real.
- El formulario de atención solo cargaba las primeras 50 opciones de tipo y subatención; ahora solicita todas las páginas. Al vincular un vecino, el nombre y teléfono se toman de su ficha y el formulario explica dónde corregirlos.
- La edición parcial de un vecino podía borrar el teléfono o cambiar su estado al omitir esos campos. Ahora los conserva. La escritura de vecinos y catálogos y su auditoría se realizan en una transacción; los conflictos de duplicación generan una respuesta controlada.
- Cuando un guardado se completa pero falla la recarga de la tabla, la interfaz informa que los datos sí quedaron guardados. La creación y asignación de roles base del cargo Usuario de Consulta se corrigió para instalaciones nuevas sin apropiarse de roles personalizados históricos.

## Protección contra envíos masivos

Se limita por cuenta el número combinado de solicitudes de creación a cargos, delegaciones, usuarios, roles, funciones y catálogos de métricas. El valor inicial es 60 intentos por 60 segundos; `SGR_ADMIN_CREATE_LIMIT` y `SGR_ADMIN_CREATE_WINDOW_SECONDS` permiten adaptarlo. El servidor responde 429 con tiempo de espera al alcanzar el límite. El contador usa una tabla persistente y transacciones; la migración `core.0004_admincreationquota` debe aplicarse mediante el despliegue habitual.

La importación de vecinos mantiene su propio límite de 1.000 filas y no consume esta cuota; la unicidad de RUT/correo y el bloqueo del formulario previenen duplicados conocidos. Las atenciones también deduplican solicitudes idénticas recientes. Estas medidas reducen envíos repetidos, pero no garantizan inmunidad ante todo abuso ni sustituyen la supervisión del entorno.

## Límites de la revisión

En una base SQLite aislada se comprobó desde el navegador la creación de un cargo, su rol base y permiso, un vecino y un tipo, subatención y atención ficticios. Después pasaron 269 pruebas Django y 19 scripts JavaScript, incluidos controles de persistencia, idempotencia, permisos, límites y carga. La comprobación de configuración y migraciones también pasó.

La revisión en navegador se interrumpió antes de poder verificar visualmente las transiciones finales; las pruebas automatizadas de los indicadores y movimiento reducido sí pasaron. No se probaron todas las combinaciones, datos reales, MariaDB ni AWS. Algunos reportes siguen pendientes de una fuente de datos reales, como se describe en `REVISION_ADJUNTOS_OCTUBRE_2026.md`.
