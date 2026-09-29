from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from organization.models import UserProfile


def login_view(request):
    # Si el usuario ya está autenticado, dirigirlo a su dashboard
    if request.user.is_authenticated:
        return redirect('activities:dashboard')

    # Soporte para accesos directos demo
    rol_param = request.GET.get('rol')
    if rol_param:
        demo_user = None
        if rol_param == 'admin':
            demo_user = User.objects.filter(username='admin').first()
        elif rol_param == 'verificador':
            demo_user = User.objects.filter(username='verificador').first()
        elif rol_param in ['gestor', 'funcionario']:
            demo_user = User.objects.filter(username='funcionario_pampa').first() or User.objects.filter(username='funcionario_companias').first()

        if demo_user:
            auth_login(request, demo_user)
            profile = getattr(demo_user, 'profile', None)
            delegation_name = profile.delegation.name if (profile and profile.delegation) else 'Consolidado Comunal'
            full_name = profile.full_name if (profile and profile.full_name) else (demo_user.get_full_name() or demo_user.username)
            request.session['user_name'] = full_name
            request.session['user_rut'] = profile.rut if profile else ''
            request.session['user_delegation'] = delegation_name

            group_names = list(demo_user.groups.values_list('name', flat=True))
            if demo_user.is_superuser or 'Administradores' in group_names:
                request.session['user_role'] = 'Administrador General'
                return redirect('activities:dashboard_admin')
            elif 'Verificadores' in group_names:
                request.session['user_role'] = 'Verificador de Evidencias'
                return redirect('activities:dashboard_verificador')
            else:
                request.session['user_role'] = 'Gestor Territorial OO.CC.'
                return redirect('activities:dashboard_gestor')

    # Procesar login real por credenciales (POST)
    if request.method == 'POST':
        username_or_rut = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        remember_me = request.POST.get('remember_me')

        if not username_or_rut or not password:
            messages.error(request, "Por favor, ingresa tu usuario/RUT y contraseña.")
            return render(request, 'login.html')

        # Resolver si el usuario ingresó un RUT en vez de un username
        resolved_username = username_or_rut
        profile = UserProfile.objects.filter(rut__iexact=username_or_rut).select_related('user').first()
        if not profile:
            # Buscar normalizando puntos y guion
            clean_input = username_or_rut.replace('.', '').replace('-', '').upper()
            for p in UserProfile.objects.select_related('user').all():
                if p.rut.replace('.', '').replace('-', '').upper() == clean_input:
                    profile = p
                    break

        if profile:
            resolved_username = profile.user.username

        # Autenticación oficial de Django
        user = authenticate(request, username=resolved_username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "Esta cuenta institucional se encuentra desactivada.")
                return render(request, 'login.html')

            auth_login(request, user)

            if not remember_me:
                request.session.set_expiry(0)

            # Cargar datos de perfil y grupo
            user_profile = getattr(user, 'profile', None)
            delegation_name = user_profile.delegation.name if (user_profile and user_profile.delegation) else 'Consolidado Comunal'
            full_name = user_profile.full_name if (user_profile and user_profile.full_name) else (user.get_full_name() or user.username)
            rut_val = user_profile.rut if user_profile else ''

            group_names = list(user.groups.values_list('name', flat=True))

            # Guardar en sesión para compatibilidad con vistas y plantillas
            request.session['user_name'] = full_name
            request.session['user_rut'] = rut_val
            request.session['user_delegation'] = delegation_name

            # Redirección dinámica basada en los Grupos de Django (RBAC)
            if user.is_superuser or 'Administradores' in group_names:
                request.session['user_role'] = 'Administrador General'
                messages.success(request, f"Bienvenido(a), {full_name} (Administrador)")
                return redirect('activities:dashboard_admin')
            elif 'Verificadores' in group_names:
                request.session['user_role'] = 'Verificador de Evidencias'
                messages.success(request, f"Bienvenido(a), {full_name} (Verificador)")
                return redirect('activities:dashboard_verificador')
            else:
                request.session['user_role'] = 'Gestor Territorial OO.CC.'
                messages.success(request, f"Bienvenido(a), {full_name} (Gestor Territorial)")
                return redirect('activities:dashboard_gestor')
        else:
            messages.error(request, "Credenciales incorrectas. Verifica tu usuario/RUT y contraseña.")

    return render(request, 'login.html')


def logout_view(request):
    auth_logout(request)
    request.session.flush()
    messages.info(request, "Has cerrado tu sesión institucional correctamente.")
    return redirect('core:login')