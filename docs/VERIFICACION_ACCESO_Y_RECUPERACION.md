# Verificación de acceso y recuperación

Fecha: 30 de octubre de 2026.

El ingreso anónimo a `/` muestra el formulario. Cuando una sesión válida ya existe, la misma dirección lleva al panel correspondiente al cargo; al cerrar sesión o al caducar la sesión vuelve a mostrarse el formulario. «Recordarme» controla la duración de la sesión, no guarda la contraseña.

## Correcciones

- El formulario acepta identificadores válidos que antes podían ser rechazados por JavaScript, mantiene el destino posterior al acceso y muestra un aviso accesible si SweetAlert no carga. El botón de mostrar contraseña comunica su estado y el formulario puede desplazarse en pantallas anchas de poca altura.
- La redirección posterior admite rutas locales seguras; rechaza destinos externos y no permite iniciar sesión sin un cargo activo. Las peticiones de acceso requieren CSRF.
- Se reemplazó el enlace de recuperación que prometía usar un código desde una sesión nueva por una explicación del flujo existente. El código se verifica en la sesión desde la que se inicia la recuperación; si se cambia de navegador, se inicia nuevamente el proceso y se usa el último código recibido.

## Evidencia y límites

- Pasaron 252 pruebas de Django 6.1.1 con SQLite aislado y contraseñas de prueba. La recuperación se comprobó con correo simulado, incluidos envío, hash, vencimiento, cinco intentos y uso único; no se enviaron correos ni se cambiaron cuentas reales.
- Pasaron las 14 pruebas JavaScript de acceso, sesión, administración y navegación social. `manage.py check` y la comprobación de migraciones terminaron sin observaciones.
- No se completó una revisión visual del nuevo formulario en navegador, ni se verificó el envío por el correo configurado en AWS. Estas pruebas locales no acreditan que la instancia pública ya tenga los cambios.
