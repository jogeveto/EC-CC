# README UAT - Módulo ExpedicionCopias: COPIAS OFICIALES

## 1. Descripción General del Módulo

El módulo **ExpedicionCopias - COPIAS OFICIALES** es un bot automatizado que procesa solicitudes de expedición de copias para **entidades oficiales**. A diferencia del módulo de particulares, este módulo organiza los documentos en una estructura de carpetas antes de enviarlos.

- Consulta casos pendientes en Dynamics 365 CRM
- Descarga documentos desde DocuWare por matrícula
- Aplica reglas de negocio y excepciones de descarga
- Organiza documentos en estructura: `Radicado/Matricula/TipoDocumento/`
- Sube carpeta completa a OneDrive
- Envía email con link a la carpeta organizada
- Actualiza el caso en CRM con la respuesta enviada
- Genera reportes de ejecución

## 2. Flujo de Procesamiento

### 2.1 Flujo Principal

```
1. Validación de franja horaria y día hábil
2. Verificación de lock (evitar ejecuciones simultáneas)
3. Validación de conexiones (DocuWare, Dynamics 365)
4. Notificación de inicio de ejecución
5. Consulta de casos en CRM (filtrados por subcategorías y especificaciones)
6. Para cada caso:
   a. Validación de franja horaria (antes de procesar cada caso)
   b. Validación de reglas no críticas
   c. Obtención de matrículas del caso
   d. Búsqueda y descarga de documentos en DocuWare
   e. Aplicación de excepciones de descarga
   f. Organización de documentos en estructura de carpetas
   g. Subida de carpeta completa a OneDrive
   h. Compartir carpeta con destinatario
   i. Envío de email con link a la carpeta
   j. Actualización del caso en CRM
7. Generación de reporte Excel
8. Envío de reporte por email
9. Eliminación de lock
```

### 2.2 Estructura de Organización de Archivos

Los documentos se organizan en la siguiente estructura:

```
[Radicado]/
  ├── [Matricula1]/
  │   ├── [TipoDocumento1]/
  │   │   ├── TipoDocumento1 1.pdf
  │   │   ├── TipoDocumento1 2.pdf
  │   │   └── ...
  │   ├── [TipoDocumento2]/
  │   │   ├── TipoDocumento2 1.pdf
  │   │   └── ...
  │   └── ...
  ├── [Matricula2]/
  │   └── ...
  └── ...
```

**Características**:
- Los archivos se renombran con el formato: `[TipoDocumento] [Número].pdf`
- Los archivos se ordenan por fecha (más antiguo primero)
- Se agrupan por matrícula y tipo de documento

### 2.3 Componentes Principales

- **CRMClient**: Consulta y actualiza casos en Dynamics 365
- **DocuWareClient**: Busca y descarga documentos desde DocuWare
- **GraphClient**: Envía emails y gestiona OneDrive
- **FileOrganizer**: Organiza archivos en estructura de carpetas
- **ExcepcionesValidator**: Valida documentos contra tabla de excepciones
- **TimeValidator**: Valida franjas horarias y días hábiles
- **NonCriticalRulesValidator**: Valida reglas no críticas

## 3. Configuración Requerida

### 3.1 Configuración de Reglas de Negocio (CopiasOficiales)

```json
{
  "ReglasNegocio": {
    "CopiasOficiales": {
      "Subcategorias": ["id1", "id2", ...],
      "Especificaciones": ["id1", "id2", ...],
      "FranjasHorarias": [
        {"inicio": "08:00", "fin": "09:00"},
        {"inicio": "14:00", "fin": "15:00"}
      ],
      "ExcepcionesDescarga": [
        {"tipoDocumento": "CITACIÓN", "actoRegistro": "DESISTIMIENTO TÁCITO"},
        ...
      ],
      "emailResponsable": "email@dominio.com",
      "PlantillasEmail": {
        "default": {
          "asunto": "Entrega de Copias - Entidades Oficiales",
          "cuerpo": "..."
        },
        "sinAdjuntos": {
          "asunto": "Notificación - Caso sin documentos disponibles",
          "cuerpo": "..."
        }
      }
    }
  }
}
```

### 3.2 Variables de Rocketbot Requeridas

- `graph_client_secret`: Secret de aplicación Graph API
- `dynamics_client_secret`: Secret de aplicación Dynamics 365
- `docuware_password`: Contraseña de DocuWare
- `database_password`: Contraseña de base de datos (opcional)

## 4. Casos de Prueba UAT

### 4.1 Casos de Prueba Funcionales

#### CP-OFI-001: Procesamiento Exitoso - Organización de Documentos
**Objetivo**: Verificar que un caso se procese correctamente organizando los documentos en estructura de carpetas.

**Precondiciones**:
- Caso en CRM con estado pendiente
- Matrícula(s) válida(s) en el campo `invt_matriculasrequeridas`
- Documentos disponibles en DocuWare para la(s) matrícula(s)
- Documentos no excluidos por excepciones
- Email válido en el campo `invt_correoelectronico` del caso

**Pasos**:
1. Crear caso de prueba en CRM con matrícula que tenga documentos
2. Ejecutar módulo `procesar_copias_oficiales`
3. Verificar que el caso se procese exitosamente

**Resultados Esperados**:
- ✅ Caso procesado exitosamente
- ✅ Documentos descargados y organizados en estructura de carpetas
- ✅ Carpeta subida a OneDrive en `/ExpedicionCopias/Oficiales/[Radicado]/`
- ✅ Carpeta compartida con destinatario (`invt_correoelectronico`)
- ✅ Email enviado con link a la carpeta
- ✅ Caso actualizado en CRM con `sp_resolvercaso = True`
- ✅ Descripción del caso contiene el cuerpo del email enviado
- ✅ Reporte Excel generado con el caso en "Procesados"

**Datos de Prueba**:
- Matrícula: [Proporcionar matrícula de prueba]
- ID Caso: [Proporcionar ID de caso de prueba]
- Radicado: [Proporcionar radicado de prueba]

---

#### CP-OFI-002: Organización por Múltiples Matrículas
**Objetivo**: Verificar que un caso con múltiples matrículas organice correctamente los documentos.

**Precondiciones**:
- Caso con múltiples matrículas separadas por coma

**Pasos**:
1. Crear caso con múltiples matrículas (ej: "12345,67890")
2. Ejecutar módulo `procesar_copias_oficiales`
3. Verificar estructura de carpetas

**Resultados Esperados**:
- ✅ Carpeta raíz con nombre del radicado
- ✅ Subcarpetas por cada matrícula
- ✅ Documentos organizados correctamente por matrícula
- ✅ Estructura: `[Radicado]/[Matricula1]/[TipoDocumento]/archivos.pdf`
- ✅ Estructura: `[Radicado]/[Matricula2]/[TipoDocumento]/archivos.pdf`

**Datos de Prueba**:
- Matrículas: [Proporcionar múltiples matrículas separadas por coma]

---

#### CP-OFI-003: Organización por Tipo de Documento
**Objetivo**: Verificar que los documentos se agrupen correctamente por tipo de documento.

**Precondiciones**:
- Matrícula con documentos de diferentes tipos

**Pasos**:
1. Crear caso con matrícula que tenga documentos de diferentes tipos
2. Ejecutar módulo `procesar_copias_oficiales`
3. Verificar organización por tipo

**Resultados Esperados**:
- ✅ Documentos agrupados por tipo de documento
- ✅ Cada tipo tiene su propia carpeta
- ✅ Archivos renombrados: `[TipoDocumento] 1.pdf`, `[TipoDocumento] 2.pdf`, etc.
- ✅ Archivos ordenados por fecha (más antiguo primero)

**Datos de Prueba**:
- Matrícula: [Proporcionar matrícula con múltiples tipos de documentos]

---

#### CP-OFI-004: Aplicación de Excepciones de Descarga
**Objetivo**: Verificar que los documentos excluidos por excepciones no se descarguen.

**Precondiciones**:
- Caso con matrícula que tenga documentos que coincidan con excepciones configuradas

**Pasos**:
1. Crear caso con matrícula que tenga documentos excluidos
2. Ejecutar módulo `procesar_copias_oficiales`
3. Verificar que los documentos excluidos no se descarguen

**Resultados Esperados**:
- ✅ Documentos excluidos no se descargan
- ✅ Solo documentos permitidos se organizan en carpetas
- ✅ Logs muestran documentos excluidos

**Datos de Prueba**:
- Matrícula: [Proporcionar matrícula con documentos excluidos]
- Tipo de documento excluido: [Ej: "CITACIÓN"]
- Acto de registro excluido: [Ej: "DESISTIMIENTO TÁCITO"]

---

#### CP-OFI-005: Caso Sin Documentos en DocuWare
**Objetivo**: Verificar el manejo de casos donde no se encuentran documentos en DocuWare.

**Precondiciones**:
- Caso con matrícula que NO tenga documentos en DocuWare

**Pasos**:
1. Crear caso con matrícula sin documentos
2. Ejecutar módulo `procesar_copias_oficiales`

**Resultados Esperados**:
- ✅ Caso marcado como error
- ✅ Error: "No se encontraron documentos en DocuWare"
- ✅ Caso aparece en reporte como "Error"
- ✅ No se envía email al cliente

**Datos de Prueba**:
- Matrícula: [Proporcionar matrícula sin documentos]

---

#### CP-OFI-006: Todos los Documentos Excluidos por Excepciones
**Objetivo**: Verificar el manejo cuando todos los documentos son excluidos por excepciones.

**Precondiciones**:
- Caso con matrícula donde TODOS los documentos coinciden con excepciones

**Pasos**:
1. Crear caso con matrícula donde todos los documentos sean excluidos
2. Ejecutar módulo `procesar_copias_oficiales`

**Resultados Esperados**:
- ✅ Caso marcado como "No Exitoso"
- ✅ Email enviado al responsable con plantilla "sinAdjuntos"
- ✅ Caso aparece en reporte como "No Exitoso"
- ✅ Mensaje: "Todos los documentos fueron excluidos por excepciones"

**Datos de Prueba**:
- Matrícula: [Proporcionar matrícula con todos los documentos excluidos]

---

#### CP-OFI-007: Validación de Reglas No Críticas
**Objetivo**: Verificar que las reglas no críticas se validen correctamente.

**Precondiciones**:
- Caso que falle alguna regla no crítica (ej: sin email, sin matrículas, etc.)

**Pasos**:
1. Crear caso que falle regla no crítica
2. Ejecutar módulo `procesar_copias_oficiales`

**Resultados Esperados**:
- ✅ Caso marcado como "No Exitoso"
- ✅ Email enviado al responsable con detalle de la regla fallida
- ✅ Caso aparece en reporte como "No Exitoso"
- ✅ Procesamiento continúa con siguiente caso

**Reglas No Críticas a Validar**:
- Caso sin email válido (`invt_correoelectronico`)
- Caso sin matrículas
- Caso no encontrado al actualizar

---

#### CP-OFI-008: Validación de Franja Horaria
**Objetivo**: Verificar que el proceso se interrumpa cuando sale de la franja horaria.

**Precondiciones**:
- Múltiples casos pendientes
- Ejecución iniciada dentro de franja horaria

**Pasos**:
1. Configurar franja horaria corta (ej: 08:00-08:05)
2. Crear múltiples casos de prueba
3. Ejecutar módulo `procesar_copias_oficiales` cerca del fin de la franja

**Resultados Esperados**:
- ✅ Procesamiento se interrumpe al salir de franja horaria
- ✅ Casos no procesados se marcan como "Pendientes"
- ✅ Reporte incluye casos pendientes
- ✅ Logs muestran interrupción por franja horaria

---

#### CP-OFI-009: Subida de Carpeta a OneDrive
**Objetivo**: Verificar que la carpeta organizada se suba correctamente a OneDrive.

**Precondiciones**:
- Caso procesado exitosamente
- Carpeta organizada localmente

**Pasos**:
1. Ejecutar módulo con caso de prueba
2. Verificar carpeta en OneDrive

**Resultados Esperados**:
- ✅ Carpeta subida a `/ExpedicionCopias/Oficiales/[Radicado]/`
- ✅ Estructura de carpetas se mantiene
- ✅ Todos los archivos se suben correctamente
- ✅ Nombres de archivos se mantienen

**Datos de Prueba**:
- Radicado: [Proporcionar radicado de prueba]

---

#### CP-OFI-010: Compartir Carpeta con Destinatario
**Objetivo**: Verificar que la carpeta se comparta correctamente con el destinatario.

**Precondiciones**:
- Carpeta subida a OneDrive
- Email válido en `invt_correoelectronico`

**Pasos**:
1. Ejecutar módulo con caso que tenga email válido
2. Verificar compartir de carpeta

**Resultados Esperados**:
- ✅ Carpeta compartida con email de `invt_correoelectronico`
- ✅ Invitación enviada por correo
- ✅ Link de acceso generado
- ✅ Permisos de solo lectura configurados

**Nota**: En modo QA, se usa `emailQa` en lugar de `invt_correoelectronico`.

---

#### CP-OFI-011: Envío de Email con Link
**Objetivo**: Verificar que el email se envíe correctamente con el link a la carpeta.

**Precondiciones**:
- Carpeta compartida en OneDrive
- Link generado

**Pasos**:
1. Ejecutar módulo
2. Verificar email enviado

**Resultados Esperados**:
- ✅ Email enviado al creador del caso (`invt_correoelectronico` o email del creador)
- ✅ Asunto correcto según plantilla
- ✅ Cuerpo del email contiene link a la carpeta
- ✅ Variables en plantilla se reemplazan correctamente
- ✅ Firma se agrega al email

**Variables de Plantilla**:
- `{link}`: Link de acceso a la carpeta
- `{onedrive_path}`: Ruta completa en OneDrive
- Variables del caso (radicado, matrículas, etc.)

---

#### CP-OFI-012: Fallo al Compartir Carpeta
**Objetivo**: Verificar el manejo cuando falla el compartir de la carpeta.

**Precondiciones**:
- Carpeta subida a OneDrive
- Error al compartir (ej: email inválido)

**Pasos**:
1. Configurar caso con email inválido o sin email
2. Ejecutar módulo

**Resultados Esperados**:
- ✅ Sistema intenta compartir con email
- ✅ Si falla, usa método tradicional de compartir
- ✅ Si falla método tradicional, usa `webUrl` como fallback
- ✅ Email de error enviado al responsable si falla compartir
- ✅ Proceso continúa con `webUrl` si está disponible

---

#### CP-OFI-013: Modo QA - Redirección de Emails
**Objetivo**: Verificar que en modo QA los emails se redirijan correctamente.

**Precondiciones**:
- `Globales.modo = "QA"`
- `Globales.emailQa` configurado

**Pasos**:
1. Configurar modo QA
2. Ejecutar módulo con caso de prueba
3. Verificar destinatario del email

**Resultados Esperados**:
- ✅ Carpeta compartida con `emailQa` en lugar de `invt_correoelectronico`
- ✅ Email enviado a `emailQa`
- ✅ Logs indican modo QA activo

---

#### CP-OFI-014: Fallo de Conexión a DocuWare
**Objetivo**: Verificar el manejo cuando falla la conexión a DocuWare.

**Precondiciones**:
- DocuWare no disponible o credenciales incorrectas

**Pasos**:
1. Configurar credenciales incorrectas de DocuWare
2. Ejecutar módulo `procesar_copias_oficiales`

**Resultados Esperados**:
- ✅ Validación de conexión falla
- ✅ Email de error enviado al responsable
- ✅ Proceso no continúa
- ✅ No se crea lock permanente

---

#### CP-OFI-015: Fallo de Conexión a Dynamics 365
**Objetivo**: Verificar el manejo cuando falla la conexión a Dynamics 365.

**Precondiciones**:
- Dynamics 365 no disponible o credenciales incorrectas

**Pasos**:
1. Configurar credenciales incorrectas de Dynamics
2. Ejecutar módulo `procesar_copias_oficiales`

**Resultados Esperados**:
- ✅ Validación de conexión falla
- ✅ Email de error enviado al responsable
- ✅ Proceso no continúa

---

#### CP-OFI-016: Generación de Reporte Excel
**Objetivo**: Verificar que el reporte Excel se genere correctamente.

**Precondiciones**:
- Casos procesados en la ejecución

**Pasos**:
1. Ejecutar módulo con casos de prueba
2. Verificar reporte generado

**Resultados Esperados**:
- ✅ Reporte Excel generado con nombre correcto
- ✅ Reporte contiene hoja "Reporte Expedición Copias"
- ✅ Columnas correctas: ID Caso, Radicado, Estado, Observaciones, etc.
- ✅ Casos procesados, errores y pendientes listados correctamente
- ✅ Fechas y horas de inicio/fin correctas
- ✅ Tipo de proceso: "OFICIALES"

**Columnas del Reporte**:
- ID Caso
- Radicado
- Matrículas
- Estado
- Observaciones
- Fecha/Hora Procesamiento

---

#### CP-OFI-017: Envío de Reporte por Email
**Objetivo**: Verificar que el reporte se envíe por email a los administradores.

**Precondiciones**:
- Ejecución completada
- Reporte generado

**Pasos**:
1. Ejecutar módulo
2. Verificar email con reporte

**Resultados Esperados**:
- ✅ Email enviado a `emailsAdministradores` configurados
- ✅ Reporte adjunto al email
- ✅ Asunto y cuerpo del email correctos
- ✅ Tipo de proceso indicado: "OFICIALES"

---

#### CP-OFI-018: Lock de Ejecución
**Objetivo**: Verificar que no se ejecuten dos instancias simultáneas.

**Precondiciones**:
- Primera ejecución en curso

**Pasos**:
1. Iniciar primera ejecución
2. Intentar iniciar segunda ejecución antes de que termine la primera

**Resultados Esperados**:
- ✅ Segunda ejecución detecta lock existente
- ✅ Segunda ejecución espera hasta que se libere el lock (máximo 24 horas)
- ✅ Lock se elimina al finalizar ejecución

---

#### CP-OFI-019: Validación de Día No Hábil
**Objetivo**: Verificar que el proceso no se ejecute en días no hábiles.

**Precondiciones**:
- Día festivo o fin de semana

**Pasos**:
1. Ejecutar módulo en día festivo o fin de semana

**Resultados Esperados**:
- ✅ Proceso no se ejecuta
- ✅ Retorna status "skipped"
- ✅ Mensaje: "Proceso no ejecutado: fuera de franja horaria o día no hábil"
- ✅ No se envía notificación de inicio

---

#### CP-OFI-020: Sanitización de Nombres de Carpetas
**Objetivo**: Verificar que los nombres de carpetas se sanitizen correctamente.

**Precondiciones**:
- Caso con caracteres especiales en radicado o matrícula

**Pasos**:
1. Crear caso con radicado que tenga caracteres especiales
2. Ejecutar módulo

**Resultados Esperados**:
- ✅ Caracteres especiales se reemplazan por guiones bajos
- ✅ Nombres de carpetas válidos para sistema de archivos
- ✅ Estructura de carpetas se crea correctamente

**Datos de Prueba**:
- Radicado: [Proporcionar radicado con caracteres especiales]

---

### 4.2 Casos de Prueba de Integración

#### CP-OFI-021: Integración Completa End-to-End
**Objetivo**: Verificar el flujo completo desde consulta de casos hasta actualización en CRM.

**Precondiciones**:
- Ambiente completo configurado
- Casos de prueba en CRM

**Pasos**:
1. Preparar casos de prueba en CRM
2. Ejecutar módulo `procesar_copias_oficiales`
3. Verificar cada paso del flujo

**Resultados Esperados**:
- ✅ Todos los pasos del flujo se ejecutan correctamente
- ✅ Integración con CRM funciona
- ✅ Integración con DocuWare funciona
- ✅ Integración con Graph API funciona
- ✅ Base de datos se actualiza correctamente
- ✅ Estructura de carpetas se crea correctamente
- ✅ OneDrive se actualiza correctamente

---

### 4.3 Casos de Prueba de Rendimiento

#### CP-OFI-022: Procesamiento de Múltiples Casos
**Objetivo**: Verificar que el módulo procese múltiples casos correctamente.

**Precondiciones**:
- Múltiples casos pendientes en CRM

**Pasos**:
1. Crear 10+ casos de prueba
2. Ejecutar módulo
3. Verificar tiempo de ejecución

**Resultados Esperados**:
- ✅ Todos los casos se procesan
- ✅ Tiempo de ejecución razonable
- ✅ Reporte incluye todos los casos
- ✅ No hay errores de memoria o timeout
- ✅ Estructuras de carpetas se crean correctamente

---

#### CP-OFI-023: Procesamiento de Caso con Muchos Documentos
**Objetivo**: Verificar el manejo de casos con gran cantidad de documentos.

**Precondiciones**:
- Matrícula con 50+ documentos

**Pasos**:
1. Crear caso con matrícula que tenga muchos documentos
2. Ejecutar módulo

**Resultados Esperados**:
- ✅ Todos los documentos se descargan
- ✅ Documentos se organizan correctamente en carpetas
- ✅ Carpeta se sube a OneDrive correctamente
- ✅ No hay errores de memoria
- ✅ Tiempo de procesamiento aceptable

---

## 5. Diferencias Clave con COPIAS (Particulares)

### 5.1 Organización de Documentos
- **COPIAS**: Unifica todos los documentos en un solo PDF
- **COPIAS OFICIALES**: Organiza documentos en estructura de carpetas por matrícula y tipo

### 5.2 Entrega de Documentos
- **COPIAS**: Envía PDF adjunto (< 28MB) o link de OneDrive (>= 28MB)
- **COPIAS OFICIALES**: Siempre sube carpeta completa a OneDrive y envía link

### 5.3 Plantillas de Email
- **COPIAS**: Plantillas diferentes por subcategoría
- **COPIAS OFICIALES**: Plantilla única (default) para todos los casos

### 5.4 Destinatario del Email
- **COPIAS**: Email del caso o email según subcategoría
- **COPIAS OFICIALES**: Email del creador del caso (`invt_correoelectronico` o email del creador)

### 5.5 Estructura en OneDrive
- **COPIAS**: `/ExpedicionCopias/Particulares/[NombreCaso]/archivo.pdf`
- **COPIAS OFICIALES**: `/ExpedicionCopias/Oficiales/[Radicado]/[Matricula]/[TipoDocumento]/archivos.pdf`

## 6. Criterios de Aceptación

### 6.1 Funcionalidad
- ✅ Todos los casos de prueba funcionales pasan
- ✅ Integraciones con sistemas externos funcionan correctamente
- ✅ Manejo de errores es robusto
- ✅ Logs son claros y útiles
- ✅ Estructura de carpetas se crea correctamente
- ✅ Organización de documentos es correcta

### 6.2 Rendimiento
- ✅ Procesamiento de caso individual < 10 minutos (más tiempo por organización)
- ✅ Procesamiento de 10 casos < 60 minutos
- ✅ No hay memory leaks
- ✅ Subida a OneDrive es eficiente

### 6.3 Calidad
- ✅ Reportes generados son correctos
- ✅ Emails enviados son correctos
- ✅ Actualizaciones en CRM son correctas
- ✅ Estructura de carpetas es clara y organizada
- ✅ Nombres de archivos son descriptivos

## 7. Datos de Prueba Requeridos

### 7.1 Matrículas de Prueba
- Matrícula con documentos de diferentes tipos
- Matrícula con documentos excluidos
- Matrícula sin documentos
- Matrícula con muchos documentos (50+)
- Múltiples matrículas para un caso

### 7.2 Casos de Prueba en CRM
- Casos con diferentes radicados
- Casos con múltiples matrículas
- Casos sin email (`invt_correoelectronico`)
- Casos sin matrículas
- Casos con caracteres especiales en radicado

### 7.3 Configuración de Prueba
- Franjas horarias de prueba
- Excepciones de descarga de prueba
- Plantillas de email de prueba
- Modo QA configurado

## 8. Checklist de Validación UAT

### Pre-Ejecución
- [ ] Configuración cargada correctamente
- [ ] Variables de Rocketbot configuradas
- [ ] Conexiones a sistemas externos funcionando
- [ ] Casos de prueba preparados en CRM
- [ ] Matrículas de prueba disponibles en DocuWare
- [ ] OneDrive accesible y configurado

### Durante Ejecución
- [ ] Validación de franja horaria funciona
- [ ] Lock de ejecución funciona
- [ ] Validación de conexiones funciona
- [ ] Notificación de inicio se envía
- [ ] Casos se consultan correctamente
- [ ] Documentos se descargan correctamente
- [ ] Excepciones se aplican correctamente
- [ ] Documentos se organizan correctamente en carpetas
- [ ] Estructura de carpetas se crea correctamente
- [ ] Carpeta se sube a OneDrive correctamente
- [ ] Carpeta se comparte correctamente
- [ ] Emails se envían correctamente
- [ ] Casos se actualizan en CRM correctamente

### Post-Ejecución
- [ ] Reporte Excel generado correctamente
- [ ] Reporte enviado por email
- [ ] Lock eliminado
- [ ] Logs disponibles y claros
- [ ] Base de datos actualizada
- [ ] Casos en CRM actualizados correctamente
- [ ] Carpetas en OneDrive accesibles
- [ ] Links de compartir funcionan

## 9. Notas Importantes

1. **Modo QA**: Si `Globales.modo = "QA"`, los emails y compartir se redirigen a `emailQa` en lugar del destinatario real.

2. **Franjas Horarias**: El proceso valida la franja horaria antes de iniciar y antes de procesar cada caso. Si sale de la franja durante el procesamiento, los casos restantes quedan pendientes.

3. **Excepciones**: Las excepciones se aplican por `tipoDocumento` y `actoRegistro`. Si `actoRegistro` está vacío, se excluyen TODOS los documentos de ese tipo.

4. **Organización**: Los documentos se organizan automáticamente por matrícula y tipo de documento. Los archivos se renombran y ordenan por fecha.

5. **OneDrive**: La carpeta completa se sube a OneDrive. Si falla el compartir con email, se usa método tradicional o `webUrl` como fallback.

6. **Reglas No Críticas**: Si una regla no crítica falla, el caso se marca como "No Exitoso" pero el procesamiento continúa con el siguiente caso.

7. **Lock**: El lock tiene un timeout de 24 horas. Si un proceso queda bloqueado, el lock se elimina automáticamente después de 24 horas.

8. **Radicado**: Se usa `sp_ticketnumber` o `sp_name` como nombre del radicado para la carpeta.

9. **Sanitización**: Los nombres de carpetas y archivos se sanitizan para evitar caracteres especiales que causen problemas en el sistema de archivos.

10. **Destinatario**: El email se envía al creador del caso. Si no hay `invt_correoelectronico`, se usa el email del creador del caso en CRM.

## 10. Contacto y Soporte

Para dudas o problemas durante las pruebas UAT, contactar al equipo de desarrollo.

---

**Versión del Documento**: 1.0  
**Fecha de Creación**: 2024-12-XX  
**Última Actualización**: 2024-12-XX
