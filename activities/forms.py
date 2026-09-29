from django import forms
from django.utils import timezone
from .models import Activity, Evidence, Validation


class ActivityForm(forms.ModelForm):
    """
    Formulario con validación controlada para Actividades (Admin Pro - Rúbrica).
    """
    class Meta:
        model = Activity
        fields = [
            'activity_code',
            'activity_date',
            'catalog',
            'problem_description',
            'executed_action',
            'contact_name',
            'contact_phone',
            'is_collective_agenda',
        ]
        widgets = {
            'activity_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'problem_description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'executed_action': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'activity_code': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_activity_date(self):
        date = self.cleaned_data.get('activity_date')
        if date and date > timezone.now().date():
            raise forms.ValidationError("La fecha de la actividad no puede ser posterior a la fecha actual.")
        return date

    def clean(self):
        cleaned_data = super().clean()
        is_agenda = cleaned_data.get('is_collective_agenda')
        contact = cleaned_data.get('contact_name')
        if is_agenda and not contact:
            raise forms.ValidationError({
                'contact_name': "Debe ingresar el nombre del contacto o dirigente cuando la actividad derive a la agenda colectiva."
            })
        return cleaned_data
