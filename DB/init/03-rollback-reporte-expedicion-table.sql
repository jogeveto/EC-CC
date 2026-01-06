-- =============================================
-- Script: 04-rollback-reporte-expedicion-table.sql
-- Descripción: Rollback de la creación de la tabla reporte_expedicion
-- NOTA: Este script NO incluye rollback del schema (según regla de oro)
-- Fecha: 2025-01-XX
-- =============================================

-- Configuración inicial
SET NOCOUNT ON;
GO

USE RPA_Automatizacion;
GO

PRINT '============================================='
PRINT 'Iniciando rollback de tabla reporte_expedicion...'
PRINT '============================================='
GO

-- =============================================
-- Eliminar tabla reporte_expedicion
-- =============================================
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'reporte_expedicion' AND schema_id = SCHEMA_ID('ExpedicionCopiasDbo'))
BEGIN
    DROP TABLE [ExpedicionCopiasDbo].[reporte_expedicion];
    PRINT 'Tabla ExpedicionCopiasDbo.reporte_expedicion eliminada exitosamente.';
END
ELSE
BEGIN
    PRINT 'La tabla ExpedicionCopiasDbo.reporte_expedicion no existe.';
END
GO

PRINT '============================================='
PRINT 'Rollback de tabla reporte_expedicion completado.'
PRINT '============================================='
GO
