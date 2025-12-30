-- =============================================
-- Script: 02-create-dynamics-crm-pqrs-table.sql
-- Descripción: Crea la tabla expedicion_copias_pqrs para almacenar datos de PQRS de Dynamics CRM
-- Fecha: 2025-01-XX
-- =============================================

USE RPA_Automatizacion;
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- Verificar si existe la función GETDATETIME_BOGOTA (puede estar en otro esquema)
IF OBJECT_ID(N'MedidasCautelaresDbo.GETDATETIME_BOGOTA', 'FN') IS NOT NULL
BEGIN
    -- Usar la función existente
    PRINT 'Usando función GETDATETIME_BOGOTA existente de MedidasCautelaresDbo';
END
ELSE
BEGIN
    -- Crear función en el esquema ExpedicionCopiasDbo si no existe
    IF OBJECT_ID(N'ExpedicionCopiasDbo.GETDATETIME_BOGOTA', 'FN') IS NOT NULL
    BEGIN
        PRINT 'Usando función GETDATETIME_BOGOTA existente de ExpedicionCopiasDbo';
    END
    ELSE
    BEGIN
        -- Crear función local si no existe en ningún esquema
        EXEC('
        CREATE FUNCTION ExpedicionCopiasDbo.GETDATETIME_BOGOTA()
        RETURNS DATETIME2
        AS
        BEGIN
            RETURN CAST(DATEADD(hour, -5, GETUTCDATE()) AS DATETIME2);
        END;
        ');
        PRINT 'Función GETDATETIME_BOGOTA creada en ExpedicionCopiasDbo';
    END
END
GO

/****************************************************************************************
 TABLE: expedicion_copias_pqrs
 Purpose: Almacena datos de PQRS consultados desde Dynamics CRM para procesamiento
****************************************************************************************/
-- Eliminar tabla si existe para recrearla correctamente
IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID(N'[ExpedicionCopiasDbo].[expedicion_copias_pqrs]') AND type = 'U')
BEGIN
    DROP TABLE ExpedicionCopiasDbo.expedicion_copias_pqrs;
    PRINT 'Tabla expedicion_copias_pqrs eliminada para recreación.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID(N'[ExpedicionCopiasDbo].[expedicion_copias_pqrs]') AND type = 'U')
BEGIN
    CREATE TABLE ExpedicionCopiasDbo.expedicion_copias_pqrs (
        -- Clave primaria
        sp_documentoid NVARCHAR(36) NOT NULL PRIMARY KEY,
        
        -- Campos principales del CRM
        sp_name NVARCHAR(100) NULL,
        sp_titulopqrs NVARCHAR(500) NULL,
        sp_descripcion NVARCHAR(MAX) NULL,
        sp_descripciondelasolucion NVARCHAR(MAX) NULL,
        sp_resolvercaso BIT NOT NULL DEFAULT 0,
        
        -- Campos de referencia (lookups) - GUIDs
        _sp_tipodecasopqrs_value NVARCHAR(36) NULL,
        _sp_serviciopqrs_value NVARCHAR(36) NULL,
        _sp_categoriapqrs_value NVARCHAR(36) NULL,
        _sp_subcategoriapqrs_value NVARCHAR(36) NULL,
        _sp_contactopqrs_value NVARCHAR(36) NULL,
        _sp_contacto_value NVARCHAR(36) NULL,
        _sp_cliente_value NVARCHAR(36) NULL,
        _sp_departamento_value NVARCHAR(36) NULL,
        _sp_ciudad_value NVARCHAR(36) NULL,
        _sp_pais_value NVARCHAR(36) NULL,
        _sp_sedepqrs_value NVARCHAR(36) NULL,
        _sp_sederesponsable_value NVARCHAR(36) NULL,
        _sp_motivopqrs_value NVARCHAR(36) NULL,
        _sp_casooriginal_value NVARCHAR(36) NULL,
        _sp_responsable_value NVARCHAR(36) NULL,
        _sp_responsabledelbackoffice_value NVARCHAR(36) NULL,
        _sp_responsabledevolucionyreingreso_value NVARCHAR(36) NULL,
        _sp_abogadoresponsable_value NVARCHAR(36) NULL,
        _sp_agentedecallcenterasignado_value NVARCHAR(36) NULL,
        _sp_agentedebackofficeasignado_value NVARCHAR(36) NULL,
        _invt_especificacion_value NVARCHAR(36) NULL,
        _invt_tipodeatencion_value NVARCHAR(36) NULL,
        _ownerid_value NVARCHAR(36) NULL,
        _owninguser_value NVARCHAR(36) NULL,
        _owningteam_value NVARCHAR(36) NULL,
        _owningbusinessunit_value NVARCHAR(36) NULL,
        _createdby_value NVARCHAR(36) NULL,
        _createdonbehalfby_value NVARCHAR(36) NULL,
        _modifiedby_value NVARCHAR(36) NULL,
        _modifiedonbehalfby_value NVARCHAR(36) NULL,
        
        -- Campos de datos del CRM
        sp_fechadecierre DATETIME2 NULL,
        versionnumber BIGINT NULL,
        sp_aceptaciondeterminos BIT NOT NULL DEFAULT 0,
        sp_nombredelaempresa NVARCHAR(255) NULL,
        invt_ansajustado BIT NOT NULL DEFAULT 0,
        sp_fechadevolucioncompleja DATETIME2 NULL,
        invt_correoelectronico NVARCHAR(255) NULL,
        invt_referenciadocumento NVARCHAR(500) NULL,
        sp_matriculainscripcion NVARCHAR(100) NULL,
        sp_correoelectronico NVARCHAR(255) NULL,
        sp_turno NVARCHAR(50) NULL,
        sp_fechadecreacinreal DATETIME2 NULL,
        sp_celular NVARCHAR(50) NULL,
        invt_matriculasrequeridas NVARCHAR(500) NULL,
        utcconversiontimezonecode INT NULL,
        sp_numerodedocumentodelcontacto NVARCHAR(50) NULL,
        sp_nombres NVARCHAR(255) NULL,
        sp_direccionip NVARCHAR(50) NULL,
        sp_pqrsclonada BIT NOT NULL DEFAULT 0,
        sp_url_seguimiento NVARCHAR(500) NULL,
        sp_numerodedocumento NVARCHAR(50) NULL,
        sp_guid NVARCHAR(36) NULL,
        overriddencreatedon DATETIME2 NULL,
        sp_clienteescontacto BIT NOT NULL DEFAULT 0,
        modifiedon DATETIME2 NULL,
        sp_fechalimitederespuestacnx DATETIME2 NULL,
        emailaddress NVARCHAR(255) NULL,
        sp_numerodecaso NVARCHAR(100) NULL,
        sp_mensajesdecorreoelecrtrnico BIT NOT NULL DEFAULT 0,
        sp_requiereactualizaciondelabel BIT NOT NULL DEFAULT 0,
        sp_tipopnc NVARCHAR(100) NULL,
        sp_estadomigracion NVARCHAR(100) NULL,
        sp_medioderespuesta INT NULL,
        sp_direccion NVARCHAR(500) NULL,
        sp_tipodedocumento NVARCHAR(100) NULL,
        timezoneruleversionnumber INT NULL,
        sp_apellidos NVARCHAR(255) NULL,
        sp_devolucioncompleja BIT NOT NULL DEFAULT 0,
        sp_reingresoaprobado BIT NOT NULL DEFAULT 0,
        sp_fechadevencimiento DATETIME2 NULL,
        sp_solucionenprimercontacto BIT NOT NULL DEFAULT 0,
        sp_usuarioresponsablelocalizador NVARCHAR(255) NULL,
        sp_ans INT NULL,
        sp_anomina BIT NOT NULL DEFAULT 0,
        sp_origen INT NULL,
        sp_nmerodedocumentocliente NVARCHAR(50) NULL,
        importsequencenumber INT NULL,
        sp_url_callcenter NVARCHAR(500) NULL,
        sp_telefonofijo NVARCHAR(50) NULL,
        statecode INT NULL,
        sp_nombredeagentequecrea NVARCHAR(255) NULL,
        sp_fechalimitederespuesta DATETIME2 NULL,
        sp_clienteescuenta BIT NOT NULL DEFAULT 0,
        sp_mensajesdetextoalcelular BIT NOT NULL DEFAULT 0,
        sp_nit NVARCHAR(50) NULL,
        statuscode INT NULL,
        sp_consecutivo NVARCHAR(100) NULL,
        sp_fechadiligenciamientodeinformacion DATETIME2 NULL,
        createdon DATETIME2 NULL,
        sp_callid NVARCHAR(100) NULL,
        sp_nroderadicado NVARCHAR(100) NULL,
        sp_fechacierrecnx DATETIME2 NULL,
        sp_requiereactualizaciondeboletn BIT NULL,
        sp_razonparaelestadomigracion NVARCHAR(500) NULL,
        sp_clonarcaso BIT NOT NULL DEFAULT 0,
        
        -- Campos extra (proceso de expedición)
        subcategoriaName NVARCHAR(255) NULL,
        BusquedaDocumentos BIT NOT NULL DEFAULT 0,
        CantDocumentos INT NOT NULL DEFAULT 0,
        UnionDocumentos BIT NOT NULL DEFAULT 0,
        alamcenadoDocumentos BIT NOT NULL DEFAULT 0,
        envioCorreo BIT NOT NULL DEFAULT 0,
        cuerpoCorreo NVARCHAR(MAX) NULL,
        actualizadoCRM BIT NOT NULL DEFAULT 0,
        
        -- Campos de auditoría
        fecha_creacion DATETIME2 NOT NULL DEFAULT GETDATE(),
        fecha_edicion DATETIME2 NOT NULL DEFAULT GETDATE()
    );
    
    PRINT 'Tabla expedicion_copias_pqrs creada exitosamente.';
END
ELSE
BEGIN
    PRINT 'La tabla expedicion_copias_pqrs ya existe.';
END
GO

/****************************************************************************************
 ÍNDICES ESTRATÉGICOS
 Propósito: Optimizar consultas frecuentes
****************************************************************************************/

-- Índice en subcategoriaName para filtros de búsqueda
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_expedicion_pqrs_subcategoria' AND object_id = OBJECT_ID(N'ExpedicionCopiasDbo.expedicion_copias_pqrs'))
    DROP INDEX ix_expedicion_pqrs_subcategoria ON ExpedicionCopiasDbo.expedicion_copias_pqrs;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_expedicion_pqrs_subcategoria' AND object_id = OBJECT_ID(N'ExpedicionCopiasDbo.expedicion_copias_pqrs'))
    CREATE INDEX ix_expedicion_pqrs_subcategoria ON ExpedicionCopiasDbo.expedicion_copias_pqrs(subcategoriaName);
GO

-- Índice en actualizadoCRM para consultas de pendientes
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_expedicion_pqrs_actualizado' AND object_id = OBJECT_ID(N'ExpedicionCopiasDbo.expedicion_copias_pqrs'))
    DROP INDEX ix_expedicion_pqrs_actualizado ON ExpedicionCopiasDbo.expedicion_copias_pqrs;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_expedicion_pqrs_actualizado' AND object_id = OBJECT_ID(N'ExpedicionCopiasDbo.expedicion_copias_pqrs'))
    CREATE INDEX ix_expedicion_pqrs_actualizado ON ExpedicionCopiasDbo.expedicion_copias_pqrs(actualizadoCRM);
GO

-- Índice compuesto para consultas de pendientes por subcategoría
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_expedicion_pqrs_pendientes' AND object_id = OBJECT_ID(N'ExpedicionCopiasDbo.expedicion_copias_pqrs'))
    DROP INDEX ix_expedicion_pqrs_pendientes ON ExpedicionCopiasDbo.expedicion_copias_pqrs;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_expedicion_pqrs_pendientes' AND object_id = OBJECT_ID(N'ExpedicionCopiasDbo.expedicion_copias_pqrs'))
    CREATE INDEX ix_expedicion_pqrs_pendientes ON ExpedicionCopiasDbo.expedicion_copias_pqrs(subcategoriaName, actualizadoCRM) 
    INCLUDE (sp_documentoid, sp_name, cuerpoCorreo);
GO

-- Índice en sp_name para búsquedas por número de PQRS
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_expedicion_pqrs_name' AND object_id = OBJECT_ID(N'ExpedicionCopiasDbo.expedicion_copias_pqrs'))
    DROP INDEX ix_expedicion_pqrs_name ON ExpedicionCopiasDbo.expedicion_copias_pqrs;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_expedicion_pqrs_name' AND object_id = OBJECT_ID(N'ExpedicionCopiasDbo.expedicion_copias_pqrs'))
    CREATE INDEX ix_expedicion_pqrs_name ON ExpedicionCopiasDbo.expedicion_copias_pqrs(sp_name);
GO

-- Índice en createdon para ordenamiento por fecha
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_expedicion_pqrs_createdon' AND object_id = OBJECT_ID(N'ExpedicionCopiasDbo.expedicion_copias_pqrs'))
    DROP INDEX ix_expedicion_pqrs_createdon ON ExpedicionCopiasDbo.expedicion_copias_pqrs;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_expedicion_pqrs_createdon' AND object_id = OBJECT_ID(N'ExpedicionCopiasDbo.expedicion_copias_pqrs'))
    CREATE INDEX ix_expedicion_pqrs_createdon ON ExpedicionCopiasDbo.expedicion_copias_pqrs(createdon DESC);
GO

PRINT 'Índices creados exitosamente.';
GO

/****************************************************************************************
 TRIGGER: Actualizar fecha_edicion automáticamente
 Propósito: Mantener fecha_edicion actualizada cuando se modifica cualquier campo
****************************************************************************************/
IF OBJECT_ID(N'ExpedicionCopiasDbo.trg_expedicion_pqrs_update', 'TR') IS NOT NULL
    DROP TRIGGER ExpedicionCopiasDbo.trg_expedicion_pqrs_update;
GO

CREATE TRIGGER ExpedicionCopiasDbo.trg_expedicion_pqrs_update
ON ExpedicionCopiasDbo.expedicion_copias_pqrs
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Solo actualizar si se modificó algún campo (excepto fecha_edicion)
    IF UPDATE(fecha_edicion)
        RETURN; -- Si se actualizó fecha_edicion explícitamente, no hacer nada
    
    -- Actualizar fecha_edicion con hora de Bogotá
    UPDATE ExpedicionCopiasDbo.expedicion_copias_pqrs
    SET fecha_edicion = (
        CASE 
            WHEN OBJECT_ID(N'MedidasCautelaresDbo.GETDATETIME_BOGOTA', 'FN') IS NOT NULL 
            THEN MedidasCautelaresDbo.GETDATETIME_BOGOTA()
            WHEN OBJECT_ID(N'ExpedicionCopiasDbo.GETDATETIME_BOGOTA', 'FN') IS NOT NULL 
            THEN ExpedicionCopiasDbo.GETDATETIME_BOGOTA()
            ELSE GETDATE()
        END
    )
    FROM ExpedicionCopiasDbo.expedicion_copias_pqrs t
    INNER JOIN inserted i ON t.sp_documentoid = i.sp_documentoid;
END;
GO

PRINT 'Trigger de actualización creado exitosamente.';
GO

/****************************************************************************************
 ACTUALIZACIÓN DE ESTADÍSTICAS
 Propósito: Optimizar el plan de ejecución de consultas
****************************************************************************************/
IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID(N'[ExpedicionCopiasDbo].[expedicion_copias_pqrs]') AND type = 'U')
BEGIN
    UPDATE STATISTICS ExpedicionCopiasDbo.expedicion_copias_pqrs WITH FULLSCAN;
    PRINT 'Estadísticas actualizadas.';
END
GO

PRINT '=============================================';
PRINT 'Creación de tabla expedicion_copias_pqrs completada.';
PRINT '=============================================';
GO
