from django.db import models
from django.conf import settings

class BaseModel(models.Model):
    """
    Clase base abstracta con trazabilidad temporal y soporte para borrado lógico.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de eliminación lógica")

    class Meta:
        abstract = True


class AuditLog(BaseModel):
    """
    Entidad de auditoría transversal para registro de operaciones críticas (RNF-008).
    Tabla: auditoria
    """
    ACTION_CHOICES = [
        ('CREATE', 'Creación'),
        ('UPDATE', 'Modificación'),
        ('DELETE', 'Eliminación'),
        ('VALIDATE', 'Validación'),
        ('LOGIN', 'Inicio de sesión'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="Usuario responsable"
    )
    affected_table = models.CharField(max_length=50, verbose_name="Tabla afectada")
    affected_record_id = models.CharField(max_length=50, verbose_name="ID de registro afectado")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Acción")
    previous_value = models.JSONField(null=True, blank=True, verbose_name="Valor anterior")
    new_value = models.JSONField(null=True, blank=True, verbose_name="Valor nuevo")
    source_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP de origen")

    class Meta:
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.action}] {self.affected_table} #{self.affected_record_id} por {self.user}"