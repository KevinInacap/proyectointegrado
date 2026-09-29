from django.db import models
from django.conf import settings
from core.models import BaseModel

class Delegation(BaseModel):
    """
    Unidades territoriales de la Municipalidad de La Serena (RF-001).
    Tabla: delegacion
    """
    STATUS_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la delegación")
    scope = models.CharField(max_length=100, verbose_name="Ámbito territorial")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Activo', verbose_name="Estado")

    class Meta:
        verbose_name = "Delegación"
        verbose_name_plural = "Delegaciones"
        ordering = ['name']

    def __str__(self):
        return self.name


class Position(BaseModel):
    """
    Cargos y funciones de funcionarios medidos en la Matriz SGR (RF-003).
    Tabla: cargo
    """
    STATUS_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre del cargo")
    description = models.TextField(blank=True, default='', verbose_name="Descripción del cargo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Activo', verbose_name="Estado")

    class Meta:
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"
        ordering = ['name']

    def __str__(self):
        return self.name


class UserProfile(BaseModel):
    """
    Perfil institucional del funcionario municipal (RF-002).
    Tabla: usuario
    Los roles y permisos se gestionan a través de los Grupos estándar de Django (user.groups).
    """
    STATUS_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
        ('Bloqueado', 'Bloqueado'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name="Cuenta de usuario"
    )
    rut = models.CharField(max_length=12, unique=True, verbose_name="RUT")
    full_name = models.CharField(max_length=150, verbose_name="Nombre completo")
    email = models.EmailField(max_length=100, unique=True, verbose_name="Correo electrónico institucional")
    delegation = models.ForeignKey(
        Delegation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name="Delegación asignada"
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name="Cargo asignado"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Activo', verbose_name="Estado")

    class Meta:
        verbose_name = "Perfil de Funcionario"
        verbose_name_plural = "Perfiles de Funcionarios"
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.rut})"

    @property
    def group_names(self):
        """Retorna los nombres de los grupos de Django a los que pertenece el usuario."""
        return list(self.user.groups.values_list('name', flat=True))

    @property
    def primary_role(self):
        """Rol legible derivado de los grupos de Django."""
        if self.user.is_superuser or 'Administradores' in self.group_names:
            return 'Administrador General'
        if 'Verificadores' in self.group_names:
            return 'Verificador de Evidencias'
        if 'Gestores Territoriales' in self.group_names:
            return 'Gestor Territorial'
        return self.group_names[0] if self.group_names else 'Sin Grupo'
