from django.db import models
from core.models import BaseModel

class Activity(BaseModel):
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

    def __str__(self):
        return f"{self.activity_code} - {self.activity_date}"


class Evidence(BaseModel):
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

    class Meta:
        verbose_name = "Evidencia"
        verbose_name_plural = "Evidencias"

    def __str__(self):
        return self.evidence_code


class Validation(BaseModel):
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

    def __str__(self):
        return f"{self.activity.activity_code} - {self.decision}"