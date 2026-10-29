# Verificación del panel social y edición de funcionarios

Fecha: 27 de octubre de 2026. Entorno: Windows, Python 3.12, Django 6.1.1 y SQLite local. Se utilizaron exclusivamente cuentas y casos ficticios.

## Cambios

- Panel de asistencia social: encabezado y acciones ordenados, indicadores por etapa, filtros etiquetados con restablecimiento y tabla con desplazamiento horizontal propio.
- Se retiró el enlace «Casos y revisión administrativa» del menú de asistencia social. El módulo administrativo conserva su acceso habitual.
- Menú móvil funcional, cierre con Escape, estados accesibles y soporte de movimiento reducido.
- Las cuentas con lectura conservan consulta, exportación e informes; las acciones de escritura requieren el permiso correspondiente. Los casos resueltos no muestran avanzar etapa.
- Editar cargo o roles conserva el RUT histórico cuando la identidad no cambia. Un RUT nuevo o distinto requiere formato y dígito verificador válidos. Se detectan duplicados entre formatos con puntos, sin puntos o K minúscula.
- Guardar cargo/roles conserva por separado los indicadores técnicos de personal y superusuario. Se valida también la reserva del rol SuperAdministrador al asignarlo mediante un cargo, antes de escribir datos.
- Se actualizó la versión de caché del JavaScript administrativo.

## Comprobaciones

- Suite completa: **133 pruebas aprobadas**. La ejecución completa utilizó un hasher rápido exclusivamente en el proceso de pruebas; no se modificó la configuración de contraseñas de la aplicación. La suite previa de 124 pruebas y las 28 pruebas de organización también pasaron con el hasher habitual.
- `python manage.py check`: sin incidencias.
- `python manage.py makemigrations --check --dry-run`: sin migraciones pendientes.
- `node scripts/test_admin_user_form.cjs`: aprobado, incluidos RUT histórico, DV inválido, duplicados y conservación de privilegios.
- `node --check static/js/admin/admin-bundle.js`: aprobado.
- JavaScript del panel renderizado por Django: sintaxis comprobada con y sin permiso de edición.
- Navegador local: búsqueda, filtro de etapa, restablecimiento, visualización de escritorio y móvil (390 px), apertura del menú y cierre por Escape comprobados. Sin errores de consola en el panel social revisado.
- Formulario real: se cambió de Asistente Social a Gestor Territorial una cuenta ficticia con RUT histórico `12.345.678-9`. La operación mostró «Funcionario guardado». La consulta de SQLite confirmó cargo y rol nuevos, RUT intacto, `is_staff=True` e `is_superuser=False`.

## Publicación y alcance

No requiere migración de esquema ni cambios manuales a los datos existentes. Las cuentas ficticias, la base SQLite y las credenciales locales no forman parte del commit.

La verificación local no acredita el despliegue AWS, la base MariaDB de producción ni el envío de correo. Una vez incorporado el cambio a `main`, la instancia se actualiza mediante el procedimiento existente:

```bash
cd ~/proyectointegrado && bash scripts/deploy_aws.sh
```

Después se debe comprobar la versión pública y recargar el navegador. El script existente respalda datos, aplica migraciones pendientes, publica estáticos y reinicia el servicio.

