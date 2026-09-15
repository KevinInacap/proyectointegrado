from django.db import models
from django.conf import settings
from core.models import BaseModel
from organization.models import Delegation
from activities.models import Activity

class CollectiveAgenda(BaseModel):
    """
    Agenda colectiva o tubo de trabajo para compromisos futuros (RF-016 a RF-021).
    Tabla: compromiso_agenda
    """
    STATUS_CHOICES = [
        ('Ingresado', 'Ingresado'),
        ('Pendiente', 'Pendiente'),
        ('En proceso', 'En proceso'),
        ('Realizado', 'Realizado'),
    ]
    ORIGIN_CHOICES = [
        ('Interno', 'Solicitud interna municipal'),
        ('Externo', 'Requerimiento vecinal / ciudadano'),
    ]

    source_activity = models.ForeignKey(
        Activity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commitments',
        verbose_name="Actividad de origen"
    )
    delegation = models.ForeignKey(
        Delegation,
        on_delete=models.CASCADE,
        related_name='commitments',
        verbose_name="Delegación"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_commitments',
        verbose_name="Funcionario responsable"
    )
    request_source = models.CharField(
        max_length=20, 
        choices=ORIGIN_CHOICES, 
        default='Externo', 
        verbose_name="Origen de la solicitud"
    )
    requester = models.CharField(max_length=150, verbose_name="Solicitante / Organización")
    territory = models.CharField(max_length=100, verbose_name="Territorio / Sector")
    support_area = models.CharField(max_length=100, blank=True, default='', verbose_name="Área municipal de apoyo")
    description = models.TextField(verbose_name="Descripción del compromiso")
    committed_date = models.DateField(verbose_name="Fecha comprometida")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Ingresado', verbose_name="Estado")
    observations = models.TextField(blank=True, default='', verbose_name="Observaciones de seguimiento")
    closing_date = models.DateField(null=True, blank=True, verbose_name="Fecha de cierre")

    class Meta:
        verbose_name = "Compromiso de Agenda Colectiva"
        verbose_name_plural = "Agenda Colectiva (Tubo de Trabajo)"
        ordering = ['committed_date']

    def __str__(self):
        return f"{self.requester} ({self.committed_date}) - {self.status}"


class CommitmentHistory(BaseModel):
    """
    Trazabilidad de cambios de estado en los compromisos de agenda (RF-018, RF-036).
    Tabla: historial_compromiso
    """
    commitment = models.ForeignKey(
        CollectiveAgenda,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name="Compromiso"
    )
    previous_status = models.CharField(max_length=30, verbose_name="Estado anterior")
    new_status = models.CharField(max_length=30, verbose_name="Nuevo estado")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commitment_updates',
        verbose_name="Autor del cambio"
    )
    observations = models.TextField(blank=True, default='', verbose_name="Observaciones del cambio")

    class Meta:
        verbose_name = "Historial de Compromiso"
        verbose_name_plural = "Historial de Compromisos"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.commitment.id}: {self.previous_status} -> {self.new_status}"
