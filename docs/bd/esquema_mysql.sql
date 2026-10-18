-- ============================================================================
-- SGR · Ilustre Municipalidad de La Serena · Esquema MySQL 8 / MariaDB 10.6+
-- Generado con: python manage.py sqlmigrate <app> 0001 (Django 5.2.18)
-- Referencial: la forma recomendada de crear el esquema es 'python manage.py migrate'.
-- ============================================================================
CREATE DATABASE IF NOT EXISTS sgr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE sgr;

-- ---- catalogos ----
--
-- Create model Delegacion
--
CREATE TABLE `catalogos_delegacion` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `codigo` varchar(15) NOT NULL UNIQUE, `nombre` varchar(100) NOT NULL, `activo` bool NOT NULL, `creado` datetime(6) NOT NULL, `actualizado` datetime(6) NOT NULL, `direccion` varchar(150) NOT NULL, `comuna` varchar(60) NOT NULL);
--
-- Create model Item
--
CREATE TABLE `catalogos_item` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `codigo` varchar(15) NOT NULL UNIQUE, `nombre` varchar(100) NOT NULL, `activo` bool NOT NULL, `creado` datetime(6) NOT NULL, `actualizado` datetime(6) NOT NULL, `descripcion` longtext NOT NULL);
--
-- Create model TipoAtencion
--
CREATE TABLE `catalogos_tipoatencion` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `codigo` varchar(15) NOT NULL UNIQUE, `nombre` varchar(100) NOT NULL, `activo` bool NOT NULL, `creado` datetime(6) NOT NULL, `actualizado` datetime(6) NOT NULL, `descripcion` longtext NOT NULL);
--
-- Create model SubAtencion
--
CREATE TABLE `catalogos_subatencion` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `codigo` varchar(15) NOT NULL UNIQUE, `nombre` varchar(100) NOT NULL, `activo` bool NOT NULL, `creado` datetime(6) NOT NULL, `actualizado` datetime(6) NOT NULL, `tipo_id` bigint NOT NULL, CONSTRAINT `subatencion_nombre_por_tipo` UNIQUE (`tipo_id`, `nombre`));
ALTER TABLE `catalogos_subatencion` ADD CONSTRAINT `catalogos_subatencio_tipo_id_65f80e79_fk_catalogos` FOREIGN KEY (`tipo_id`) REFERENCES `catalogos_tipoatencion` (`id`);

-- ---- cuentas ----
--
-- Create model Rol
--
CREATE TABLE `cuentas_rol` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `codigo` varchar(15) NOT NULL UNIQUE, `nombre` varchar(60) NOT NULL UNIQUE, `descripcion` longtext NOT NULL, `permisos` json NOT NULL, `alcance` varchar(12) NOT NULL, `activo` bool NOT NULL, `es_sistema` bool NOT NULL, `creado` datetime(6) NOT NULL, `actualizado` datetime(6) NOT NULL);
--
-- Create model Usuario
--
CREATE TABLE `cuentas_usuario` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `password` varchar(128) NOT NULL, `last_login` datetime(6) NULL, `username` varchar(30) NOT NULL UNIQUE, `correo` varchar(120) NOT NULL UNIQUE, `nombre` varchar(100) NOT NULL, `is_active` bool NOT NULL, `creado` datetime(6) NOT NULL, `actualizado` datetime(6) NOT NULL, `rol_id` bigint NOT NULL);
CREATE TABLE `cuentas_usuario_delegaciones` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `usuario_id` bigint NOT NULL, `delegacion_id` bigint NOT NULL);
--
-- Create model SolicitudRecuperacion
--
CREATE TABLE `cuentas_solicitudrecuperacion` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `token` varchar(64) NOT NULL UNIQUE, `codigo_hash` varchar(128) NOT NULL, `creado` datetime(6) NOT NULL, `expira` datetime(6) NOT NULL, `ultimo_envio` datetime(6) NOT NULL, `intentos` smallint UNSIGNED NOT NULL CHECK (`intentos` >= 0), `reenvios` smallint UNSIGNED NOT NULL CHECK (`reenvios` >= 0), `verificado_en` datetime(6) NULL, `usado_en` datetime(6) NULL, `anulado` bool NOT NULL, `usuario_id` bigint NOT NULL);
ALTER TABLE `cuentas_usuario` ADD CONSTRAINT `cuentas_usuario_rol_id_2fc1a534_fk_cuentas_rol_id` FOREIGN KEY (`rol_id`) REFERENCES `cuentas_rol` (`id`);
ALTER TABLE `cuentas_usuario_delegaciones` ADD CONSTRAINT `cuentas_usuario_delegaci_usuario_id_delegacion_id_d7687d2f_uniq` UNIQUE (`usuario_id`, `delegacion_id`);
ALTER TABLE `cuentas_usuario_delegaciones` ADD CONSTRAINT `cuentas_usuario_dele_usuario_id_801a885f_fk_cuentas_u` FOREIGN KEY (`usuario_id`) REFERENCES `cuentas_usuario` (`id`);
ALTER TABLE `cuentas_usuario_delegaciones` ADD CONSTRAINT `cuentas_usuario_dele_delegacion_id_ac5f3da3_fk_catalogos` FOREIGN KEY (`delegacion_id`) REFERENCES `catalogos_delegacion` (`id`);
ALTER TABLE `cuentas_solicitudrecuperacion` ADD CONSTRAINT `cuentas_solicitudrec_usuario_id_3e81cb95_fk_cuentas_u` FOREIGN KEY (`usuario_id`) REFERENCES `cuentas_usuario` (`id`);

-- ---- atenciones ----
--
-- Create model Vecino
--
CREATE TABLE `atenciones_vecino` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `rut` varchar(12) NOT NULL UNIQUE, `nombre` varchar(100) NOT NULL, `telefono` varchar(20) NOT NULL, `correo` varchar(120) NOT NULL, `direccion` varchar(150) NOT NULL, `creado` datetime(6) NOT NULL);
--
-- Create model Atencion
--
CREATE TABLE `atenciones_atencion` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `descripcion` longtext NOT NULL, `fecha_registro` datetime(6) NOT NULL, `token_envio` varchar(64) NULL UNIQUE, `delegacion_id` bigint NOT NULL, `responsable_id` bigint NOT NULL, `subatencion_id` bigint NOT NULL, `tipo_id` bigint NOT NULL, `vecino_id` bigint NOT NULL);
ALTER TABLE `atenciones_atencion` ADD CONSTRAINT `atenciones_atencion_delegacion_id_58e20d54_fk_catalogos` FOREIGN KEY (`delegacion_id`) REFERENCES `catalogos_delegacion` (`id`);
ALTER TABLE `atenciones_atencion` ADD CONSTRAINT `atenciones_atencion_responsable_id_6175a950_fk_cuentas_u` FOREIGN KEY (`responsable_id`) REFERENCES `cuentas_usuario` (`id`);
ALTER TABLE `atenciones_atencion` ADD CONSTRAINT `atenciones_atencion_subatencion_id_65e29858_fk_catalogos` FOREIGN KEY (`subatencion_id`) REFERENCES `catalogos_subatencion` (`id`);
ALTER TABLE `atenciones_atencion` ADD CONSTRAINT `atenciones_atencion_tipo_id_02b07ba8_fk_catalogos` FOREIGN KEY (`tipo_id`) REFERENCES `catalogos_tipoatencion` (`id`);
ALTER TABLE `atenciones_atencion` ADD CONSTRAINT `atenciones_atencion_vecino_id_54acdb45_fk_atenciones_vecino_id` FOREIGN KEY (`vecino_id`) REFERENCES `atenciones_vecino` (`id`);

