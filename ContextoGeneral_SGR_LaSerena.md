# 🏛️ CONTEXTO GENERAL INSTITUCIONAL Y TÉCNICO
## Sistema de Gestión de Resultados (SGR) — Ilustre Municipalidad de La Serena
### Asignatura: Proyecto Integrado | Evaluación: Análisis, Diseño, Base de Datos y Prototipo Funcional
### Institución: INACAP | Sede La Serena | Profesor: Jorge Cortés

---

## 1. RESUMEN EJECUTIVO Y CONTEXTO TERRITORIAL

### 1.1 La Comuna de La Serena
La Serena es la capital de la Región de Coquimbo, caracterizada por ser una comuna diversa con funciones administrativas, residenciales, patrimoniales, turísticas y rurales.
- **Población Total (Censo 2024):** 250.141 habitantes.
- **Distribución Territorial:** 89,14% urbana y 10,86% rural dispersa.
- **Desafío Operativo:** La dispersión territorial y la alta demanda ciudadana exigen un modelo de gestión descentralizado a través de **Delegaciones Municipales**, acercando el municipio a los barrios y localidades rurales.

### 1.2 Autoridades Comunales Vigentes (Período 2024–2028)
- **Alcaldesa de La Serena:** **Daniela Norambuena Borgheresi**, Ingeniera Agrónoma, ex Seremi de Agricultura y ex Gobernadora de Elqui. Enfoca su plan de gobierno comunal en la modernización digital, transparencia, seguridad y recuperación del espacio público.
- **Concejo Municipal (10 Concejales/as):**
  1. Cristian Marín Pastén
  2. Rayén Pojomovsky Aliste
  3. Alejandro Astudillo Olguín
  4. Gladys Marín Ossandón
  5. Francisca Barahona Araya
  6. María Teresa Prouvay Cornejo
  7. Camilo Araya Plaza
  8. Marcela Damke Marín
  9. Matías Espinosa Morales
  10. Luisa Jinete Cárcamo

---

## 2. RED DE LAS 6 DELEGACIONES MUNICIPALES (SEDES TERRITORIALES)

Conforme al Reglamento Interno Municipal, las delegaciones canalizan demandas ciudadanas, coordinan servicios en terreno y gestionan emergencias comunales.

| # | Delegación | Territorio y ámbito predominante |
|---|---|---|
| 1 | **Centro** | Casco histórico, administrativo, comercial y patrimonial |
| 2 | **Las Compañías** | Sector urbano norte |
| 3 | **La Pampa** | Sector urbano sur |
| 4 | **La Antena - La Florida** | Sector urbano oriental |
| 5 | **Avenida del Mar** | Borde costero |
| 6 | **Rural** | Localidades agrícolas, valles, caletas y comunidades dispersas |

Las direcciones, teléfonos, correos y responsables no se fijan en este documento: deben cargarse desde una fuente municipal verificada y mantenerse en la base del entorno correspondiente.

---

## 3. ROLES OBLIGATORIOS DEL SISTEMA SGR Y MATRIZ RBAC

Conforme a la especificación académica de INACAP (Sección 3 y RF-002 / RNF-005), el sistema implementa **6 roles formales** con segregación estricta de responsabilidades:

```
                                  ┌─────────────────────────────┐
                                  │    ADMINISTRADOR GENERAL    │
                                  │ (Configuración, Roles, BD)  │
                                  └──────────────┬──────────────┘
                                                 │
                                  ┌──────────────┴──────────────┐
                                  │   COORDINADOR DEL SISTEMA   │
                                  │  (Metas, Períodos, Reportes)│
                                  └──────────────┬──────────────┘
                                                 │
                 ┌───────────────────────────────┼───────────────────────────────┐
                 │                               │                               │
  ┌──────────────┴──────────────┐ ┌──────────────┴──────────────┐ ┌──────────────┴──────────────┐
  │     DELEGADO MUNICIPAL      │ │   GESTOR / FUNCIONARIO      │ │     VERIFICADOR TÉCNICO     │
  │ (Jefatura de Sede Territorial│ │ (Terreno, Casos, Evidencias)│ │(Auditoría y Aprobación EVI) │
  └─────────────────────────────┘ └─────────────────────────────┘ └─────────────────────────────┘
                                                 │
                                  ┌──────────────┴──────────────┐
                                  │     USUARIO DE CONSULTA     │
                                  │ (Solo Lectura / Reportes)   │
                                  └─────────────────────────────┘
```

### Tabla de Privilegios por Rol:
1. **Administrador General:** Control total del sistema, gestión de usuarios, roles, catálogo de servicios, parámetros del semáforo y revisión de registros de auditoría (`auditoria`).
2. **Coordinador del Sistema:** Supervisa las 6 delegaciones, abre y cierra períodos de medición trimestrales (T1, T2, T3, T4), aprueba metas comunales y exporta reportes consolidados.
3. **Delegado Municipal:** Jefatura territorial de la delegación; asigna tareas, monitorea el tubo de trabajo colectivo de sus funcionarios y reasigna casos ante ausencias (HU-15).
4. **Funcionario / Gestor Territorial:** Registra en ventanilla y terreno atenciones de vecinos, solicitudes ciudadanas, sube fotografías de respaldo con código único `EVI-XXXX` y actualiza estados de trámites (HU-01, HU-02).
5. **Verificador Técnico:** Rol de control de calidad documental; revisa las evidencias cargadas por los gestores, emite dictamen de aprobación, rechazo o corrección con observaciones. Solo una evidencia aprobada suma al avance (RN-009).
6. **Usuario de Consulta:** Perfil de solo lectura (DIDECO, Alcaldía, Concejales o Auditores externos) con acceso a tableros y reportes sin facultades operativas de edición.

---

## 4. CUENTAS DE PRUEBA

No se publican nombres, RUT ni correos de cuentas ficticias o institucionales en este documento. La semilla normal no crea usuarios; las cuentas de evaluación, si se necesitan, se crean localmente con datos sintéticos y una contraseña privada fuera del repositorio.

---

## 5. REGLAS DE NEGOCIO Y MODELO MATEMÁTICO SGR (RN-001 A RN-013)

### Fórmulas del Sistema:
1. **Suma de Ponderadores (RN-001):**
   $$\sum \text{Ponderadores de un cargo} = 100\%$$
2. **Porcentaje de Cumplimiento por Ítem (RN-004):**
   $$\% \text{ Cumplimiento} = \left(\frac{\text{Avance Real Aprobado}}{\text{Meta del Período}}\right) \times 100$$
3. **Cumplimiento Ponderado (RN-005):**
   $$\text{Aporte Ponderado} = \frac{\% \text{ Cumplimiento} \times \text{Ponderador}}{100} \quad (\text{Tope máximo: } 150\%)$$
4. **Meta Esperada al Día (RN-007):**
   $$\text{Meta Esperada} = \left(\frac{\text{Días Transcurridos Computables}}{\text{Días Totales del Período}}\right) \times 100$$
   *Ejemplo oficial T3:* Día 56 de 91 días computables $\rightarrow$ **61,54%** meta acumulada esperada.
5. **Regla del Semáforo Institucional (RN-008):**
   - 🟢 **Verde (Normal):** $\text{Avance Real} \ge \text{Meta Esperada al Día}$
   - 🟡 **Ámbar (Prevención):** $60\% \le \text{Avance Real} < \text{Meta Esperada al Día}$
   - 🔴 **Rojo (Rezago):** $\text{Avance Real} < 60\%$ de la meta esperada.
6. **Atención Social en 3 Etapas (RN-012):**
   Un caso social vinculado a un RUT vecinal permite registrar hasta 3 gestiones secuenciales sin duplicar la ficha principal:
   - *Etapa 1:* Ingreso y recepción de antecedentes.
   - *Etapa 2:* Visita en terreno y levantamiento técnico (con fotografía obligatoria).
   - *Etapa 3:* Resolución, entrega de subsidio o cierre en agenda colectiva.

---

## 6. AUDITORÍA DE BOTONES Y CORRECCIÓN DE BUGS EN LA INTERFAZ

Durante el análisis exhaustivo del código frontend (`templates/activities/admin/views/` y `static/js/admin/admin-bundle.js`), se identificaron y subsanaron los siguientes fallos:

### 6.1 Botones que NO Servían o Estaban Muertos (Identificados y Corregidos):
| Vista / Componente | Elemento / Botón | Causa del Fallo Original | Solución Implementada |
|---|---|---|---|
| **Metas SGR** (`metas.html`) | Botón `Exportar Excel` | Función `exportarMetasExcel()` no existía en JS | Implementada exportación completa vía SheetJS XLSX |
| **Metas SGR** (`metas.html`) | Botón `+ Nueva Meta / Ítem` | Función `abrirModalNuevaMeta()` no existía | Modal interactivo SweetAlert2 para registrar metas con ponderador y cálculo de días |
| **Metas SGR** (`metas.html`) | 4 Botones de lápiz (Editar) | No tenían atributo `onclick` | Vinculados a `editarMeta(cargo, item, pond, val)` |
| **Tipo de Atención** (`tipo_atencion.html`) | Botón `Nuevo Tipo de Atención` | Función `abrirModalNuevoTipoAtencion()` no existía | Creado modal con SweetAlert2 para agregar categorías al catálogo |
| **Tipo de Atención** (`tipo_atencion.html`) | Botón `Nueva Sub Atención` | Función `abrirModalNuevaSubAtencion()` no existía | Creado modal para vincular subatención y plazo a categoría |
| **Tipo de Atención** (`tipo_atencion.html`) | Botón `Nuevo Tipo de Gestión` | Función `abrirModalNuevoTipoGestion()` no existía | Creado modal para etapas de gestión social |
| **Tipo de Atención** (`tipo_atencion.html`) | 11 Botones de lápiz en tablas | No tenían atributo `onclick` | Vinculados a funciones de edición en vivo |
| **Panel Lateral** (`drawer_editor.html`) | Botón `Cancelar` / `Cerrar` | `cerrarAdminDrawer()` no existía | Implementado control del panel lateral y backdrop |
| **Panel Lateral** (`drawer_editor.html`) | Botón `Guardar Cambios` | `ejecutarGuardadoDrawer()` no existía | Implementado guardado en tiempo real en memoria y backend |
| **Barra Flotante por Lote** (`floating_batch_bar.html`) | Botón `Cambiar Estado` / `Eliminar` | `ejecutarAccionLote()` no existía | Conectado a acciones masivas sobre filas seleccionadas |
| **Barra Flotante por Lote** (`floating_batch_bar.html`) | Botón `Deseleccionar (X)` | `deseleccionarTodoFilas()` no existía | Implementado desmarcado global y ocultamiento de barra |
| **Atenciones** (`atenciones.html`) | Botón de Ojo (Expediente) | Truncamiento visual en tabla | Tabla configurada con `colgroup` fijo, sin scroll horizontal |
| **Dashboard** (`dashboard.html`) | Calendario municipal | Fecha fija en HTML (estática) | Conectado a fecha real del sistema con navegación `<` y `>` |

---

## 7. VALIDACIONES DE FORMULARIOS Y PROTECCIÓN DE SEGURIDAD (ANTI-HACK)

Para cumplir con las exigencias de la rúbrica de INACAP y proteger la aplicación:

### 7.1 Validación de Nombres y Apellidos (Sin Números)
- **Evento Keypress:** Detecta si la tecla presionada es un dígito `[0-9]` y cancela el evento con `e.preventDefault()`.
- **Filtro al Pegar / Input:** Limpia automáticamente cualquier número pegado con `value.replace(/[0-9]/g, '')`.
- **Aplicado a:** `usrFullName`, `vecinoNombre`, `txtAtencionNombre`, `modalRolNombre`.

### 7.2 Validación Estricta de Correo Institucional
- **Expresión Regular:** `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`
- Verifica que contenga `@` y una extensión de dominio válida (`.cl`, `.com`, `.gob.cl`, `.laserena.cl`). Rechaza cadenas incompletas o sin dominio.

### 7.3 Algoritmo Chileno Módulo 11 para Validación de RUT
- Valida la relación matemática exacta entre el cuerpo numérico y el dígito verificador (DV).
- Soporta dígitos `0-9` y letra `K`.
- **Formateo automático:** Transforma entradas como `123456789` en formato oficial `12.345.678-9`.

### 7.4 Control de Espacios Vacíos y Campos Obligatorios
- Todo formulario aplica `.trim()` sobre los valores antes del envío.
- Si un campo obligatorio contiene solo espacios, se bloquea la operación y se muestra una alerta visual SweetAlert2 descriptiva.

### 7.5 Protección Anti-Inyección de Código y Anti-XSS
- Se implementó la función de desinfección `sanitizarTexto()` que convierte caracteres peligrosos en entidades HTML seguras:
  - `<` $\rightarrow$ `&lt;`
  - `>` $\rightarrow$ `&gt;`
  - `"` $\rightarrow$ `&quot;`
  - `'` $\rightarrow$ `&#x27;`
  - `/` $\rightarrow$ `&#x2F;`
- En el backend, las consultas utilizan el ORM parametrizado de Django, evitando vulnerabilidades de inyección SQL (SQLi).

---

## 8. ANÁLISIS DE BASE DE DATOS Y RECOMENDACIÓN PARA AWS ACADEMY

### 8.1 Verificación de Tablas: ¿Falta Alguna Tabla?
El diseño institucional consolidado cuenta con **19 tablas normalizadas** (cumple y excede la rúbrica de INACAP):

| # | Tabla MySQL | Módulo / Aplicación | Propósito Institucional |
|---|---|---|---|
| 1 | `delegacion` | `organization` | Registro de las 6 sedes territoriales |
| 2 | `cargo` | `organization` | Cargos municipales medibles |
| 3 | `rol` | `organization` | Catálogo de roles (RBAC) |
| 4 | `usuario` | `organization` | Cuentas institucionales y RUTs |
| 5 | `usuario_rol` | `organization` | Tabla asociativa N:M de asignación de roles |
| 6 | `periodo` | `metrics` | Períodos trimestrales de evaluación |
| 7 | `item_medicion` | `metrics` | Catálogo de indicadores y tareas evaluables |
| 8 | `meta` | `metrics` | Ponderadores y valores objetivo por cargo/período |
| 9 | `catalogo_servicio` | `activities` | Clasificación oficial de atenciones y áreas |
| 10 | `actividad` | `activities` | Registro de actividades diarias y atenciones |
| 11 | `evidencia` | `activities` | Vínculo a archivos fotográficos (`EVI-XXXX`) |
| 12 | `validacion` | `activities` | Dictamen técnico del verificador (Aprobado/Rechazado) |
| 13 | `compromiso_agenda` | `agenda` | Agenda colectiva y compromisos barriales |
| 14 | `historial_compromiso` | `agenda` | Trazabilidad de transiciones de estado |
| 15 | `caso_social` | `social` | Ficha única de atención a personas vulnerables |
| 16 | `gestion_social` | `social` | Etapas 1, 2 y 3 del caso social (RN-012) |
| 17 | `indicador_diario` | `metrics` | Snapshot diario de cumplimiento y semáforo |
| 18 | `ajuste_desempeno` | `metrics` | Felicitaciones y penalizaciones parametrizadas |
| 19 | `auditoria` | `core` | Bitácora inmutable de operaciones (CREATE, UPDATE, DELETE) |

### 8.2 Actualización en Tiempo Real
- **Inhabilitación de Usuario:** Al cambiar el estado de un funcionario a `Inactivo`, la base de datos actualiza en la misma transacción `usuario.estado = 'Inactivo'` y desactiva la cuenta de autenticación (`is_active = 0`). El usuario pierde acceso de inmediato.
- **Matriz de Permisos (Lectura / Edición / Cierre):** Las casillas de la matriz de roles persisten en tiempo real mediante `Role.permissions_data`, permitiendo restringir operaciones específicas sin reiniciar el servidor.

### 8.3 Recomendación de Base de Datos para AWS Academy Learner Lab
La elección de servicios, capacidad, costos y reglas de red se hará durante la etapa de despliegue, según los recursos disponibles en el laboratorio. La base de datos no debe exponerse públicamente por comodidad de administración. Antes de publicar: restringir el acceso de red, separar credenciales, verificar respaldos y probar la restauración.
