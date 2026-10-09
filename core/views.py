from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta
import secrets
import re
from .models import PasswordRecoveryCode
from organization.models import UserProfile


def _normalize_rut(value):
    return re.sub(r'[^0-9kK]', '', value or '').upper()


def _find_profile_for_login(identifier):
    """Resuelve únicamente RUT o nombre completo; el correo no es credencial de acceso."""
    normalized_rut = _normalize_rut(identifier)
    if normalized_rut and normalized_rut[:-1].isdigit():
        matches = [
            profile for profile in UserProfile.objects.select_related('user').all()
            if _normalize_rut(profile.rut) == normalized_rut
        ]
        if len(matches) == 1:
            return matches[0]
    matches = UserProfile.objects.select_related('user').filter(full_name__iexact=identifier)
    return matches.first() if matches.count() == 1 else None


def _role_redirect(role_name):
    normalized = (role_name or '').strip().casefold()
    if normalized in {'verificador', 'verificador técnico'}:
        return 'activities:dashboard_verificador'
    if normalized in {'gestor territorial', 'funcionario', 'funcionario / gestor territorial'}:
        return 'activities:dashboard_gestor'
    if normalized == 'administrador general':
        return 'activities:dashboard_admin'
    return 'core:login'


def _start_session_for_user(request, user, profile):
    role_name = profile.roles.filter(deleted_at__isnull=True).values_list('name', flat=True).first()
    if not role_name:
        messages.error(request, 'Tu cuenta está activa, pero todavía no tiene un rol asignado. Solicita al administrador que configure tu acceso.')
        logout(request)
        return redirect('core:login')
    login(request, user)
    request.session['user_role'] = role_name
    request.session['user_name'] = profile.full_name
    request.session['user_rut'] = profile.rut
    request.session['user_delegation'] = profile.delegation.name if profile.delegation else 'Sin delegación asignada'
    return redirect(_role_redirect(role_name))

def login_view(request):
    rol_param = request.GET.get('rol')
    if rol_param:
        if rol_param == 'admin':
            request.session['user_role'] = 'Administrador General'
            request.session['user_name'] = 'Alcaldía La Serena'
            request.session['user_rut'] = '11.111.111-1'
            request.session['user_delegation'] = 'Consolidado Comunal'
            return redirect('activities:dashboard_admin')
        elif rol_param == 'coordinador':
            request.session['user_role'] = 'Coordinador del Sistema'
            request.session['user_name'] = 'Marcelo Salazar Peña'
            request.session['user_rut'] = '13.456.789-0'
            request.session['user_delegation'] = 'Supervisión Comunal SGR'
            return redirect('core:login')
        elif rol_param == 'delegado':
            request.session['user_role'] = 'Delegado Municipal'
            request.session['user_name'] = 'Gonzalo Pizarro Rojas'
            request.session['user_rut'] = '14.234.567-8'
            request.session['user_delegation'] = 'Delegación Las Compañías'
            return redirect('core:login')
        elif rol_param == 'verificador':
            request.session['user_role'] = 'Verificador Técnico'
            request.session['user_name'] = 'Esteban Morales Vega'
            request.session['user_rut'] = '15.678.901-2'
            request.session['user_delegation'] = 'Delegación Las Compañías'
            return redirect('activities:dashboard_verificador')
        elif rol_param == 'consulta':
            request.session['user_role'] = 'Usuario de Consulta'
            request.session['user_name'] = 'Valeria Cáceres Soto'
            request.session['user_rut'] = '16.789.012-3'
            request.session['user_delegation'] = 'Auditoría Transversal'
            return redirect('core:login')
        elif rol_param in ['gestor', 'funcionario']:
            request.session['user_role'] = 'Gestor Territorial'
            request.session['user_name'] = 'Rodrigo Tapia Gallardo'
            request.session['user_rut'] = '17.892.456-3'
            request.session['user_delegation'] = 'Delegación Las Compañías'
            return redirect('activities:dashboard_gestor')

    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            profile = _find_profile_for_login(identifier)
            if profile and profile.user:
                user = authenticate(request, username=profile.user.username, password=password)

        if user is None or not user.is_active:
            messages.error(request, 'Usuario o contraseña incorrectos.')
            return render(request, 'login.html', status=401)

        profile = getattr(user, 'profile', None)
        if profile is None or profile.status != 'Activo':
            messages.error(request, 'La cuenta no tiene un perfil activo en el sistema.')
            return render(request, 'login.html', status=403)

        return _start_session_for_user(request, user, profile)

    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    request.session.flush()
    messages.info(request, "Has cerrado tu sesión correctamente.")
    return redirect('core:login')


def password_recovery_view(request):
    """Solicita código y permite cambiar la contraseña mediante sesión temporal."""
    recovery_user_id = request.session.get('recovery_user_id')
    if request.method == 'POST':
        action = request.POST.get('action', 'request_code')
        if action == 'request_code':
            identifier = request.POST.get('identifier', '').strip()
            profile = UserProfile.objects.select_related('user').filter(rut__iexact=identifier).first()
            if not profile:
                profile = UserProfile.objects.select_related('user').filter(email__iexact=identifier).first()
            if not profile or profile.status != 'Activo' or not profile.user.is_active:
                return render(request, 'password_recovery.html', {'error': 'No encontramos una cuenta activa con esos datos.'}, status=400)

            PasswordRecoveryCode.objects.filter(user=profile.user, used_at__isnull=True).update(used_at=timezone.now())
            code = f'{secrets.randbelow(1000000):06d}'
            recovery = PasswordRecoveryCode.objects.create(
                user=profile.user,
                code_hash=make_password(code),
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            send_mail(
                'Código de recuperación — SGR La Serena',
                f'Hola {profile.full_name}, tu código de recuperación es: {code}. Expira en 10 minutos.',
                None,
                [profile.email],
                fail_silently=False,
            )
            request.session['recovery_user_id'] = profile.user_id
            return render(request, 'password_recovery.html', {'step': 'verify', 'notice': 'Te enviamos un código al correo registrado.'})

        if action == 'reset_password' and recovery_user_id:
            code = request.POST.get('code', '').strip()
            new_password = request.POST.get('new_password', '')
            recovery = PasswordRecoveryCode.objects.filter(user_id=recovery_user_id, used_at__isnull=True).first()
            if not recovery or not recovery.is_valid:
                request.session.pop('recovery_user_id', None)
                return render(request, 'password_recovery.html', {'error': 'El código expiró o superó el límite de intentos.'}, status=400)
            if not check_password(code, recovery.code_hash):
                recovery.attempts += 1
                recovery.save(update_fields=['attempts', 'updated_at'])
                return render(request, 'password_recovery.html', {'step': 'verify', 'error': 'El código ingresado no es válido.'}, status=400)
            if len(new_password) < 8:
                return render(request, 'password_recovery.html', {'step': 'verify', 'error': 'La nueva contraseña debe tener al menos 8 caracteres.'}, status=400)
            user = recovery.user
            user.set_password(new_password)
            user.save(update_fields=['password'])
            recovery.used_at = timezone.now()
            recovery.save(update_fields=['used_at', 'updated_at'])
            request.session.pop('recovery_user_id', None)
            return render(request, 'password_recovery.html', {'success': 'Contraseña actualizada. Ya puedes iniciar sesión.'})

    return render(request, 'password_recovery.html', {'step': 'verify' if recovery_user_id else 'request'})
