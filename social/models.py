from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models import BaseModel
from organization.models import Delegation
from activities.models import ServiceCatalog

class SocialCase(BaseModel):
    """
    Ficha única de atención social a vecinos / ciudadanos (RF-015, RN-012).
    Tabla: caso_social
    """
    user_rut = models.CharField(max_length=12, verbose_name="RUT de la persona usuaria")
    user_name = models.CharField(max_length=150, verbose_name="Nombre de la persona usuaria")
    contact_phone = models.CharField(max_length=20, blank=True, default='', verbose_name="Teléfono de contacto")
    delegation = models.ForeignKey(
        Delegation,
        on_delete=models.CASCADE,
        related_name='social_cases',
        verbose_name="Delegación"
    )
    entry_date = models.DateField(verbose_name="Fecha de ingreso")

    class Meta:
        verbose_name = "Caso Social"
        verbose_name_plural = "Casos Sociales"
        ordering = ['-entry_date']

    def clean(self):
        super().clean()
        if self.entry_date and self.entry_date > timezone.now().date():
            raise ValidationError({
                'entry_date': 'La fecha de ingreso del caso no puede ser una fecha futura.'
            })

    def __str__(self):
        return f"{self.user_name} ({self.user_rut})"


class SocialManagement(BaseModel):
    """
    Secuencia de gestiones por caso social (hasta 3 gestiones según RN-012).
    Tabla: gestion_social
    """
    case = models.ForeignKey(
        SocialCase,
        on_delete=models.CASCADE,
        related_name='managements',
        verbose_name="Caso social asociado"
    )
    stage = models.PositiveSmallIntegerField(verbose_name="Etapa / N° de gestión (1 a 3)")
    catalog = models.ForeignKey(
        ServiceCatalog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='social_managements',
        verbose_name="Servicio / Prestación entregada"
    )
    management_type = models.CharField(max_length=100, verbose_name="Tipo de gestión realizada")
    management_date = models.DateField(verbose_name="Fecha de la gestión")
    result = models.TextField(verbose_name="Resultado de la atención")

    class Meta:
        verbose_name = "Gestión Social"
        verbose_name_plural = "Gestiones Sociales"
        ordering = ['case', 'stage']
        unique_together = ('case', 'stage')

    def clean(self):
        super().clean()
        if self.stage and (self.stage < 1 or self.stage > 3):
            raise ValidationError({
                'stage': 'Por normativa comunal (RN-012), cada caso social permite un máximo de 3 etapas consecutivas (valores 1 a 3).'
            })

    def __str__(self):
        return f"{self.case.user_name} - Etapa {self.stage}"
