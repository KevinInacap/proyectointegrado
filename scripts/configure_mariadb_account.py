"""Prepara el acceso local a MariaDB sin mostrar ni publicar su contraseña.

Debe ejecutarlo el propietario del servidor antes del cambio de SQLite a MariaDB.
No modifica el motor activo de Django: el corte se hace después de verificar los datos.
"""

import os
import secrets
import subprocess
from pathlib import Path

import MySQLdb
from dotenv import dotenv_values, set_key


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
DATABASE = "sgr_municipal"
ACCOUNT = "sgr_user"


def mariadb(sql):
    return subprocess.run(
        ["sudo", "mariadb", "--batch", "--skip-column-names"],
        input=sql,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def main():
    if os.name != "posix":
        raise SystemExit("Este paso solo se ejecuta en la instancia Linux de AWS.")
    if not ENV_FILE.is_file():
        raise SystemExit("Falta el archivo .env privado del servidor.")
    if ENV_FILE.stat().st_uid != os.getuid():
        raise SystemExit("Ejecuta el comando como ec2-user, no como root.")

    config = dotenv_values(ENV_FILE)
    if config.get("DB_ENGINE", "sqlite3").lower() != "sqlite3":
        raise SystemExit("La aplicación ya no usa SQLite; no se rotará su clave en funcionamiento.")

    try:
        account_count = mariadb(
            "SELECT COUNT(*) FROM mysql.user "
            "WHERE User='sgr_user' AND Host='localhost';\n"
        )
        database_count = mariadb(
            "SELECT COUNT(*) FROM information_schema.schemata "
            "WHERE schema_name='sgr_municipal';\n"
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"No se pudo revisar MariaDB (código {exc.returncode}).") from exc
    if account_count != "1" or database_count != "1":
        raise SystemExit("La cuenta local o la base de datos esperada no existen; no se cambió nada.")

    password = secrets.token_urlsafe(48)
    for name, value in {
        "DB_USER": ACCOUNT,
        "DB_PASSWORD": password,
        "DB_HOST": "localhost",
        "DB_PORT": "3306",
    }.items():
        set_key(str(ENV_FILE), name, value, quote_mode="never")
    os.chmod(ENV_FILE, 0o600)

    try:
        mariadb(f"ALTER USER '{ACCOUNT}'@'localhost' IDENTIFIED BY '{password}';\n")
        connection = MySQLdb.connect(
            host="localhost", user=ACCOUNT, passwd=password, db=DATABASE
        )
        connection.close()
    except (subprocess.CalledProcessError, MySQLdb.Error) as exc:
        raise SystemExit(
            "No se pudo validar el acceso. El portal sigue en SQLite; vuelve a ejecutar este comando."
        ) from exc

    print("Acceso local a MariaDB validado. La clave quedó solo en el .env privado.")


if __name__ == "__main__":
    main()
