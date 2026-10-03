import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from .models import UserProfile, Role, Delegation, Position
from core.models import AuditLog

def _get_request_data(request):
    """Auxiliar para parsear payload JSON o form-data"""
    if request.content_type == 'application/json':
        try:
            return json.loads(request.body.decode('utf-8'))
        except Exception:
            return {}
    return request.POST

def api_users_list(request):
    """
    Retorna la lista completa de usuarios y perfiles desde la base de datos,
    junto con los catálogos de delegaciones, cargos y roles.
    """
    profiles = UserProfile.objects.select_related('user', 'delegation', 'position').prefetch_related('roles').filter(deleted_at__isnull=True).order_by('full_name')
    
    users_data = []
    for p in profiles:
        users_data.append({
            'id': p.id,
            'user_id': p.user.id if p.user else None,
            'username': p.user.username if p.user else '',
            'full_name': p.full_name,
            'email': p.email,
            'rut': p.rut,
            'status': p.status,
            'is_active': p.user.is_active if p.user else (p.status == 'Activo'),
            'is_staff': p.user.is_staff if p.user else False,
            'is_superuser': p.user.is_superuser if p.user else False,
            'delegation_id': p.delegation.id if p.delegation else None,
            'delegation_name': p.delegation.name if p.delegation else 'Sin delegación',
            'position_id': p.position.id if p.position else None,
            'position_name': p.position.name if p.position else 'Sin cargo asignado',
            'roles': [{'id': r.id, 'name': r.name} for r in p.roles.all()],
            'roles_str': ', '.join([r.name for r in p.roles.all()]) or 'Sin rol',
            'created_at': p.created_at.strftime('%d/%m/%Y %H:%M') if getattr(p, 'created_at', None) else '',
        })
        
    delegations = [{'id': d.id, 'name': d.name} for d in Delegation.objects.filter(status='Activo').order_by('name')]
    positions = [{'id': p.id, 'name': p.name} for p in Position.objects.filter(status='Activo').order_by('name')]
    roles = [{'id': r.id, 'name': r.name, 'description': r.description} for r in Role.objects.all().order_by('name')]

    total = len(users_data)
    activos = sum(1 for u in users_data if u['status'] == 'Activo')
    inactivos = total - activos
    admins = sum(1 for u in users_data if u['is_superuser'] or any('Admin' in r['name'] for r in u['roles']))

    return JsonResponse({
        'success': True,
        'users': users_data,
        'delegations': delegations,
        'positions': positions,
        'roles': roles,
        'summary': {
            'total': total,
            'activos': activos,
            'inactivos': inactivos,
            'admins': admins
        }
    })

@csrf_exempt
def api_user_create(request):
    """
    Crea un nuevo usuario en auth_user y su perfil institucional en UserProfile,
    con auditoría en la base de datos.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
        
    data = _get_request_data(request)
    
    username = data.get('username', '').strip()
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    rut = data.get('rut', '').strip()
    password = data.get('password', '').strip() or 'MuniLaSerena2026!'
    status = data.get('status', 'Activo')
    delegation_id = data.get('delegation_id')
    position_id = data.get('position_id')
    role_ids = data.get('role_ids', [])
    is_staff = bool(data.get('is_staff', False))
    is_superuser = bool(data.get('is_superuser', False))

    if not username or not full_name or not email or not rut:
        return JsonResponse({'success': False, 'message': 'Nombre, RUT, Correo y Usuario son obligatorios.'}, status=400)

    # Validaciones de unicidad
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({'success': False, 'message': f"El nombre de usuario '{username}' ya está en uso."}, status=400)
    
    if UserProfile.objects.filter(rut=rut).exists():
        return JsonResponse({'success': False, 'message': f"El RUT '{rut}' ya se encuentra registrado."}, status=400)

    if UserProfile.objects.filter(email__iexact=email).exists():
        return JsonResponse({'success': False, 'message': f"El correo institucional '{email}' ya se encuentra registrado."}, status=400)

    try:
        with transaction.atomic():
            # Crear cuenta de usuario Django
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=full_name.split()[0] if full_name else '',
                last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
            )
            user.is_active = (status == 'Activo')
            user.is_staff = is_staff or is_superuser
            user.is_superuser = is_superuser
            user.save()

            # Delegación y Cargo
            delegation = Delegation.objects.filter(id=delegation_id).first() if delegation_id else None
            position = Position.objects.filter(id=position_id).first() if position_id else None

            # Crear Perfil Institucional
            profile = UserProfile.objects.create(
                user=user,
                rut=rut,
                full_name=full_name,
                email=email,
                delegation=delegation,
                position=position,
                status=status
            )

            # Asignar roles
            if role_ids:
                roles = Role.objects.filter(id__in=role_ids)
                profile.roles.set(roles)

            # Registro de Auditoría
            current_admin = request.user if request.user.is_authenticated else user
            AuditLog.objects.create(
                user=current_admin,
                affected_table='usuario',
                affected_record_id=str(profile.id),
                action='CREATE',
                new_value={
                    'username': username,
                    'full_name': full_name,
                    'rut': rut,
                    'email': email,
                    'status': status,
                    'delegation': delegation.name if delegation else None,
                    'position': position.name if position else None,
                    'roles': [r.name for r in profile.roles.all()]
                }
            )

        return JsonResponse({
            'success': True,
            'message': f"Usuario '{full_name}' creado exitosamente en la base de datos.",
            'user_id': profile.id
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Error al crear usuario: {str(e)}"}, status=500)

@csrf_exempt
def api_user_update(request, pk):
    """
    Actualiza datos de un usuario existente, roles, privilegios y delegación.
    """
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    profile = get_object_or_404(UserProfile, id=pk)
    data = _get_request_data(request)

    full_name = data.get('full_name', '').strip() or profile.full_name
    email = data.get('email', '').strip().lower() or profile.email
    rut = data.get('rut', '').strip() or profile.rut
    status = data.get('status') or profile.status
    delegation_id = data.get('delegation_id')
    position_id = data.get('position_id')
    role_ids = data.get('role_ids')
    password = data.get('password', '').strip()
    is_staff = data.get('is_staff')
    is_superuser = data.get('is_superuser')

    # Validar que no choque RUT o Email con otro usuario
    if UserProfile.objects.filter(rut=rut).exclude(id=profile.id).exists():
        return JsonResponse({'success': False, 'message': f"El RUT '{rut}' pertenece a otro funcionario."}, status=400)
    
    if UserProfile.objects.filter(email__iexact=email).exclude(id=profile.id).exists():
        return JsonResponse({'success': False, 'message': f"El correo '{email}' pertenece a otro funcionario."}, status=400)

    try:
        with transaction.atomic():
            old_value = {
                'full_name': profile.full_name,
                'email': profile.email,
                'rut': profile.rut,
                'status': profile.status,
                'delegation': profile.delegation.name if profile.delegation else None,
                'position': profile.position.name if profile.position else None,
            }

            profile.full_name = full_name
            profile.email = email
            profile.rut = rut
            profile.status = status

            if delegation_id is not None:
                profile.delegation = Delegation.objects.filter(id=delegation_id).first() if delegation_id else None
            
            if position_id is not None:
                profile.position = Position.objects.filter(id=position_id).first() if position_id else None

            if role_ids is not None:
                profile.roles.set(Role.objects.filter(id__in=role_ids))

            profile.save()

            # Actualizar cuenta de auth_user asociada
            user = profile.user
            if user:
                user.email = email
                user.is_active = (status == 'Activo')
                if full_name:
                    parts = full_name.split()
                    user.first_name = parts[0]
                    user.last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
                if is_staff is not None:
                    user.is_staff = bool(is_staff)
                if is_superuser is not None:
                    user.is_superuser = bool(is_superuser)
                if password:
                    user.set_password(password)
                user.save()

            # Auditoría
            current_admin = request.user if request.user.is_authenticated else user
            AuditLog.objects.create(
                user=current_admin,
                affected_table='usuario',
                affected_record_id=str(profile.id),
                action='UPDATE',
                previous_value=old_value,
                new_value={
                    'full_name': profile.full_name,
                    'email': profile.email,
                    'rut': profile.rut,
                    'status': profile.status,
                    'delegation': profile.delegation.name if profile.delegation else None,
                    'position': profile.position.name if profile.position else None,
                    'roles': [r.name for r in profile.roles.all()]
                }
            )

        return JsonResponse({
            'success': True,
            'message': f"Usuario '{full_name}' actualizado correctamente."
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Error al actualizar: {str(e)}"}, status=500)

@csrf_exempt
def api_user_toggle_status(request, pk):
    """
    Habilita o Inhabilita un usuario con 1 click.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    profile = get_object_or_404(UserProfile, id=pk)
    
    # Prevenir deshabilitar al usuario admin principal
    if profile.user and profile.user.username == 'admin' and profile.status == 'Activo':
        return JsonResponse({'success': False, 'message': 'No es posible inhabilitar la cuenta de Administrador Principal del sistema.'}, status=400)

    nuevo_estado = 'Inactivo' if profile.status == 'Activo' else 'Activo'
    profile.status = nuevo_estado
    profile.save()

    if profile.user:
        profile.user.is_active = (nuevo_estado == 'Activo')
        profile.user.save()

    # Auditoría
    current_admin = request.user if request.user.is_authenticated else profile.user
    AuditLog.objects.create(
        user=current_admin,
        affected_table='usuario',
        affected_record_id=str(profile.id),
        action='UPDATE',
        new_value={'status': nuevo_estado, 'action_type': 'TOGGLE_STATUS'}
    )

    action_label = "habilitado" if nuevo_estado == 'Activo' else "inhabilitado"
    return JsonResponse({
        'success': True,
        'new_status': nuevo_estado,
        'is_active': (nuevo_estado == 'Activo'),
        'message': f"Usuario '{profile.full_name}' ha sido {action_label} exitosamente."
    })

@csrf_exempt
def api_user_delete(request, pk):
    """
    Elimina un usuario de la base de datos (con salvaguardas institucionales).
    """
    if request.method not in ['POST', 'DELETE']:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    profile = get_object_or_404(UserProfile, id=pk)
    
    # Salvaguarda: No borrar admin principal
    if profile.user and profile.user.username == 'admin':
        return JsonResponse({'success': False, 'message': 'Por seguridad institucional, la cuenta de Administrador Principal no puede ser eliminada.'}, status=400)

    nombre = profile.full_name
    user_auth = profile.user

    try:
        with transaction.atomic():
            current_admin = request.user if request.user.is_authenticated else user_auth
            AuditLog.objects.create(
                user=current_admin,
                affected_table='usuario',
                affected_record_id=str(profile.id),
                action='DELETE',
                previous_value={'full_name': nombre, 'rut': profile.rut, 'email': profile.email}
            )
            
            # Borrar perfil y cuenta asociada
            profile.delete()
            if user_auth:
                user_auth.delete()

        return JsonResponse({
            'success': True,
            'message': f"El usuario '{nombre}' fue eliminado exitosamente de la base de datos."
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Error al eliminar usuario: {str(e)}"}, status=500)

@csrf_exempt
def api_user_reset_password(request, pk):
    """
    Restablece la contraseña de un usuario directamente desde el panel de administración.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    profile = get_object_or_404(UserProfile, id=pk)
    data = _get_request_data(request)
    new_password = data.get('password', '').strip()

    if not new_password or len(new_password) < 6:
        return JsonResponse({'success': False, 'message': 'La contraseña debe tener al menos 6 caracteres.'}, status=400)

    if not profile.user:
        return JsonResponse({'success': False, 'message': 'El perfil no tiene una cuenta de autenticación vinculada.'}, status=400)

    profile.user.set_password(new_password)
    profile.user.save()

    current_admin = request.user if request.user.is_authenticated else profile.user
    AuditLog.objects.create(
        user=current_admin,
        affected_table='usuario',
        affected_record_id=str(profile.id),
        action='UPDATE',
        new_value={'action_type': 'PASSWORD_RESET'}
    )

    return JsonResponse({
        'success': True,
        'message': f"Contraseña actualizada con éxito para el usuario '{profile.full_name}'."
    })

def api_audit_logs(request):
    """
    Retorna el historial de auditoría y trazabilidad de acciones realizadas por administradores.
    """
    logs_qs = AuditLog.objects.select_related('user').order_by('-created_at')[:150]
    logs_data = []

    for l in logs_qs:
        admin_name = 'Sistema Municipal'
        admin_username = 'sistema'
        if l.user:
            admin_name = l.user.get_full_name() or l.user.username
            admin_username = l.user.username

        desc = ""
        nv = l.new_value or {}
        ov = l.previous_value or {}

        if l.action == 'CREATE':
            target_name = nv.get('full_name') or nv.get('code') or f"#{l.affected_record_id}"
            desc = f"Creó nuevo registro en {l.affected_table}: {target_name}"
        elif l.action == 'UPDATE':
            if nv.get('action_type') == 'TOGGLE_STATUS':
                desc = f"Cambió estado a '{nv.get('status')}' (ID #{l.affected_record_id})"
            elif nv.get('action_type') == 'PASSWORD_RESET':
                desc = f"Restableció contraseña de acceso para usuario ID #{l.affected_record_id}"
            else:
                target_name = nv.get('full_name') or ov.get('full_name') or f"ID #{l.affected_record_id}"
                desc = f"Modificó perfil / roles de {target_name}"
        elif l.action == 'DELETE':
            target_name = ov.get('full_name') or f"ID #{l.affected_record_id}"
            desc = f"Eliminó permanentemente a: {target_name}"
        elif l.action == 'VALIDATE':
            decision = nv.get('decision', 'Revisado')
            desc = f"Validó actividad ({decision})"
        else:
            desc = f"Operación {l.action} en {l.affected_table}"

        logs_data.append({
            'id': l.id,
            'timestamp': l.created_at.strftime('%d/%m/%Y %H:%M:%S') if l.created_at else '',
            'admin_username': admin_username,
            'admin_name': admin_name,
            'action': l.action,
            'affected_table': l.affected_table,
            'affected_record_id': l.affected_record_id,
            'description': desc,
            'details': nv or ov
        })

    return JsonResponse({
        'success': True,
        'logs': logs_data
    })


# ==============================================================================
# CATÁLOGO Y GESTIÓN DE ROLES Y MATRIZ DE PERMISOS (RBAC MYADMIN)
# ==============================================================================

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

def _all_system_perm_codes():
    codes = []
    for mod in SYSTEM_PERMISSIONS_CATALOG:
        for p in mod['permissions']:
            codes.append(p['code'])
    return codes

def api_permissions_catalog(request):
    """
    Retorna el catálogo completo estructurado de módulos, permisos y funciones del sistema.
    """
    total_perms = sum(len(m['permissions']) for m in SYSTEM_PERMISSIONS_CATALOG)
    return JsonResponse({
        'success': True,
        'catalog': SYSTEM_PERMISSIONS_CATALOG,
        'total_permissions': total_perms,
        'modules_count': len(SYSTEM_PERMISSIONS_CATALOG)
    })

def api_roles_list(request):
    """
    Retorna la lista completa de roles con sus permisos asignados, contador de usuarios,
    indicadores de sistema y el catálogo de funciones disponibles (MyAdmin).
    """
    roles_qs = Role.objects.filter(deleted_at__isnull=True).order_by('id')
    roles_data = []

    for r in roles_qs:
        perms = r.permissions_data or []
        users_qs = r.users.filter(deleted_at__isnull=True)
        users_count = users_qs.count()
        users_sample = list(users_qs.values_list('full_name', flat=True)[:5])

        roles_data.append({
            'id': r.id,
            'name': r.name,
            'description': r.description or 'Sin descripción',
            'is_system': r.is_system,
            'permissions': perms,
            'permissions_count': len(perms),
            'users_count': users_count,
            'users_sample': users_sample,
            'created_at': r.created_at.strftime('%d/%m/%Y %H:%M') if r.created_at else '',
            'updated_at': r.updated_at.strftime('%d/%m/%Y %H:%M') if r.updated_at else '',
        })

    all_codes = _all_system_perm_codes()
    total_system_roles = sum(1 for r in roles_data if r['is_system'])
    total_custom_roles = len(roles_data) - total_system_roles

    return JsonResponse({
        'success': True,
        'roles': roles_data,
        'catalog': SYSTEM_PERMISSIONS_CATALOG,
        'summary': {
            'total_roles': len(roles_data),
            'system_roles': total_system_roles,
            'custom_roles': total_custom_roles,
            'total_permissions_available': len(all_codes),
        }
    })

@csrf_exempt
def api_role_create(request):
    """
    Crea un nuevo rol en la base de datos con su matriz de permisos asignada y auditoría (MyAdmin).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    data = _get_request_data(request)
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    permissions = data.get('permissions', [])
    is_system = bool(data.get('is_system', False))

    if not name:
        return JsonResponse({'success': False, 'message': 'El nombre del rol es obligatorio.'}, status=400)

    if Role.objects.filter(name__iexact=name, deleted_at__isnull=True).exists():
        return JsonResponse({'success': False, 'message': f"Ya existe un rol activo con el nombre '{name}'."}, status=400)

    try:
        with transaction.atomic():
            role = Role.objects.create(
                name=name,
                description=description,
                is_system=is_system,
                permissions_data=permissions
            )

            current_admin = request.user if request.user.is_authenticated else None
            AuditLog.objects.create(
                user=current_admin,
                affected_table='rol',
                affected_record_id=str(role.id),
                action='CREATE',
                new_value={
                    'name': name,
                    'description': description,
                    'permissions_count': len(permissions),
                    'permissions': permissions,
                    'is_system': is_system,
                }
            )

        return JsonResponse({
            'success': True,
            'message': f"Rol '{name}' creado exitosamente con {len(permissions)} permisos.",
            'role': {
                'id': role.id,
                'name': role.name,
                'description': role.description,
                'is_system': role.is_system,
                'permissions': role.permissions_data,
                'permissions_count': len(role.permissions_data or []),
                'users_count': 0,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Error al crear el rol: {str(e)}"}, status=500)

@csrf_exempt
def api_role_update(request, pk):
    """
    Modifica un rol existente, su descripción y su matriz de funciones/permisos (MyAdmin).
    """
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    role = get_object_or_404(Role, id=pk)
    data = _get_request_data(request)

    new_name = data.get('name', '').strip() or role.name
    new_description = data.get('description', '').strip()
    if 'description' not in data:
        new_description = role.description

    new_permissions = data.get('permissions')
    if new_permissions is None:
        new_permissions = role.permissions_data

    # Validar duplicados si se cambia el nombre
    if new_name != role.name and Role.objects.filter(name__iexact=new_name, deleted_at__isnull=True).exclude(id=role.id).exists():
        return JsonResponse({'success': False, 'message': f"El nombre '{new_name}' ya se encuentra en uso por otro rol."}, status=400)

    try:
        with transaction.atomic():
            prev_perms_count = len(role.permissions_data or [])
            prev_name = role.name

            role.name = new_name
            role.description = new_description
            role.permissions_data = new_permissions
            role.save()

            current_admin = request.user if request.user.is_authenticated else None
            AuditLog.objects.create(
                user=current_admin,
                affected_table='rol',
                affected_record_id=str(role.id),
                action='UPDATE',
                previous_value={'name': prev_name, 'permissions_count': prev_perms_count},
                new_value={
                    'name': new_name,
                    'description': new_description,
                    'permissions_count': len(new_permissions),
                    'permissions': new_permissions,
                }
            )

        return JsonResponse({
            'success': True,
            'message': f"Rol '{role.name}' actualizado correctamente con {len(new_permissions)} permisos.",
            'role': {
                'id': role.id,
                'name': role.name,
                'description': role.description,
                'is_system': role.is_system,
                'permissions': role.permissions_data,
                'permissions_count': len(role.permissions_data or []),
                'users_count': role.users.filter(deleted_at__isnull=True).count(),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Error al actualizar el rol: {str(e)}"}, status=500)

@csrf_exempt
def api_role_delete(request, pk):
    """
    Elimina un rol de la base de datos (con verificación de protección de sistema y usuarios).
    """
    if request.method not in ['POST', 'DELETE']:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    role = get_object_or_404(Role, id=pk)

    # Protección de roles base del sistema
    protected_roles = ['Administrador', 'Operador', 'Consultor', 'Verificador']
    if role.name in protected_roles or (role.is_system and role.name == 'Administrador'):
        return JsonResponse({
            'success': False,
            'message': f"El rol '{role.name}' es un rol protegido fundamental de la plataforma municipal y no puede ser eliminado."
        }, status=403)

    assigned_users = role.users.filter(deleted_at__isnull=True).count()
    if assigned_users > 0:
        return JsonResponse({
            'success': False,
            'message': f"No se puede eliminar el rol '{role.name}' porque actualmente tiene {assigned_users} funcionario(s) asignado(s). Reasigne a los usuarios antes de borrarlo."
        }, status=400)

    try:
        with transaction.atomic():
            current_admin = request.user if request.user.is_authenticated else None
            role_name = role.name
            role_id = role.id

            AuditLog.objects.create(
                user=current_admin,
                affected_table='rol',
                affected_record_id=str(role_id),
                action='DELETE',
                previous_value={
                    'name': role_name,
                    'description': role.description,
                    'permissions_count': len(role.permissions_data or []),
                }
            )

            role.delete()

        return JsonResponse({
            'success': True,
            'message': f"El rol '{role_name}' ha sido eliminado exitosamente del sistema."
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Error al eliminar el rol: {str(e)}"}, status=500)

@csrf_exempt
def api_role_duplicate(request, pk):
    """
    Duplica un rol existente junto con toda su matriz de permisos (función phpMyAdmin).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    origin_role = get_object_or_404(Role, id=pk)
    data = _get_request_data(request)

    base_name = data.get('name', '').strip() or f"{origin_role.name} (Copia)"
    candidate_name = base_name
    counter = 1
    while Role.objects.filter(name__iexact=candidate_name, deleted_at__isnull=True).exists():
        counter += 1
        candidate_name = f"{base_name} {counter}"

    try:
        with transaction.atomic():
            new_role = Role.objects.create(
                name=candidate_name,
                description=f"Copia basada en {origin_role.name}: {origin_role.description}",
                is_system=False,
                permissions_data=list(origin_role.permissions_data or [])
            )

            current_admin = request.user if request.user.is_authenticated else None
            AuditLog.objects.create(
                user=current_admin,
                affected_table='rol',
                affected_record_id=str(new_role.id),
                action='CREATE',
                new_value={
                    'name': candidate_name,
                    'cloned_from': origin_role.name,
                    'permissions_count': len(new_role.permissions_data),
                }
            )

        return JsonResponse({
            'success': True,
            'message': f"Rol clonado exitosamente como '{candidate_name}'.",
            'role': {
                'id': new_role.id,
                'name': new_role.name,
                'description': new_role.description,
                'is_system': False,
                'permissions': new_role.permissions_data,
                'permissions_count': len(new_role.permissions_data),
                'users_count': 0,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Error al clonar rol: {str(e)}"}, status=500)

@csrf_exempt
def api_add_custom_permission(request):
    """
    Permite al Super Administrador registrar una nueva función/privilegio dinámico en el catálogo.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    data = _get_request_data(request)
    module_id = data.get('module_id', '').strip()
    code = data.get('code', '').strip()
    name = data.get('name', '').strip()
    desc = data.get('desc', '').strip()

    if not code or not name:
        return JsonResponse({'success': False, 'message': 'Código y Nombre de la función son requeridos.'}, status=400)

    # Buscar módulo o agregar a existente
    target_mod = next((m for m in SYSTEM_PERMISSIONS_CATALOG if m['module_id'] == module_id), None)
    if not target_mod:
        target_mod = SYSTEM_PERMISSIONS_CATALOG[0]

    # Verificar si ya existe
    if any(p['code'] == code for p in target_mod['permissions']):
        return JsonResponse({'success': False, 'message': f"La función con código '{code}' ya existe."}, status=400)

    target_mod['permissions'].append({
        'code': code,
        'name': name,
        'desc': desc
    })

    return JsonResponse({
        'success': True,
        'message': f"Nueva función '{name}' agregada al catálogo de privilegios.",
        'catalog': SYSTEM_PERMISSIONS_CATALOG
    })


