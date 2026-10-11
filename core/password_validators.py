from django.core.exceptions import ValidationError


class InstitutionalPasswordValidator:
    """Política compartida por altas, cambios, admin y recuperación."""

    def validate(self, password, user=None):
        if (len(password) < 8 or not any(c.isupper() for c in password)
                or not any(c.islower() for c in password)
                or not any(c in '0123456789' for c in password)
                or not any(not c.isalnum() and not c.isspace() for c in password)):
            raise ValidationError(self.get_help_text(), code='password_complexity')

    def get_help_text(self):
        return 'La contraseña debe tener al menos 8 caracteres, mayúscula, minúscula, número y carácter especial.'
