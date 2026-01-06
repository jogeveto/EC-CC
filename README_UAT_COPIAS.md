# README UAT - Módulo ExpedicionCopias: COPIAS (Particulares)

## 1. Descripción General del Módulo

El módulo **ExpedicionCopias - COPIAS** es un bot automatizado que procesa solicitudes de expedición de copias para **particulares**. El bot realiza las siguientes funciones principales:

- Consulta casos pendientes en Dynamics 365 CRM
- Descarga documentos desde DocuWare por matrícula
- Aplica reglas de negocio y excepciones de descarga
- Unifica documentos en un PDF único
- Envía el PDF al solicitante (adjunto o link de OneDrive según tamaño)
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
   f. Unificación de PDFs en un solo archivo
   g. Envío del PDF (adjunto si < 28MB, OneDrive si >= 28MB)
   h. Actualización del caso en CRM
7. Generación de reporte Excel
8. Envío de reporte por email
9. Eliminación de lock
```

### 2.2 Componentes Principales

- **CRMClient**: Consulta y actualiza casos en Dynamics 365
- **DocuWareClient**: Busca y descarga documentos desde DocuWare
- **GraphClient**: Envía emails y gestiona OneDrive
- **PDFMerger**: Unifica múltiples PDFs en uno solo
- **ExcepcionesValidator**: Valida documentos contra tabla de excepciones
- **TimeValidator**: Valida franjas horarias y días hábiles
- **NonCriticalRulesValidator**: Valida reglas no críticas

## 3. Configuración Requerida

### 3.1 Configuración de Reglas de Negocio (Copias)

```json
{
  "ReglasNegocio": {
    "Copias": {
      "Subcategorias": ["id1", "id2", ...],
      "Especificaciones": ["id1", "id2", ...],
      "FranjasHorarias": [
        {"inicio": "09:00", "fin": "10:00"},
        {"inicio": "15:00", "fin": "16:00"}
      ],
      "ExcepcionesDescarga": [
        {"tipoDocumento": "CITACIÓN", "actoRegistro": "DESISTIMIENTO TÁCITO"},
        ...
      ],
      "emailResponsable": "email@dominio.com",
      "PlantillasEmail": {
        "subcategoria_id": {
          "adjunto": {
            "asunto": "...",
            "cuerpo": "..."
          },
          "onedrive": {
            "asunto": "...",
            "cuerpo": "..."
          },
          "sinAdjuntos": {
            "asunto": "...",
            "cuerpo": "..."
          }
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

#### CP-COP-001: Procesamiento Exitoso - PDF Pequeño (< 28MB)
**Objetivo**: Verificar que un caso con documentos que generan un PDF < 28MB se procese correctamente enviando el PDF como adjunto.

**Precondiciones**:
- Caso en CRM con estado pendiente
- Matrícula(s) válida(s) en el campo `invt_matriculasrequeridas`
- Documentos disponibles en DocuWare para la(s) matrícula(s)
- Documentos no excluidos por excepciones
- PDF resultante < 28MB
- Email válido en el caso

**Pasos**:
1. Crear caso de prueba en CRM con matrícula que tenga documentos pequeños
2. Ejecutar módulo `procesar_copias`
3. Verificar que el caso se procese exitosamente

**Resultados Esperados**:
- ✅ Caso procesado exitosamente
- ✅ Email enviado con PDF adjunto
- ✅ Caso actualizado en CRM con `sp_resolvercaso = True`
- ✅ Descripción del caso contiene el cuerpo del email enviado
- ✅ Reporte Excel generado con el caso en "Procesados"

**Datos de Prueba**:
- Matrícula: [Proporcionar matrícula de prueba]
- ID Caso: [Proporcionar ID de caso de prueba]

---

#### CP-COP-002: Procesamiento Exitoso - PDF Grande (>= 28MB)
**Objetivo**: Verificar que un caso con documentos que generan un PDF >= 28MB se procese correctamente subiendo a OneDrive y enviando link.

**Precondiciones**:
- Caso en CRM con estado pendiente
- Matrícula(s) válida(s) con muchos documentos
- PDF resultante >= 28MB

**Pasos**:
1. Crear caso de prueba con matrícula que tenga muchos documentos
2. Ejecutar módulo `procesar_copias`
3. Verificar que el PDF se suba a OneDrive

**Resultados Esperados**:
- ✅ Caso procesado exitosamente
- ✅ PDF subido a OneDrive en carpeta `/ExpedicionCopias/Particulares/[NombreCaso]/`
- ✅ Email enviado con link de OneDrive
- ✅ Link compartido con `emailResponsable` configurado
- ✅ Caso actualizado en CRM correctamente

**Datos de Prueba**:
- Matrícula: [Proporcionar matrícula con muchos documentos]
- ID Caso: [Proporcionar ID de caso de prueba]

---

#### CP-COP-003: Aplicación de Excepciones de Descarga
**Objetivo**: Verificar que los documentos excluidos por excepciones no se descarguen.

**Precondiciones**:
- Caso con matrícula que tenga documentos que coincidan con excepciones configuradas
- Excepciones configuradas en `ExcepcionesDescarga`

**Pasos**:
1. Crear caso con matrícula que tenga documentos excluidos
2. Ejecutar módulo `procesar_copias`
3. Verificar que los documentos excluidos no se descarguen

**Resultados Esperados**:
- ✅ Documentos excluidos no se descargan
- ✅ Solo documentos permitidos se incluyen en el PDF
- ✅ Logs muestran documentos excluidos

**Datos de Prueba**:
- Matrícula: [Proporcionar matrícula con documentos excluidos]
- Tipo de documento excluido: [Ej: "CITACIÓN"]
- Acto de registro excluido: [Ej: "DESISTIMIENTO TÁCITO"]

---

#### CP-COP-004: Caso Sin Documentos en DocuWare
**Objetivo**: Verificar el manejo de casos donde no se encuentran documentos en DocuWare.

**Precondiciones**:
- Caso con matrícula que NO tenga documentos en DocuWare

**Pasos**:
1. Crear caso con matrícula sin documentos
2. Ejecutar módulo `procesar_copias`

**Resultados Esperados**:
- ✅ Caso marcado como error
- ✅ Error: "No se encontraron documentos en DocuWare"
- ✅ Caso aparece en reporte como "Error"
- ✅ No se envía email al cliente

**Datos de Prueba**:
- Matrícula: [Proporcionar matrícula sin documentos]

---

#### CP-COP-005: Todos los Documentos Excluidos por Excepciones
**Objetivo**: Verificar el manejo cuando todos los documentos son excluidos por excepciones.

**Precondiciones**:
- Caso con matrícula donde TODOS los documentos coinciden con excepciones

**Pasos**:
1. Crear caso con matrícula donde todos los documentos sean excluidos
2. Ejecutar módulo `procesar_copias`

**Resultados Esperados**:
- ✅ Caso marcado como "No Exitoso"
- ✅ Email enviado al responsable con plantilla "sinAdjuntos"
- ✅ Caso aparece en reporte como "No Exitoso"
- ✅ Mensaje: "Todos los documentos fueron excluidos por excepciones"

**Datos de Prueba**:
- Matrícula: [Proporcionar matrícula con todos los documentos excluidos]

---

#### CP-COP-006: Validación de Reglas No Críticas
**Objetivo**: Verificar que las reglas no críticas se validen correctamente.

**Precondiciones**:
- Caso que falle alguna regla no crítica (ej: sin email, sin matrículas, etc.)

**Pasos**:
1. Crear caso que falle regla no crítica
2. Ejecutar módulo `procesar_copias`

**Resultados Esperados**:
- ✅ Caso marcado como "No Exitoso"
- ✅ Email enviado al responsable con detalle de la regla fallida
- ✅ Caso aparece en reporte como "No Exitoso"
- ✅ Procesamiento continúa con siguiente caso

**Reglas No Críticas a Validar**:
- Caso sin email válido
- Caso sin matrículas
- Caso no encontrado al actualizar

---

#### CP-COP-007: Validación de Franja Horaria
**Objetivo**: Verificar que el proceso se interrumpa cuando sale de la franja horaria.

**Precondiciones**:
- Múltiples casos pendientes
- Ejecución iniciada dentro de franja horaria

**Pasos**:
1. Configurar franja horaria corta (ej: 09:00-09:05)
2. Crear múltiples casos de prueba
3. Ejecutar módulo `procesar_copias` cerca del fin de la franja

**Resultados Esperados**:
- ✅ Procesamiento se interrumpe al salir de franja horaria
- ✅ Casos no procesados se marcan como "Pendientes"
- ✅ Reporte incluye casos pendientes
- ✅ Logs muestran interrupción por franja horaria

---

#### CP-COP-008: Múltiples Matrículas en un Caso
**Objetivo**: Verificar que un caso con múltiples matrículas se procese correctamente.

**Precondiciones**:
- Caso con campo `invt_matriculasrequeridas` con múltiples matrículas separadas por coma

**Pasos**:
1. Crear caso con múltiples matrículas (ej: "12345,67890")
2. Ejecutar módulo `procesar_copias`

**Resultados Esperados**:
- ✅ Documentos de todas las matrículas se descargan
- ✅ PDF unificado contiene documentos de todas las matrículas
- ✅ Orden cronológico correcto (más antiguo primero)

**Datos de Prueba**:
- Matrículas: [Proporcionar múltiples matrículas separadas por coma]

---

#### CP-COP-009: Plantillas de Email por Subcategoría
**Objetivo**: Verificar que se use la plantilla correcta según la subcategoría del caso.

**Precondiciones**:
- Caso con subcategoría configurada
- Plantillas diferentes por subcategoría

**Pasos**:
1. Crear caso con subcategoría específica
2. Ejecutar módulo `procesar_copias`
3. Verificar email enviado

**Resultados Esperados**:
- ✅ Email usa plantilla correcta según subcategoría
- ✅ Variables en plantilla se reemplazan correctamente
- ✅ Firma se agrega al email

**Variables de Plantilla**:
- `[Nombre de la sociedad]`
- `[Número PQRS]`
- `[Fecha hoy]`
- `[CLIENTE]`
- `[Correo electrónico]`
- `[Fecha de ingreso de la solicitud]`
- `[Fecha de respuesta]`
- `{link}` (para plantilla onedrive)

---

#### CP-COP-010: Fallo de Conexión a DocuWare
**Objetivo**: Verificar el manejo cuando falla la conexión a DocuWare.

**Precondiciones**:
- DocuWare no disponible o credenciales incorrectas

**Pasos**:
1. Configurar credenciales incorrectas de DocuWare
2. Ejecutar módulo `procesar_copias`

**Resultados Esperados**:
- ✅ Validación de conexión falla
- ✅ Email de error enviado al responsable
- ✅ Proceso no continúa
- ✅ No se crea lock permanente

---

#### CP-COP-011: Fallo de Conexión a Dynamics 365
**Objetivo**: Verificar el manejo cuando falla la conexión a Dynamics 365.

**Precondiciones**:
- Dynamics 365 no disponible o credenciales incorrectas

**Pasos**:
1. Configurar credenciales incorrectas de Dynamics
2. Ejecutar módulo `procesar_copias`

**Resultados Esperados**:
- ✅ Validación de conexión falla
- ✅ Email de error enviado al responsable
- ✅ Proceso no continúa

---

#### CP-COP-012: Generación de Reporte Excel
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

**Columnas del Reporte**:
- ID Caso
- Radicado
- Matrículas
- Estado
- Observaciones
- Fecha/Hora Procesamiento

---

#### CP-COP-013: Envío de Reporte por Email
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

---

#### CP-COP-014: Lock de Ejecución
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

#### CP-COP-015: Validación de Día No Hábil
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

### 4.2 Casos de Prueba de Integración

#### CP-COP-016: Integración Completa End-to-End
**Objetivo**: Verificar el flujo completo desde consulta de casos hasta actualización en CRM.

**Precondiciones**:
- Ambiente completo configurado
- Casos de prueba en CRM

**Pasos**:
1. Preparar casos de prueba en CRM
2. Ejecutar módulo `procesar_copias`
3. Verificar cada paso del flujo

**Resultados Esperados**:
- ✅ Todos los pasos del flujo se ejecutan correctamente
- ✅ Integración con CRM funciona
- ✅ Integración con DocuWare funciona
- ✅ Integración con Graph API funciona
- ✅ Base de datos se actualiza correctamente

---

### 4.3 Casos de Prueba de Rendimiento

#### CP-COP-017: Procesamiento de Múltiples Casos
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

---

#### CP-COP-018: Procesamiento de Caso con Muchos Documentos
**Objetivo**: Verificar el manejo de casos con gran cantidad de documentos.

**Precondiciones**:
- Matrícula con 50+ documentos

**Pasos**:
1. Crear caso con matrícula que tenga muchos documentos
2. Ejecutar módulo

**Resultados Esperados**:
- ✅ Todos los documentos se descargan
- ✅ PDF unificado se genera correctamente
- ✅ No hay errores de memoria
- ✅ Tiempo de procesamiento aceptable

---

## 5. Criterios de Aceptación

### 5.1 Funcionalidad
- ✅ Todos los casos de prueba funcionales pasan
- ✅ Integraciones con sistemas externos funcionan correctamente
- ✅ Manejo de errores es robusto
- ✅ Logs son claros y útiles

### 5.2 Rendimiento
- ✅ Procesamiento de caso individual < 5 minutos
- ✅ Procesamiento de 10 casos < 30 minutos
- ✅ No hay memory leaks

### 5.3 Calidad
- ✅ Reportes generados son correctos
- ✅ Emails enviados son correctos
- ✅ Actualizaciones en CRM son correctas

## 6. Datos de Prueba Requeridos

### 6.1 Matrículas de Prueba
- Matrícula con documentos pequeños (< 28MB total)
- Matrícula con documentos grandes (>= 28MB total)
- Matrícula con documentos excluidos
- Matrícula sin documentos
- Matrícula con muchos documentos (50+)

### 6.2 Casos de Prueba en CRM
- Casos con diferentes subcategorías
- Casos con múltiples matrículas
- Casos sin email
- Casos sin matrículas
- Casos con estados diferentes

### 6.3 Configuración de Prueba
- Franjas horarias de prueba
- Excepciones de descarga de prueba
- Plantillas de email de prueba

## 7. Checklist de Validación UAT

### Pre-Ejecución
- [ ] Configuración cargada correctamente
- [ ] Variables de Rocketbot configuradas
- [ ] Conexiones a sistemas externos funcionando
- [ ] Casos de prueba preparados en CRM
- [ ] Matrículas de prueba disponibles en DocuWare

### Durante Ejecución
- [ ] Validación de franja horaria funciona
- [ ] Lock de ejecución funciona
- [ ] Validación de conexiones funciona
- [ ] Notificación de inicio se envía
- [ ] Casos se consultan correctamente
- [ ] Documentos se descargan correctamente
- [ ] Excepciones se aplican correctamente
- [ ] PDFs se unifican correctamente
- [ ] Emails se envían correctamente
- [ ] Casos se actualizan en CRM correctamente

### Post-Ejecución
- [ ] Reporte Excel generado correctamente
- [ ] Reporte enviado por email
- [ ] Lock eliminado
- [ ] Logs disponibles y claros
- [ ] Base de datos actualizada
- [ ] Casos en CRM actualizados correctamente

## 8. Notas Importantes

1. **Modo QA**: Si `Globales.modo = "QA"`, los emails se envían a `emailQa` en lugar del destinatario real.

2. **Franjas Horarias**: El proceso valida la franja horaria antes de iniciar y antes de procesar cada caso. Si sale de la franja durante el procesamiento, los casos restantes quedan pendientes.

3. **Excepciones**: Las excepciones se aplican por `tipoDocumento` y `actoRegistro`. Si `actoRegistro` está vacío, se excluyen TODOS los documentos de ese tipo.

4. **Tamaño de PDF**: El límite es 28MB. PDFs >= 28MB se suben a OneDrive automáticamente.

5. **Plantillas de Email**: Las plantillas varían por subcategoría y modo de envío (adjunto/onedrive).

6. **Reglas No Críticas**: Si una regla no crítica falla, el caso se marca como "No Exitoso" pero el procesamiento continúa con el siguiente caso.

7. **Lock**: El lock tiene un timeout de 24 horas. Si un proceso queda bloqueado, el lock se elimina automáticamente después de 24 horas.

## 9. Contacto y Soporte

Para dudas o problemas durante las pruebas UAT, contactar al equipo de desarrollo.

---

**Versión del Documento**: 1.0  
**Fecha de Creación**: 2024-12-XX  
**Última Actualización**: 2024-12-XX
