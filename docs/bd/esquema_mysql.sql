-- ============================================================================
-- SGR · Ilustre Municipalidad de La Serena · Esquema MySQL 8 / MariaDB 10.6+ (Etapa 3)
-- Generado con: python manage.py sqlmigrate <app> <migración> (Django 5.2.18)
-- Referencial: la forma recomendada de crear el esquema es 'python manage.py migrate'.
-- Las migraciones de datos (renumeración de códigos y permisos) se aplican con migrate.
-- ============================================================================
CREATE DATABASE IF NOT EXISTS sgr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE sgr;

-- ---- catalogos 0001 ----
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

-- ---- catalogos 0002 ----
--
-- Add field ambito to item
--
ALTER TABLE `catalogos_item` ADD COLUMN `ambito` varchar(3) DEFAULT 'GES' NOT NULL;
ALTER TABLE `catalogos_item` ALTER COLUMN `ambito` DROP DEFAULT;
--
-- Add field es_felicitacion to item
--
ALTER TABLE `catalogos_item` ADD COLUMN `es_felicitacion` bool DEFAULT 0 NOT NULL;
ALTER TABLE `catalogos_item` ALTER COLUMN `es_felicitacion` DROP DEFAULT;
--
-- Alter field codigo on delegacion
--
-- (no-op)
--
-- Alter field codigo on item
--
-- (no-op)
--
-- Alter field codigo on subatencion
--
-- (no-op)
--
-- Alter field codigo on tipoatencion
--
-- (no-op)

-- ---- cuentas 0001 ----
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

-- ---- cuentas 0002 ----
--
-- Add field cargo to usuario
--
ALTER TABLE `cuentas_usuario` ADD COLUMN `cargo` varchar(30) DEFAULT '' NOT NULL;
ALTER TABLE `cuentas_usuario` ALTER COLUMN `cargo` DROP DEFAULT;
--
-- Add field debe_cambiar_clave to usuario
--
ALTER TABLE `cuentas_usuario` ADD COLUMN `debe_cambiar_clave` bool DEFAULT 0 NOT NULL;
ALTER TABLE `cuentas_usuario` ALTER COLUMN `debe_cambiar_clave` DROP DEFAULT;
--
-- Alter field codigo on rol
--
-- (no-op)

-- ---- atenciones 0001 ----
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

-- ---- matriz 0001 ----
--
-- Create model Trimestre
--
CREATE TABLE `matriz_trimestre` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `codigo` varchar(15) NOT NULL UNIQUE, `nombre` varchar(60) NOT NULL, `inicio` date NOT NULL, `fin` date NOT NULL, `estado` varchar(12) NOT NULL, `creado` datetime(6) NOT NULL, `actualizado` datetime(6) NOT NULL);
--
-- Create model Ausencia
--
CREATE TABLE `matriz_ausencia` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `tipo` varchar(15) NOT NULL, `desde` date NOT NULL, `hasta` date NOT NULL, `motivo` varchar(200) NOT NULL, `creado` datetime(6) NOT NULL, `actualizado` datetime(6) NOT NULL, `funcionario_id` bigint NOT NULL, `registrado_por_id` bigint NOT NULL);
--
-- Create model Organizacion
--
CREATE TABLE `matriz_organizacion` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `codigo` varchar(15) NOT NULL UNIQUE, `nombre` varchar(100) NOT NULL, `activo` bool NOT NULL, `creado` datetime(6) NOT NULL, `actualizado` datetime(6) NOT NULL, `tipo` varchar(20) NOT NULL, `subtipo` varchar(80) NOT NULL, `direccion` varchar(150) NOT NULL, `comuna` varchar(60) NOT NULL, `dirigente` varchar(100) NOT NULL, `telefono` varchar(20) NOT NULL, `delegacion_id` bigint NOT NULL);
--
-- Create model MetaTrimestre
--
CREATE TABLE `matriz_metatrimestre` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `cargo` varchar(30) NOT NULL, `cantidad` integer UNSIGNED NOT NULL CHECK (`cantidad` >= 0), `item_id` bigint NOT NULL, `trimestre_id` bigint NOT NULL, CONSTRAINT `meta_unica` UNIQUE (`trimestre_id`, `item_id`, `cargo`));
--
-- Create model Actividad
--
CREATE TABLE `matriz_actividad` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `codigo` varchar(15) NOT NULL UNIQUE, `fecha` date NOT NULL, `tipo_registro` varchar(15) NOT NULL, `solicitante_tipo` varchar(15) NOT NULL, `nombre_contacto` varchar(100) NOT NULL, `telefono_contacto` varchar(20) NOT NULL, `descripcion` longtext NOT NULL, `respaldo` varchar(100) NOT NULL, `puntaje` smallint UNSIGNED NOT NULL CHECK (`puntaje` >= 0), `motivo_sin_puntaje` varchar(200) NOT NULL, `creado` datetime(6) NOT NULL, `delegacion_id` bigint NOT NULL, `funcionario_id` bigint NOT NULL, `item_id` bigint NOT NULL, `registrado_por_id` bigint NOT NULL, `organizacion_id` bigint NULL, `trimestre_id` bigint NOT NULL);
ALTER TABLE `matriz_ausencia` ADD CONSTRAINT `matriz_ausencia_funcionario_id_cfc88669_fk_cuentas_usuario_id` FOREIGN KEY (`funcionario_id`) REFERENCES `cuentas_usuario` (`id`);
ALTER TABLE `matriz_ausencia` ADD CONSTRAINT `matriz_ausencia_registrado_por_id_9648a21d_fk_cuentas_usuario_id` FOREIGN KEY (`registrado_por_id`) REFERENCES `cuentas_usuario` (`id`);
ALTER TABLE `matriz_organizacion` ADD CONSTRAINT `matriz_organizacion_delegacion_id_f20b1600_fk_catalogos` FOREIGN KEY (`delegacion_id`) REFERENCES `catalogos_delegacion` (`id`);
ALTER TABLE `matriz_metatrimestre` ADD CONSTRAINT `matriz_metatrimestre_item_id_6b14041b_fk_catalogos_item_id` FOREIGN KEY (`item_id`) REFERENCES `catalogos_item` (`id`);
ALTER TABLE `matriz_metatrimestre` ADD CONSTRAINT `matriz_metatrimestre_trimestre_id_01ca9202_fk_matriz_tr` FOREIGN KEY (`trimestre_id`) REFERENCES `matriz_trimestre` (`id`);
ALTER TABLE `matriz_actividad` ADD CONSTRAINT `matriz_actividad_delegacion_id_3d1c817b_fk_catalogos` FOREIGN KEY (`delegacion_id`) REFERENCES `catalogos_delegacion` (`id`);
ALTER TABLE `matriz_actividad` ADD CONSTRAINT `matriz_actividad_funcionario_id_106485a2_fk_cuentas_usuario_id` FOREIGN KEY (`funcionario_id`) REFERENCES `cuentas_usuario` (`id`);
ALTER TABLE `matriz_actividad` ADD CONSTRAINT `matriz_actividad_item_id_ebfe724d_fk_catalogos_item_id` FOREIGN KEY (`item_id`) REFERENCES `catalogos_item` (`id`);
ALTER TABLE `matriz_actividad` ADD CONSTRAINT `matriz_actividad_registrado_por_id_662bf162_fk_cuentas_u` FOREIGN KEY (`registrado_por_id`) REFERENCES `cuentas_usuario` (`id`);
ALTER TABLE `matriz_actividad` ADD CONSTRAINT `matriz_actividad_organizacion_id_cb2856f8_fk_matriz_or` FOREIGN KEY (`organizacion_id`) REFERENCES `matriz_organizacion` (`id`);
ALTER TABLE `matriz_actividad` ADD CONSTRAINT `matriz_actividad_trimestre_id_08468067_fk_matriz_trimestre_id` FOREIGN KEY (`trimestre_id`) REFERENCES `matriz_trimestre` (`id`);
CREATE INDEX `matriz_acti_funcion_c42a40_idx` ON `matriz_actividad` (`funcionario_id`, `fecha`);
CREATE INDEX `matriz_acti_trimest_881b80_idx` ON `matriz_actividad` (`trimestre_id`, `item_id`);

-- ---- tubo 0001 ----
--
-- Create model AreaApoyo
--
CREATE TABLE `tubo_areaapoyo` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `codigo` varchar(15) NOT NULL UNIQUE, `nombre` varchar(100) NOT NULL, `activo` bool NOT NULL, `creado` datetime(6) NOT NULL, `actualizado` datetime(6) NOT NULL, `descripcion` varchar(200) NOT NULL);
--
-- Create model Compromiso
--
CREATE TABLE `tubo_compromiso` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `codigo` varchar(15) NOT NULL UNIQUE, `titulo` varchar(150) NOT NULL, `descripcion` longtext NOT NULL, `solicitante` varchar(120) NOT NULL, `estado` varchar(12) NOT NULL, `creado` datetime(6) NOT NULL, `actualizado` datetime(6) NOT NULL, `realizado_en` datetime(6) NULL, `actividad_id` bigint NULL, `area_apoyo_id` bigint NULL, `atencion_id` bigint NULL, `creado_por_id` bigint NOT NULL, `delegacion_id` bigint NOT NULL, `responsable_id` bigint NOT NULL);
--
-- Create model Evidencia
--
CREATE TABLE `tubo_evidencia` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `foto` varchar(100) NOT NULL, `descripcion` varchar(200) NOT NULL, `origen` varchar(3) NOT NULL, `estado` varchar(10) NOT NULL, `subida_en` datetime(6) NOT NULL, `revisada_en` datetime(6) NULL, `comentario_revision` varchar(300) NOT NULL, `compromiso_id` bigint NOT NULL, `revisada_por_id` bigint NULL, `subida_por_id` bigint NOT NULL);
--
-- Create model HistorialCompromiso
--
CREATE TABLE `tubo_historialcompromiso` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `estado_anterior` varchar(12) NOT NULL, `estado_nuevo` varchar(12) NOT NULL, `comentario` varchar(300) NOT NULL, `fecha` datetime(6) NOT NULL, `compromiso_id` bigint NOT NULL, `usuario_id` bigint NOT NULL);
--
-- Create model TokenApi
--
CREATE TABLE `tubo_tokenapi` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `clave_hash` varchar(64) NOT NULL UNIQUE, `creado` datetime(6) NOT NULL, `expira` datetime(6) NOT NULL, `ultimo_uso` datetime(6) NULL, `usuario_id` bigint NOT NULL);
ALTER TABLE `tubo_compromiso` ADD CONSTRAINT `tubo_compromiso_actividad_id_4f74804c_fk_matriz_actividad_id` FOREIGN KEY (`actividad_id`) REFERENCES `matriz_actividad` (`id`);
ALTER TABLE `tubo_compromiso` ADD CONSTRAINT `tubo_compromiso_area_apoyo_id_71f3708e_fk_tubo_areaapoyo_id` FOREIGN KEY (`area_apoyo_id`) REFERENCES `tubo_areaapoyo` (`id`);
ALTER TABLE `tubo_compromiso` ADD CONSTRAINT `tubo_compromiso_atencion_id_7d8fdc2e_fk_atenciones_atencion_id` FOREIGN KEY (`atencion_id`) REFERENCES `atenciones_atencion` (`id`);
ALTER TABLE `tubo_compromiso` ADD CONSTRAINT `tubo_compromiso_creado_por_id_e203ca00_fk_cuentas_usuario_id` FOREIGN KEY (`creado_por_id`) REFERENCES `cuentas_usuario` (`id`);
ALTER TABLE `tubo_compromiso` ADD CONSTRAINT `tubo_compromiso_delegacion_id_2a11025a_fk_catalogos` FOREIGN KEY (`delegacion_id`) REFERENCES `catalogos_delegacion` (`id`);
ALTER TABLE `tubo_compromiso` ADD CONSTRAINT `tubo_compromiso_responsable_id_d80e2a84_fk_cuentas_usuario_id` FOREIGN KEY (`responsable_id`) REFERENCES `cuentas_usuario` (`id`);
ALTER TABLE `tubo_evidencia` ADD CONSTRAINT `tubo_evidencia_compromiso_id_44fa2e2a_fk_tubo_compromiso_id` FOREIGN KEY (`compromiso_id`) REFERENCES `tubo_compromiso` (`id`);
ALTER TABLE `tubo_evidencia` ADD CONSTRAINT `tubo_evidencia_revisada_por_id_dddaa93a_fk_cuentas_usuario_id` FOREIGN KEY (`revisada_por_id`) REFERENCES `cuentas_usuario` (`id`);
ALTER TABLE `tubo_evidencia` ADD CONSTRAINT `tubo_evidencia_subida_por_id_78710f0d_fk_cuentas_usuario_id` FOREIGN KEY (`subida_por_id`) REFERENCES `cuentas_usuario` (`id`);
ALTER TABLE `tubo_historialcompromiso` ADD CONSTRAINT `tubo_historialcompro_compromiso_id_2b632195_fk_tubo_comp` FOREIGN KEY (`compromiso_id`) REFERENCES `tubo_compromiso` (`id`);
ALTER TABLE `tubo_historialcompromiso` ADD CONSTRAINT `tubo_historialcompro_usuario_id_fdb6d588_fk_cuentas_u` FOREIGN KEY (`usuario_id`) REFERENCES `cuentas_usuario` (`id`);
ALTER TABLE `tubo_tokenapi` ADD CONSTRAINT `tubo_tokenapi_usuario_id_0bbd417a_fk_cuentas_usuario_id` FOREIGN KEY (`usuario_id`) REFERENCES `cuentas_usuario` (`id`);

