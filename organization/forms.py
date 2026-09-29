from django import forms
from .models import Delegation, Position, UserProfile


class DelegationForm(forms.ModelForm):
    """
    Formulario de validación para Delegaciones territoriales.
    """
    class Meta:
        model = Delegation
        fields = ['name', 'scope', 'status']

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 4:
            raise forms.ValidationError("El nombre de la delegación debe contener al menos 4 caracteres.")
        return name


class UserProfileForm(forms.ModelForm):
    """
    Formulario de validación de Perfil de Funcionario y RUT chileno.
    """
    class Meta:
        model = UserProfile
        fields = ['rut', 'full_name', 'email', 'delegation', 'position', 'status']

    def clean_rut(self):
        rut = self.cleaned_data.get('rut', '').strip().upper()
        clean = rut.replace('.', '').replace('-', '')
        if len(clean) < 8 or len(clean) > 9:
            raise forms.ValidationError("El formato de RUT ingresado no es válido (ejemplo: 12.345.678-K).")
        return rut
