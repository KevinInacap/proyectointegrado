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


class Role(BaseModel):
    """
    Roles del sistema municipal (RF-002, RNF-005).
    Tabla: rol
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="Nombre del rol")
    description = models.CharField(max_length=255, blank=True, default='', verbose_name="Descripción del rol")

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ['name']

    def __str__(self):
        return self.name


class UserProfile(BaseModel):
    """
    Perfil institucional del funcionario municipal (RF-002).
    Tabla: usuario
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
    roles = models.ManyToManyField(
        Role,
        blank=True,
        related_name='users',
        verbose_name="Roles autorizados"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Activo', verbose_name="Estado")

    class Meta:
        verbose_name = "Perfil de Funcionario"
        verbose_name_plural = "Perfiles de Funcionarios"
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.rut})"
