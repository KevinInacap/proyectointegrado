from django.db import migrations


PERMISSIONS = [
    ('delegaciones', 'delegaciones.view', 'Ver Delegaciones', 'Consultar información y listado de delegaciones'),
    ('delegaciones', 'delegaciones.create', 'Crear Delegación', 'Registrar nuevas unidades territoriales'),
    ('delegaciones', 'delegaciones.edit', 'Editar Delegación', 'Modificar dirección, ámbito y datos'),
    ('delegaciones', 'delegaciones.delete', 'Inactivar / Borrar', 'Suspender o dar de baja una delegación'),
    ('usuarios', 'usuarios.view', 'Ver Funcionarios', 'Listar funcionarios y consultar perfiles'),
    ('usuarios', 'usuarios.create', 'Crear Funcionarios', 'Registrar nuevas cuentas de usuario'),
    ('usuarios', 'usuarios.edit', 'Modificar Cuentas', 'Editar datos, delegación, cargo y roles'),
    ('usuarios', 'usuarios.toggle_status', 'Activar/Desactivar', 'Habilitar o suspender acceso al sistema'),
    ('usuarios', 'usuarios.reset_password', 'Resetear Contraseñas', 'Asignar nueva contraseña de acceso'),
    ('usuarios', 'usuarios.delete', 'Eliminar Usuarios', 'Borrado lógico o permanente de cuentas'),
    ('cargos', 'cargos.view', 'Ver Cargos', 'Consultar cargos disponibles y su asignación a paneles'),
    ('cargos', 'cargos.create', 'Crear Cargos', 'Registrar nuevos cargos institucionales'),
    ('cargos', 'cargos.edit', 'Editar Cargos', 'Modificar nombre, descripción o estado de un cargo'),
    ('cargos', 'cargos.delete', 'Inactivar Cargos', 'Inactivar cargos sin funcionarios asignados'),
    ('roles', 'roles.view', 'Ver Roles y Privilegios', 'Visualizar roles configurados y permisos'),
    ('roles', 'roles.create', 'Crear Nuevos Roles', 'Definir nuevos perfiles con permisos personalizados'),
    ('roles', 'roles.edit', 'Editar Matriz y Permisos', 'Modificar asignación de privilegios a roles'),
    ('roles', 'roles.delete', 'Eliminar Roles', 'Dar de baja roles no protegidos'),
    ('roles', 'roles.manage_features', 'Administrar Funciones', 'Registrar nuevas funciones y privilegios al sistema'),
    ('metas', 'metas.view', 'Ver Metas e Indicadores', 'Consultar cumplimiento y metas asignadas'),
    ('metas', 'metas.create', 'Crear Metas Mensuales', 'Definir nuevas metas territoriales'),
    ('metas', 'metas.edit', 'Actualizar Indicadores', 'Registrar avances y mediciones diarias'),
    ('metas', 'metas.delete', 'Anular Metas', 'Eliminar o recalibrar metas fijadas'),
    ('tipo_atencion', 'tipo_atencion.view', 'Ver Catálogo de Servicios', 'Consultar tipos y sub-tipos vigentes'),
    ('tipo_atencion', 'tipo_atencion.create', 'Agregar Nuevos Servicios', 'Crear tipos y sub-atenciones'),
    ('tipo_atencion', 'tipo_atencion.edit', 'Editar Servicios', 'Modificar descripciones y clasificaciones'),
    ('tipo_atencion', 'tipo_atencion.delete', 'Desactivar Servicios', 'Inactivar servicios obsoletos'),
    ('atenciones', 'atenciones.view', 'Ver Registro de Atenciones', 'Consultar bitácora general de atenciones'),
    ('atenciones', 'atenciones.create', 'Registrar Nueva Atención', 'Ingresar solicitud ciudadana o trámite'),
    ('atenciones', 'atenciones.edit', 'Editar Atenciones', 'Modificar estado, evidencia y notas'),
    ('atenciones', 'atenciones.validate', 'Validar / Aprobar', 'Rol Verificador: autorizar atenciones con evidencia'),
    ('atenciones', 'atenciones.reject', 'Observar / Rechazar', 'Devolver trámites incompletos o sin respaldo'),
    ('atenciones', 'atenciones.export', 'Exportar Registros', 'Descargar atenciones en Excel y PDF'),
    ('vecinos', 'vecinos.view', 'Ver Padrón de Vecinos', 'Consultar ficha de vecinos y antecedentes'),
    ('vecinos', 'vecinos.create', 'Registrar Nuevo Vecino', 'Ingresar vecino con RUT y domicilio'),
    ('vecinos', 'vecinos.edit', 'Modificar Datos de Vecinos', 'Actualizar teléfono, dirección y sector'),
    ('vecinos', 'vecinos.social_aid', 'Gestionar Casos Sociales', 'Vincular subsidios, ayudas y asistencias'),
    ('vecinos', 'vecinos.delete', 'Eliminar Vecino', 'Dar de baja registros duplicados o erróneos'),
    ('vecinos', 'vecinos.export', 'Exportar Padrón Comunal', 'Descarga oficial de registros a Excel'),
    ('reportes', 'reportes.view', 'Visualizar Dashboard y Métricas', 'Acceso a gráficos y tableros interactivos'),
    ('reportes', 'reportes.export_excel', 'Descargar Excel Oficial', 'Generación de planillas consolidadas'),
    ('reportes', 'reportes.export_pdf', 'Generar PDF Institucional', 'Informes formales con timbre municipal'),
    ('auditoria', 'auditoria.view', 'Ver Log de Auditoría', 'Rastrear quién, cuándo y qué se modificó'),
    ('auditoria', 'auditoria.config', 'Parámetros del Sistema', 'Configuración global y seguridad avanzada'),
]

ADMIN_ROLE_NAME = 'Administrador'
LEGACY_ADMIN_ROLE_NAME = 'Administrador General'
COARSE_PERMISSIONS = ('lectura', 'edicion', 'derivacion', 'cierre')


def seed_catalog_and_admin_role(apps, schema_editor):
    database = schema_editor.connection.alias
    PermissionDefinition = apps.get_model('organization', 'PermissionDefinition')
    Role = apps.get_model('organization', 'Role')

    for module_id, code, name, description in PERMISSIONS:
        PermissionDefinition.objects.using(database).update_or_create(
            code=code,
            defaults={
                'module_id': module_id,
                'name': name,
                'description': description,
                'is_system': True,
                'deleted_at': None,
            },
        )

    canonical = Role.objects.using(database).filter(name=ADMIN_ROLE_NAME).first()
    legacy = Role.objects.using(database).filter(name=LEGACY_ADMIN_ROLE_NAME).first()
    if canonical and legacy and canonical.pk != legacy.pk:
        raise RuntimeError(
            'Existen dos roles distintos para Administrador; resuelve la duplicidad antes de migrar.'
        )
    role = canonical or legacy
    if role is None:
        role = Role.objects.using(database).create(
            name=ADMIN_ROLE_NAME,
            description='Administración integral de usuarios, configuración, permisos y operación del sistema.',
            is_system=True,
            permissions_data=[],
        )

    role.name = ADMIN_ROLE_NAME
    role.description = role.description or 'Administración integral del sistema.'
    role.is_system = True
    role.deleted_at = None
    role.permissions_data = sorted(
        {str(code).strip().casefold() for code in (role.permissions_data or []) if str(code).strip()}
        | {code for _, code, _, _ in PERMISSIONS}
        | set(COARSE_PERMISSIONS)
    )
    role.save(using=database)


class Migration(migrations.Migration):
    dependencies = [('organization', '0007_clear_unverified_demo_contacts')]
    operations = [
        migrations.RunPython(seed_catalog_and_admin_role, migrations.RunPython.noop),
    ]
