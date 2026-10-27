# Sesiones e historial del asistente social

Verificación local del 27 de octubre de 2026: Windows, Python 3.12, Django 6.1.1, SQLite y navegador Chromium. Se utilizaron cuentas y casos ficticios.

## Correcciones

- Las respuestas dinámicas llevan `private`, `no-store`, `no-cache`, `must-revalidate`, vencimiento inmediato y `Vary: Cookie`. Los archivos estáticos conservan su política de caché.
- Las páginas principales ocultan el documento al salir. Una restauración del historial o BFCache vuelve a consultar al servidor antes de mostrar la pantalla privada.
- Al regresar a una pestaña o ventana se verifica una firma opaca del contexto vigente: sesión, cuenta, cargo, delegación, roles y permisos. Una sesión distinta o expirada conduce al panel vigente o al acceso. La firma no permite autenticarse y no expone la cookie ni la contraseña.
- Un formulario antiguo de login no puede reemplazar una sesión ya autenticada mediante un GET o un POST reenviado. Para cambiar de cuenta se debe cerrar primero la sesión actual.
- `Recordarme` controla la duración de la cookie; las contraseñas no se guardan en localStorage/sessionStorage y se limpian de los campos al abandonar la página.
- Las nueve pestañas del asistente tienen enlaces reales, sección inicial resuelta por Django y navegación compatible con recarga y Atrás/Adelante. Las direcciones anteriores del panel y `/integral/` siguen funcionando. Secciones desconocidas devuelven 404 y se mantienen las restricciones por cargo, rol y delegación.
- El despliegue comprueba que los nuevos JavaScript de sesión y navegación se hayan publicado junto con el resto de estáticos.

## Direcciones

Todas usan el prefijo `/activities/dashboard/asistente-social/`:

| Sección | Sufijo |
|---|---|
| Casos Sociales Únicos | `casos/` |
| Flujo 3 Etapas | `flujo/` |
| Visitas a Terreno | `terreno/` |
| Catálogo de Ayudas | `beneficios/` |
| Informes Sociales | `informes/` |
| Emergencias y Crisis | `emergencias/` |
| Articulación de Redes | `redes/` |
| Metas y Semáforo SGR | `metas/` |
| Mantenedores SGR | `mantenedores/` |

## Evidencia

- **147 pruebas Django aprobadas**, incluida invalidación de la cookie anterior, rechazo de acceso administrativo desde otra cuenta, formularios históricos, cambio de permisos y todas las rutas sociales. La suite completa usó un hasher rápido solo durante las pruebas; la configuración de contraseñas de la aplicación permanece intacta.
- `node scripts/test_session_guard.cjs`: aprobado; cubre BFCache, historial, pestañas/ventanas, sesión expirada, fallo de red y verificaciones pendientes al abandonar la página.
- `node scripts/test_social_navigation.cjs`: aprobado; cubre las nueve rutas, recarga lógica, Atrás/Adelante sin duplicar historial y clics para abrir otra pestaña.
- `node scripts/test_admin_user_form.cjs`: aprobado, conservando la regresión previa del RUT y de privilegios técnicos.
- `manage.py check`, revisión de migraciones, sintaxis de JavaScript, `bash -n scripts/deploy_aws.sh` y `git diff --check`: sin incidencias.
- Navegador local: administrador → cerrar sesión desde el menú → iniciar como asistente → Atrás dos veces. Se mantuvo el panel social sin controles administrativos. Recargar otra pestaña administrativa antigua también condujo al panel social.
- Navegador local: las nueve pestañas mostraron su dirección y panel correspondiente; cada una conservó su sección después de recargar. Atrás desde Mantenedores abrió Metas y Adelante volvió a Mantenedores. Sin errores de consola en el panel social revisado.

## Publicación

No hay migración nueva ni cambio manual de datos. La comprobación local no acredita la instancia pública ni MariaDB. Tras incorporar a `main`, ejecutar en EC2:

```bash
cd ~/proyectointegrado && bash scripts/deploy_aws.sh
```

Después recargar con Ctrl+F5 para cargar los nuevos scripts y repetir el flujo de acceso. La corrección protege los documentos cargados con esta versión; una pestaña abierta antes del despliegue debe recargarse primero.
