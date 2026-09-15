from django.db import models
from django.conf import settings
from core.models import BaseModel
from organization.models import Delegation
from metrics.models import MeasurementPeriod, MeasurementItem

class ServiceCatalog(BaseModel):
    """
    Catálogo institucional de actividades, servicios y prestaciones municipales (RF-004).
    Tabla: catalogo_servicio
    """
    STATUS_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]

    area = models.CharField(max_length=50, verbose_name="Área municipal")
    service = models.CharField(max_length=100, verbose_name="Servicio principal")
    attention_type = models.CharField(max_length=100, verbose_name="Tipo de atención")
    subattention_type = models.CharField(max_length=100, blank=True, default='', verbose_name="Subtipo de atención")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Activo', verbose_name="Estado")

    class Meta:
        verbose_name = "Catálogo de Servicio"
        verbose_name_plural = "Catálogo de Servicios"
        ordering = ['area', 'service']

    def __str__(self):
        return f"[{self.area}] {self.service} - {self.attention_type}"


class Activity(BaseModel):
    """
    Registro diario de actividades y solicitudes atendidas en delegaciones (RF-009, RF-010).
    Tabla: actividad
    """
    VALIDATION_STATUS_CHOICES = [
        ('Pending', 'Pendiente'),
        ('Approved', 'Aprobado'),
        ('Rejected', 'Rechazado'),
        ('Requires correction', 'Requiere corrección'),
    ]

    activity_code = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Código de actividad"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name="Funcionario responsable"
    )
    delegation = models.ForeignKey(
        Delegation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name="Delegación"
    )
    period = models.ForeignKey(
        MeasurementPeriod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name="Período de medición"
    )
    item = models.ForeignKey(
        MeasurementItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name="Ítem de medición asociado"
    )
    catalog = models.ForeignKey(
        ServiceCatalog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name="Clasificación en catálogo"
    )
    activity_date = models.DateField(verbose_name="Fecha de actividad")
    problem_description = models.TextField(verbose_name="Descripción del problema")
    executed_action = models.TextField(verbose_name="Acción ejecutada")
    contact_name = models.CharField(
        max_length=150, 
        blank=True, 
        default='', 
        verbose_name="Nombre de contacto"
    )
    contact_phone = models.CharField(
        max_length=20, 
        blank=True, 
        default='', 
        verbose_name="Teléfono de contacto"
    )
    is_collective_agenda = models.BooleanField(
        default=False, 
        verbose_name="¿Ingresa a agenda colectiva?"
    )
    validation_status = models.CharField(
        max_length=30,
        choices=VALIDATION_STATUS_CHOICES,
        default='Pending',
        verbose_name="Estado de validación"
    )

    class Meta:
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"
        ordering = ['-activity_date', '-created_at']

    def __str__(self):
        return f"{self.activity_code} - {self.activity_date}"


class Evidence(BaseModel):
    """
    Evidencia documental o fotográfica asociada a la actividad (RF-011, RF-012).
    Tabla: evidencia
    """
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='evidences',
        verbose_name="Actividad asociada"
    )
    evidence_code = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Código de evidencia"
    )
    file_path = models.CharField(max_length=255, verbose_name="Ruta del archivo")
    file_name = models.CharField(max_length=150, verbose_name="Nombre del archivo")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_evidences',
        verbose_name="Subido por"
    )

    class Meta:
        verbose_name = "Evidencia"
        verbose_name_plural = "Evidencias"
        ordering = ['-created_at']

    def __str__(self):
        return self.evidence_code


class Validation(BaseModel):
    """
    Validación formal de evidencias por parte del Verificador (RF-013, RF-014).
    Tabla: validacion
    """
    DECISION_CHOICES = [
        ('Approved', 'Aprobado'),
        ('Rejected', 'Rechazado'),
        ('Requires correction', 'Requiere corrección'),
    ]

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='validations',
        verbose_name="Actividad"
    )
    verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_validations',
        verbose_name="Verificador responsable"
    )
    decision = models.CharField(
        max_length=30, 
        choices=DECISION_CHOICES, 
        verbose_name="Decisión"
    )
    observations = models.TextField(
        blank=True, 
        default='', 
        verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Validación"
        verbose_name_plural = "Validaciones"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.activity.activity_code} - {self.decision}"