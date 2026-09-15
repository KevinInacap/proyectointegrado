-- =============================================================================
-- SISTEMA DE GESTIÓN DE RESULTADOS (SGR) - ILUSTRE MUNICIPALIDAD DE LA SERENA
-- SCRIPT DE CREACIÓN DE BASE DE DATOS MYSQL CONFORME A DER INSTITUCIONAL
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `sgr_laserena_db` 
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_spanish_ci;

USE `sgr_laserena_db`;

-- Desactivar temporalmente verificación de claves foráneas para creación limpia
SET FOREIGN_KEY_CHECKS = 0;

-- 1. TABLA: delegacion (App: organization)
DROP TABLE IF EXISTS `delegacion`;
CREATE TABLE `delegacion` (
    `id_delegacion` INT AUTO_INCREMENT PRIMARY KEY,
    `nombre` VARCHAR(100) NOT NULL UNIQUE,
    `ambito` VARCHAR(100) NOT NULL,
    `estado` ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    INDEX `idx_delegacion_nombre` (`nombre`),
    INDEX `idx_delegacion_estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 2. TABLA: cargo (App: organization)
DROP TABLE IF EXISTS `cargo`;
CREATE TABLE `cargo` (
    `id_cargo` INT AUTO_INCREMENT PRIMARY KEY,
    `nombre` VARCHAR(100) NOT NULL UNIQUE,
    `descripcion` TEXT NULL,
    `estado` ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    INDEX `idx_cargo_nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 3. TABLA: rol (App: organization)
DROP TABLE IF EXISTS `rol`;
CREATE TABLE `rol` (
    `id_rol` INT AUTO_INCREMENT PRIMARY KEY,
    `nombre_rol` VARCHAR(50) NOT NULL UNIQUE,
    `descripcion` VARCHAR(255) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 4. TABLA: usuario (App: organization)
DROP TABLE IF EXISTS `usuario`;
CREATE TABLE `usuario` (
    `id_usuario` INT AUTO_INCREMENT PRIMARY KEY,
    `rut` VARCHAR(12) NOT NULL UNIQUE,
    `nombre_completo` VARCHAR(150) NOT NULL,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `id_delegacion` INT NULL,
    `id_cargo` INT NULL,
    `estado` ENUM('Activo', 'Inactivo', 'Bloqueado') DEFAULT 'Activo',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    INDEX `idx_usuario_rut` (`rut`),
    INDEX `idx_usuario_email` (`email`),
    CONSTRAINT `fk_usuario_delegacion` FOREIGN KEY (`id_delegacion`) 
        REFERENCES `delegacion` (`id_delegacion`) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT `fk_usuario_cargo` FOREIGN KEY (`id_cargo`) 
        REFERENCES `cargo` (`id_cargo`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 5. TABLA ASOCIATIVA: usuario_rol (App: organization)
DROP TABLE IF EXISTS `usuario_rol`;
CREATE TABLE `usuario_rol` (
    `id_usuario` INT NOT NULL,
    `id_rol` INT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (`id_usuario`, `id_rol`),
    CONSTRAINT `fk_usuariorol_usuario` FOREIGN KEY (`id_usuario`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_usuariorol_rol` FOREIGN KEY (`id_rol`) 
        REFERENCES `rol` (`id_rol`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 6. TABLA: periodo (App: metrics)
DROP TABLE IF EXISTS `periodo`;
CREATE TABLE `periodo` (
    `id_periodo` INT AUTO_INCREMENT PRIMARY KEY,
    `nombre` VARCHAR(50) NOT NULL UNIQUE,
    `fecha_inicio` DATE NOT NULL,
    `fecha_termino` DATE NOT NULL,
    `dias_computables` INT NOT NULL DEFAULT 90,
    `umbral_minimo` DECIMAL(5,2) NOT NULL DEFAULT 80.00,
    `tope_cumplimiento` DECIMAL(5,2) NOT NULL DEFAULT 150.00,
    `estado` ENUM('Planificado', 'Abierto', 'Cerrado') DEFAULT 'Abierto',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    INDEX `idx_periodo_fechas` (`fecha_inicio`, `fecha_termino`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 7. TABLA: item_medicion (App: metrics)
DROP TABLE IF EXISTS `item_medicion`;
CREATE TABLE `item_medicion` (
    `id_item` INT AUTO_INCREMENT PRIMARY KEY,
    `nombre` VARCHAR(120) NOT NULL UNIQUE,
    `descripcion` TEXT NULL,
    `tipo` ENUM('Cuantitativo', 'Porcentual') DEFAULT 'Cuantitativo',
    `estado` ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 8. TABLA: meta (App: metrics)
DROP TABLE IF EXISTS `meta`;
CREATE TABLE `meta` (
    `id_meta` INT AUTO_INCREMENT PRIMARY KEY,
    `id_periodo` INT NOT NULL,
    `id_cargo` INT NOT NULL,
    `id_item` INT NOT NULL,
    `valor_objetivo` DECIMAL(10,2) NOT NULL,
    `unidad_medida` VARCHAR(30) NOT NULL DEFAULT 'Atenciones',
    `ponderacion` DECIMAL(5,2) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    UNIQUE KEY `uk_periodo_cargo_item` (`id_periodo`, `id_cargo`, `id_item`),
    CONSTRAINT `fk_meta_periodo` FOREIGN KEY (`id_periodo`) 
        REFERENCES `periodo` (`id_periodo`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_meta_cargo` FOREIGN KEY (`id_cargo`) 
        REFERENCES `cargo` (`id_cargo`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_meta_item` FOREIGN KEY (`id_item`) 
        REFERENCES `item_medicion` (`id_item`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 9. TABLA: catalogo_servicio (App: activities)
DROP TABLE IF EXISTS `catalogo_servicio`;
CREATE TABLE `catalogo_servicio` (
    `id_catalogo` INT AUTO_INCREMENT PRIMARY KEY,
    `area` VARCHAR(50) NOT NULL,
    `servicio` VARCHAR(100) NOT NULL,
    `tipo_atencion` VARCHAR(100) NOT NULL,
    `subtipo_atencion` VARCHAR(100) NULL,
    `estado` ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    INDEX `idx_catalogo_area` (`area`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 10. TABLA: actividad (App: activities)
DROP TABLE IF EXISTS `actividad`;
CREATE TABLE `actividad` (
    `id_actividad` INT AUTO_INCREMENT PRIMARY KEY,
    `codigo_actividad` VARCHAR(50) NOT NULL UNIQUE,
    `id_usuario` INT NULL,
    `id_delegacion` INT NULL,
    `id_periodo` INT NULL,
    `id_item` INT NULL,
    `id_catalogo` INT NULL,
    `fecha_actividad` DATE NOT NULL,
    `descripcion_problema` TEXT NOT NULL,
    `accion_ejecutada` TEXT NOT NULL,
    `contacto_nombre` VARCHAR(150) NULL,
    `contacto_telefono` VARCHAR(20) NULL,
    `es_agenda_colectiva` TINYINT(1) DEFAULT 0,
    `estado_validacion` ENUM('Pending', 'Approved', 'Rejected', 'Requires correction') DEFAULT 'Pending',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    INDEX `idx_actividad_codigo` (`codigo_actividad`),
    INDEX `idx_actividad_fecha` (`fecha_actividad`),
    CONSTRAINT `fk_actividad_usuario` FOREIGN KEY (`id_usuario`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT `fk_actividad_delegacion` FOREIGN KEY (`id_delegacion`) 
        REFERENCES `delegacion` (`id_delegacion`) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT `fk_actividad_periodo` FOREIGN KEY (`id_periodo`) 
        REFERENCES `periodo` (`id_periodo`) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT `fk_actividad_item` FOREIGN KEY (`id_item`) 
        REFERENCES `item_medicion` (`id_item`) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT `fk_actividad_catalogo` FOREIGN KEY (`id_catalogo`) 
        REFERENCES `catalogo_servicio` (`id_catalogo`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 11. TABLA: evidencia (App: activities)
DROP TABLE IF EXISTS `evidencia`;
CREATE TABLE `evidencia` (
    `id_evidencia` INT AUTO_INCREMENT PRIMARY KEY,
    `id_actividad` INT NOT NULL,
    `codigo_evidencia` VARCHAR(50) NOT NULL UNIQUE,
    `ruta_archivo` VARCHAR(255) NOT NULL,
    `nombre_archivo` VARCHAR(150) NOT NULL,
    `subido_por` INT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    INDEX `idx_evidencia_codigo` (`codigo_evidencia`),
    CONSTRAINT `fk_evidencia_actividad` FOREIGN KEY (`id_actividad`) 
        REFERENCES `actividad` (`id_actividad`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_evidencia_subidopor` FOREIGN KEY (`subido_por`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 12. TABLA: validacion (App: activities)
DROP TABLE IF EXISTS `validacion`;
CREATE TABLE `validacion` (
    `id_validacion` INT AUTO_INCREMENT PRIMARY KEY,
    `id_actividad` INT NOT NULL,
    `id_verificador` INT NULL,
    `decision` ENUM('Approved', 'Rejected', 'Requires correction') NOT NULL,
    `observaciones` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT `fk_validacion_actividad` FOREIGN KEY (`id_actividad`) 
        REFERENCES `actividad` (`id_actividad`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_validacion_verificador` FOREIGN KEY (`id_verificador`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 13. TABLA: compromiso_agenda (App: agenda)
DROP TABLE IF EXISTS `compromiso_agenda`;
CREATE TABLE `compromiso_agenda` (
    `id_compromiso` INT AUTO_INCREMENT PRIMARY KEY,
    `id_actividad_origen` INT NULL,
    `id_delegacion` INT NOT NULL,
    `id_responsable` INT NULL,
    `origen_solicitud` ENUM('Interno', 'Externo') DEFAULT 'Externo',
    `solicitante` VARCHAR(150) NOT NULL,
    `territorio` VARCHAR(100) NOT NULL,
    `area_apoyo` VARCHAR(100) NULL,
    `descripcion` TEXT NOT NULL,
    `fecha_comprometida` DATE NOT NULL,
    `estado` ENUM('Ingresado', 'Pendiente', 'En proceso', 'Realizado') DEFAULT 'Ingresado',
    `observaciones` TEXT NULL,
    `fecha_cierre` DATE NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    INDEX `idx_compromiso_fecha` (`fecha_comprometida`),
    INDEX `idx_compromiso_estado` (`estado`),
    CONSTRAINT `fk_compromiso_actividad` FOREIGN KEY (`id_actividad_origen`) 
        REFERENCES `actividad` (`id_actividad`) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT `fk_compromiso_delegacion` FOREIGN KEY (`id_delegacion`) 
        REFERENCES `delegacion` (`id_delegacion`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_compromiso_responsable` FOREIGN KEY (`id_responsable`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 14. TABLA: historial_compromiso (App: agenda)
DROP TABLE IF EXISTS `historial_compromiso`;
CREATE TABLE `historial_compromiso` (
    `id_historial` INT AUTO_INCREMENT PRIMARY KEY,
    `id_compromiso` INT NOT NULL,
    `estado_anterior` VARCHAR(30) NOT NULL,
    `nuevo_estado` VARCHAR(30) NOT NULL,
    `id_autor` INT NULL,
    `observaciones` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT `fk_historial_compromiso` FOREIGN KEY (`id_compromiso`) 
        REFERENCES `compromiso_agenda` (`id_compromiso`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_historial_autor` FOREIGN KEY (`id_autor`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 15. TABLA: caso_social (App: social)
DROP TABLE IF EXISTS `caso_social`;
CREATE TABLE `caso_social` (
    `id_caso` INT AUTO_INCREMENT PRIMARY KEY,
    `rut_usuario` VARCHAR(12) NOT NULL,
    `nombre_usuario` VARCHAR(150) NOT NULL,
    `telefono_contacto` VARCHAR(20) NULL,
    `id_delegacion` INT NOT NULL,
    `fecha_ingreso` DATE NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    INDEX `idx_casosocial_rut` (`rut_usuario`),
    CONSTRAINT `fk_casosocial_delegacion` FOREIGN KEY (`id_delegacion`) 
        REFERENCES `delegacion` (`id_delegacion`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 16. TABLA: gestion_social (App: social)
DROP TABLE IF EXISTS `gestion_social`;
CREATE TABLE `gestion_social` (
    `id_gestion` INT AUTO_INCREMENT PRIMARY KEY,
    `id_caso` INT NOT NULL,
    `etapa` TINYINT NOT NULL COMMENT 'Gestión 1, 2 o 3 según regla RN-012',
    `id_catalogo` INT NULL,
    `tipo_gestion` VARCHAR(100) NOT NULL,
    `fecha_gestion` DATE NOT NULL,
    `resultado` TEXT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    UNIQUE KEY `uk_caso_etapa` (`id_caso`, `etapa`),
    CONSTRAINT `fk_gestionsocial_caso` FOREIGN KEY (`id_caso`) 
        REFERENCES `caso_social` (`id_caso`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_gestionsocial_catalogo` FOREIGN KEY (`id_catalogo`) 
        REFERENCES `catalogo_servicio` (`id_catalogo`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 17. TABLA: indicador_diario (App: metrics)
DROP TABLE IF EXISTS `indicador_diario`;
CREATE TABLE `indicador_diario` (
    `id_indicador` INT AUTO_INCREMENT PRIMARY KEY,
    `id_usuario` INT NOT NULL,
    `id_periodo` INT NOT NULL,
    `fecha_calculo` DATE NOT NULL,
    `avance_acumulado` INT NOT NULL DEFAULT 0,
    `cumplimiento_porcentaje` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    `cumplimiento_ponderado` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    `meta_esperada_dia` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    `semaforo` ENUM('Verde', 'Ámbar', 'Rojo') NOT NULL DEFAULT 'Ámbar',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    UNIQUE KEY `uk_usuario_periodo_fecha` (`id_usuario`, `id_periodo`, `fecha_calculo`),
    CONSTRAINT `fk_indicador_usuario` FOREIGN KEY (`id_usuario`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_indicador_periodo` FOREIGN KEY (`id_periodo`) 
        REFERENCES `periodo` (`id_periodo`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 18. TABLA: ajuste_desempeno (App: metrics)
DROP TABLE IF EXISTS `ajuste_desempeno`;
CREATE TABLE `ajuste_desempeno` (
    `id_ajuste` INT AUTO_INCREMENT PRIMARY KEY,
    `id_usuario` INT NOT NULL,
    `id_periodo` INT NOT NULL,
    `tipo` ENUM('Felicitacion', 'Reclamo', 'Penalizacion') NOT NULL,
    `valor_porcentaje` DECIMAL(5,2) NOT NULL,
    `motivo` TEXT NOT NULL,
    `registrado_por` INT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT `fk_ajuste_usuario` FOREIGN KEY (`id_usuario`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_ajuste_periodo` FOREIGN KEY (`id_periodo`) 
        REFERENCES `periodo` (`id_periodo`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_ajuste_registrado_por` FOREIGN KEY (`registrado_por`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- 19. TABLA: auditoria (App: core)
DROP TABLE IF EXISTS `auditoria`;
CREATE TABLE `auditoria` (
    `id_auditoria` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `id_usuario` INT NULL,
    `tabla_afectada` VARCHAR(50) NOT NULL,
    `id_registro_afectado` VARCHAR(50) NOT NULL,
    `accion` ENUM('CREATE', 'UPDATE', 'DELETE', 'VALIDATE', 'LOGIN') NOT NULL,
    `valor_anterior` JSON NULL,
    `valor_nuevo` JSON NULL,
    `ip_origen` VARCHAR(45) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    INDEX `idx_auditoria_tabla` (`tabla_afectada`),
    INDEX `idx_auditoria_usuario` (`id_usuario`),
    CONSTRAINT `fk_auditoria_usuario` FOREIGN KEY (`id_usuario`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- Reactivar verificación de claves foráneas
SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- INSERCIÓN DE DATOS SEMILLA (DATOS REALES MUNICIPALES PARA DEMOSTRACIÓN)
-- =============================================================================

INSERT INTO `delegacion` (`id_delegacion`, `nombre`, `ambito`, `estado`) VALUES
(1, 'Avenida del Mar', 'Borde costero, turismo, residencial y servicios', 'Activo'),
(2, 'Centro', 'Centro histórico, administrativo, comercial y patrimonial', 'Activo'),
(3, 'La Antena - La Florida', 'Sector urbano oriental y barrios asociados', 'Activo'),
(4, 'Las Compañías', 'Sector urbano norte de alta densidad y fuerte identidad territorial', 'Activo'),
(5, 'La Pampa', 'Sector urbano sur y áreas residenciales asociadas', 'Activo'),
(6, 'Rural', 'Localidades y comunidades rurales dispersas', 'Activo');

INSERT INTO `cargo` (`id_cargo`, `nombre`, `descripcion`, `estado`) VALUES
(1, 'Coordinador General SGR', 'Supervisión transversal de indicadores y metas comunales', 'Activo'),
(2, 'Delegado Municipal', 'Jefatura territorial a cargo de la gestión de la delegación', 'Activo'),
(3, 'Gestor Territorial', 'Atención directa en terreno, registro de actividades y requerimientos', 'Activo'),
(4, 'Verificador Técnico', 'Auditoría y validación documental de evidencias', 'Activo'),
(5, 'Asistente Social Territorial', 'Atención de casos sociales, subsidios y Registro Social de Hogares', 'Activo');

INSERT INTO `rol` (`id_rol`, `nombre_rol`, `descripcion`) VALUES
(1, 'Administrador', 'Configuración integral, parámetros, usuarios y auditoría'),
(2, 'Coordinador', 'Supervisión institucional, metas y reportes consolidados'),
(3, 'Delegado', 'Jefatura de delegación y gestión del tubo de trabajo colectivo'),
(4, 'Funcionario', 'Registro operativo de actividades, atenciones y evidencias'),
(5, 'Verificador', 'Revisión técnica, aprobación o rechazo de evidencias');

INSERT INTO `periodo` (`id_periodo`, `nombre`, `fecha_inicio`, `fecha_termino`, `dias_computables`, `umbral_minimo`, `tope_cumplimiento`, `estado`) VALUES
(1, 'Segundo Semestre 2026', '2026-07-01', '2026-12-31', 91, 80.00, 150.00, 'Abierto');
