-- =============================================================================
-- PROYECTO: ANALÍTICA DE CAMPAÑA WHATSAPP BPO
-- BASE DE DATOS: MySQL 8.0+
-- TABLA: mensajeria
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. FUNNEL DE ENTREGA (Tasa de éxito de mensajes salientes)
-- Mide el porcentaje de mensajes salientes por estado (read, delivered, failed).
-- -----------------------------------------------------------------------------
WITH MensajesOutgoing AS (
    SELECT 
        status,
        COUNT(*) AS total_mensajes
    FROM mensajeria
    WHERE message_type = 'outgoing'
    GROUP BY status
),
TotalesGbl AS (
    SELECT SUM(total_mensajes) AS total_enviados FROM MensajesOutgoing
)
SELECT 
    m.status AS estado_entrega,
    m.total_mensajes,
    ROUND((m.total_mensajes * 100.0) / t.total_enviados, 2) AS porcentaje_contribucion
FROM MensajesOutgoing m
CROSS JOIN TotalesGbl t
ORDER BY m.total_mensajes DESC;


-- -----------------------------------------------------------------------------
-- 2. SLA DE RESPUESTA OPERATIVA (Tiempo promedio en minutos)
-- Calcula el intervalo entre un mensaje incoming del cliente y la siguiente 
-- acción del asesor (activity u outgoing) dentro de la misma conversación.
-- -----------------------------------------------------------------------------
WITH SecuenciaConversacion AS (
    SELECT 
        conversation_id,
        message_type,
        created_at,
        LEAD(created_at) OVER (
            PARTITION BY conversation_id 
            ORDER BY created_at
        ) AS fecha_siguiente_evento,
        LEAD(message_type) OVER (
            PARTITION BY conversation_id 
            ORDER BY created_at
        ) AS tipo_siguiente_evento
    FROM mensajeria
)
SELECT 
    ROUND(
        AVG(
            TIMESTAMPDIFF(SECOND, created_at, fecha_siguiente_evento) / 60.0
        ), 2
    ) AS sla_promedio_respuesta_minutos
FROM SecuenciaConversacion
WHERE message_type = 'incoming'
  AND tipo_siguiente_evento IN ('activity', 'outgoing')
  AND fecha_siguiente_evento IS NOT NULL;


-- -----------------------------------------------------------------------------
-- 3. CURVA DE CALOR HORARIA (Dimensionamiento de Personal / WFM)
-- Muestra el volumen de mensajes entrantes (incoming) agrupados por hora.
-- -----------------------------------------------------------------------------
SELECT 
    EXTRACT(HOUR FROM created_at) AS hora_del_dia,
    COUNT(*) AS volumen_mensajes_incoming
FROM mensajeria
WHERE message_type = 'incoming'
GROUP BY EXTRACT(HOUR FROM created_at)
ORDER BY hora_del_dia ASC;