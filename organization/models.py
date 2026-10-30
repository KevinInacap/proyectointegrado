from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from core.models import BaseModel

class Delegation(BaseModel):
    STATUS_CHOICES = [('Activo', 'Activo'), ('Inactivo', 'Inactivo')]
    code = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="Código de delegación")
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la delegación")
    scope = models.CharField(max_length=100, verbose_name="Ámbito territorial")
    commune = models.CharField(max_length=100, default='La Serena', verbose_name='Comuna')
    address = models.CharField(max_length=200, blank=True, default='', verbose_name="Dirección")
    phone = models.CharField(max_length=30, blank=True, default='', verbose_name="Teléfono")
    email = models.EmailField(max_length=120, blank=True, default='', verbose_name="Correo de contacto")
    schedule = models.CharField(max_length=120, blank=True, default='', verbose_name="Horario de atención")
    manager_name = models.CharField(max_length=150, blank=True, default='', verbose_name="Delegado o encargado")
    photo_url = models.CharField(max_length=255, blank=True, default='', verbose_name="Ruta o URL de fotografía")
    description = models.TextField(blank=True, default='', verbose_name="Descripción territorial")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Activo', verbose_name="Estado")

    class Meta:
        verbose_name = "Delegación"
        verbose_name_plural = "Delegaciones"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # El identificador no depende del nombre: renombrar una sede no cambia su código.
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.code:
            base = f'DEL-{str(self.pk).zfill(3)[-16:]}'
            candidate = base
            suffix = 1
            # Un código ingresado manualmente puede anticipar el siguiente ID.
            # No debe impedir guardar otra sede con código automático.
            while type(self).objects.filter(code__iexact=candidate).exists():
                suffix += 1
                candidate = f'{base[:20 - len(str(suffix)) - 1]}-{suffix}'
            self.code = candidate
            type(self).objects.filter(pk=self.pk).update(code=self.code)


class Position(BaseModel):
    base_role = models.ForeignKey('Role', on_delete=models.PROTECT, null=True, blank=True,
                                  related_name='base_positions', verbose_name='Rol base del cargo')
    STATUS_CHOICES = [('Activo', 'Activo'), ('Inactivo', 'Inactivo')]
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
    # Los registros históricos ambiguos permanecen sin vincular hasta su revisión.
    position = models.ForeignKey(Position, on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='access_roles', verbose_name='Cargo del rol')
    name = models.CharField(max_length=50, unique=True, verbose_name="Nombre del rol")
    description = models.CharField(max_length=255, blank=True, default='', verbose_name="Descripción del rol")
    is_system = models.BooleanField(default=False, verbose_name="Rol de sistema protegido")
    permissions_data = models.JSONField(default=list, blank=True, verbose_name="Permisos y funciones asignadas")
    permission_definitions = models.ManyToManyField(
        'PermissionDefinition', blank=True, related_name='roles',
        verbose_name="Permisos detallados del catálogo"
    )

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ['name']

    def __str__(self):
        return self.name


class PermissionDefinition(BaseModel):
    module_id = models.CharField(max_length=50, verbose_name="Módulo")
    code = models.CharField(max_length=100, unique=True, verbose_name="Código")
    name = models.CharField(max_length=120, verbose_name="Nombre")
    description = models.CharField(max_length=255, blank=True, default='', verbose_name="Descripción")
    is_system = models.BooleanField(default=False, verbose_name="Permiso base del sistema")

    class Meta:
        db_table = 'permiso_definicion'
        ordering = ['module_id', 'name']

    def __str__(self):
        return f"{self.code} — {self.name}"


class UserProfile(BaseModel):
    STATUS_CHOICES = [('Activo', 'Activo'), ('Inactivo', 'Inactivo'), ('Bloqueado', 'Bloqueado')]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile',
        verbose_name="Cuenta de usuario"
    )
    rut = models.CharField(max_length=12, unique=True, verbose_name="RUT")
    full_name = models.CharField(max_length=150, verbose_name="Nombre completo")
    email = models.EmailField(max_length=100, unique=True, verbose_name="Correo electrónico institucional")
    delegation = models.ForeignKey(
        Delegation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='users', verbose_name="Delegación asignada"
    )
    position = models.ForeignKey(
        Position, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='users', verbose_name="Cargo asignado"
    )
    roles = models.ManyToManyField(
        Role, blank=True, related_name='users', verbose_name="Roles autorizados"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Activo', verbose_name="Estado")

    def clean(self):
        super().clean()
        if self.delegation and (
            self.delegation.status != 'Activo' or self.delegation.deleted_at is not None
        ):
            raise ValidationError({'delegation': 'La delegación debe estar activa y vigente.'})
        if self.position and (
            self.position.status != 'Activo' or self.position.deleted_at is not None
        ):
            raise ValidationError({'position': 'El cargo debe estar activo y vigente.'})

    class Meta:
        verbose_name = "Perfil de Funcionario"
        verbose_name_plural = "Perfiles de Funcionarios"
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.rut})"
