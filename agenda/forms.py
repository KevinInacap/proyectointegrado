from django import forms
from django.utils import timezone
from .models import CollectiveAgenda, CommitmentHistory


class CollectiveAgendaForm(forms.ModelForm):
    """
    Formulario con validación controlada para Agenda Colectiva (Admin Pro).
    """
    class Meta:
        model = CollectiveAgenda
        fields = [
            'requester',
            'territory',
            'support_area',
            'description',
            'committed_date',
            'status',
            'observations',
        ]
        widgets = {
            'committed_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'observations': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

    def clean_committed_date(self):
        committed = self.cleaned_data.get('committed_date')
        if committed and committed < timezone.now().date():
            raise forms.ValidationError("La fecha comprometida no puede ser anterior a la fecha actual.")
        return committed
