"""Validación de texto de las API administrativas, independiente de la interfaz."""
import json
import re
from functools import wraps
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse


def field_error(value, limit, kind='text', required=False):
    if value is None and not required:
        return None
    if not isinstance(value, str):
        return 'Debe ser texto.'
    text = value.strip()
    if len(value) > limit:
        return f'Admite hasta {limit} caracteres.'
    if not text:
        return 'Este campo es obligatorio.' if required else None
    if re.search(r'[<>\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', text):
        return 'No se permiten etiquetas HTML ni caracteres de control.'
    if kind == 'name' and (len(text) < 2 or not any(c.isalpha() for c in text)
            or any(not (c.isalpha() or c in " .’'-") for c in text)):
        return 'Usa al menos dos letras; se admiten espacios, puntos, apóstrofes y guiones.'
    if kind == 'label' and (len(text) < 2 or not any(c.isalpha() for c in text)):
        return 'Ingresa un nombre descriptivo de al menos dos caracteres.'
    if kind == 'phone' and (not re.fullmatch(r'\+?[0-9][0-9 () .-]*', text)
            or not 8 <= len(re.sub(r'\D', '', text)) <= 15):
        return 'Ingresa de 8 a 15 dígitos; puedes usar +, espacios, paréntesis y guiones.'
    if kind == 'email':
        try:
            validate_email(text)
        except ValidationError:
            return 'Ingresa un correo electrónico válido.'
    if kind == 'username' and not re.fullmatch(r'[\w.@+-]+', text, re.UNICODE):
        return 'Usa letras, números y los signos . @ + - _.'
    if kind == 'rut' and not re.fullmatch(r'[0-9.kK-]+', text):
        return 'El RUT solo admite números, puntos, guion y dígito verificador K.'
    return None


def payload_errors(data, schema):
    errors = {}
    for key, rule in schema.items():
        if key not in data:
            continue
        message = field_error(data[key], *rule)
        if message:
            errors[key] = message
    return errors


def validated_payload(schema):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method in ('POST', 'PUT', 'PATCH'):
                try:
                    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
                except (ValueError, UnicodeDecodeError):
                    return JsonResponse({'success': False, 'message': 'Solicitud JSON inválida.'}, status=400)
                if not isinstance(data, dict) and not hasattr(data, 'getlist'):
                    return JsonResponse({'success': False, 'message': 'La solicitud debe ser un objeto.'}, status=400)
                errors = payload_errors(data, schema)
                if errors:
                    return JsonResponse({'success': False, 'message': 'Revisa los campos indicados.', 'errors': errors,
                                         'details': [f'{key}: {value}' for key, value in errors.items()]}, status=400)
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


USER_FIELDS = {'username': (150, 'username', True), 'full_name': (150, 'name', True), 'email': (100, 'email', True), 'rut': (12, 'text', True)}
ROLE_FIELDS = {'name': (50, 'label', True), 'description': (255, 'text', False)}
POSITION_FIELDS = {'name': (50, 'label', True), 'description': (500, 'text', False)}
PERMISSION_FIELDS = {'module_id': (50, 'text', False), 'code': (100, 'text', True),
    'name': (120, 'label', True), 'desc': (255, 'text', False)}
DELEGATION_FIELDS = {'name': (100, 'label', True), 'scope': (100, 'label', True), 'commune': (100, 'name', True),
    'address': (200, 'text', False), 'phone': (30, 'phone', False), 'email': (120, 'email', False),
    'manager_name': (150, 'name', False), 'schedule': (120, 'text', False), 'description': (500, 'text', False), 'photo_url': (255, 'text', False)}
NEIGHBOR_FIELDS = {'nombre': (150, 'name', True), 'email': (254, 'email', False), 'direccion': (255, 'text', True),
    'telefono': (20, 'phone', False), 'territorio': (100, 'text', False), 'rut': (15, 'rut', True)}
