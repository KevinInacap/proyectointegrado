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
        elif rol_param == 'coordinador':
            request.session['user_role'] = 'Coordinador del Sistema'
            request.session['user_name'] = 'Marcelo Salazar Peña'
            request.session['user_rut'] = '13.456.789-0'
            request.session['user_delegation'] = 'Supervisión Comunal SGR'
            return redirect('activities:dashboard_admin')
        elif rol_param == 'delegado':
            request.session['user_role'] = 'Delegado Municipal'
            request.session['user_name'] = 'Gonzalo Pizarro Rojas'
            request.session['user_rut'] = '14.234.567-8'
            request.session['user_delegation'] = 'Delegación Las Compañías'
            return redirect('activities:dashboard_admin')
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
            return redirect('activities:dashboard_admin')
        elif rol_param in ['gestor', 'funcionario']:
            request.session['user_role'] = 'Gestor Territorial'
            request.session['user_name'] = 'Rodrigo Tapia Gallardo'
            request.session['user_rut'] = '17.892.456-3'
            request.session['user_delegation'] = 'Delegación Las Compañías'
            return redirect('activities:dashboard_gestor')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        u_lower = username.lower()
        
        if username == '11.111.111-1' or 'admin' in u_lower:
            request.session['user_role'] = 'Administrador General'
            request.session['user_name'] = 'Alcaldía La Serena'
            request.session['user_rut'] = username or '11.111.111-1'
            request.session['user_delegation'] = 'Consolidado Comunal'
            return redirect('activities:dashboard_admin')
        elif username == '13.456.789-0' or 'coord' in u_lower:
            request.session['user_role'] = 'Coordinador del Sistema'
            request.session['user_name'] = 'Marcelo Salazar Peña'
            request.session['user_rut'] = username or '13.456.789-0'
            request.session['user_delegation'] = 'Supervisión Comunal SGR'
            return redirect('activities:dashboard_admin')
        elif username == '14.234.567-8' or 'deleg' in u_lower:
            request.session['user_role'] = 'Delegado Municipal'
            request.session['user_name'] = 'Gonzalo Pizarro Rojas'
            request.session['user_rut'] = username or '14.234.567-8'
            request.session['user_delegation'] = 'Delegación Las Compañías'
            return redirect('activities:dashboard_admin')
        elif username == '15.678.901-2' or 'verif' in u_lower:
            request.session['user_role'] = 'Verificador Técnico'
            request.session['user_name'] = 'Esteban Morales Vega'
            request.session['user_rut'] = username or '15.678.901-2'
            request.session['user_delegation'] = 'Delegación Las Compañías'
            return redirect('activities:dashboard_verificador')
        elif username == '16.789.012-3' or 'consul' in u_lower:
            request.session['user_role'] = 'Usuario de Consulta'
            request.session['user_name'] = 'Valeria Cáceres Soto'
            request.session['user_rut'] = username or '16.789.012-3'
            request.session['user_delegation'] = 'Auditoría Transversal'
            return redirect('activities:dashboard_admin')
        elif username == '18.345.678-K' or 'centro' in u_lower:
            request.session['user_role'] = 'Gestor Territorial'
            request.session['user_name'] = 'Camila Araya Miranda'
            request.session['user_rut'] = '18.345.678-K'
            request.session['user_delegation'] = 'Delegación Centro Histórico'
            return redirect('activities:dashboard_gestor')
        else:
            request.session['user_role'] = 'Gestor Territorial'
            request.session['user_name'] = 'Rodrigo Tapia Gallardo'
            request.session['user_rut'] = username or '17.892.456-3'
            request.session['user_delegation'] = 'Delegación Las Compañías'
            return redirect('activities:dashboard_gestor')

    return render(request, 'login.html')

def logout_view(request):
    request.session.flush()
    messages.info(request, "Has cerrado tu sesión correctamente.")
    return redirect('core:login')