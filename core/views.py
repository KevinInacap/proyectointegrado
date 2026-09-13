from django.shortcuts import render, redirect
from django.contrib import messages

def login_view(request):
    rol_param = request.GET.get('rol')
    if rol_param:
        if rol_param == 'admin':
            request.session['user_role'] = 'Administrador General'
            request.session['user_name'] = 'Alcaldía La Serena'
            request.session['user_rut'] = '11.111.111-1'
            request.session['user_delegation'] = 'Consolidado Comunal'
            return redirect('activities:dashboard_admin')
        elif rol_param == 'verificador':
            request.session['user_role'] = 'Supervisor Territorial'
            request.session['user_name'] = 'Jorge Cortés Pavez'
            request.session['user_rut'] = '22.222.222-2'
            request.session['user_delegation'] = 'Delegación Las Compañías'
            return redirect('activities:dashboard_verificador')
        elif rol_param in ['gestor', 'funcionario']:
            request.session['user_role'] = 'Territorial OO.CC.'
            request.session['user_name'] = 'Kevin Encina Molina'
            request.session['user_rut'] = '12.345.678-K'
            request.session['user_delegation'] = 'Delegación La Pampa'
            return redirect('activities:dashboard_gestor')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        
        if username == '11.111.111-1' or 'admin' in username.lower():
            request.session['user_role'] = 'Administrador General'
            request.session['user_name'] = 'Alcaldía La Serena'
            request.session['user_rut'] = username or '11.111.111-1'
            request.session['user_delegation'] = 'Consolidado Comunal'
            return redirect('activities:dashboard_admin')
        elif username == '22.222.222-2' or 'verif' in username.lower():
            request.session['user_role'] = 'Supervisor Territorial'
            request.session['user_name'] = 'Jorge Cortés Pavez'
            request.session['user_rut'] = username or '22.222.222-2'
            request.session['user_delegation'] = 'Delegación Las Compañías'
            return redirect('activities:dashboard_verificador')
        else:
            request.session['user_role'] = 'Territorial OO.CC.'
            request.session['user_name'] = 'Kevin Encina Molina'
            request.session['user_rut'] = username or '12.345.678-K'
            request.session['user_delegation'] = 'Delegación La Pampa'
            return redirect('activities:dashboard_gestor')

    return render(request, 'login.html')

def logout_view(request):
    request.session.flush()
    messages.info(request, "Has cerrado tu sesión correctamente.")
    return redirect('core:login')