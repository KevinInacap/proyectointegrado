from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, f"¡Bienvenido(a), {user.get_full_name() or user.username}!")
            return redirect('activities:dashboard')
        else:
            messages.error(request, "Credenciales inválidas. Por favor verifique su usuario/RUT y contraseña.")

    return render(request, 'login.html')

def logout_view(request):
    auth_logout(request)
    messages.info(request, "Has cerrado tu sesión correctamente.")
    return redirect('core:login')