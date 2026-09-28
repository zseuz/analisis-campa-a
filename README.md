# 📊 Analítica de Campaña WhatsApp BPO & Monitoreo SLA

Dashboard analítico desarrollado en **Power BI** para la evaluación del rendimiento, efectividad técnica y respuesta operativa de una campaña masiva de mensajería a través de la **API de WhatsApp (Meta)** en una operación BPO.

---

## 📌 ¿Qué es este proyecto?

Este proyecto proporciona una solución integral de **Business Intelligence y Operaciones (WFM)** que permite monitorear y diagnosticar el ciclo completo de comunicación con clientes:
1. **Entrega y Salud Técnica:** Monitoreo en tiempo real del funnel de salida (*read, delivered, failed*) y detección de errores de la API.
2. **Eficiencia y SLA Operativo:** Medición del tiempo de respuesta del equipo de atención al cliente ante mensajes entrantes.
3. **Dimensionamiento de Personal (WFM):** Análisis de la demanda horaria para optimizar turnos y recursos de asesores.
4. **Voz del Cliente (NLP):** Clasificación de intenciones y motivos de contacto entrantes.

---

## 🚀 ¿Qué se realizó?

### 1. Extracción, Limpieza y Modelado de Datos
* **Fuente de Datos:** Tabla de mensajería con registros transaccionales de eventos (`incoming`, `outgoing`, `activity`).
* **Ingeniería de Características en SQL:**
  * **Funnel de Entrega:** Agregación y cálculo porcentual del estado de los envíos masivos.
  * **SLA de Primera Respuesta:** Uso de funciones analíticas de ventana (`LEAD()`, `TIMESTAMPDIFF()`) para medir con precisión los minutos transcurridos entre un mensaje entrante del cliente y la primera acción o respuesta del asesor.
  * **Curva de Demanda:** Extracción temporal por hora para modelar curvas de carga operativa.
* **Extracción de Atributos JSON:** Procesamiento de errores técnicos contenidos en la metadata cuando `status = 'failed'`.

---

### 2. Principales Indicadores Clave (KPIs)

| KPI | Valor Obtenido | Descripción |
| :--- | :---: | :--- |
| **Tasa de Fallas Masivas** | **55.68%** | 1,396 envíos no entregados debido a incidencias de integración con la API. |
| **Efectividad de Lectura** | **28.24%** | Mensajes leídos confirmados por los destinatarios finales. |
| **SLA Promedio de Respuesta** | **14.8 min** | Tiempo promedio de atención del asesor ante consultas entrantes. |
| **Tráfico Entrante (Incoming)** | **430 msgs** | Volumen de respuestas generadas por los clientes tras la campaña. |

---

### 3. Visualizaciones y Tablero en Power BI (`data-info.pbix`)

El reporte [`data-info.pbix`](./data-info.pbix) incluye:
* **Filtros Interactivos:** Segmentación por rango de fechas, estado de entrega (`failed`, `delivered`, `read`) y categoría de cliente.
* **Funnel de Distribución Saliente:** Gráfico circular/dona con el ratio de mensajes enviados, entregados, leídos y fallidos.
* **Top de Errores de API (Meta WhatsApp):** Diagnóstico visual de las causas de fallo técnico.
* **Curva de Calor Horaria (WFM):** Gráfico de área/líneas con la distribución del tráfico por hora del día para identificar horas pico.
* **Categorización de Intenciones (NLP):** Distribución de temas consultados: *Consultas Generales*, *Soporte/Información*, *Pedidos/Ventas* y *Quejas/Reclamos*.

---

## 💡 Hallazgos e Insights Estratégicos

1. **Causa Raíz de los Fallos Técnicos (98.4%):**
   * El error predominante fue `#132000 Params Mismatch` de la API de Meta.
   * **Diagnóstico:** Se enviaron registros con variables dinámicas vacías o nulas dentro de las plantillas de WhatsApp.
   * **Recomendación:** Implementar una validación *pre-flight* en el backend que bloquee registros incompletos antes del disparo masivo.

2. **Cuello de Botella Operativo en Turnos:**
   * La curva de demanda demostró una concentración crítica entre las **13:00 y las 16:00 horas**.
   * Durante este intervalo el SLA promedio se degrada debido a la coincidencia con horarios de almuerzo o menor disponibilidad de asesores.
   * **Recomendación:** Reescalonar descansos y reforzar turnos comerciales en la franja de 13:00 a 16:00.

3. **Automatización y Autoservicio:**
   * Gran parte de los mensajes entrantes corresponden a consultas recurrentes y pedidos de catálogo.
   * **Recomendación:** Integrar un bot de triaje interactivo para autogestionar pedidos y transferir a asesores únicamente casos complejos o quejas.

---

## 📂 Contenido del Repositorio

```text
├── data-info.pbix       # Reporte interactivo de Power BI (modelo, medidas y dashboard)
└── README.md            # Documentación técnica y ejecutiva del proyecto
```

---

## 🛠️ Requisitos para Visualizar

1. **Power BI Desktop** (versión actualizada recomendada para compatibilidad de visuales y DAX).
2. Descarga o clona este repositorio:
   ```bash
   git clone https://github.com/zseuz/analisis-campa-a.git
   ```
3. Abre el archivo [`data-info.pbix`](./data-info.pbix) directamente en Power BI Desktop.
