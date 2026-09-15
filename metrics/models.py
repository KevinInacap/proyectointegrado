from django.db import models
from django.conf import settings
from core.models import BaseModel
from organization.models import Position

class MeasurementPeriod(BaseModel):
    """
    Período de medición de la gestión municipal (RF-005, RN-007).
    Tabla: periodo
    """
    STATUS_CHOICES = [
        ('Planificado', 'Planificado'),
        ('Abierto', 'Abierto'),
        ('Cerrado', 'Cerrado'),
    ]

    name = models.CharField(max_length=50, unique=True, verbose_name="Nombre del período")
    start_date = models.DateField(verbose_name="Fecha de inicio")
    end_date = models.DateField(verbose_name="Fecha de término")
    computable_days = models.PositiveIntegerField(default=90, verbose_name="Días computables")
    minimum_threshold = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=80.00, 
        verbose_name="Umbral mínimo colectivo (%)"
    )
    compliance_cap = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=150.00, 
        verbose_name="Tope de cumplimiento (%)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Abierto', verbose_name="Estado")

    class Meta:
        verbose_name = "Período de Medición"
        verbose_name_plural = "Períodos de Medición"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} ({self.status})"


class MeasurementItem(BaseModel):
    """
    Ítems medibles asignados a las funciones de cada cargo (RF-003).
    Tabla: item_medicion
    """
    TYPE_CHOICES = [
        ('Cuantitativo', 'Cuantitativo (conteo de atenciones)'),
        ('Porcentual', 'Porcentual (tasa de resolución)'),
    ]
    STATUS_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]

    name = models.CharField(max_length=120, unique=True, verbose_name="Nombre del ítem de medición")
    description = models.TextField(blank=True, default='', verbose_name="Descripción operativa")
    item_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='Cuantitativo', verbose_name="Tipo de ítem")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Activo', verbose_name="Estado")

    class Meta:
        verbose_name = "Ítem de Medición"
        verbose_name_plural = "Ítems de Medición"
        ordering = ['name']

    def __str__(self):
        return self.name


class Goal(BaseModel):
    """
    Metas y ponderadores por cargo, ítem y período (RF-006, RF-007, RN-001).
    Tabla: meta
    """
    period = models.ForeignKey(
        MeasurementPeriod,
        on_delete=models.CASCADE,
        related_name='goals',
        verbose_name="Período de medición"
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name='goals',
        verbose_name="Cargo evaluado"
    )
    item = models.ForeignKey(
        MeasurementItem,
        on_delete=models.CASCADE,
        related_name='goals',
        verbose_name="Ítem medible"
    )
    target_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor objetivo / Meta")
    unit_of_measure = models.CharField(max_length=30, default='Atenciones', verbose_name="Unidad de medida")
    weight = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Ponderación (%)")

    class Meta:
        verbose_name = "Meta de Gestión"
        verbose_name_plural = "Metas de Gestión"
        unique_together = ('period', 'position', 'item')
        ordering = ['period', 'position', 'item']

    def __str__(self):
        return f"{self.position} | {self.item}: {self.target_value} ({self.weight}%)"


class DailyIndicator(BaseModel):
    """
    Indicador diario consolidado y semáforo de cumplimiento (RF-026, RF-027, RN-008).
    Tabla: indicador_diario
    """
    SEMAPHORE_CHOICES = [
        ('Verde', 'Verde (Avance >= Meta esperada al día)'),
        ('Ámbar', 'Ámbar (Avance entre 60% y 99% de lo esperado)'),
        ('Rojo', 'Rojo (Avance < 60% de lo esperado)'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_indicators',
        verbose_name="Funcionario"
    )
    period = models.ForeignKey(
        MeasurementPeriod,
        on_delete=models.CASCADE,
        related_name='daily_indicators',
        verbose_name="Período"
    )
    calculation_date = models.DateField(verbose_name="Fecha de cálculo")
    accumulated_progress = models.PositiveIntegerField(default=0, verbose_name="Avance acumulado válido")
    compliance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="% Cumplimiento")
    weighted_compliance = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Cumplimiento ponderado (%)")
    expected_target_to_date = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Meta esperada al día (%)")
    traffic_light = models.CharField(max_length=20, choices=SEMAPHORE_CHOICES, default='Ámbar', verbose_name="Semáforo")

    class Meta:
        verbose_name = "Indicador Diario"
        verbose_name_plural = "Indicadores Diarios"
        unique_together = ('user', 'period', 'calculation_date')
        ordering = ['-calculation_date', 'user']

    def __str__(self):
        return f"{self.user} - {self.calculation_date}: {self.traffic_light} ({self.weighted_compliance}%)"


class PerformanceAdjustment(BaseModel):
    """
    Ajustes de desempeño por felicitaciones o penalizaciones (RF-025, RN-011).
    Tabla: ajuste_desempeno
    """
    ADJUSTMENT_CHOICES = [
        ('Felicitacion', 'Felicitación ciudadana (+%)'),
        ('Reclamo', 'Reclamo fundamentado (-%)'),
        ('Penalizacion', 'Penalización operativa (-%)'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='performance_adjustments',
        verbose_name="Funcionario"
    )
    period = models.ForeignKey(
        MeasurementPeriod,
        on_delete=models.CASCADE,
        related_name='performance_adjustments',
        verbose_name="Período"
    )
    adjustment_type = models.CharField(max_length=30, choices=ADJUSTMENT_CHOICES, verbose_name="Tipo de ajuste")
    percentage_value = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Valor porcentual (%)")
    reason = models.TextField(verbose_name="Motivo del ajuste")
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_adjustments',
        verbose_name="Registrado por"
    )

    class Meta:
        verbose_name = "Ajuste de Desempeño"
        verbose_name_plural = "Ajustes de Desempeño"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.adjustment_type} ({self.percentage_value}%)"
