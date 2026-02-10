-- DROP SCHEMA ExpedicionCopiasDbo;

CREATE SCHEMA ExpedicionCopiasDbo;
-- RPA_Automatizacion.ExpedicionCopiasDbo.reporte_expedicion definition

-- Drop table

-- DROP TABLE RPA_Automatizacion.ExpedicionCopiasDbo.reporte_expedicion;

CREATE TABLE RPA_Automatizacion.ExpedicionCopiasDbo.reporte_expedicion (
	id int IDENTITY(1,1) NOT NULL,
	codigo_asistente nvarchar(100) COLLATE Modern_Spanish_CI_AS NULL,
	codigo_bot nvarchar(100) COLLATE Modern_Spanish_CI_AS NULL,
	usuario_red_bot_runner nvarchar(100) COLLATE Modern_Spanish_CI_AS NULL,
	nombre_estacion_bot_runner nvarchar(100) COLLATE Modern_Spanish_CI_AS NULL,
	id_proceso int NULL,
	no_radicado nvarchar(500) COLLATE Modern_Spanish_CI_AS NULL,
	matriculas nvarchar(1000) COLLATE Modern_Spanish_CI_AS NULL,
	estado_proceso nvarchar(50) COLLATE Modern_Spanish_CI_AS NULL,
	observacion nvarchar(MAX) COLLATE Modern_Spanish_CI_AS NULL,
	fecha_inicio_ejecucion date NULL,
	hora_inicio_ejecucion time NULL,
	fecha_fin_ejecucion date NULL,
	hora_fin_ejecucion time NULL,
	fecha_creacion datetime DEFAULT getdate() NOT NULL,
	fecha_actualizacion datetime DEFAULT getdate() NOT NULL,
	CONSTRAINT PK_reporte_expedicion PRIMARY KEY (id)
);