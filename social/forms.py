from django import forms
from django.utils import timezone
from .models import SocialCase, SocialManagement


class SocialCaseForm(forms.ModelForm):
    """
    Formulario con validación controlada para Casos Sociales (Admin Pro - Rúbrica).
    """
    class Meta:
        model = SocialCase
        fields = ['user_name', 'user_rut', 'contact_phone', 'delegation', 'entry_date']

    def clean_entry_date(self):
        entry_date = self.cleaned_data.get('entry_date')
        if entry_date and entry_date > timezone.now().date():
            raise forms.ValidationError("La fecha de ingreso del caso no puede ser una fecha futura.")
        return entry_date
