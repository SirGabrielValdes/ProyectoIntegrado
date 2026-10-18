-- Crea la base y el usuario del SGR en MySQL/MariaDB local de la EC2.
-- Reemplace CAMBIAR_CLAVE por la misma clave definida en DB_PASSWORD del archivo .env.
-- Uso: sudo mysql < deploy/crear_bd_local.sql
CREATE DATABASE IF NOT EXISTS sgr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'sgr'@'localhost' IDENTIFIED BY 'CAMBIAR_CLAVE';
GRANT ALL PRIVILEGES ON sgr.* TO 'sgr'@'localhost';
FLUSH PRIVILEGES;
