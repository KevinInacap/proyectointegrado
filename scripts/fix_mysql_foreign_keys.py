import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import connection

sql_commands = [
    # 1. codigo_recuperacion_clave -> CASCADE
    ("codigo_recuperacion_clave", "codigo_recuperacion_clave_user_id_358c0f22_fk_auth_user_id",
     "ALTER TABLE codigo_recuperacion_clave DROP FOREIGN KEY codigo_recuperacion_clave_user_id_358c0f22_fk_auth_user_id",
     "ALTER TABLE codigo_recuperacion_clave ADD CONSTRAINT codigo_recuperacion_clave_user_id_358c0f22_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user (id) ON DELETE CASCADE"),

    # 2. organization_userprofile -> CASCADE
    ("organization_userprofile", "organization_userprofile_user_id_183a4e22_fk_auth_user_id",
     "ALTER TABLE organization_userprofile DROP FOREIGN KEY organization_userprofile_user_id_183a4e22_fk_auth_user_id",
     "ALTER TABLE organization_userprofile ADD CONSTRAINT organization_userprofile_user_id_183a4e22_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user (id) ON DELETE CASCADE"),

    # 3. organization_userprofile_roles -> CASCADE
    ("organization_userprofile_roles", "organization_userpro_userprofile_id_d9b67151_fk_organizat",
     "ALTER TABLE organization_userprofile_roles DROP FOREIGN KEY organization_userpro_userprofile_id_d9b67151_fk_organizat",
     "ALTER TABLE organization_userprofile_roles ADD CONSTRAINT organization_userpro_userprofile_id_d9b67151_fk_organizat FOREIGN KEY (userprofile_id) REFERENCES organization_userprofile (id) ON DELETE CASCADE"),

    # 4. auth_user_groups -> CASCADE
    ("auth_user_groups", "auth_user_groups_user_id_6a12ed8b_fk_auth_user_id",
     "ALTER TABLE auth_user_groups DROP FOREIGN KEY auth_user_groups_user_id_6a12ed8b_fk_auth_user_id",
     "ALTER TABLE auth_user_groups ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user (id) ON DELETE CASCADE"),

    # 5. auth_user_user_permissions -> CASCADE
    ("auth_user_user_permissions", "auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id",
     "ALTER TABLE auth_user_user_permissions DROP FOREIGN KEY auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id",
     "ALTER TABLE auth_user_user_permissions ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user (id) ON DELETE CASCADE"),

    # 6. core_auditlog -> SET NULL
    ("core_auditlog", "core_auditlog_user_id_3797aaab_fk_auth_user_id",
     "ALTER TABLE core_auditlog DROP FOREIGN KEY core_auditlog_user_id_3797aaab_fk_auth_user_id",
     "ALTER TABLE core_auditlog ADD CONSTRAINT core_auditlog_user_id_3797aaab_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user (id) ON DELETE SET NULL"),

    # 7. django_admin_log -> CASCADE
    ("django_admin_log", "django_admin_log_user_id_c564eba6_fk_auth_user_id",
     "ALTER TABLE django_admin_log DROP FOREIGN KEY django_admin_log_user_id_c564eba6_fk_auth_user_id",
     "ALTER TABLE django_admin_log ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user (id) ON DELETE CASCADE"),

    # 8. activities_activity -> SET NULL
    ("activities_activity", "activities_activity_user_id_233a83a7_fk_auth_user_id",
     "ALTER TABLE activities_activity DROP FOREIGN KEY activities_activity_user_id_233a83a7_fk_auth_user_id",
     "ALTER TABLE activities_activity ADD CONSTRAINT activities_activity_user_id_233a83a7_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user (id) ON DELETE SET NULL"),

    # 9. activities_evidence -> SET NULL
    ("activities_evidence", "activities_evidence_uploaded_by_id_9243624c_fk_auth_user_id",
     "ALTER TABLE activities_evidence DROP FOREIGN KEY activities_evidence_uploaded_by_id_9243624c_fk_auth_user_id",
     "ALTER TABLE activities_evidence ADD CONSTRAINT activities_evidence_uploaded_by_id_9243624c_fk_auth_user_id FOREIGN KEY (uploaded_by_id) REFERENCES auth_user (id) ON DELETE SET NULL"),

    # 10. activities_validation -> SET NULL
    ("activities_validation", "activities_validation_verifier_id_aff08b53_fk_auth_user_id",
     "ALTER TABLE activities_validation DROP FOREIGN KEY activities_validation_verifier_id_aff08b53_fk_auth_user_id",
     "ALTER TABLE activities_validation ADD CONSTRAINT activities_validation_verifier_id_aff08b53_fk_auth_user_id FOREIGN KEY (verifier_id) REFERENCES auth_user (id) ON DELETE SET NULL"),

    # 11. agenda_collectiveagenda -> SET NULL
    ("agenda_collectiveagenda", "agenda_collectiveagenda_assigned_to_id_44866077_fk_auth_user_id",
     "ALTER TABLE agenda_collectiveagenda DROP FOREIGN KEY agenda_collectiveagenda_assigned_to_id_44866077_fk_auth_user_id",
     "ALTER TABLE agenda_collectiveagenda ADD CONSTRAINT agenda_collectiveagenda_assigned_to_id_44866077_fk_auth_user_id FOREIGN KEY (assigned_to_id) REFERENCES auth_user (id) ON DELETE SET NULL"),

    # 12. agenda_commitmenthistory -> SET NULL
    ("agenda_commitmenthistory", "agenda_commitmenthistory_author_id_424fb01a_fk_auth_user_id",
     "ALTER TABLE agenda_commitmenthistory DROP FOREIGN KEY agenda_commitmenthistory_author_id_424fb01a_fk_auth_user_id",
     "ALTER TABLE agenda_commitmenthistory ADD CONSTRAINT agenda_commitmenthistory_author_id_424fb01a_fk_auth_user_id FOREIGN KEY (author_id) REFERENCES auth_user (id) ON DELETE SET NULL"),

    # 13. metrics_dailyindicator -> CASCADE
    ("metrics_dailyindicator", "metrics_dailyindicator_user_id_a211ef31_fk_auth_user_id",
     "ALTER TABLE metrics_dailyindicator DROP FOREIGN KEY metrics_dailyindicator_user_id_a211ef31_fk_auth_user_id",
     "ALTER TABLE metrics_dailyindicator ADD CONSTRAINT metrics_dailyindicator_user_id_a211ef31_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user (id) ON DELETE CASCADE"),

    # 14. metrics_performanceadjustment -> CASCADE
    ("metrics_performanceadjustment", "metrics_performanceadjustment_user_id_9c022e82_fk_auth_user_id",
     "ALTER TABLE metrics_performanceadjustment DROP FOREIGN KEY metrics_performanceadjustment_user_id_9c022e82_fk_auth_user_id",
     "ALTER TABLE metrics_performanceadjustment ADD CONSTRAINT metrics_performanceadjustment_user_id_9c022e82_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user (id) ON DELETE CASCADE"),

    # 15. metrics_performanceadjustment (registered_by) -> SET NULL
    ("metrics_performanceadjustment", "metrics_performancea_registered_by_id_6a516385_fk_auth_user",
     "ALTER TABLE metrics_performanceadjustment DROP FOREIGN KEY metrics_performancea_registered_by_id_6a516385_fk_auth_user",
     "ALTER TABLE metrics_performanceadjustment ADD CONSTRAINT metrics_performancea_registered_by_id_6a516385_fk_auth_user FOREIGN KEY (registered_by_id) REFERENCES auth_user (id) ON DELETE SET NULL"),
]

print("Actualizando restricciones de clave foránea en MySQL...")
with connection.cursor() as cursor:
    for table, fk_name, drop_sql, add_sql in sql_commands:
        try:
            cursor.execute(drop_sql)
            cursor.execute(add_sql)
            print(f"[OK] {table}.{fk_name} -> Actualizada con éxito.")
        except Exception as e:
            print(f"[SKIP/INFO] {table}.{fk_name}: {e}")

print("¡Restricciones de clave foránea actualizadas en MySQL!")
