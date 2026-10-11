import json
import re
from copy import deepcopy
from functools import wraps
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import UserProfile, Role, Delegation, Position, PermissionDefinition
from core.models import AuditLog, PasswordRecoveryCode


def admin_only(view_func):
    """Autoriza con la cuenta y el rol vigentes, nunca con la sesión editable."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated or not user.is_active:
            return JsonResponse({'success': False, 'message': 'Autenticación requerida.'}, status=403)
        if not user.is_superuser:
            if not UserProfile.objects.filter(
                user=user, status='Activo', deleted_at__isnull=True,
                roles__name='Administrador General', roles__deleted_at__isnull=True,
            ).exists():
                return JsonResponse({'success': False, 'message': 'Se requiere el rol Administrador General.'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapped


def _get_request_data(request):
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
            return data if isinstance(data, dict) else {}
        except (ValueError, UnicodeDecodeError):
            return {}
    return request.POST


def _text(data, key, default=''):
    value = data.get(key, default)
    # Estos campos son texto plano y algunos consumidores los insertan en HTML.
    return value.strip() if isinstance(value, str) and not re.search(r'[<>]', value) else None


def _password(data, key='password'):
    value = data.get(key, '')
    return value if isinstance(value, str) else None


def _protected_account(request, profile):
    return not request.user.is_superuser and (profile.user.is_staff or profile.user.is_superuser)


def _boolean(data, key):
    value = data.get(key)
    if isinstance(value, bool):
        return value
    if value in ('true', '1', 'on', 'True', 1):
        return True
    if value in ('false', '0', 'off', 'False', 0):
        return False
    return None


def _ids(value):
    if not isinstance(value, list) or any(
        isinstance(item, bool) or not str(item).isdigit() for item in value
    ):
        return None
    return list(dict.fromkeys(int(item) for item in value))


def _valid_status(value, allow_blocked=False):
    return value in (('Activo', 'Inactivo', 'Bloqueado') if allow_blocked else ('Activo', 'Inactivo'))


def _validated_roles(value):
    ids = _ids(value)
    if ids is None:
        return None
    roles = list(Role.objects.filter(id__in=ids, deleted_at__isnull=True))
    return roles if len(roles) == len(ids) else None


def _validated_permissions(value):
    if not isinstance(value, list) or any(not isinstance(code, str) for code in value):
        return None
    codes = list(dict.fromkeys(value))
    return codes if set(codes) <= set(_all_system_perm_codes()) else None


def _is_valid_chilean_rut(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:\d{1,8}|\d{1,2}(?:\.\d{3}){1,2})-?[0-9kK]', value.strip()):
        return False
    cleaned = value.replace('-', '').replace('.', '')
    number, verifier = cleaned[:-1], cleaned[-1].upper()
    total, multiplier = 0, 2
    for digit in reversed(number):
        total += int(digit) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1
    result = 11 - (total % 11)
    expected = '0' if result == 11 else ('K' if result == 10 else str(result))
    return verifier == expected


def _validate_delegation_details(data):
    text_fields = ('name', 'scope', 'address', 'phone', 'schedule', 'manager_name', 'description')
    if any(_text(data, field) is None for field in text_fields):
        return 'Los campos de texto deben ser cadenas.'
    if any(re.search(r'[<>]', _text(data, field)) for field in text_fields):
        return 'Los campos de la delegación no pueden contener etiquetas HTML.'
    email = _text(data, 'email')
    if email is None:
        return 'El correo de contacto no tiene un formato válido.'
    if email:
        try:
            validate_email(email)
        except ValidationError:
            return 'El correo de contacto no tiene un formato válido.'
    photo_url = _text(data, 'photo_url')
    if photo_url is None or (photo_url and not re.fullmatch(
        r'(?:/static/(?!.*\.\.)[A-Za-z0-9_./-]+|https?://[^\s"\'<>]+)', photo_url
    )):
        return 'La fotografía debe ser una ruta /static/ segura o una URL http(s) válida.'
    return None


@admin_only
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
        
    delegations = [{'id': d.id, 'name': d.name} for d in Delegation.objects.filter(status='Activo', deleted_at__isnull=True).order_by('name')]
    positions = [{'id': p.id, 'name': p.name} for p in Position.objects.filter(status='Activo', deleted_at__isnull=True).order_by('name')]
    roles = [{'id': r.id, 'name': r.name, 'description': r.description} for r in Role.objects.filter(deleted_at__isnull=True).order_by('name')]

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

@admin_only
def api_user_create(request):
    """
    Crea un nuevo usuario en auth_user y su perfil institucional en UserProfile,
    con auditoría en la base de datos.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
        
    data = _get_request_data(request)
    
    username = _text(data, 'username')
    full_name = _text(data, 'full_name')
    email = (_text(data, 'email') or '').lower()
    rut = _text(data, 'rut')
    password = _password(data)
    status = data.get('status', 'Activo')
    delegation_id = data.get('delegation_id')
    position_id = data.get('position_id')
    role_ids = data.get('role_ids', [])
    is_staff = _boolean(data, 'is_staff') if 'is_staff' in data else False
    is_superuser = _boolean(data, 'is_superuser') if 'is_superuser' in data else False

    if None in (username, full_name, email, rut, password) or is_staff is None or is_superuser is None:
        return JsonResponse({'success': False, 'message': 'Datos de usuario inválidos.'}, status=400)
    if not request.user.is_superuser and (is_staff or is_superuser):
        return JsonResponse({'success': False, 'message': 'Solo un superusuario puede conceder acceso técnico.'}, status=403)
    if not _valid_status(status, True):
        return JsonResponse({'success': False, 'message': 'Estado inválido.'}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'success': False, 'message': 'Correo inválido.'}, status=400)
    roles = _validated_roles(role_ids)
    if roles is None:
        return JsonResponse({'success': False, 'message': 'Roles inválidos.'}, status=400)
    if not password:
        return JsonResponse({'success': False, 'message': 'La contraseña es obligatoria.'}, status=400)
    try:
        validate_password(password, User(username=username, email=email,
                                         first_name=full_name.split()[0] if full_name else '',
                                         last_name=' '.join(full_name.split()[1:])))
    except ValidationError as exc:
        return JsonResponse({'success': False, 'message': 'Contraseña insegura.', 'details': exc.messages}, status=400)
    if not username or not full_name or not email or not rut:
        return JsonResponse({'success': False, 'message': 'Nombre, RUT, Correo y Usuario son obligatorios.'}, status=400)

    if not _is_valid_chilean_rut(rut):
        return JsonResponse({'success': False, 'message': 'RUT inválido. Revisa el número y el dígito verificador.'}, status=400)

    # Validaciones de unicidad
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({'success': False, 'message': f"El nombre de usuario '{username}' ya está en uso."}, status=400)
    
    if UserProfile.objects.filter(rut=rut).exists():
        return JsonResponse({'success': False, 'message': f"El RUT '{rut}' ya se encuentra registrado."}, status=400)

    if UserProfile.objects.filter(email__iexact=email).exists():
        return JsonResponse({'success': False, 'message': f"El correo institucional '{email}' ya se encuentra registrado."}, status=400)

    if delegation_id and _ids([delegation_id]) is None or position_id and _ids([position_id]) is None:
        return JsonResponse({'success': False, 'message': 'Delegación o cargo inválido.'}, status=400)
    delegation = Delegation.objects.filter(id=delegation_id, status='Activo', deleted_at__isnull=True).first() if delegation_id else None
    position = Position.objects.filter(id=position_id, status='Activo', deleted_at__isnull=True).first() if position_id else None
    if delegation_id and not delegation:
        return JsonResponse({'success': False, 'message': 'La delegación seleccionada no existe o está inactiva.'}, status=400)
    if position_id and not position:
        return JsonResponse({'success': False, 'message': 'El cargo seleccionado no existe o está inactivo.'}, status=400)

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

@admin_only
def api_user_update(request, pk):
    """
    Actualiza datos de un usuario existente, roles, privilegios y delegación.
    """
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    profile = get_object_or_404(UserProfile, id=pk, deleted_at__isnull=True)
    data = _get_request_data(request)

    full_name = _text(data, 'full_name', profile.full_name)
    email = (_text(data, 'email', profile.email) or '').lower()
    rut = _text(data, 'rut', profile.rut)
    status = data.get('status') or profile.status
    delegation_id = data.get('delegation_id')
    position_id = data.get('position_id')
    role_ids = data.get('role_ids')
    password = _password(data)
    is_staff = data.get('is_staff')
    is_superuser = data.get('is_superuser')

    if _protected_account(request, profile) or (not request.user.is_superuser and (
        _boolean(data, 'is_staff') is True or _boolean(data, 'is_superuser') is True
    )):
        return JsonResponse({'success': False, 'message': 'Solo un superusuario puede administrar acceso técnico.'}, status=403)

    if None in (full_name, email, rut, password) or not full_name or len(full_name) > 150 or not _valid_status(status, True):
        return JsonResponse({'success': False, 'message': 'Datos de usuario inválidos.'}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'success': False, 'message': 'Correo inválido.'}, status=400)
    if not _is_valid_chilean_rut(rut):
        return JsonResponse({'success': False, 'message': 'RUT inválido.'}, status=400)
    roles = _validated_roles(role_ids) if role_ids is not None else None
    if role_ids is not None and roles is None:
        return JsonResponse({'success': False, 'message': 'Roles inválidos.'}, status=400)
    if password:
        try:
            validate_password(password, profile.user)
        except ValidationError as exc:
            return JsonResponse({'success': False, 'message': 'Contraseña insegura.', 'details': exc.messages}, status=400)
    if profile.user_id == request.user.id and (
        status != 'Activo' or
        (role_ids is not None and not request.user.is_superuser and
         not any(role.name == 'Administrador General' for role in roles)) or
        (is_superuser is not None and request.user.is_superuser and
         _boolean(data, 'is_superuser') is False)
    ):
        return JsonResponse({'success': False, 'message': 'No puede revocar su propio acceso administrativo.'}, status=400)
    if is_staff is not None and _boolean(data, 'is_staff') is None:
        return JsonResponse({'success': False, 'message': 'is_staff inválido.'}, status=400)
    if is_superuser is not None and _boolean(data, 'is_superuser') is None:
        return JsonResponse({'success': False, 'message': 'is_superuser inválido.'}, status=400)
    if delegation_id and _ids([delegation_id]) is None or position_id and _ids([position_id]) is None:
        return JsonResponse({'success': False, 'message': 'Delegación o cargo inválido.'}, status=400)
    delegation = Delegation.objects.filter(id=delegation_id, status='Activo', deleted_at__isnull=True).first() if delegation_id else None
    position = Position.objects.filter(id=position_id, status='Activo', deleted_at__isnull=True).first() if position_id else None
    if delegation_id and not delegation or position_id and not position:
        return JsonResponse({'success': False, 'message': 'Delegación o cargo inválido.'}, status=400)

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

            if 'delegation_id' in data:
                profile.delegation = delegation
            
            if 'position_id' in data:
                profile.position = position

            if role_ids is not None:
                profile.roles.set(roles)

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
                    user.is_staff = _boolean(data, 'is_staff')
                if is_superuser is not None:
                    user.is_superuser = _boolean(data, 'is_superuser')
                if user.is_superuser:
                    user.is_staff = True
                if password:
                    user.set_password(password)
                    PasswordRecoveryCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
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

@admin_only
def api_user_toggle_status(request, pk):
    """
    Habilita o Inhabilita un usuario con 1 click.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    profile = get_object_or_404(UserProfile, id=pk, deleted_at__isnull=True)
    if _protected_account(request, profile):
        return JsonResponse({'success': False, 'message': 'Cuenta técnica protegida.'}, status=403)
    if profile.user_id == request.user.id:
        return JsonResponse({'success': False, 'message': 'No puede cambiar su propio estado.'}, status=400)
    
    # Prevenir deshabilitar al usuario admin principal
    if profile.user and profile.user.username == 'admin' and profile.status == 'Activo':
        return JsonResponse({'success': False, 'message': 'No es posible inhabilitar la cuenta de Administrador Principal del sistema.'}, status=400)

    nuevo_estado = 'Inactivo' if profile.status == 'Activo' else 'Activo'
    with transaction.atomic():
        profile.status = nuevo_estado
        profile.save(update_fields=['status', 'updated_at'])
        if profile.user:
            profile.user.is_active = (nuevo_estado == 'Activo')
            profile.user.save(update_fields=['is_active'])
        AuditLog.objects.create(
        user=request.user,
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

@admin_only
def api_user_delete(request, pk):
    """
    Elimina un usuario de la base de datos (con salvaguardas institucionales).
    """
    if request.method not in ['POST', 'DELETE']:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    profile = get_object_or_404(UserProfile, id=pk, deleted_at__isnull=True)
    if _protected_account(request, profile):
        return JsonResponse({'success': False, 'message': 'Cuenta técnica protegida.'}, status=403)
    if profile.user_id == request.user.id:
        return JsonResponse({'success': False, 'message': 'No puede dar de baja su propia cuenta.'}, status=400)
    
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
            
            # Baja lógica: conserva historial, evidencias y auditoría.
            profile.deleted_at = timezone.now()
            profile.status = 'Inactivo'
            profile.save(update_fields=['deleted_at', 'status', 'updated_at'])
            if user_auth:
                user_auth.is_active = False
                user_auth.save(update_fields=['is_active'])

        return JsonResponse({
            'success': True,
            'message': f"El usuario '{nombre}' fue dado de baja y conservado en la auditoría."
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Error al eliminar usuario: {str(e)}"}, status=500)

@admin_only
def api_user_reset_password(request, pk):
    """
    Restablece la contraseña de un usuario directamente desde el panel de administración.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    profile = get_object_or_404(UserProfile, id=pk, deleted_at__isnull=True)
    if _protected_account(request, profile):
        return JsonResponse({'success': False, 'message': 'Cuenta técnica protegida.'}, status=403)
    data = _get_request_data(request)
    new_password = _password(data)

    if not new_password:
        return JsonResponse({'success': False, 'message': 'La contraseña es obligatoria.'}, status=400)

    if not profile.user:
        return JsonResponse({'success': False, 'message': 'El perfil no tiene una cuenta de autenticación vinculada.'}, status=400)
    try:
        validate_password(new_password, profile.user)
    except ValidationError as exc:
        return JsonResponse({'success': False, 'message': 'Contraseña insegura.', 'details': exc.messages}, status=400)

    with transaction.atomic():
        profile.user.set_password(new_password)
        profile.user.save(update_fields=['password'])
        PasswordRecoveryCode.objects.filter(user=profile.user, used_at__isnull=True).update(used_at=timezone.now())
        AuditLog.objects.create(
        user=request.user,
        affected_table='usuario',
        affected_record_id=str(profile.id),
        action='UPDATE',
        new_value={'action_type': 'PASSWORD_RESET'}
    )

    return JsonResponse({
        'success': True,
        'message': f"Contraseña actualizada con éxito para el usuario '{profile.full_name}'."
    })

@admin_only
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

def _permissions_catalog():
    catalog = deepcopy(SYSTEM_PERMISSIONS_CATALOG)
    modules = {module['module_id']: module for module in catalog}
    for permission in PermissionDefinition.objects.filter(deleted_at__isnull=True).order_by('module_id', 'name'):
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
        if not any(item['code'] == permission.code for item in target['permissions']):
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

@admin_only
def api_permissions_catalog(request):
    """
    Retorna el catálogo completo estructurado de módulos, permisos y funciones del sistema.
    """
    catalog = _permissions_catalog()
    total_perms = sum(len(m['permissions']) for m in catalog)
    return JsonResponse({
        'success': True,
        'catalog': catalog,
        'total_permissions': total_perms,
        'modules_count': len(catalog)
    })

@admin_only
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

    catalog = _permissions_catalog()
    return JsonResponse({
        'success': True,
        'roles': roles_data,
        'catalog': catalog,
        'summary': {
            'total_roles': len(roles_data),
            'system_roles': total_system_roles,
            'custom_roles': total_custom_roles,
            'total_permissions_available': len(all_codes),
        }
    })

@admin_only
def api_role_create(request):
    """
    Crea un nuevo rol en la base de datos con su matriz de permisos asignada y auditoría (MyAdmin).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    data = _get_request_data(request)
    name = _text(data, 'name')
    description = _text(data, 'description')
    permissions = data.get('permissions', [])
    is_system = False

    if name is None or description is None or not name or len(name) > 50 or len(description) > 255:
        return JsonResponse({'success': False, 'message': 'Nombre o descripción inválidos.'}, status=400)
    permissions = _validated_permissions(permissions)
    if permissions is None:
        return JsonResponse({'success': False, 'message': 'Permisos inválidos.'}, status=400)

    if Role.objects.filter(name__iexact=name).exists():
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

@admin_only
def api_role_update(request, pk):
    """
    Modifica un rol existente, su descripción y su matriz de funciones/permisos (MyAdmin).
    """
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    role = get_object_or_404(Role, id=pk, deleted_at__isnull=True)
    data = _get_request_data(request)

    new_name = _text(data, 'name', role.name)
    new_description = _text(data, 'description')
    if 'description' not in data:
        new_description = role.description

    new_permissions = data.get('permissions')
    if new_permissions is None:
        new_permissions = role.permissions_data

    if role.is_system or role.name == 'Administrador General':
        return JsonResponse({'success': False, 'message': 'El rol de sistema está protegido.'}, status=403)
    if new_name is None or new_description is None or not new_name or len(new_name) > 50 or len(new_description) > 255:
        return JsonResponse({'success': False, 'message': 'Nombre o descripción inválidos.'}, status=400)
    new_permissions = _validated_permissions(new_permissions)
    if new_permissions is None:
        return JsonResponse({'success': False, 'message': 'Permisos inválidos.'}, status=400)

    # Validar duplicados si se cambia el nombre
    if new_name != role.name and Role.objects.filter(name__iexact=new_name).exclude(id=role.id).exists():
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

@admin_only
def api_role_delete(request, pk):
    """
    Elimina un rol de la base de datos (con verificación de protección de sistema y usuarios).
    """
    if request.method not in ['POST', 'DELETE']:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    role = get_object_or_404(Role, id=pk, deleted_at__isnull=True)

    # Protección de roles base del sistema
    protected_roles = ['Administrador', 'Operador', 'Consultor', 'Verificador']
    if role.is_system or role.name in protected_roles or role.name == 'Administrador General':
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

            role.deleted_at = timezone.now()
            role.save(update_fields=['deleted_at', 'updated_at'])

        return JsonResponse({
            'success': True,
            'message': f"El rol '{role_name}' ha sido eliminado exitosamente del sistema."
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Error al eliminar el rol: {str(e)}"}, status=500)

@admin_only
def api_role_duplicate(request, pk):
    """
    Duplica un rol existente junto con toda su matriz de permisos (función phpMyAdmin).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    origin_role = get_object_or_404(Role, id=pk, deleted_at__isnull=True)
    data = _get_request_data(request)

    base_name = _text(data, 'name', f"{origin_role.name} (Copia)")
    if base_name is None or not base_name or len(base_name) > 50:
        return JsonResponse({'success': False, 'message': 'Nombre inválido.'}, status=400)
    candidate_name = base_name
    counter = 1
    while Role.objects.filter(name__iexact=candidate_name).exists():
        counter += 1
        candidate_name = f"{base_name} {counter}"
        if len(candidate_name) > 50:
            return JsonResponse({'success': False, 'message': 'Nombre demasiado largo.'}, status=400)

    try:
        with transaction.atomic():
            new_role = Role.objects.create(
                name=candidate_name,
                description=f"Copia basada en {origin_role.name}: {origin_role.description}",
                is_system=False,
                permissions_data=deepcopy(origin_role.permissions_data or [])
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

@admin_only
def api_add_custom_permission(request):
    """
    Permite al Super Administrador registrar una nueva función/privilegio dinámico en el catálogo.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    data = _get_request_data(request)
    module_id = _text(data, 'module_id')
    code = _text(data, 'code')
    name = _text(data, 'name')
    desc = _text(data, 'desc')

    if None in (module_id, code, name, desc) or not re.fullmatch(r'[a-z_]+\.[a-z_]+', code or '') or not name or len(code) > 100 or len(name) > 120 or len(module_id) > 50 or len(desc) > 255:
        return JsonResponse({'success': False, 'message': 'Datos del permiso inválidos.'}, status=400)
    if module_id and code.split('.')[0] != module_id:
        return JsonResponse({'success': False, 'message': 'El código debe pertenecer al módulo.'}, status=400)

    if code in _all_system_perm_codes():
        return JsonResponse({'success': False, 'message': f"La función con código '{code}' ya existe."}, status=400)

    with transaction.atomic():
        permission = PermissionDefinition.objects.create(
        module_id=module_id or 'personalizados',
        code=code,
        name=name,
        description=desc,
        is_system=False,
    )
        AuditLog.objects.create(
        user=request.user,
        affected_table='permiso_definicion',
        affected_record_id=str(permission.id),
        action='CREATE',
        new_value={'module_id': permission.module_id, 'code': code, 'name': name},
        source_ip=request.META.get('REMOTE_ADDR'),
    )

    return JsonResponse({
        'success': True,
        'message': f"Nueva función '{name}' agregada al catálogo de privilegios.",
        'catalog': _permissions_catalog()
    })


def _catalog_audit(request, table, record, action, previous=None):
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        affected_table=table,
        affected_record_id=str(record.id),
        action=action,
        previous_value=previous,
        new_value={
            'name': record.name,
            'status': record.status,
            'scope': getattr(record, 'scope', None),
            'description': getattr(record, 'description', None),
            'address': getattr(record, 'address', None),
            'phone': getattr(record, 'phone', None),
            'email': getattr(record, 'email', None),
            'schedule': getattr(record, 'schedule', None),
            'manager_name': getattr(record, 'manager_name', None),
            'photo_url': getattr(record, 'photo_url', None),
        },
        source_ip=request.META.get('REMOTE_ADDR'),
    )


@admin_only
def api_delegations(request):
    """Lista y crea delegaciones usadas por la asignación real de funcionarios."""
    if request.method == 'GET':
        from activities.models import Activity
        from agenda.models import CollectiveAgenda
        from metrics.models import DailyIndicator
        from social.models import SocialCase

        items = Delegation.objects.filter(deleted_at__isnull=True).order_by('name')
        today = timezone.localdate()
        result = []
        for item in items:
            active_profiles = item.users.filter(deleted_at__isnull=True, status='Activo').select_related('position').prefetch_related('roles')
            commitments = CollectiveAgenda.objects.filter(delegation=item, deleted_at__isnull=True)
            total_commitments = commitments.count()
            resolved_commitments = commitments.filter(status='Realizado').count()
            latest_indicator_date = DailyIndicator.objects.filter(
                user__profile__delegation=item, deleted_at__isnull=True
            ).order_by('-calculation_date').values_list('calculation_date', flat=True).first()
            indicators = DailyIndicator.objects.none()
            if latest_indicator_date:
                indicators = DailyIndicator.objects.filter(
                    user__profile__delegation=item, calculation_date=latest_indicator_date,
                    deleted_at__isnull=True
                )
            compliance = indicators.aggregate(value=Avg('weighted_compliance'))['value']
            result.append({
                'id': item.id, 'name': item.name, 'scope': item.scope,
                'status': item.status, 'address': item.address, 'phone': item.phone,
                'email': item.email, 'schedule': item.schedule,
                'manager_name': item.manager_name, 'photo_url': item.photo_url,
                'description': item.description,
                'users_count': active_profiles.count(),
                'staff': [{
                    'name': profile.full_name, 'rut': profile.rut,
                    'position': profile.position.name if profile.position else 'Sin cargo asignado',
                    'email': profile.email,
                    'role': profile.roles.first().name if profile.roles.exists() else 'Sin rol',
                } for profile in active_profiles],
                'monthly_activities': Activity.objects.filter(
                    delegation=item, activity_date__year=today.year,
                    activity_date__month=today.month, deleted_at__isnull=True
                ).count(),
                'registered_neighbors': SocialCase.objects.filter(
                    delegation=item, deleted_at__isnull=True
                ).values('user_rut').distinct().count(),
                'commitments_total': total_commitments,
                'resolution_rate': round((resolved_commitments / total_commitments) * 100) if total_commitments else None,
                'compliance_percentage': round(float(compliance), 1) if compliance is not None else None,
                'satisfaction_percentage': None,
            })
        return JsonResponse({'success': True, 'delegations': result})
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

    data = _get_request_data(request)
    name, scope = _text(data, 'name'), _text(data, 'scope')
    status = data.get('status', 'Activo')
    if name is None or scope is None or not name or not scope or len(name) > 100 or len(scope) > 100:
        return JsonResponse({'success': False, 'message': 'Nombre y ámbito territorial inválidos.'}, status=400)
    if status not in ('Activo', 'Inactivo'):
        return JsonResponse({'success': False, 'message': 'Estado inválido.'}, status=400)
    if Delegation.objects.filter(name__iexact=name).exists():
        return JsonResponse({'success': False, 'message': 'Ya existe una delegación con ese nombre.'}, status=400)
    detail_error = _validate_delegation_details(data)
    if detail_error:
        return JsonResponse({'success': False, 'message': detail_error}, status=400)
    if any(len(_text(data, field)) > limit for field, limit in (
        ('address', 200), ('phone', 30), ('email', 120), ('schedule', 120),
        ('manager_name', 150), ('photo_url', 255)
    )):
        return JsonResponse({'success': False, 'message': 'Detalle demasiado largo.'}, status=400)
    with transaction.atomic():
        item = Delegation.objects.create(
            name=name, scope=scope, status=status,
            address=_text(data, 'address'), phone=_text(data, 'phone'),
            email=(_text(data, 'email') or '').lower(), schedule=_text(data, 'schedule'),
            manager_name=_text(data, 'manager_name'), photo_url=_text(data, 'photo_url'),
            description=_text(data, 'description'),
        )
        _catalog_audit(request, 'delegacion', item, 'CREATE')
    return JsonResponse({'success': True, 'message': f"Delegación '{name}' creada y guardada.", 'id': item.id})


@admin_only
def api_delegation_update(request, pk):
    if request.method not in ('POST', 'PUT'):
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    item = get_object_or_404(Delegation, id=pk, deleted_at__isnull=True)
    data = _get_request_data(request)
    name = _text(data, 'name', item.name)
    scope = _text(data, 'scope', item.scope)
    status = data.get('status', item.status)
    if name is None or scope is None or not name or not scope or len(name) > 100 or len(scope) > 100 or status not in ('Activo', 'Inactivo'):
        return JsonResponse({'success': False, 'message': 'Revisa el nombre, ámbito y estado.'}, status=400)
    if status == 'Inactivo' and item.status == 'Activo' and item.users.filter(deleted_at__isnull=True, status='Activo').exists():
        return JsonResponse({'success': False, 'message': 'La delegación tiene funcionarios activos.'}, status=400)
    if Delegation.objects.filter(name__iexact=name).exclude(id=pk).exists():
        return JsonResponse({'success': False, 'message': 'Ya existe otra delegación con ese nombre.'}, status=400)
    merged = {field: getattr(item, field) for field in (
        'name', 'scope', 'address', 'phone', 'email', 'schedule',
        'manager_name', 'photo_url', 'description'
    )}
    merged.update({key: data.get(key) for key in merged if key in data})
    detail_error = _validate_delegation_details(merged)
    if detail_error:
        return JsonResponse({'success': False, 'message': detail_error}, status=400)
    if any(len(_text(merged, field)) > limit for field, limit in (
        ('address', 200), ('phone', 30), ('email', 120), ('schedule', 120),
        ('manager_name', 150), ('photo_url', 255)
    )):
        return JsonResponse({'success': False, 'message': 'Detalle demasiado largo.'}, status=400)
    previous = {'name': item.name, 'scope': item.scope, 'status': item.status, 'address': item.address,
                'phone': item.phone, 'email': item.email, 'schedule': item.schedule,
                'manager_name': item.manager_name, 'photo_url': item.photo_url, 'description': item.description}
    with transaction.atomic():
        item.name, item.scope, item.status = name, scope, status
        for field in ('address', 'phone', 'email', 'schedule', 'manager_name', 'photo_url', 'description'):
            if field in data:
                setattr(item, field, _text(data, field))
        item.email = item.email.lower()
        item.save(update_fields=['name', 'scope', 'status', 'address', 'phone', 'email', 'schedule',
                                 'manager_name', 'photo_url', 'description', 'updated_at'])
        _catalog_audit(request, 'delegacion', item, 'UPDATE', previous)
    return JsonResponse({'success': True, 'message': f"Delegación '{name}' actualizada."})


@admin_only
def api_delegation_toggle(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    item = get_object_or_404(Delegation, id=pk, deleted_at__isnull=True)
    previous = {'name': item.name, 'scope': item.scope, 'status': item.status}
    if item.status == 'Activo' and item.users.filter(deleted_at__isnull=True, status='Activo').exists():
        return JsonResponse({'success': False, 'message': 'La delegación tiene funcionarios activos.'}, status=400)
    item.status = 'Inactivo' if item.status == 'Activo' else 'Activo'
    with transaction.atomic():
        item.save(update_fields=['status', 'updated_at'])
        _catalog_audit(request, 'delegacion', item, 'UPDATE', previous)
    return JsonResponse({'success': True, 'message': f"Delegación {item.status.lower()} correctamente.", 'status': item.status})


@admin_only
def api_positions(request):
    """Lista y crea cargos institucionales asignables a funcionarios."""
    if request.method == 'GET':
        items = Position.objects.filter(deleted_at__isnull=True).order_by('name')
        return JsonResponse({'success': True, 'positions': [{
            'id': item.id, 'name': item.name, 'description': item.description,
            'status': item.status,
            'users_count': item.users.filter(deleted_at__isnull=True).count(),
        } for item in items]})
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    data = _get_request_data(request)
    name, description = _text(data, 'name'), _text(data, 'description')
    status = data.get('status', 'Activo')
    if name is None or description is None or not name or len(name) > 100:
        return JsonResponse({'success': False, 'message': 'Nombre o descripción inválidos.'}, status=400)
    if status not in ('Activo', 'Inactivo'):
        return JsonResponse({'success': False, 'message': 'Estado inválido.'}, status=400)
    if Position.objects.filter(name__iexact=name).exists():
        return JsonResponse({'success': False, 'message': 'Ya existe un cargo con ese nombre.'}, status=400)
    with transaction.atomic():
        item = Position.objects.create(name=name, description=description, status=status)
        _catalog_audit(request, 'cargo', item, 'CREATE')
    return JsonResponse({'success': True, 'message': f"Cargo '{name}' creado y guardado.", 'id': item.id})


@admin_only
def api_position_update(request, pk):
    if request.method not in ('POST', 'PUT'):
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    item = get_object_or_404(Position, id=pk, deleted_at__isnull=True)
    data = _get_request_data(request)
    name = _text(data, 'name', item.name)
    description = _text(data, 'description', item.description)
    status = data.get('status', item.status)
    if name is None or description is None or not name or len(name) > 100 or status not in ('Activo', 'Inactivo'):
        return JsonResponse({'success': False, 'message': 'Revisa el nombre y estado.'}, status=400)
    if status == 'Inactivo' and item.status == 'Activo' and item.users.filter(deleted_at__isnull=True, status='Activo').exists():
        return JsonResponse({'success': False, 'message': 'El cargo tiene funcionarios activos.'}, status=400)
    if Position.objects.filter(name__iexact=name).exclude(id=pk).exists():
        return JsonResponse({'success': False, 'message': 'Ya existe otro cargo con ese nombre.'}, status=400)
    previous = {'name': item.name, 'description': item.description, 'status': item.status}
    with transaction.atomic():
        item.name, item.description, item.status = name, description, status
        item.save(update_fields=['name', 'description', 'status', 'updated_at'])
        _catalog_audit(request, 'cargo', item, 'UPDATE', previous)
    return JsonResponse({'success': True, 'message': f"Cargo '{name}' actualizado."})


@admin_only
def api_position_toggle(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    item = get_object_or_404(Position, id=pk, deleted_at__isnull=True)
    previous = {'name': item.name, 'description': item.description, 'status': item.status}
    if item.status == 'Activo' and item.users.filter(deleted_at__isnull=True, status='Activo').exists():
        return JsonResponse({'success': False, 'message': 'El cargo tiene funcionarios activos.'}, status=400)
    item.status = 'Inactivo' if item.status == 'Activo' else 'Activo'
    with transaction.atomic():
        item.save(update_fields=['status', 'updated_at'])
        _catalog_audit(request, 'cargo', item, 'UPDATE', previous)
    return JsonResponse({'success': True, 'message': f"Cargo {item.status.lower()} correctamente.", 'status': item.status})


