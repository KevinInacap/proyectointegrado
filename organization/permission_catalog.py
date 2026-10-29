"""Catálogo de permisos institucionales y consulta de definiciones vigentes."""
from copy import deepcopy

from .models import PermissionDefinition


SYSTEM_PERMISSIONS_CATALOG = [
    {
        'module_id': 'delegaciones',
        'module_name': 'Delegaciones Municipales',
        'icon': 'bi-building',
        'description': 'Gestión de recintos y ámbito territorial comunal',
        'permissions': [
            {'code': 'delegaciones.view', 'name': 'Ver Delegaciones', 'desc': 'Consultar información y listado de delegaciones'},
            {'code': 'delegaciones.create', 'name': 'Crear Delegación', 'desc': 'Registrar nuevas unidades territoriales'},
            {'code': 'delegaciones.edit', 'name': 'Editar Delegación', 'desc': 'Modificar dirección, ámbito y datos'},
            {'code': 'delegaciones.delete', 'name': 'Inactivar / Borrar', 'desc': 'Suspender o dar de baja una delegación'},
        ]
    },
    {
        'module_id': 'usuarios',
        'module_name': 'Gestión de Usuarios y Personal',
        'icon': 'bi-people',
        'description': 'Control de cuentas de funcionarios municipales y perfiles',
        'permissions': [
            {'code': 'usuarios.view', 'name': 'Ver Funcionarios', 'desc': 'Listar funcionarios y consultar perfiles'},
            {'code': 'usuarios.create', 'name': 'Crear Funcionarios', 'desc': 'Registrar nuevas cuentas de usuario'},
            {'code': 'usuarios.edit', 'name': 'Modificar Cuentas', 'desc': 'Editar datos, delegación, cargo y roles'},
            {'code': 'usuarios.toggle_status', 'name': 'Activar/Desactivar', 'desc': 'Habilitar o suspender acceso al sistema'},
            {'code': 'usuarios.reset_password', 'name': 'Resetear Contraseñas', 'desc': 'Asignar nueva contraseña de acceso'},
            {'code': 'usuarios.delete', 'name': 'Eliminar Usuarios', 'desc': 'Borrado lógico o permanente de cuentas'},
        ]
    },
    {
        'module_id': 'cargos',
        'module_name': 'Cargos y Paneles',
        'icon': 'bi-person-badge',
        'description': 'Administración del cargo que determina el panel institucional de entrada',
        'permissions': [
            {'code': 'cargos.view', 'name': 'Ver Cargos', 'desc': 'Consultar cargos disponibles y su asignación a paneles'},
            {'code': 'cargos.create', 'name': 'Crear Cargos', 'desc': 'Registrar nuevos cargos institucionales'},
            {'code': 'cargos.edit', 'name': 'Editar Cargos', 'desc': 'Modificar nombre, descripción o estado de un cargo'},
            {'code': 'cargos.delete', 'name': 'Inactivar Cargos', 'desc': 'Inactivar cargos sin funcionarios asignados'},
        ]
    },
    {
        'module_id': 'roles',
        'module_name': 'Roles y Matriz de Permisos',
        'icon': 'bi-shield-check',
        'description': 'Gestión de perfiles y asignación de permisos del sistema',
        'permissions': [
            {'code': 'roles.view', 'name': 'Ver Roles y Privilegios', 'desc': 'Visualizar roles configurados y permisos'},
            {'code': 'roles.create', 'name': 'Crear Nuevos Roles', 'desc': 'Definir nuevos perfiles con permisos personalizados'},
            {'code': 'roles.edit', 'name': 'Editar Matriz y Permisos', 'desc': 'Modificar asignación de privilegios a roles'},
            {'code': 'roles.delete', 'name': 'Eliminar Roles', 'desc': 'Dar de baja roles no protegidos'},
            {'code': 'roles.manage_features', 'name': 'Administrar Funciones', 'desc': 'Registrar nuevas funciones y privilegios al sistema'},
        ]
    },
    {
        'module_id': 'metas',
        'module_name': 'Metas e Indicadores SGR',
        'icon': 'bi-bullseye',
        'description': 'Medición de metas de atención ciudadana y desempeño',
        'permissions': [
            {'code': 'metas.view', 'name': 'Ver Metas e Indicadores', 'desc': 'Consultar cumplimiento y metas asignadas'},
            {'code': 'metas.create', 'name': 'Crear Metas Mensuales', 'desc': 'Definir nuevas metas territoriales'},
            {'code': 'metas.edit', 'name': 'Actualizar Indicadores', 'desc': 'Registrar avances y mediciones diarias'},
            {'code': 'metas.delete', 'name': 'Anular Metas', 'desc': 'Eliminar o recalibrar metas fijadas'},
        ]
    },
    {
        'module_id': 'tipo_atencion',
        'module_name': 'Catálogo de Atención Municipal',
        'icon': 'bi-tags',
        'description': 'Tipos de atención, sub-atenciones y servicios',
        'permissions': [
            {'code': 'tipo_atencion.view', 'name': 'Ver Catálogo de Servicios', 'desc': 'Consultar tipos y sub-tipos vigentes'},
            {'code': 'tipo_atencion.create', 'name': 'Agregar Nuevos Servicios', 'desc': 'Crear tipos y sub-atenciones'},
            {'code': 'tipo_atencion.edit', 'name': 'Editar Servicios', 'desc': 'Modificar descripciones y clasificaciones'},
            {'code': 'tipo_atencion.delete', 'name': 'Desactivar Servicios', 'desc': 'Inactivar servicios obsoletos'},
        ]
    },
    {
        'module_id': 'atenciones',
        'module_name': 'Atenciones y Trámites Ciudadanos',
        'icon': 'bi-headset',
        'description': 'Registro operativo, tickets y atención en terreno',
        'permissions': [
            {'code': 'atenciones.view', 'name': 'Ver Registro de Atenciones', 'desc': 'Consultar bitácora general de atenciones'},
            {'code': 'atenciones.create', 'name': 'Registrar Nueva Atención', 'desc': 'Ingresar solicitud ciudadana o trámite'},
            {'code': 'atenciones.edit', 'name': 'Editar Atenciones', 'desc': 'Modificar estado, evidencia y notas'},
            {'code': 'atenciones.validate', 'name': 'Validar / Aprobar', 'desc': 'Rol Verificador: autorizar atenciones con evidencia'},
            {'code': 'atenciones.reject', 'name': 'Observar / Rechazar', 'desc': 'Devolver trámites incompletos o sin respaldo'},
            {'code': 'atenciones.export', 'name': 'Exportar Registros', 'desc': 'Descargar atenciones en Excel y PDF'},
        ]
    },
    {
        'module_id': 'vecinos',
        'module_name': 'Vecinos y Casos Sociales',
        'icon': 'bi-person-vcard',
        'description': 'Padrón de vecinos, ayudas sociales y compromisos',
        'permissions': [
            {'code': 'vecinos.view', 'name': 'Ver Padrón de Vecinos', 'desc': 'Consultar ficha de vecinos y antecedentes'},
            {'code': 'vecinos.create', 'name': 'Registrar Nuevo Vecino', 'desc': 'Ingresar vecino con RUT y domicilio'},
            {'code': 'vecinos.edit', 'name': 'Modificar Datos de Vecinos', 'desc': 'Actualizar teléfono, dirección y sector'},
            {'code': 'vecinos.social_aid', 'name': 'Gestionar Casos Sociales', 'desc': 'Vincular subsidios, ayudas y asistencias'},
            {'code': 'vecinos.delete', 'name': 'Eliminar Vecino', 'desc': 'Dar de baja registros duplicados o erróneos'},
            {'code': 'vecinos.export', 'name': 'Exportar Padrón Comunal', 'desc': 'Descarga oficial de registros a Excel'},
        ]
    },
    {
        'module_id': 'reportes',
        'module_name': 'Reportes y Estadísticas Oficiales',
        'icon': 'bi-bar-chart-line',
        'description': 'Generación de informes gerenciales e indicadores',
        'permissions': [
            {'code': 'reportes.view', 'name': 'Visualizar Dashboard y Métricas', 'desc': 'Acceso a gráficos y tableros interactivos'},
            {'code': 'reportes.export_excel', 'name': 'Descargar Excel Oficial', 'desc': 'Generación de planillas consolidadas'},
            {'code': 'reportes.export_pdf', 'name': 'Generar PDF Institucional', 'desc': 'Informes formales con timbre municipal'},
        ]
    },
    {
        'module_id': 'auditoria',
        'module_name': 'Auditoría Transversal y Sistema',
        'icon': 'bi-clock-history',
        'description': 'Trazabilidad de cambios, seguridad y administración',
        'permissions': [
            {'code': 'auditoria.view', 'name': 'Ver Log de Auditoría', 'desc': 'Rastrear quién, cuándo y qué se modificó'},
            {'code': 'auditoria.config', 'name': 'Parámetros del Sistema', 'desc': 'Configuración global y seguridad avanzada'},
        ]
    }
]

def _permissions_catalog():
    catalog = deepcopy(SYSTEM_PERMISSIONS_CATALOG)
    modules = {module['module_id']: module for module in catalog}
    definitions = {
        permission.code: permission
        for permission in PermissionDefinition.objects.filter(deleted_at__isnull=True).order_by('module_id', 'name')
    }
    known_codes = set()
    for module in catalog:
        for item in module['permissions']:
            known_codes.add(item['code'])
            definition = definitions.get(item['code'])
            if definition:
                item['name'] = definition.name
                item['desc'] = definition.description

    for permission in definitions.values():
        if permission.code in known_codes:
            continue
        target = modules.get(permission.module_id)
        if not target:
            target = {
                'module_id': permission.module_id,
                'module_name': permission.module_id.replace('_', ' ').title(),
                'icon': 'bi-puzzle',
                'description': 'Permisos personalizados del sistema',
                'permissions': [],
            }
            catalog.append(target)
            modules[permission.module_id] = target
        target['permissions'].append({
            'code': permission.code,
            'name': permission.name,
            'desc': permission.description,
        })
    return catalog


def _all_system_perm_codes():
    codes = []
    for mod in _permissions_catalog():
        for p in mod['permissions']:
            codes.append(p['code'])
    return codes
