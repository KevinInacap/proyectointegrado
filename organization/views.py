from core.input_validation import validated_payload, USER_FIELDS, ROLE_FIELDS, POSITION_FIELDS, DELEGATION_FIELDS
from .role_assignment import roles_with_position_base as _roles_with_position_base
from .authorization import admin_only, permission_gate, _has_administrator_role, _users_scope, _delegations_scope
from .permission_catalog import _permissions_catalog, _all_system_perm_codes
from .audit_views import api_audit_logs
import json
import logging
import re
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Avg, F, Value
from django.db.models.functions import Replace, Trim, Upper
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import UserProfile, Role, Delegation, Position, PermissionDefinition
from .access import (
    ADMINISTRATOR_ROLE_NAME,
    SUPER_ADMINISTRATOR_ROLE_NAME,
    SUPER_ADMINISTRATOR_RUT,
    is_administrator_role,
    is_super_administrator,
    role_permission_codes,
    role_name_for_position,
    set_role_permission_codes,
)
from core.models import AuditLog, PasswordRecoveryCode

logger = logging.getLogger(__name__)


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
    return value if isinstance(value, str) and len(value) <= 128 else None


def _protected_account(request, profile):
    if is_super_administrator(getattr(request, 'user', None)):
        return False
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


def _active_role_position(value):
    ids = _ids([value])
    if not ids:
        return None
    return Position.objects.filter(pk=ids[0], status='Activo', deleted_at__isnull=True).first()


def _role_matches_position(role, position):
    if not position:
        return False
    if role.position_id == position.pk:
        return True
    return (role.position_id is None and position.base_role_id == role.pk
            and not role.base_positions.exclude(pk=position.pk).exists())


def _validated_permissions(value):
    if not isinstance(value, list) or any(not isinstance(code, str) for code in value):
        return None
    codes = list(dict.fromkeys(value))
    return codes if set(codes) <= set(_all_system_perm_codes()) else None


def _is_valid_chilean_rut(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[0-9]{1,8}|[0-9]{1,2}(?:\.[0-9]{3}){1,2})-?[0-9kK]', value.strip()):
        return False
    cleaned = _rut_identity(value)
    number, verifier = cleaned[:-1], cleaned[-1].upper()
    if not int(number):
        return False
    total, multiplier = 0, 2
    for digit in reversed(number):
        total += int(digit) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1
    result = 11 - (total % 11)
    expected = '0' if result == 11 else ('K' if result == 10 else str(result))
    return verifier == expected


def _rut_identity(value):
    """Compara la identidad sin cambiar ni corregir su dígito verificador."""
    return str(value or '').strip().replace('.', '').replace('-', '').upper()


def _format_rut(value):
    cleaned = _rut_identity(value)
    number, verifier = cleaned[:-1], cleaned[-1]
    groups = []
    while number:
        groups.append(number[-3:])
        number = number[:-3]
    return '.'.join(reversed(groups)) + '-' + verifier


def _profiles_with_rut(value):
    # Incluye registros históricos con otro formato o dados de baja: el RUT
    # identifica a una sola persona aunque su cuenta se encuentre inactiva.
    return UserProfile.objects.annotate(
        rut_identity=Upper(Replace(Replace(Trim(F('rut')), Value('.'), Value('')), Value('-'), Value(''))),
    ).filter(rut_identity=_rut_identity(value))


def _reserved_super_administrator_identity(rut, email):
    return (_rut_identity(rut) == _rut_identity(SUPER_ADMINISTRATOR_RUT)
            or email.strip().lower() == 'keviinencinamolina2k20@gmail.com')


def _validate_delegation_details(data):
    text_fields = ('name', 'scope', 'commune', 'address', 'phone', 'schedule', 'manager_name', 'description')
    if any(_text(data, field) is None for field in text_fields):
        return 'Los campos de texto deben ser cadenas.'
    if any(re.search(r'[<>]', _text(data, field)) for field in text_fields):
        return 'Los campos de la delegación no pueden contener etiquetas HTML.'
    name, scope, commune = (_text(data, field) for field in ('name', 'scope', 'commune'))
    label_pattern = r"[^\W_][\w .,'’&/-]{1,99}"
    if any(
        len(value) < 3 or not re.fullmatch(label_pattern, value, flags=re.UNICODE)
        or not re.search(r'[^\W\d_]', value, flags=re.UNICODE)
        for value in (name, scope, commune)
    ):
        return 'Nombre, ámbito y comuna deben contener texto válido de 3 a 100 caracteres.'
    address = _text(data, 'address')
    if address and not re.fullmatch(r"[^\W_][\w .,#º°/-]{0,199}", address, flags=re.UNICODE):
        return 'La dirección contiene caracteres no válidos.'
    phone = _text(data, 'phone')
    if phone and not re.fullmatch(r'\+?[0-9][0-9() .-]{6,29}', phone):
        return 'El teléfono debe tener entre 7 y 30 dígitos o signos telefónicos.'
    schedule = _text(data, 'schedule')
    if schedule and not re.fullmatch(r"[\w :.,/-]{1,120}", schedule, flags=re.UNICODE):
        return 'El horario contiene caracteres no válidos.'
    manager = _text(data, 'manager_name')
    if manager and not re.fullmatch(r"[^\W_][\w .'-]{1,149}", manager, flags=re.UNICODE):
        return 'El nombre de la persona encargada contiene caracteres no válidos.'
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


@permission_gate({'GET': 'usuarios.view'})
def api_users_list(request):
    """
    Retorna la lista completa de usuarios y perfiles desde la base de datos,
    junto con los catálogos de delegaciones, cargos y roles.
    """
    profiles = _users_scope(request).select_related('user', 'delegation', 'position').prefetch_related('roles').order_by('full_name')
    
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
            'delegation_code': p.delegation.code if p.delegation else '',
            'position_id': p.position.id if p.position else None,
            'position_name': p.position.name if p.position else 'Sin cargo asignado',
            'roles': [{'id': r.id, 'name': r.name} for r in p.roles.all()],
            'roles_str': ', '.join([r.name for r in p.roles.all()]) or 'Sin rol',
            'created_at': p.created_at.strftime('%d/%m/%Y %H:%M') if getattr(p, 'created_at', None) else '',
            'last_login': timezone.localtime(p.user.last_login).strftime('%d/%m/%Y %H:%M') if p.user and p.user.last_login else '',
        })
        
    delegations = [{'id': d.id, 'code': d.code, 'name': d.name} for d in _delegations_scope(request).filter(status='Activo').order_by('name')]
    positions = [{'id': p.id, 'name': p.name, 'base_role_id': p.base_role_id} for p in Position.objects.filter(status='Activo', deleted_at__isnull=True).order_by('name')]
    roles = [{'id': r.id, 'name': r.name, 'description': r.description, 'position_id': r.position_id} for r in Role.objects.filter(deleted_at__isnull=True).order_by('name')]

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

@permission_gate({'POST': 'usuarios.create'})
@validated_payload(USER_FIELDS)
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
    if len(username) > 150 or len(full_name) > 150 or len(email) > 100 or len(rut) > 12:
        return JsonResponse({'success': False, 'message': 'Usuario, nombre, correo o RUT superan el largo permitido.'}, status=400)

    if not _is_valid_chilean_rut(rut):
        return JsonResponse({'success': False, 'message': 'RUT inválido. Revisa el número y el dígito verificador.'}, status=400)
    rut = _format_rut(rut)

    # Validaciones de unicidad
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({'success': False, 'message': f"El nombre de usuario '{username}' ya está en uso."}, status=400)
    
    if _profiles_with_rut(rut).exists():
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
    if any(not _role_matches_position(role, position) for role in roles):
        return JsonResponse({'success': False, 'message': 'Los roles seleccionados deben pertenecer al cargo del funcionario.'}, status=400)
    if position and position.base_role_id and (not position.base_role.is_system or position.base_role.deleted_at is not None):
        return JsonResponse({'success': False, 'message': 'El rol base vinculado al cargo requiere revisión administrativa antes de asignarlo.'}, status=409)
    if position and position.base_role_id and (position.base_role.position_id not in (None, position.pk) or position.base_role.base_positions.exclude(pk=position.pk).exists()):
        return JsonResponse({'success': False, 'message': 'El rol base está asociado a otro cargo y requiere revisión administrativa.'}, status=409)
    if position and not position.base_role_id and Role.objects.filter(name__iexact=role_name_for_position(position.name)).exists():
        return JsonResponse({'success': False, 'message': 'El cargo no tiene un rol base vinculado y existe otro rol con ese nombre. Contacta a Administración para revisar el catálogo.'}, status=409)
    if (position and (is_administrator_role(role_name_for_position(position.name))
                      or position.base_role_id and is_administrator_role(position.base_role))
            and not request.user.is_superuser and not _has_administrator_role(request.user)):
        return JsonResponse({'success': False, 'message': 'Solo un Administrador puede asignar un cargo administrativo.'}, status=403)
    if not _has_administrator_role(request.user):
        actor = UserProfile.objects.select_related('delegation').filter(
            user=request.user, status='Activo', deleted_at__isnull=True,
        ).first()
        if not actor or not actor.delegation_id or not delegation or delegation.pk != actor.delegation_id:
            return JsonResponse({'success': False, 'message': 'Solo puede crear usuarios dentro de su delegación asignada.'}, status=403)
        if any(is_administrator_role(role) for role in roles):
            return JsonResponse({'success': False, 'message': 'Solo un Administrador puede asignar el rol global.'}, status=403)

    assigns_super_administrator = (
        any(role_name_for_position(role.name) == SUPER_ADMINISTRATOR_ROLE_NAME for role in roles)
        or position and (role_name_for_position(position.name) == SUPER_ADMINISTRATOR_ROLE_NAME
                         or position.base_role_id and role_name_for_position(position.base_role.name) == SUPER_ADMINISTRATOR_ROLE_NAME)
    )
    if assigns_super_administrator and not _reserved_super_administrator_identity(rut, email):
        return JsonResponse({'success': False, 'message': 'El rol SuperAdministrador está reservado exclusivamente para la máxima autoridad institucional.'}, status=403)

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

            # El cargo define el panel y añade su rol base. Los roles extra
            # seleccionados por administración se mantienen.
            profile.roles.set(_roles_with_position_base(roles, position))

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
        return JsonResponse({'success': False, 'message': 'No se pudo completar la operación. Inténtalo nuevamente.'}, status=500)

@permission_gate({'POST': 'usuarios.edit', 'PUT': 'usuarios.edit'})
@validated_payload(USER_FIELDS)
def api_user_update(request, pk):
    """
    Actualiza datos de un usuario existente, roles, privilegios y delegación.
    """
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    profile = get_object_or_404(_users_scope(request), id=pk)
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

    if (None in (full_name, email, rut, password) or not full_name or len(full_name) > 150
            or len(email) > 100 or len(rut) > 12 or not _valid_status(status, True)):
        return JsonResponse({'success': False, 'message': 'Datos de usuario inválidos.'}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'success': False, 'message': 'Correo inválido.'}, status=400)
    rut_changed = _rut_identity(rut) != _rut_identity(profile.rut)
    if rut_changed:
        if not _is_valid_chilean_rut(rut):
            return JsonResponse({'success': False, 'message': 'RUT inválido. Revisa el número y el dígito verificador.'}, status=400)
        rut = _format_rut(rut)
    else:
        # Una edición de cargo/rol no debe modificar ni bloquear un RUT
        # histórico. Solo exigimos el DV cuando cambia la identidad.
        rut = profile.rut
    roles = _validated_roles(role_ids) if role_ids is not None else None
    if role_ids is not None and roles is None:
        return JsonResponse({'success': False, 'message': 'Roles inválidos.'}, status=400)
    if role_ids is not None and not _has_administrator_role(request.user) and any(
        is_administrator_role(role) for role in roles
    ):
        return JsonResponse({'success': False, 'message': 'Solo un Administrador puede asignar el rol global.'}, status=403)
    if not _has_administrator_role(request.user) and any(
        is_administrator_role(role)
        for role in profile.roles.filter(deleted_at__isnull=True)
    ):
        return JsonResponse({'success': False, 'message': 'Solo un Administrador puede modificar una cuenta con el rol global.'}, status=403)
    if password:
        try:
            validate_password(password, profile.user)
        except ValidationError as exc:
            return JsonResponse({'success': False, 'message': 'Contraseña insegura.', 'details': exc.messages}, status=400)
    if profile.user_id == request.user.id and (
        status != 'Activo' or
        (role_ids is not None and not request.user.is_superuser and
         not any(is_administrator_role(role) for role in roles)) or
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
    effective_position = position if 'position_id' in data else profile.position
    if roles is not None:
        unchanged_position = (effective_position.pk if effective_position else None) == profile.position_id
        previous_ids = set(profile.roles.values_list('id', flat=True)) if unchanged_position else set()
        if any(not _role_matches_position(role, effective_position) and role.pk not in previous_ids for role in roles):
            return JsonResponse({'success': False, 'message': 'Los roles nuevos deben pertenecer al cargo del funcionario.'}, status=400)
    if effective_position and effective_position.base_role_id and (not effective_position.base_role.is_system or effective_position.base_role.deleted_at is not None):
        return JsonResponse({'success': False, 'message': 'El rol base vinculado al cargo requiere revisión administrativa antes de asignarlo.'}, status=409)
    if effective_position and effective_position.base_role_id and (effective_position.base_role.position_id not in (None, effective_position.pk) or effective_position.base_role.base_positions.exclude(pk=effective_position.pk).exists()):
        return JsonResponse({'success': False, 'message': 'El rol base está asociado a otro cargo y requiere revisión administrativa.'}, status=409)
    if effective_position and not effective_position.base_role_id and Role.objects.filter(name__iexact=role_name_for_position(effective_position.name)).exists():
        return JsonResponse({'success': False, 'message': 'El cargo no tiene un rol base vinculado y existe otro rol con ese nombre. Contacta a Administración para revisar el catálogo.'}, status=409)
    if (effective_position and (is_administrator_role(role_name_for_position(effective_position.name))
                                or effective_position.base_role_id and is_administrator_role(effective_position.base_role))
            and not request.user.is_superuser and not _has_administrator_role(request.user)):
        return JsonResponse({'success': False, 'message': 'Solo un Administrador puede asignar un cargo administrativo.'}, status=403)
    if not _has_administrator_role(request.user):
        actor = UserProfile.objects.filter(
            user=request.user, status='Activo', deleted_at__isnull=True,
        ).first()
        if not actor or not actor.delegation_id or (
            'delegation_id' in data and (not delegation or delegation.pk != actor.delegation_id)
        ):
            return JsonResponse({'success': False, 'message': 'No puede mover usuarios fuera de su delegación asignada.'}, status=403)

    # Validar que no choque RUT o Email con otro usuario
    if rut_changed and _profiles_with_rut(rut).exclude(id=profile.id).exists():
        return JsonResponse({'success': False, 'message': f"El RUT '{rut}' pertenece a otro funcionario."}, status=400)
    
    if UserProfile.objects.filter(email__iexact=email).exclude(id=profile.id).exists():
        return JsonResponse({'success': False, 'message': f"El correo '{email}' pertenece a otro funcionario."}, status=400)

    selected_roles = roles if role_ids is not None else list(
        profile.roles.filter(deleted_at__isnull=True)
    )
    next_base_name = role_name_for_position(effective_position.name if effective_position else None)
    if profile.position and profile.position.base_role_id and (
            not effective_position or profile.position.pk != effective_position.pk):
        selected_roles = [role for role in selected_roles if role.pk != profile.position.base_role_id]
    if role_ids is None and 'position_id' in data and (not effective_position or profile.position_id != effective_position.pk):
        # Al cambiar de cargo no conservar permisos adicionales del cargo anterior.
        selected_roles = [role for role in selected_roles if _role_matches_position(role, effective_position)]
    assigns_super_administrator = (
        next_base_name == SUPER_ADMINISTRATOR_ROLE_NAME
        or effective_position and effective_position.base_role_id and role_name_for_position(effective_position.base_role.name) == SUPER_ADMINISTRATOR_ROLE_NAME
        or any(role_name_for_position(role.name) == SUPER_ADMINISTRATOR_ROLE_NAME for role in selected_roles)
    )
    if assigns_super_administrator and not _reserved_super_administrator_identity(rut, email):
        return JsonResponse({'success': False, 'message': 'El rol SuperAdministrador está reservado exclusivamente para la máxima autoridad institucional.'}, status=403)

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

            profile.roles.set(_roles_with_position_base(selected_roles, profile.position))

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
        return JsonResponse({'success': False, 'message': 'No se pudo completar la operación. Inténtalo nuevamente.'}, status=500)

@permission_gate({'POST': 'usuarios.toggle_status'})
def api_user_toggle_status(request, pk):
    """
    Habilita o Inhabilita un usuario con 1 click.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    profile = get_object_or_404(_users_scope(request), id=pk)
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

@permission_gate({'POST': 'usuarios.delete', 'DELETE': 'usuarios.delete'})
def api_user_delete(request, pk):
    """
    Elimina un usuario de la base de datos (con salvaguardas institucionales).
    """
    if request.method not in ['POST', 'DELETE']:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    profile = get_object_or_404(_users_scope(request), id=pk)
    if _protected_account(request, profile):
        return JsonResponse({'success': False, 'message': 'Cuenta técnica protegida.'}, status=403)
    if profile.user_id == request.user.id:
        return JsonResponse({'success': False, 'message': 'No puede dar de baja su propia cuenta.'}, status=400)

    # Salvaguarda: Nadie puede eliminar al SuperAdministrador institucional
    if is_super_administrator(profile):
        return JsonResponse({'success': False, 'message': 'Por jerarquía institucional, la cuenta del SuperAdministrador no puede ser eliminada.'}, status=403)

    caller_is_super = is_super_administrator(request.user)
    target_is_admin = profile.roles.filter(deleted_at__isnull=True).filter(
        name__in=[ADMINISTRATOR_ROLE_NAME, 'Administrador General']
    ).exists() or (profile.user and (profile.user.is_superuser or profile.user.is_staff))

    # Solo el SuperAdministrador puede eliminar administradores
    if target_is_admin and not caller_is_super:
        return JsonResponse({
            'success': False,
            'message': 'Solo el SuperAdministrador puede eliminar a funcionarios con rol de Administrador.'
        }, status=403)

    # Salvaguarda: No borrar admin principal a menos que sea SuperAdministrador
    if profile.user and profile.user.username == 'admin' and not caller_is_super:
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
            
            # Eliminación real en cascada: se refleja al instante en MySQL y phpMyAdmin
            if user_auth:
                user_auth.delete()
            else:
                profile.delete()

        return JsonResponse({
            'success': True,
            'message': f"El usuario '{nombre}' fue eliminado exitosamente del sistema y de la base de datos."
        })

    except Exception:
        logger.exception('No se pudo dar de baja al funcionario %s', pk)
        return JsonResponse({'success': False, 'message': 'No se pudo dar de baja al funcionario. Inténtalo nuevamente.'}, status=500)

@permission_gate({'POST': 'usuarios.reset_password'})
def api_user_reset_password(request, pk):
    """
    Restablece la contraseña de un usuario directamente desde el panel de administración.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    profile = get_object_or_404(_users_scope(request), id=pk)
    if _protected_account(request, profile):
        return JsonResponse({'success': False, 'message': 'Cuenta técnica protegida.'}, status=403)
    data = _get_request_data(request)
    new_password = _password(data)

    if not new_password:
        return JsonResponse({'success': False, 'message': 'La contraseña es obligatoria y admite hasta 128 caracteres.'}, status=400)

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
        'message': f"Contraseña actualizada con éxito para el usuario '{profile.full_name}'.",
        'account_status': profile.status,
        'is_active': bool(profile.user.is_active),
        'has_active_role': profile.roles.filter(deleted_at__isnull=True).exists(),
    })

# ==============================================================================
# CATÁLOGO Y GESTIÓN DE ROLES Y MATRIZ DE PERMISOS (RBAC MYADMIN)
# ==============================================================================

@permission_gate({'GET': 'roles.view'})
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

@permission_gate({'GET': 'roles.view'})
def api_roles_list(request):
    """
    Retorna la lista completa de roles con sus permisos asignados, contador de usuarios,
    indicadores de sistema y el catálogo de funciones disponibles (MyAdmin).
    """
    roles_qs = Role.objects.filter(deleted_at__isnull=True).select_related('position').prefetch_related(
        'permission_definitions', 'base_positions'
    ).order_by('id')
    roles_data = []

    for r in roles_qs:
        perms = sorted(role_permission_codes(r))
        users_qs = _users_scope(request).filter(roles=r)
        users_count = users_qs.count()
        users_sample = list(users_qs.values_list('full_name', flat=True)[:5])

        roles_data.append({
            'id': r.id,
            'name': r.name,
            'description': r.description or '',
            'position_id': r.position_id,
            'position_name': r.position.name if r.position_id else None,
            'is_base_role': bool(r.base_positions.all()),
            'is_system': r.is_system,
            'is_admin_role': is_administrator_role(r),
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

@permission_gate({'POST': 'roles.create'})
@admin_only
@validated_payload(ROLE_FIELDS)
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
    position = _active_role_position(data.get('position_id'))

    if not position:
        return JsonResponse({'success': False, 'message': 'Selecciona un cargo activo para el rol.'}, status=400)

    if name is None or description is None or not name or len(name) > 50 or len(description) > 255:
        return JsonResponse({'success': False, 'message': 'Nombre o descripción inválidos.'}, status=400)
    permissions = _validated_permissions(permissions)
    if permissions is None:
        return JsonResponse({'success': False, 'message': 'Permisos inválidos.'}, status=400)

    if is_administrator_role(name):
        return JsonResponse({'success': False, 'message': 'El nombre Administrador está reservado para el rol de sistema.'}, status=400)
    if Role.objects.filter(name__iexact=name).exists():
        return JsonResponse({'success': False, 'message': f"Ya existe un rol activo con el nombre '{name}'."}, status=400)

    try:
        with transaction.atomic():
            role = Role.objects.create(
                name=name,
                description=description,
                is_system=is_system,
                permissions_data=[],
                position=position,
            )
            permissions = set_role_permission_codes(role, permissions)

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
                    'position_id': position.pk,
                }
            )

        return JsonResponse({
            'success': True,
            'message': f"Rol '{name}' creado exitosamente con {len(permissions)} permisos.",
            'role': {
                'id': role.id,
                'name': role.name,
                'description': role.description,
                'position_id': position.pk,
                'position_name': position.name,
                'is_base_role': False,
                'is_system': role.is_system,
                'is_admin_role': False,
                'permissions': role.permissions_data,
                'permissions_count': len(role.permissions_data or []),
                'users_count': 0,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'No se pudo completar la operación. Inténtalo nuevamente.'}, status=500)

@permission_gate({'POST': 'roles.edit', 'PUT': 'roles.edit'})
@admin_only
@validated_payload(ROLE_FIELDS)
def api_role_update(request, pk):
    """
    Modifica un rol existente, su descripción y su matriz de funciones/permisos (MyAdmin).
    """
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    role = get_object_or_404(Role, id=pk, deleted_at__isnull=True)
    data = _get_request_data(request)

    position = role.position
    if 'position_id' in data:
        requested_position = _ids([data.get('position_id')])
        if (requested_position and requested_position[0] == role.position_id
                and role.position and role.position.deleted_at is None):
            # Un cargo inactivo existente puede conservar su vínculo durante una edición.
            position = role.position
        else:
            position = _active_role_position(data.get('position_id'))
        if not position:
            return JsonResponse({'success': False, 'message': 'Selecciona un cargo activo para el rol.'}, status=400)
        if role.base_positions.exclude(pk=position.pk).exists():
            return JsonResponse({'success': False, 'message': 'El rol base debe permanecer vinculado a su cargo.'}, status=400)
        if role.position_id != position.pk and role.users.exclude(position_id=position.pk).exists():
            return JsonResponse({'success': False, 'message': 'El rol tiene funcionarios de otro cargo; revisa sus asignaciones antes de vincularlo.'}, status=409)
    elif not position:
        return JsonResponse({'success': False, 'message': 'Selecciona un cargo para regularizar este rol histórico.'}, status=400)

    new_name = _text(data, 'name', role.name)
    new_description = _text(data, 'description')
    if 'description' not in data:
        new_description = role.description

    new_permissions = data.get('permissions')
    if new_permissions is None:
        new_permissions = sorted(role_permission_codes(role))

    if is_administrator_role(role) or role.name in ('SuperAdministrador', 'Super Administrador'):
        return JsonResponse({'success': False, 'message': 'El rol de administración está protegido.'}, status=403)
    if (role.is_system or role.base_positions.exists()) and new_name != role.name:
        return JsonResponse({'success': False, 'message': 'El nombre del rol base se modifica desde su cargo.'}, status=400)
    if new_name is None or new_description is None or not new_name or len(new_name) > 50 or len(new_description) > 255:
        return JsonResponse({'success': False, 'message': 'Nombre o descripción inválidos.'}, status=400)
    if is_administrator_role(new_name):
        return JsonResponse({'success': False, 'message': 'El nombre Administrador está reservado para el rol de sistema.'}, status=400)
    new_permissions = _validated_permissions(new_permissions)
    if new_permissions is None:
        return JsonResponse({'success': False, 'message': 'Permisos inválidos.'}, status=400)

    # Validar duplicados si se cambia el nombre
    if new_name != role.name and Role.objects.filter(name__iexact=new_name).exclude(id=role.id).exists():
        return JsonResponse({'success': False, 'message': f"El nombre '{new_name}' ya se encuentra en uso por otro rol."}, status=400)

    try:
        with transaction.atomic():
            prev_permissions = sorted(role_permission_codes(role))
            prev_perms_count = len(prev_permissions)
            prev_name = role.name

            role.name = new_name
            role.description = new_description
            role.position = position
            role.save(update_fields=['name', 'description', 'position', 'updated_at'])
            if (role.is_system and not position.base_role_id and not role.base_positions.exists()
                    and role_name_for_position(position.name).casefold() == role.name.casefold()):
                position.base_role = role
                position.save(update_fields=['base_role', 'updated_at'])
            new_permissions = set_role_permission_codes(role, new_permissions)

            current_admin = request.user if request.user.is_authenticated else None
            AuditLog.objects.create(
                user=current_admin,
                affected_table='rol',
                affected_record_id=str(role.id),
                action='UPDATE',
                previous_value={'name': prev_name, 'permissions_count': prev_perms_count, 'permissions': prev_permissions},
                new_value={
                    'name': new_name,
                    'description': new_description,
                    'permissions_count': len(new_permissions),
                    'permissions': new_permissions,
                    'position_id': position.pk,
                }
            )

        return JsonResponse({
            'success': True,
            'message': f"Rol '{role.name}' actualizado correctamente con {len(new_permissions)} permisos.",
            'role': {
                'id': role.id,
                'name': role.name,
                'description': role.description,
                'position_id': position.pk,
                'position_name': position.name,
                'is_base_role': role.base_positions.exists(),
                'is_system': role.is_system,
                'is_admin_role': is_administrator_role(role),
                'permissions': sorted(role_permission_codes(role)),
                'permissions_count': len(role_permission_codes(role)),
                'users_count': role.users.filter(deleted_at__isnull=True).count(),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'No se pudo completar la operación. Inténtalo nuevamente.'}, status=500)

@permission_gate({'POST': 'roles.delete', 'DELETE': 'roles.delete'})
@admin_only
def api_role_delete(request, pk):
    """
    Elimina un rol de la base de datos (con verificación de protección de sistema y usuarios).
    """
    if request.method not in ['POST', 'DELETE']:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    role = get_object_or_404(Role, id=pk, deleted_at__isnull=True)

    # Protección de roles base del sistema
    protected_roles = ['Operador', 'Consultor', 'Verificador']
    if role.is_system or role.base_positions.exists() or role.name in protected_roles or is_administrator_role(role):
        return JsonResponse({
            'success': False,
            'message': f"El rol '{role.name}' es un rol protegido fundamental de la plataforma municipal y no puede ser eliminado."
        }, status=403)

    assigned_users = role.users.count()
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
                    'permissions_count': len(role_permission_codes(role)),
                }
            )

            role.delete()

        return JsonResponse({
            'success': True,
            'message': f"El rol '{role_name}' ha sido eliminado exitosamente del sistema."
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'No se pudo completar la operación. Inténtalo nuevamente.'}, status=500)

@permission_gate({'POST': 'roles.create'})
@admin_only
@validated_payload(ROLE_FIELDS)
def api_role_duplicate(request, pk):
    """
    Duplica un rol existente junto con toda su matriz de permisos (función phpMyAdmin).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    origin_role = get_object_or_404(Role, id=pk, deleted_at__isnull=True)
    data = _get_request_data(request)
    position = _active_role_position(data.get('position_id'))
    if not position:
        return JsonResponse({'success': False, 'message': 'Selecciona un cargo activo para duplicar el rol.'}, status=400)

    base_name = _text(data, 'name', f"{origin_role.name[:42]} (Copia)")
    if base_name is None or not base_name or len(base_name) > 50:
        return JsonResponse({'success': False, 'message': 'Nombre inválido.'}, status=400)
    if is_administrator_role(base_name):
        return JsonResponse({'success': False, 'message': 'El nombre Administrador está reservado para el rol de sistema.'}, status=400)
    candidate_name = base_name
    counter = 1
    while Role.objects.filter(name__iexact=candidate_name).exists():
        counter += 1
        suffix = f' {counter}'
        if 'name' in data:
            if len(base_name) + len(suffix) > 50:
                return JsonResponse({'success': False, 'message': 'Nombre demasiado largo.'}, status=400)
            candidate_name = f'{base_name}{suffix}'
        else:
            suffix = f' (Copia) {counter}'
            candidate_name = f'{origin_role.name[:50 - len(suffix)]}{suffix}'

    try:
        with transaction.atomic():
            new_role = Role.objects.create(
                name=candidate_name,
                description=origin_role.description,
                is_system=False,
                permissions_data=[],
                position=position,
            )
            cloned_permissions = set_role_permission_codes(new_role, role_permission_codes(origin_role))

            current_admin = request.user if request.user.is_authenticated else None
            AuditLog.objects.create(
                user=current_admin,
                affected_table='rol',
                affected_record_id=str(new_role.id),
                action='CREATE',
                new_value={
                    'name': candidate_name,
                    'cloned_from': origin_role.name,
                    'position_id': position.pk,
                    'permissions_count': len(cloned_permissions),
                }
            )

        return JsonResponse({
            'success': True,
            'message': f"Rol clonado exitosamente como '{candidate_name}'.",
            'role': {
                'id': new_role.id,
                'name': new_role.name,
                'description': new_role.description,
                'position_id': position.pk,
                'position_name': position.name,
                'is_base_role': False,
                'is_system': False,
                'is_admin_role': False,
                'permissions': cloned_permissions,
                'permissions_count': len(cloned_permissions),
                'users_count': 0,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'No se pudo completar la operación. Inténtalo nuevamente.'}, status=500)

@permission_gate({'POST': 'roles.manage_features'})
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
            'commune': getattr(record, 'commune', None),
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


@permission_gate({'GET': 'delegaciones.view', 'POST': 'delegaciones.create'})
@validated_payload(DELEGATION_FIELDS)
def api_delegations(request):
    """Lista y crea delegaciones usadas por la asignación real de funcionarios."""
    if request.method == 'GET':
        from activities.models import Activity
        from agenda.models import CollectiveAgenda
        from metrics.models import DailyIndicator
        from social.models import SocialCase

        items = _delegations_scope(request).order_by('name')
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
                'id': item.id, 'code': item.code, 'name': item.name, 'scope': item.scope,
                'commune': item.commune,
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
    if not _has_administrator_role(request.user):
        return JsonResponse({'success': False, 'message': 'Solo Administración puede crear delegaciones.'}, status=403)

    data = _get_request_data(request)
    name, scope = _text(data, 'name'), _text(data, 'scope')
    commune = _text(data, 'commune', 'La Serena')
    code = _text(data, 'code')
    status = data.get('status', 'Activo')
    if name is None or scope is None or not name or not scope or len(name) > 100 or len(scope) > 100:
        return JsonResponse({'success': False, 'message': 'Nombre y ámbito territorial inválidos.'}, status=400)
    if not commune or len(commune) > 100:
        return JsonResponse({'success': False, 'message': 'Comuna inválida.'}, status=400)
    if status not in ('Activo', 'Inactivo'):
        return JsonResponse({'success': False, 'message': 'Estado inválido.'}, status=400)
    if Delegation.objects.filter(name__iexact=name).exists():
        return JsonResponse({'success': False, 'message': 'Ya existe una delegación con ese nombre.'}, status=400)
    if code is None or (code and (not re.fullmatch(r'[A-Za-z0-9-]{2,20}', code) or Delegation.objects.filter(code__iexact=code).exists())):
        return JsonResponse({'success': False, 'message': 'Código inválido o ya utilizado.'}, status=400)
    detail_error = _validate_delegation_details({**data, 'commune': commune})
    if detail_error:
        return JsonResponse({'success': False, 'message': detail_error}, status=400)
    if any(len(_text(data, field)) > limit for field, limit in (
        ('address', 200), ('phone', 30), ('email', 120), ('schedule', 120),
        ('manager_name', 150), ('photo_url', 255), ('description', 500)
    )):
        return JsonResponse({'success': False, 'message': 'Detalle demasiado largo.'}, status=400)
    with transaction.atomic():
        item = Delegation.objects.create(
            name=name, code=code.upper() if code else None, scope=scope, commune=commune, status=status,
            address=_text(data, 'address'), phone=_text(data, 'phone'),
            email=(_text(data, 'email') or '').lower(), schedule=_text(data, 'schedule'),
            manager_name=_text(data, 'manager_name'), photo_url=_text(data, 'photo_url'),
            description=_text(data, 'description'),
        )
        _catalog_audit(request, 'delegacion', item, 'CREATE')
    return JsonResponse({'success': True, 'message': f"Delegación '{name}' creada y guardada.", 'id': item.id, 'code': item.code})


@permission_gate({'POST': 'delegaciones.edit', 'PUT': 'delegaciones.edit'})
@validated_payload(DELEGATION_FIELDS)
def api_delegation_update(request, pk):
    if request.method not in ('POST', 'PUT'):
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    item = get_object_or_404(_delegations_scope(request), id=pk)
    data = _get_request_data(request)
    name = _text(data, 'name', item.name)
    code = _text(data, 'code', item.code)
    scope = _text(data, 'scope', item.scope)
    commune = _text(data, 'commune', item.commune)
    status = data.get('status', item.status)
    if name is None or scope is None or not name or not scope or len(name) > 100 or len(scope) > 100 or status not in ('Activo', 'Inactivo'):
        return JsonResponse({'success': False, 'message': 'Revisa el nombre, ámbito y estado.'}, status=400)
    if not commune or len(commune) > 100:
        return JsonResponse({'success': False, 'message': 'Comuna inválida.'}, status=400)
    if status == 'Inactivo' and item.status == 'Activo' and item.users.filter(deleted_at__isnull=True, status='Activo').exists():
        return JsonResponse({'success': False, 'message': 'La delegación tiene funcionarios activos.'}, status=400)
    if Delegation.objects.filter(name__iexact=name).exclude(id=pk).exists():
        return JsonResponse({'success': False, 'message': 'Ya existe otra delegación con ese nombre.'}, status=400)
    if not code or not re.fullmatch(r'[A-Za-z0-9-]{2,20}', code) or Delegation.objects.filter(code__iexact=code).exclude(id=pk).exists():
        return JsonResponse({'success': False, 'message': 'Código inválido o ya utilizado.'}, status=400)
    merged = {field: getattr(item, field) for field in (
        'name', 'scope', 'commune', 'address', 'phone', 'email', 'schedule',
        'manager_name', 'photo_url', 'description'
    )}
    merged.update({key: data.get(key) for key in merged if key in data})
    detail_error = _validate_delegation_details(merged)
    if detail_error:
        return JsonResponse({'success': False, 'message': detail_error}, status=400)
    if any(len(_text(merged, field)) > limit for field, limit in (
        ('address', 200), ('phone', 30), ('email', 120), ('schedule', 120),
        ('manager_name', 150), ('photo_url', 255), ('description', 500)
    )):
        return JsonResponse({'success': False, 'message': 'Detalle demasiado largo.'}, status=400)
    previous = {'code': item.code, 'name': item.name, 'scope': item.scope, 'commune': item.commune, 'status': item.status, 'address': item.address,
                'phone': item.phone, 'email': item.email, 'schedule': item.schedule,
                'manager_name': item.manager_name, 'photo_url': item.photo_url, 'description': item.description}
    with transaction.atomic():
        item.name, item.code, item.scope, item.commune, item.status = name, code.upper(), scope, commune, status
        for field in ('address', 'phone', 'email', 'schedule', 'manager_name', 'photo_url', 'description'):
            if field in data:
                setattr(item, field, _text(data, field))
        item.email = item.email.lower()
        item.save(update_fields=['name', 'code', 'scope', 'commune', 'status', 'address', 'phone', 'email', 'schedule',
                                 'manager_name', 'photo_url', 'description', 'updated_at'])
        _catalog_audit(request, 'delegacion', item, 'UPDATE', previous)
    return JsonResponse({'success': True, 'message': f"Delegación '{name}' actualizada."})


@permission_gate({'POST': 'delegaciones.delete'})
def api_delegation_toggle(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    item = get_object_or_404(_delegations_scope(request), id=pk)
    previous = {'name': item.name, 'scope': item.scope, 'status': item.status}
    if item.status == 'Activo' and item.users.filter(deleted_at__isnull=True, status='Activo').exists():
        return JsonResponse({'success': False, 'message': 'La delegación tiene funcionarios activos.'}, status=400)
    item.status = 'Inactivo' if item.status == 'Activo' else 'Activo'
    with transaction.atomic():
        item.save(update_fields=['status', 'updated_at'])
        _catalog_audit(request, 'delegacion', item, 'UPDATE', previous)
    return JsonResponse({'success': True, 'message': f"Delegación {item.status.lower()} correctamente.", 'status': item.status})


@permission_gate({'POST': 'delegaciones.delete', 'DELETE': 'delegaciones.delete'})
def api_delegation_delete(request, pk):
    """Elimina una delegación sin referencias operativas y registra la auditoría."""
    if request.method not in ('POST', 'DELETE'):
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    item = get_object_or_404(_delegations_scope(request), id=pk, deleted_at__isnull=True)

    from activities.models import Activity
    from agenda.models import CollectiveAgenda
    from social.models import SocialCase

    dependencies = {
        'funcionarios': item.users.count(),
        'atenciones': Activity.objects.filter(delegation=item).count(),
        'compromisos de agenda': CollectiveAgenda.objects.filter(delegation=item).count(),
        'casos sociales': SocialCase.objects.filter(delegation=item).count(),
    }
    in_use = [f"{count} {name}" for name, count in dependencies.items() if count]
    if in_use:
        return JsonResponse({
            'success': False,
            'message': 'No se puede eliminar la delegación porque tiene registros vinculados: ' + ', '.join(in_use) + '.',
        }, status=400)

    previous = {'name': item.name, 'code': item.code, 'scope': item.scope}
    name = item.name
    with transaction.atomic():
        _catalog_audit(request, 'delegacion', item, 'DELETE', previous)
        item.delete()
    return JsonResponse({'success': True, 'message': f"Delegación '{name}' eliminada de la base de datos."})


def _position_mutation_denied(request, item=None, name=None):
    """Un permiso de catálogo no permite promover roles ni cambiar otras sedes."""
    if _has_administrator_role(request.user):
        return None
    administrative = any(
        is_administrator_role(role_name_for_position(label))
        for label in (name, item.name if item else None) if label
    ) or bool(item and item.base_role_id and is_administrator_role(item.base_role))
    if administrative:
        return JsonResponse({
            'success': False,
            'message': 'Solo Administración puede crear o modificar cargos administrativos.',
        }, status=403)
    if item:
        actor = UserProfile.objects.select_related('delegation').filter(
            user=request.user, status='Activo', deleted_at__isnull=True,
        ).first()
        if (not actor or not actor.delegation_id or actor.delegation.status != 'Activo'
                or actor.delegation.deleted_at is not None or item.users.filter(
                    deleted_at__isnull=True,
                ).exclude(delegation_id=actor.delegation_id).exists()):
            return JsonResponse({
                'success': False,
                'message': 'Solo Administración puede modificar cargos de otras delegaciones.',
            }, status=403)
    return None


@permission_gate({'GET': 'cargos.view', 'POST': 'cargos.create'})
@validated_payload(POSITION_FIELDS)
def api_positions(request):
    """Lista y crea cargos institucionales asignables a funcionarios."""
    if request.method == 'GET':
        items = Position.objects.filter(deleted_at__isnull=True).order_by('name')
        return JsonResponse({'success': True, 'positions': [{
            'id': item.id, 'name': item.name, 'description': item.description,
            'status': item.status, 'base_role_id': item.base_role_id,
            'users_count': _users_scope(request).filter(position=item).count(),
        } for item in items]})
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    data = _get_request_data(request)
    name, description = _text(data, 'name'), _text(data, 'description')
    status = data.get('status', 'Activo')
    if name is None or description is None or not name or len(name) > 50 or len(description) > 500:
        return JsonResponse({'success': False, 'message': 'Nombre o descripción inválidos.'}, status=400)
    if status not in ('Activo', 'Inactivo'):
        return JsonResponse({'success': False, 'message': 'Estado inválido.'}, status=400)
    denied = _position_mutation_denied(request, name=name)
    if denied:
        return denied
    if Position.objects.filter(name__iexact=name).exists():
        return JsonResponse({'success': False, 'message': 'Ya existe un cargo con ese nombre.'}, status=400)
    if Role.objects.filter(name__iexact=role_name_for_position(name)).exists():
        return JsonResponse({'success': False, 'message': 'Ese nombre ya está ocupado por un rol. Usa un nombre distinto para el cargo.'}, status=400)
    with transaction.atomic():
        item = Position.objects.create(name=name, description=description, status=status)
        _roles_with_position_base([], item)
        _catalog_audit(request, 'cargo', item, 'CREATE')
    return JsonResponse({'success': True, 'message': f"Cargo '{name}' guardado. Se creó su rol base sin permisos; configúralos en Roles.", 'id': item.id, 'base_role': role_name_for_position(item.name)})


@permission_gate({'POST': 'cargos.edit', 'PUT': 'cargos.edit'})
@validated_payload(POSITION_FIELDS)
def api_position_update(request, pk):
    if request.method not in ('POST', 'PUT'):
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    item = get_object_or_404(Position, id=pk, deleted_at__isnull=True)
    data = _get_request_data(request)
    name = _text(data, 'name', item.name)
    description = _text(data, 'description', item.description)
    status = data.get('status', item.status)
    if name is None or description is None or not name or len(name) > 50 or len(description) > 500 or status not in ('Activo', 'Inactivo'):
        return JsonResponse({'success': False, 'message': 'Revisa el nombre y estado.'}, status=400)
    denied = _position_mutation_denied(request, item, name)
    if denied:
        return denied
    if status == 'Inactivo' and item.status == 'Activo' and item.users.filter(deleted_at__isnull=True, status='Activo').exists():
        return JsonResponse({'success': False, 'message': 'El cargo tiene funcionarios activos.'}, status=400)
    if Position.objects.filter(name__iexact=name).exclude(id=pk).exists():
        return JsonResponse({'success': False, 'message': 'Ya existe otro cargo con ese nombre.'}, status=400)
    previous = {'name': item.name, 'description': item.description, 'status': item.status}
    next_name = role_name_for_position(name)
    base_role = item.base_role
    if base_role and (not base_role.is_system or base_role.deleted_at is not None):
        return JsonResponse({'success': False, 'message': 'El rol base vinculado al cargo requiere revisión administrativa antes de modificarlo.'}, status=409)
    if base_role and (base_role.position_id not in (None, item.pk) or base_role.base_positions.exclude(pk=item.pk).exists()):
        return JsonResponse({'success': False, 'message': 'El rol base está vinculado a otro cargo y requiere revisión administrativa.'}, status=409)
    if Role.objects.filter(name__iexact=next_name).exclude(pk=base_role.pk if base_role else None).exists():
        return JsonResponse({'success': False, 'message': 'El nombre ya pertenece a otro rol. No se modificó el cargo.'}, status=400)
    if base_role and is_administrator_role(base_role) and base_role.name != next_name:
        return JsonResponse({'success': False, 'message': 'No se puede renombrar un rol administrativo protegido desde el cargo.'}, status=403)
    if base_role and base_role.base_positions.exclude(pk=item.pk).exists() and base_role.name != next_name:
        return JsonResponse({'success': False, 'message': 'Este rol base es compartido por otros cargos y no se puede renombrar.'}, status=400)
    with transaction.atomic():
        if base_role:
            base_role.name = next_name
            base_role.save(update_fields=['name', 'updated_at'])
            item.base_role = base_role
        item.name, item.description, item.status = name, description, status
        item.save(update_fields=['name', 'description', 'status', 'base_role', 'updated_at'])
        _roles_with_position_base([], item)
        _catalog_audit(request, 'cargo', item, 'UPDATE', previous)
    return JsonResponse({'success': True, 'message': f"Cargo '{name}' y su rol base quedaron sincronizados.", 'base_role': role_name_for_position(item.name)})


@permission_gate({'POST': 'cargos.delete'})
def api_position_toggle(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    item = get_object_or_404(Position, id=pk, deleted_at__isnull=True)
    denied = _position_mutation_denied(request, item)
    if denied:
        return denied
    previous = {'name': item.name, 'description': item.description, 'status': item.status}
    if item.status == 'Activo' and item.users.filter(deleted_at__isnull=True, status='Activo').exists():
        return JsonResponse({'success': False, 'message': 'El cargo tiene funcionarios activos.'}, status=400)
    item.status = 'Inactivo' if item.status == 'Activo' else 'Activo'
    with transaction.atomic():
        item.save(update_fields=['status', 'updated_at'])
        _catalog_audit(request, 'cargo', item, 'UPDATE', previous)
    return JsonResponse({'success': True, 'message': f"Cargo {item.status.lower()} correctamente.", 'status': item.status})


@permission_gate({'POST': 'cargos.delete', 'DELETE': 'cargos.delete'})
def api_position_delete(request, pk):
    """Elimina permanentemente un cargo institucional si no tiene funcionarios asignados."""
    if request.method not in ('POST', 'DELETE'):
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    item = get_object_or_404(Position, id=pk, deleted_at__isnull=True)
    denied = _position_mutation_denied(request, item)
    if denied:
        return denied
    assigned_count = item.users.filter(deleted_at__isnull=True).count()
    if assigned_count > 0:
        return JsonResponse({
            'success': False,
            'message': f"No se puede eliminar el cargo '{item.name}' porque tiene {assigned_count} funcionario(s) asignado(s). Reasigna los funcionarios antes de eliminarlo."
        }, status=400)
    if item.goals.exists():
        return JsonResponse({'success': False, 'message': 'El cargo tiene metas registradas. Consérvalo inactivo para mantener su historial.'}, status=409)
    if item.access_roles.exists():
        return JsonResponse({'success': False, 'message': 'El cargo tiene roles asociados. Desactívalo para conservar sus permisos e historial.'}, status=409)
    with transaction.atomic():
        _catalog_audit(request, 'cargo', item, 'DELETE', {'name': item.name, 'description': item.description})
        item.delete()
    return JsonResponse({'success': True, 'message': f"Cargo '{item.name}' eliminado exitosamente de la base de datos."})




