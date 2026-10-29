"""Relación persistida entre un cargo y su rol base."""
from .access import role_name_for_position
from .models import Role


def roles_with_position_base(selected_roles, position):
    result = list(selected_roles)
    if not position:
        return result
    base_role = position.base_role
    if not base_role:
        base_name = role_name_for_position(position.name)
        # Un nombre coincidente no demuestra que el rol pertenezca al cargo.
        # La asociación debe ser explícita; nunca heredar permisos de otro rol.
        if Role.objects.filter(name__iexact=base_name).exists():
            raise ValueError('El cargo no tiene un rol base vinculado y su nombre coincide con otro rol.')
        base_role = Role.objects.create(name=base_name,
            description=f'Rol base del cargo {position.name}.', is_system=True, permissions_data=[], position=position)
        position.base_role = base_role
        position.save(update_fields=['base_role', 'updated_at'])
    if not base_role.is_system:
        raise ValueError('El rol base vinculado al cargo requiere revisión administrativa.')
    if base_role.deleted_at is not None:
        raise ValueError('El rol base vinculado al cargo está eliminado y requiere revisión administrativa.')
    if base_role.position_id not in (None, position.pk) or base_role.base_positions.exclude(pk=position.pk).exists():
        raise ValueError('El rol base está vinculado a otro cargo y requiere revisión administrativa.')
    if base_role.position_id is None:
        base_role.position = position
        base_role.save(update_fields=['position', 'updated_at'])
    if all(role.pk != base_role.pk for role in result):
        result.append(base_role)
    return result
