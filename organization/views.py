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

