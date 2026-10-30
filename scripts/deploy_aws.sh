#!/usr/bin/env bash
# Actualiza la instancia de AWS desde main sin sobrescribir .env ni borrar datos.
set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

if [[ ! -f .env || ! -x .venv/bin/python ]]; then
    echo 'Falta .env o el entorno virtual; se canceló el despliegue.' >&2
    exit 1
fi
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo 'Hay cambios locales en archivos versionados; no se sobrescribieron.' >&2
    exit 1
fi

.venv/bin/python - <<'PY'
from dotenv import dotenv_values

settings = dotenv_values('.env')
if settings.get('DB_ENGINE') != 'mysql' or settings.get('DB_NAME') != 'sgr_municipal':
    raise SystemExit('La instancia no apunta a la base MariaDB esperada.')
if settings.get('DEBUG', '').lower() not in ('false', '0'):
    raise SystemExit('DEBUG debe estar desactivado antes de desplegar.')
PY

git fetch origin main
current="$(git rev-parse HEAD)"
target="$(git rev-parse FETCH_HEAD)"
backup_dir="$(dirname "$project_root")/sgr-backups"
deployed_marker="$backup_dir/deployed.sha"

static_matches() {
    # Comprueba todos los archivos propios versionados, no solo una selección:
    # evita declarar el despliegue correcto con otro módulo antiguo en Nginx.
    local source relative
    while IFS= read -r -d '' source; do
        relative="${source#static/}"
        cmp -s "$source" "staticfiles/$relative" || return 1
        cmp -s "$source" "/var/www/sgr/static/$relative" || return 1
    done < <(git ls-files -z -- static/)
}

if [[ "$current" == "$target" && -f "$deployed_marker" && "$(< "$deployed_marker")" == "$target" ]] && static_matches; then
    sudo systemctl is-active --quiet sgr
    curl --fail --silent --show-error --max-time 8 --output /dev/null http://127.0.0.1/
    curl --fail --silent --show-error --max-time 8 --output /dev/null http://127.0.0.1/static/css/dashboard_position.css
    echo "Portal al día y saludable: ${current:0:8}"
    exit 0
fi
if [[ "$current" != "$target" ]] && ! git merge-base --is-ancestor "$current" "$target"; then
    echo 'main no es una actualización directa; revisa las ramas antes de desplegar.' >&2
    exit 1
fi

umask 077
install -d -m 700 "$backup_dir"
chmod 700 "$backup_dir"
stamp="$(date -u +%Y%m%d-%H%M%S)"
db_backup="$backup_dir/sgr_municipal-$stamp.sql"
env_backup="$backup_dir/env-$stamp"
if [[ -e "$db_backup" || -e "$env_backup" ]]; then
    echo 'Ya existe un respaldo con este nombre; espera un segundo e inténtalo de nuevo.' >&2
    exit 1
fi

sudo mariadb-dump --single-transaction --quick --routines --triggers --databases sgr_municipal > "$db_backup"
test -s "$db_backup"
cp -p .env "$env_backup"
chmod 600 "$db_backup" "$env_backup"
echo "Respaldo privado creado: $(basename "$db_backup")"

if [[ "$current" != "$target" ]]; then
    git merge --ff-only "$target"
fi
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
.venv/bin/python manage.py check --database default
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput --verbosity 0
# collectstatic puede conservar un archivo anterior si el destino tiene una
# fecha posterior. El checksum garantiza que los archivos propios coincidan.
rsync -ac "$project_root/static/" "$project_root/staticfiles/"
# Nginx sirve /var/www/sgr/static, no STATIC_ROOT. Publicar también los
# archivos nuevos de cada panel evita páginas sin estilos tras actualizar.
sudo install -d -o nginx -g nginx -m 755 /var/www/sgr/static
sudo rsync -ac --chown=nginx:nginx "$project_root/staticfiles/" /var/www/sgr/static/
sudo systemctl restart sgr

for attempt in 1 2 3 4 5; do
    if sudo systemctl is-active --quiet sgr && \
       curl --fail --silent --max-time 8 --output /dev/null http://127.0.0.1/ && \
       curl --fail --silent --max-time 8 --output /dev/null http://127.0.0.1/static/css/dashboard_position.css &&
       curl --fail --silent --max-time 8 --output /dev/null http://127.0.0.1/static/css/admin/admin-glass-pro.css &&
       curl --fail --silent --max-time 8 --output /dev/null http://127.0.0.1/static/js/admin/admin-bundle.js &&
       curl --fail --silent --max-time 8 --output /dev/null http://127.0.0.1/static/js/admin/neighbors.js &&
       curl --fail --silent --max-time 8 --output /dev/null http://127.0.0.1/static/js/admin/roles.js &&
       curl --fail --silent --max-time 8 --output /dev/null http://127.0.0.1/static/js/admin/form-feedback.js &&
       curl --fail --silent --max-time 8 --output /dev/null http://127.0.0.1/static/css/admin/interactions.css &&
       curl --fail --silent --max-time 8 --output /dev/null http://127.0.0.1/static/js/session-guard.js &&
       curl --fail --silent --max-time 8 --output /dev/null http://127.0.0.1/static/js/social-navigation.js &&
       static_matches; then
        printf '%s\n' "$target" > "$deployed_marker"
        chmod 600 "$deployed_marker"
        echo "Despliegue correcto: ${target:0:8}"
        exit 0
    fi
    sleep 1
done

echo 'El portal no respondió tras actualizar. Revisa sgr y conserva los respaldos indicados.' >&2
exit 1

