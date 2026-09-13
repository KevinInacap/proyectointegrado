from django.shortcuts import render, redirect
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        request.session['user_rut'] = username or '12345678-9'
        request.session['user_role'] = 'Funcionario Territorial'
        request.session['user_name'] = 'Juan Pérez'
        
        messages.success(request, f"¡Bienvenido(a), {request.session['user_name']}!")
        return redirect('activities:dashboard')
    
    rol_param = request.GET.get('rol')
    if rol_param:
        roles_map = {
            'funcionario': 'Funcionario Territorial',
            'verificador': 'Verificador de Evidencias',
            'delegado': 'Delegado Municipal',
            'admin': 'Administrador del Sistema'
        }
        request.session['user_role'] = roles_map.get(rol_param, 'Funcionario Territorial')
        request.session['user_name'] = 'Juan Pérez' if rol_param == 'funcionario' else 'Jorge Cortés'
        return redirect('activities:dashboard')

    return render(request, 'login.html')

def logout_view(request):
    request.session.flush()
    messages.info(request, "Has cerrado tu sesión correctamente.")
    return redirect('core:login')