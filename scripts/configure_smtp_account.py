"""Configura Gmail en AWS sin mostrar ni guardar la clave en Git o el historial."""

from datetime import datetime, timezone
from email.message import EmailMessage
from getpass import getpass
import os
from pathlib import Path
import shutil
import smtplib
import ssl
import subprocess
import sys

from dotenv import dotenv_values, set_key


def main():
    project_root = Path(__file__).resolve().parents[1]
    env_file = project_root / '.env'
    if not env_file.is_file():
        raise SystemExit('No existe .env en el servidor.')

    values = dotenv_values(env_file)
    sender = values.get('EMAIL_HOST_USER') or 'skbubusspa@gmail.com'
    host = values.get('EMAIL_HOST') or 'smtp.gmail.com'
    port = int(values.get('EMAIL_PORT') or '587')
    if host != 'smtp.gmail.com' or port != 587:
        raise SystemExit('Esta configuración está preparada solo para Gmail con TLS en el puerto 587.')

    print(f'Se probará el envío desde {sender} hacia ese mismo correo.')
    password = getpass('Clave de aplicación de Gmail (no se mostrará): ').replace(' ', '').strip()
    if not password:
        raise SystemExit('No se ingresó una clave; no se cambió la configuración.')

    message = EmailMessage()
    message['Subject'] = 'Prueba de correo | SGR La Serena'
    message['From'] = sender
    message['To'] = sender
    message.set_content('La instancia AWS pudo enviar correo mediante Gmail. No es un código de recuperación.')

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            smtp.login(sender, password)
            refused = smtp.send_message(message)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
    except (OSError, smtplib.SMTPException) as exc:
        detail = f' (código {exc.smtp_code})' if isinstance(exc, smtplib.SMTPResponseException) else ''
        raise SystemExit(f'Gmail no aceptó la prueba: {type(exc).__name__}{detail}. No se guardó la clave.') from None

    old_umask = os.umask(0o077)
    try:
        backups = project_root.parent / 'sgr-backups'
        backups.mkdir(mode=0o700, exist_ok=True)
        backups.chmod(0o700)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        backup = backups / f'env-before-smtp-{stamp}'
        if backup.exists():
            raise SystemExit('Ya existe un respaldo de este instante; inténtalo de nuevo.')
        shutil.copy2(env_file, backup)
        backup.chmod(0o600)

        for key, value in (
            ('EMAIL_HOST', host),
            ('EMAIL_PORT', str(port)),
            ('EMAIL_HOST_USER', sender),
            ('EMAIL_HOST_PASSWORD', password),
            ('EMAIL_USE_TLS', 'True'),
            ('DEFAULT_FROM_EMAIL', sender),
        ):
            set_key(str(env_file), key, value)
        env_file.chmod(0o600)
    finally:
        os.umask(old_umask)

    subprocess.run(['sudo', 'systemctl', 'restart', 'sgr'], check=True)
    subprocess.run(['sudo', 'systemctl', 'is-active', '--quiet', 'sgr'], check=True)
    print('SMTP_OK: Gmail aceptó un correo de prueba y el portal volvió a iniciar.')
    print('Revisa la bandeja de entrada del remitente para confirmar la recepción.')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError:
        print('El correo se configuró, pero el servicio no reinició correctamente.', file=sys.stderr)
        raise SystemExit(1)
