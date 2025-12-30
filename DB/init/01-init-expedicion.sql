-- =============================================
-- Script: 01-init-expedicion.sql
-- Descripción: Crea la base de datos RPA_Automatizacion y el esquema ExpedicionCopiasDbo
-- Fecha: 2025-01-XX
-- =============================================

-- Configuración inicial
SET NOCOUNT ON;
GO

PRINT '============================================='
PRINT 'Iniciando creación de base de datos...'
PRINT '============================================='
GO

-- =============================================
-- Crear base de datos RPA_Automatizacion
-- Production uses a single database with multiple schemas
-- =============================================
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'RPA_Automatizacion')
BEGIN
    CREATE DATABASE RPA_Automatizacion
    COLLATE Modern_Spanish_CI_AS;
    PRINT 'Base de datos RPA_Automatizacion creada exitosamente.';
END
ELSE
BEGIN
    PRINT 'La base de datos RPA_Automatizacion ya existe.';
END
GO

USE RPA_Automatizacion;
GO

-- =============================================
-- Crear esquema ExpedicionCopiasDbo
-- =============================================
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'ExpedicionCopiasDbo')
BEGIN
    EXEC('CREATE SCHEMA ExpedicionCopiasDbo');
    PRINT 'Esquema ExpedicionCopiasDbo creado exitosamente.';
END
ELSE
BEGIN
    PRINT 'El esquema ExpedicionCopiasDbo ya existe.';
END
GO

PRINT '============================================='
PRINT 'Creación de base de datos y esquema completada.'
PRINT '============================================='
GO

