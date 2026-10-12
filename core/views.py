from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Replace, Upper
from django.utils import timezone
from datetime import timedelta
import hashlib
import hmac
import ipaddress
import secrets
import re
import unicodedata
from .models import LoginThrottle, PasswordRecoveryCode
from organization.models import UserProfile


class _RecoveryEmailError(Exception):
    """Fallo de entrega que no debe cambiar la respuesta pública."""


def _send_password_recovery_email(full_name, recipient, code):
    """Envía el correo de recuperación en formato HTML y texto plano."""
    if not settings.DEBUG and settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
        # En producción jamás mostrar un código de recuperación en los logs.
        raise _RecoveryEmailError('El correo saliente no está configurado.')
    context = {'full_name': full_name, 'code': code, 'valid_minutes': 10}
    subject = 'Tu código para recuperar el acceso | Municipalidad de La Serena'
    message = EmailMultiAlternatives(
        subject=subject,
        body=render_to_string('emails/password_recovery.txt', context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(render_to_string('emails/password_recovery.html', context), 'text/html')
    return message.send(fail_silently=False)


def _normalize_rut(value):
    return re.sub(r'[^0-9kK]', '', value or '').upper()


def _login_rate_key(request):
    """Usa la IP real solo cuando la petición viene del proxy local de confianza."""
    origin = request.META.get('REMOTE_ADDR', '')
    if origin in ('127.0.0.1', '::1'):
        origin = request.META.get('HTTP_X_REAL_IP', origin)
    try:
        origin = str(ipaddress.ip_address(origin))
    except (TypeError, ValueError):
        origin = 'origen-desconocido'
    return hmac.new(settings.SECRET_KEY.encode(), origin.encode(), hashlib.sha256).hexdigest()


def _record_login_failure(key, now):
    with transaction.atomic():
        attempt, _ = LoginThrottle.objects.select_for_update().get_or_create(ip_key=key)
        if now - attempt.window_started_at >= timedelta(minutes=5):
            attempt.failures = 0
            attempt.window_started_at = now
            attempt.blocked_until = None
        attempt.failures += 1
        if attempt.failures >= 20:
            attempt.blocked_until = now + timedelta(minutes=5)
        attempt.save(update_fields=['failures', 'window_started_at', 'blocked_until'])
        return bool(attempt.blocked_until and attempt.blocked_until > now)


def _find_profile_for_login(identifier):
    """Resuelve una cuenta por RUT o correo electrónico registrado."""
    normalized_identifier = (identifier or '').strip()
    if '@' in normalized_identifier:
        matches = UserProfile.objects.select_related('user').filter(
            email__iexact=normalized_identifier, deleted_at__isnull=True
        )
        return matches.first() if matches.count() == 1 else None

    normalized_rut = _normalize_rut(identifier)
    if normalized_rut and normalized_rut[:-1].isdigit():
        matches = list(UserProfile.objects.select_related('user')
                       .filter(deleted_at__isnull=True)
                       .annotate(normalized_rut=Upper(Replace(Replace(F('rut'), Value('.'), Value('')), Value('-'), Value(''))))
                       .filter(normalized_rut=normalized_rut)[:2])
        if len(matches) == 1:
            return matches[0]
    return None


def _normalized_label(value):
    value = unicodedata.normalize('NFKD', value or '')
    return ''.join(char for char in value if not unicodedata.combining(char)).strip().casefold()


def dashboard_route_for_position(position_name):
    """Cargo selecciona el panel; los permisos del rol se validan aparte."""
    return {
        'administrador general': 'activities:dashboard_admin',
        'coordinador del sistema': 'activities:dashboard_coordinador',
        'delegado municipal': 'activities:dashboard_delegado',
        'gestor territorial': 'activities:dashboard_gestor',
        'verificador tecnico': 'activities:dashboard_verificador',
        'asistente social': 'activities:dashboard_asistente',
        'auditor municipal': 'activities:dashboard_auditor',
    }.get(_normalized_label(position_name), 'activities:dashboard_cargo' if _normalized_label(position_name) else 'core:login')


def _start_session_for_user(request, user, profile):
    role_name = profile.roles.filter(deleted_at__isnull=True).values_list('name', flat=True).first()
    position_name = profile.position.name if profile.position and profile.position.status == 'Activo' and profile.position.deleted_at is None else None
    destination = dashboard_route_for_position(position_name)
    if destination == 'core:login':
        messages.error(request, 'Tu cuenta todavía no tiene un cargo activo con panel asignado. Contacta a administración.')
        return redirect('core:login')
    login(request, user)
    request.session['user_role'] = role_name or ''
    request.session['user_position'] = position_name
    request.session['user_name'] = profile.full_name
    request.session['user_rut'] = profile.rut
    request.session['user_delegation'] = profile.delegation.name if profile.delegation else 'Sin delegación asignada'
    return redirect(destination)

def login_view(request):
    if not getattr(getattr(request, 'user', None), 'is_authenticated', False):
        for key in ('user_role', 'user_position', 'user_name', 'user_rut', 'user_delegation'):
            request.session.pop(key, None)
    if request.method == 'POST':
        now = timezone.now()
        rate_key = _login_rate_key(request)
        throttle = LoginThrottle.objects.filter(pk=rate_key).first()
        if throttle and throttle.blocked_until and throttle.blocked_until > now:
            messages.error(request, 'Demasiados intentos. Intenta de nuevo en unos minutos.')
            return render(request, 'login.html', status=429)
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = None
        if identifier and password:
            profile = _find_profile_for_login(identifier)
            if profile and profile.user:
                user = authenticate(request, username=profile.user.username, password=password)

        if user is None or not user.is_active:
            limited = _record_login_failure(rate_key, now)
            messages.error(request, 'Demasiados intentos. Intenta de nuevo en unos minutos.' if limited else 'Usuario o contraseña incorrectos.')
            return render(request, 'login.html', status=429 if limited else 401)

        profile = getattr(user, 'profile', None)
        if profile is None or profile.status != 'Activo' or profile.deleted_at is not None:
            limited = _record_login_failure(rate_key, now)
            messages.error(request, 'Demasiados intentos. Intenta de nuevo en unos minutos.' if limited else 'Usuario o contraseña incorrectos.')
            return render(request, 'login.html', status=429 if limited else 401)

        LoginThrottle.objects.filter(pk=rate_key).delete()
        return _start_session_for_user(request, user, profile)

    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    request.session.flush()
    messages.info(request, "Has cerrado tu sesión correctamente.")
    return redirect('core:login')


def password_recovery_view(request):
    """Recuperación con respuesta pública uniforme y código de un solo uso."""
    recovery_user_id = request.session.get('recovery_user_id')
    if request.method == 'POST':
        action = request.POST.get('action', 'request_code')
        if action == 'request_code':
            now = timezone.now()
            last_request = request.session.get('recovery_last_request_at')
            request.session['recovery_pending'] = True
            session_limited = isinstance(last_request, (int, float)) and now.timestamp() - last_request < 45
            if not session_limited:
                request.session['recovery_last_request_at'] = now.timestamp()
                request.session.pop('recovery_user_id', None)
                request.session.pop('recovery_verified_code_id', None)
                identifier = request.POST.get('identifier', '').strip()
                # Comparte la misma resolución normalizada del login: acepta el RUT
                # con o sin puntos/guion y falla de forma cerrada si hay duplicados.
                profile = _find_profile_for_login(identifier)
                if profile and profile.status == 'Activo' and profile.user.is_active and profile.email:
                    try:
                        with transaction.atomic():
                            # El bloqueo serializa solicitudes de sesiones distintas para la misma cuenta.
                            profile.user.__class__.objects.select_for_update().get(pk=profile.user_id)
                            latest = PasswordRecoveryCode.objects.filter(user=profile.user).order_by('-created_at').first()
                            if latest and latest.created_at and now - latest.created_at < timedelta(seconds=45):
                                request.session['recovery_user_id'] = profile.user_id
                            else:
                                code = f'{secrets.randbelow(1000000):06d}'
                                try:
                                    sent = _send_password_recovery_email(profile.full_name, profile.email, code)
                                except Exception as exc:
                                    raise _RecoveryEmailError from exc
                                if sent != 1:
                                    raise _RecoveryEmailError
                                PasswordRecoveryCode.objects.filter(user=profile.user, used_at__isnull=True).update(used_at=now)
                                PasswordRecoveryCode.objects.create(
                                    user=profile.user,
                                    code_hash=make_password(code),
                                    expires_at=now + timedelta(minutes=10),
                                )
                                request.session['recovery_user_id'] = profile.user_id
                    except _RecoveryEmailError:
                        # La respuesta pública no depende de la disponibilidad del correo.
                        pass
            return render(request, 'password_recovery.html', {
                'step': 'verify',
                'notice': 'Si existe una cuenta activa con esos datos, enviamos un código al correo registrado.',
            })

        if action == 'verify_code' and recovery_user_id:
            code = request.POST.get('code', '').strip()
            with transaction.atomic():
                recovery = (PasswordRecoveryCode.objects.select_for_update()
                            .filter(user_id=recovery_user_id, used_at__isnull=True,
                                    user__is_active=True, user__profile__status='Activo',
                                    user__profile__deleted_at__isnull=True).first())
                if not recovery or not recovery.is_valid:
                    request.session.pop('recovery_user_id', None)
                    request.session.pop('recovery_pending', None)
                    return render(request, 'password_recovery.html', {'step': 'verify', 'error': 'El código no es válido o expiró. Solicita uno nuevo si es necesario.'}, status=400)
                if not re.fullmatch(r'[0-9]{6}', code) or not check_password(code, recovery.code_hash):
                    recovery.attempts += 1
                    recovery.save(update_fields=['attempts', 'updated_at'])
                    return render(request, 'password_recovery.html', {'step': 'verify', 'error': 'El código no es válido o expiró. Solicita uno nuevo si es necesario.'}, status=400)
                request.session['recovery_verified_code_id'] = recovery.pk
            return render(request, 'password_recovery.html', {'step': 'new_password'})

        if action == 'reset_password' and recovery_user_id and request.session.get('recovery_verified_code_id'):
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            if not confirm_password or new_password != confirm_password:
                return render(request, 'password_recovery.html', {
                    'step': 'new_password', 'error': 'Las contraseñas no coinciden.',
                }, status=400)
            with transaction.atomic():
                recovery = (PasswordRecoveryCode.objects.select_for_update()
                            .filter(pk=request.session['recovery_verified_code_id'], user_id=recovery_user_id,
                                    used_at__isnull=True, user__is_active=True,
                                    user__profile__status='Activo',
                                    user__profile__deleted_at__isnull=True).first())
                if not recovery or not recovery.is_valid:
                    request.session.pop('recovery_verified_code_id', None)
                    request.session.pop('recovery_user_id', None)
                    request.session.pop('recovery_pending', None)
                    return render(request, 'password_recovery.html', {'step': 'request', 'error': 'El código expiró o superó el límite de intentos.'}, status=400)
                user = recovery.user
                try:
                    validate_password(new_password, user=user)
                except ValidationError as exc:
                    return render(request, 'password_recovery.html', {'step': 'new_password', 'error': ' '.join(exc.messages)}, status=400)
                user.set_password(new_password)
                user.save(update_fields=['password'])
                PasswordRecoveryCode.objects.filter(user_id=recovery_user_id, used_at__isnull=True).update(used_at=timezone.now())
            request.session.pop('recovery_user_id', None)
            request.session.pop('recovery_pending', None)
            request.session.pop('recovery_verified_code_id', None)
            return render(request, 'password_recovery.html', {'success': 'Contraseña actualizada. Ya puedes iniciar sesión.'})

        if action in {'reset_password', 'verify_code'}:
            return render(request, 'password_recovery.html', {'step': 'verify', 'error': 'El código no es válido o expiró. Solicita uno nuevo si es necesario.'}, status=400)
    verified_id = request.session.get('recovery_verified_code_id')
    if verified_id:
        recovery = PasswordRecoveryCode.objects.filter(
            pk=verified_id, user_id=recovery_user_id, used_at__isnull=True,
        ).first() if recovery_user_id else None
        if not recovery or not recovery.is_valid:
            request.session.pop('recovery_verified_code_id', None)
            verified_id = None
    step = 'new_password' if verified_id else ('verify' if request.session.get('recovery_pending') else 'request')
    return render(request, 'password_recovery.html', {'step': step})
