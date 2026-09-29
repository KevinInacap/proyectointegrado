# Sistema de Gestión de Resultados (SGR) — Ilustre Municipalidad de La Serena

Prototipo institucional desarrollado

## 🏛️ Descripción del Proyecto

El **Sistema de Gestión de Resultados (SGR)** es una solución web diseñada para centralizar, monitorear y evaluar la gestión operativa de funcionarios y delegaciones de la **Ilustre Municipalidad de La Serena** (Región de Coquimbo, Chile). 

### Características Principales:
* **Portal de Acceso Institucional:** Pantalla de inicio de sesión con identidad visual municipal, fotografía panorámica del Faro Monumental de La Serena y panel de acceso.
* **Dashboard Operativo:** Visualización de métricas de cumplimiento, metas diarias y estado de actividades territoriales.
* **Trazabilidad de Evidencias:** Registro de actividades con código correlativo e inmutable, respaldos fotográficos y flujo de validación.

---

## 🎨 Proceso de Diseño y Construcción de la Interfaz de Acceso (Login)

La pantalla de acceso institucional fue concebida para combinar rigor técnico, pertinencia comunal y una experiencia visual de alto estándar. A continuación, se detallan las decisiones de diseño e ingeniería de interfaz aplicadas en su desarrollo:

### 1. Elección y Adaptación de la Fotografía Panorámica
* **Pertinencia Territorial:** Se seleccionó una fotografía panorámica real en alta resolución del icónico **Faro Monumental de La Serena** capturada en horario de atardecer, resaltando la costanera y el patrimonio arquitectónico de la ciudad.
* **Encuadre Asimétrico Estratégico:** Aplicando la regla de los tercios, el monumento se posicionó íntegramente en el tercio izquierdo de la imagen (torre blanca, almenas terracota y garitas esquineras), reservando más del 50% central y derecho con espacio negativo sobre el Océano Pacífico. Esta distribución permite alojar la tarjeta de autenticación de forma equilibrada sin obstaculizar la vista del monumento.
* **Crédito de Autoría Visual:** En la esquina inferior izquierda se incorporó una cápsula translúcida con desenfoque de fondo que formaliza el reconocimiento a los autores de la captura:  
  *`"Fotografía por Kevin Encina Molina y Scarlett Williams Medalla"`*.

### 2. Estilo Visual Moderno (Efecto Cristal / Glassmorphism)
* **Arquitectura de Cristal Real (`Frosted Glass`):** Se sustituyó el esquema convencional de formularios planos y opacos por un contenedor diseñado con técnicas de filtrado óptico (`backdrop-filter: blur(28px) saturate(200%)`). Este acabado translúcido permite que los tonos crepusculares del fondo se refracten con naturalidad a través de la tarjeta.
* **Biselado y Luz Cenital:** El contenedor incorpora bordes asimétricos con mayor luminosidad en las aristas superior e izquierda, simulando el impacto de una fuente de luz cenital que aporta relieve, volumen y sensación tridimensional de cristal pulido.
* **Micro-interacción 3D Suave:** Se implementó una respuesta giroscópica sutil mediante Vanilla Tilt, generando una inclinación controlada y un destello especular al interactuar con el cursor, otorgando dinamismo sin interferir con la usabilidad.

### 3. Mejoras de Experiencia de Usuario y Accesibilidad
* **Campos de Entrada Integrados:** Los campos de RUT y contraseña cuentan con fondos oscuros translúcidos, eliminando contrastes invasivos. Disponen de iconos vectoriales alineados, opción para alternar la visibilidad de la contraseña y un formato de ejemplo formal chileno (`12.345.678-K`).
* **Optimización de Contrastes:** Se ajustaron las tonalidades de textos, títulos y enlaces de recuperación para asegurar una lectura inmediata y accesible bajo criterios WCAG, manteniendo alta visibilidad sobre cualquier sección del fondo.
* **Botón Principal Institucional:** El botón de acceso aplica los colores granate y rojo corporativos de la Ilustre Municipalidad de La Serena (`#e11d48` a `#9f1239`), complementado con micro-animación de elevación al posicionar el cursor.

---

## 🛠️ Stack Tecnológico

* **Backend:** Python 3 / Django
* **Frontend:** HTML5, CSS3, JavaScript Vanilla
* **Framework UI & Efectos:** Bootstrap 5.3, Bootstrap Icons, Vanilla Tilt
* **Base de Datos:** SQLite / MySQL compatible
* **Control de Versiones:** Git / GitHub

---

## 🚀 Instalación y Puesta en Marcha

### 1. Crear el entorno virtual
```bash
python -m venv .venv
```

### 2. Activar el entorno virtual

* **En Git Bash:**
  ```bash
  source .venv/Scripts/activate
  ```

* **En Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```

* **En Windows (CMD):**
  ```cmd
  .venv\Scripts\activate.bat
  ```

* **En Linux / macOS:**
  ```bash
  source .venv/bin/activate
  ```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crea tu archivo local `.env` a partir de la plantilla:
* En Git Bash / Linux:
  ```bash
  cp .env.example .env
  ```
* En Windows (PowerShell):
  ```powershell
  Copy-Item .env.example .env
  ```

### 5. Verificar y aplicar migraciones
```bash
python manage.py check
python manage.py migrate
```

### 6. Cargar datos reproducibles (Seed)
Ejecuta el comando para poblar la base de datos con usuarios y datos operativos:
```bash
python manage.py seed_data
```

### 7. Ejecutar el servidor de desarrollo
```bash
python manage.py runserver
```

Abre en el navegador:  
* **Portal de Acceso:** `http://127.0.0.1:8000/`  
* **Django Admin:** `http://127.0.0.1:8000/admin/`  

---

## 👥 Cuentas de Prueba Documentadas (Evaluación Sumativa II)

El sistema implementa control de acceso basado en roles con **Grupos de Django (`django.contrib.auth.models.Group`)** y **Scoping Territorial**:

| Usuario | Contraseña | RUT | Grupo / Rol | Contexto / Delegación | Alcance y Permisos |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`admin`** | `Admin1234!` | `11.111.111-1` | **Administradores** | Centro Histórico | **Superusuario:** Acceso total, gestión transversal de usuarios, delegaciones, eliminación física y auditoría. |
| **`admin_control`** | `Admin1234!` | `13.444.555-6` | **Administradores** | Centro Histórico | Control comunal, auditoría y parametrización de metas. |
| **`verificador`** | `Verificador1234!` | `15.678.901-2` | **Verificadores** | Las Compañías | Auditoría técnica y validación formal de evidencias; no puede crear registros operacionales. |
| **`verificador_centro`**| `Verificador1234!` | `16.789.012-3` | **Verificadores** | Centro Histórico | Revisión y validación sector centro. |
| **`funcionario_companias`**| `Funcionario1234!` | `17.892.456-3` | **Gestores Territoriales**| Las Compañías | **Usuario limitado:** Solo visualiza y opera datos de la Delegación Las Compañías (Scoping). Sin permiso de borrado. |
| **`funcionario_centro`** | `Funcionario1234!` | `18.345.678-K` | **Gestores Territoriales**| Centro Histórico | **Usuario limitado:** Solo opera en Centro Histórico. No visualiza Las Compañías. |
| **`funcionario_pampa`** | `Funcionario1234!` | `12.345.678-K` | **Gestores Territoriales**| La Pampa | Operación territorial en La Pampa. |
| **`funcionario_rural`** | `Funcionario1234!` | `19.876.543-2` | **Gestores Territoriales**| Sector Rural | Operación territorial en Sector Rural. |

---

## 🏛️ Estructura de Aplicaciones y Arquitectura Django

El proyecto divide responsabilidades en 6 aplicaciones modulares del dominio:

* **`core/`**: Configuración transversal, vistas de autenticación (`login_view`, `logout_view`), modelo base abstracto de auditoría (`BaseModel`: `created_at`, `updated_at`, `deleted_at`), registro de auditoría (`AuditLog`) y comando de semillas reproducible (`seed_data.py`).
* **`organization/`**: Entidades maestras territoriales e institucionales (`Delegation`, `Position`, `UserProfile`), extensión de `CustomUserAdmin` con acciones de asignación masiva de grupos y delegaciones, y `UserProfileStackedInline`.
* **`activities/`**: Módulo operativo central (`Activity`, `Evidence`, `Validation`, `ServiceCatalog`), formularios con validación controlada (`ActivityForm`), vistas de dashboard y acciones de validación/borrado lógico en Django Admin.
* **`agenda/`**: Tubo de trabajo y compromisos vecinales (`CollectiveAgenda`, `CommitmentHistory`) con acciones masivas e historial inline.
* **`social/`**: Casos sociales y gestiones encadenadas (`SocialCase`, `SocialManagement`) con scoping territorial y validación controlada en `clean()`.
* **`metrics/`**: Metas de gestión y cálculo de avance (`MeasurementPeriod`, `MeasurementItem`, `Goal`, `DailyIndicator`, `PerformanceAdjustment`).

---

## 🛡️ Evidencias para la Defensa en Laboratorio

1. **Admin Básico:** Registro de más de 8 tablas maestras y operativas con `list_display`, `search_fields`, `list_filter`, `ordering` y `list_select_related`.
2. **Admin Pro:**
   - **Inlines:** `UserProfileStackedInline` en Usuarios, `EvidenceInline` en Actividades, `SocialManagementInline` en Casos Sociales, `CommitmentHistoryInline` en Agenda.
   - **Acciones Personalizadas:** En Usuarios (asignar grupos y delegaciones), en Actividades (aprobar, corrección, borrado lógico), en Casos Sociales (derivar a evaluación, restaurar) y en Agenda (marcar en proceso, marcar cumplido).
   - **Validación Controlada `clean()`:** Bloqueo de fechas futuras en actividades y casos sociales; obligatoriedad de dirigente de contacto si deriva a agenda colectiva.
3. **Seguridad y Scoping:**
   - Ingresar con `admin`: Visibilidad comunal completa, capacidad de editar y eliminar cualquier registro.
   - Ingresar con `funcionario_companias`: Solo visualiza registros de su delegación ("Delegación Las Compañías"), sin acceso a registros de otras delegaciones y sin permisos de borrado físico (`has_delete_permission = False`).

---

**Ilustre Municipalidad de La Serena · Proyecto Integrado Backend**
