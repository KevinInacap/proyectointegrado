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

### 1. Activar el entorno virtual
En Windows (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1
```

En Linux / macOS:
```bash
source .venv/bin/activate
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Aplicar migraciones
```bash
python manage.py migrate
```

### 4. Ejecutar el servidor de desarrollo
```bash
python manage.py runserver
```

Abre en el navegador:  
👉 **`http://127.0.0.1:8000/`**

---

**Ilustre Municipalidad de La Serena · Proyecto Integrado**
