-- =============================================
-- Script: 03-create-reporte-expedicion-table.sql
-- Descripción: Crea la tabla reporte_expedicion en el esquema ExpedicionCopiasDbo
-- Fecha: 2025-01-XX
-- =============================================

-- Configuración inicial
SET NOCOUNT ON;
GO

USE RPA_Automatizacion;
GO

PRINT '============================================='
PRINT 'Iniciando creación de tabla reporte_expedicion...'
PRINT '============================================='
GO

-- =============================================
-- Validar que el esquema ExpedicionCopiasDbo existe
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

-- =============================================
-- Crear tabla reporte_expedicion
-- =============================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'reporte_expedicion' AND schema_id = SCHEMA_ID('ExpedicionCopiasDbo'))
BEGIN
    CREATE TABLE [ExpedicionCopiasDbo].[reporte_expedicion] (
        [id] INT IDENTITY(1,1) NOT NULL,
        [codigo_asistente] NVARCHAR(100) NULL,
        [codigo_bot] NVARCHAR(100) NULL,
        [usuario_red_bot_runner] NVARCHAR(100) NULL,
        [nombre_estacion_bot_runner] NVARCHAR(100) NULL,
        [id_proceso] INT NULL,
        [no_radicado] NVARCHAR(500) NULL,
        [matriculas] NVARCHAR(1000) NULL,
        [estado_proceso] NVARCHAR(50) NULL,
        [observacion] NVARCHAR(MAX) NULL,
        [fecha_inicio_ejecucion] DATE NULL,
        [hora_inicio_ejecucion] TIME NULL,
        [fecha_fin_ejecucion] DATE NULL,
        [hora_fin_ejecucion] TIME NULL,
        [fecha_creacion] DATETIME NOT NULL DEFAULT GETDATE(),
        [fecha_actualizacion] DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT [PK_reporte_expedicion] PRIMARY KEY CLUSTERED ([id] ASC)
    );
    
    PRINT 'Tabla ExpedicionCopiasDbo.reporte_expedicion creada exitosamente.';
END
ELSE
BEGIN
    PRINT 'La tabla ExpedicionCopiasDbo.reporte_expedicion ya existe.';
END
GO

PRINT '============================================='
PRINT 'Creación de tabla reporte_expedicion completada.'
PRINT '============================================='
GO
