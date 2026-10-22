from django.db import models
from django.conf import settings
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
    activity = models.OneToOneField(
        'activities.Activity', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='social_case', verbose_name='Atención de ingreso vinculada',
    )

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

    @property
    def current_stage(self):
        last = self.managements.filter(deleted_at__isnull=True).order_by('-stage').first()
        return last.stage if last else 1

    @property
    def latest_management(self):
        return self.managements.filter(deleted_at__isnull=True).order_by('-stage').first()

    @property
    def can_advance(self):
        return self.current_stage < 3

    @property
    def next_stage(self):
        return min(self.current_stage + 1, 3)

    @property
    def status_label(self):
        stage = self.current_stage
        if stage == 1:
            return "Etapa 1: Ingreso y Evaluación"
        elif stage == 2:
            return "Etapa 2: Visita en Terreno"
        elif stage == 3:
            return "Etapa 3: Resolución y Entrega"
        return "Ingresado"

    @property
    def is_resolved(self):
        return self.current_stage == 3

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


class SocialReviewRequest(BaseModel):
    """Solicitud trazable de revisión o corrección administrativa de un caso social."""
    TYPE_CHOICES = [
        ('revision', 'Revisión'),
        ('edicion', 'Corrección de datos'),
    ]
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]

    request_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendiente')
    case = models.ForeignKey(
        SocialCase, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='review_requests', verbose_name='Caso relacionado',
    )
    management = models.ForeignKey(
        SocialManagement, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='review_requests', verbose_name='Gestión relacionada',
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='social_review_requests', verbose_name='Funcionario solicitante',
    )
    requester_name = models.CharField(max_length=150)
    requester_position = models.CharField(max_length=100, blank=True, default='')
    requester_delegation = models.CharField(max_length=100, blank=True, default='')
    target_label = models.CharField(max_length=180, blank=True, default='')
    reason = models.TextField(max_length=1200)
    requested_changes = models.JSONField(default=dict, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_social_requests', verbose_name='Administrador revisor',
    )
    resolution_note = models.TextField(max_length=1000, blank=True, default='')
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Solicitud de revisión social'
        verbose_name_plural = 'Solicitudes de revisión social'
        ordering = ['status', '-created_at']

    def __str__(self):
        return f"{self.get_request_type_display()} · {self.target_label or 'Caso social'} · {self.get_status_display()}"


class SocialNotification(BaseModel):
    """Aviso interno persistente para administración y respuesta al solicitante."""
    EVENT_CHOICES = [
        ('request', 'Nueva solicitud'),
        ('result', 'Resultado de solicitud'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='social_notifications', verbose_name='Destinatario',
    )
    review_request = models.ForeignKey(
        SocialReviewRequest, on_delete=models.CASCADE,
        related_name='notifications', verbose_name='Solicitud relacionada',
    )
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES, default='request')
    message = models.CharField(max_length=500)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Notificación social'
        verbose_name_plural = 'Notificaciones sociales'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['recipient', 'review_request', 'event_type'],
                name='uniq_social_notification_recipient_request_event',
            ),
        ]

    def __str__(self):
        return self.message

