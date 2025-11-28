# 🧭 ROADMAP DEFINITIVO PARA MCSTATUS

Roadmap completo para transformar mcstatus en un sistema profesional y escalable de monitoreo de servidores Minecraft.

---

## PHASE 0 — Auditoría Técnica y Base Sólida

**Objetivo**: Asegurar que la base del proyecto es escalable, mantenible y consistente antes de construir encima.

### 0.1 Limpieza General del Repo
- [ ] Reorganizar carpetas: `/scrapers`, `/core`, `/api`, `/dashboard`, `/deduplication`, `/detectors`, `/tests`
- [ ] Normalizar nombres de archivos, imports y dependencias
- [ ] Revisar `.gitignore`
- [ ] Agregar documentación de estructura interna en `ARCHITECTURE.md`

### 0.2 Ambiente y Dependencias
- [ ] Pasar a `poetry` o `uv` para manejar dependencias
- [ ] Crear `requirements-minimal.txt` y `requirements-full.txt`
- [ ] Añadir pre-commit hooks:
  - [ ] Black (formatting)
  - [ ] isort (imports)
  - [ ] flake8 (linting)
  - [ ] mypy (type checking)

### 0.3 Base de Datos
- [ ] Migrar a PostgreSQL (si usás SQLite, se queda chico)
- [ ] Crear esquema versionado con Alembic
- [ ] Convenciones de tablas:
  - `servers`
  - `aliases`
  - `samples`
  - `scrape_logs`
  - `detections`
  - `dedupe_history`

**Entregable**: `ARCHITECTURE.md`, DB sólida, repo limpio, dependencias correctas

---

## PHASE 1 — Scraping Profesional

**Objetivo**: Anti-rate-limits, anti-ban, escalable a 10k+ servidores

### 1.1 Proxy Pool + Rotación
- [ ] Implementar rotación automática por request
- [ ] Soporte para:
  - [ ] Proxies HTTP/HTTPS
  - [ ] Proxies residenciales (opcional)
  - [ ] Tor (opcional)
- [ ] Backoff exponencial inteligente:
  - Si NameMC → 429 → esperar + rotar IP

### 1.2 Scraper Dual
- [ ] Scraper por `requests` (rápido)
- [ ] Scraper `Selenium` (lento pero seguro)
- [ ] Automatizar fallback:
  ```python
  if simple_scrape fails 3 times:
      use selenium_retry
  ```

### 1.3 Sistema de Colas
- [ ] Worker pool con:
  - [ ] Límite de concurrencia
  - [ ] Monitoreo de éxito/errores
  - [ ] Prioridad (fresh servers > old servers)

### 1.4 Métricas del Scraper
- [ ] Crear tabla + dashboard:
  - Requests por minuto
  - Tasa de éxito
  - Número de servidores nuevos por día
  - Errores totales por página

**Entregable**: Un scraper industrial que nunca se bloquea y escala a 10k servidores

---

## PHASE 2 — Detección Premium/Semi-Premium/Cracked (Versión PRO)

**Objetivo**: Sistema robusto, auditable y explicable de clasificación de servidores

### 2.1 Fingerprinting por Protocolo
- [ ] Implementar análisis de nivel bajo:
  - [ ] Análisis del handshake
  - [ ] Tiempo de respuesta para cada step
  - [ ] Patrones de disconnect
  - [ ] Análisis de protocolo en crudo (byte signatures)

### 2.2 Heurísticas Basadas en Plugins
- [ ] Detectar plugins conocidos:
  - [ ] BungeeCord
  - [ ] FlameCord
  - [ ] Geyser
  - [ ] SkinsRestorer
  - [ ] AuthMe
  - [ ] FastLogin
  - [ ] Floodgate
- [ ] Detectar combinaciones sospechosas

### 2.3 Scoring Probabilístico
- [ ] Modelo simple donde cada indicio suma/resta score
- [ ] Resultado final:
  - Premium (score > 0.8)
  - Semi-Premium (0.4–0.8)
  - Cracked (score < 0.4)

### 2.4 Registro de Evidencia
- [ ] Guardar:
  - [ ] Raw handshake
  - [ ] Heurísticas disparadas
  - [ ] Logs de detección
  - [ ] Timestamp

### 2.5 Revisión Manual
- [ ] Crear panel para "inspeccionar servidor" con:
  - [ ] Resumen de detección
  - [ ] Evidencias
  - [ ] Botones: RELABEL, FLAG AS SUSPECT

**Entregable**: Detectores robustos, auditables y explicables

---

## PHASE 3 — Deduplicación (Versión Enterprise)

**Objetivo**: Perfeccionar el sistema de deduplicación al nivel de NameMC real

### 3.1 Nuevas Estrategias de Matching

#### Player Sample Matching
- [ ] Si comparten ≥30% de jugadores en 3 días → alta probabilidad de duplicado

#### MOTD Fuzzy Matching
- [ ] Similitud difusa
- [ ] Normalización por colores
- [ ] Ignorar exclamaciones/random characters

#### Geolocalización
- [ ] Si 2 IPs difieren pero resuelven a mismas coords → posible alias

#### Fingerprint Temporal
- [ ] Coincidencia de timestamps de reinicios
- [ ] Latencia similar

### 3.2 Motor de Canonicalización
- [ ] Regla general:
  ```
  Pick canonical server based on:
  - earliest detection
  - highest uptime
  - most samples collected
  ```

### 3.3 UI de Dedup Admin
- [ ] Permitir:
  - [ ] Ver potenciales duplicados
  - [ ] Aprobar merge
  - [ ] Revertir merge
  - [ ] Añadir alias manual
  - [ ] Ver historial de merges

### 3.4 Dedupe Pipeline
- [ ] Crear pipeline diario:
  - [ ] Correr dedupe fuerte
  - [ ] Generar reportes
  - [ ] Aplicar merges automáticos (bajo riesgo)
  - [ ] Enviar "manual review" para casos dudosos

**Entregable**: Deduplication Engine profesional y totalmente auditable

---

## PHASE 4 — API + Dashboard PRO

**Objetivo**: Panel visual completo estilo NameMC Premium

### 4.1 Mejoras API

#### Endpoints Nuevos
- [ ] `/api/server/{id}/history`
- [ ] `/api/server/{id}/aliases`
- [ ] `/api/dedupe/conflicts`
- [ ] `/api/detection/{id}/evidence`

#### Caché
- [ ] Redis o SQLite FTS con TTL

#### Filtros Avanzados
- [ ] Versión
- [ ] Región
- [ ] Premium state
- [ ] Tags

### 4.2 Dashboard Admin
- [ ] Secciones:
  - [ ] Servers Explorer
  - [ ] Deduplication Center
  - [ ] Detection Analyzer
  - [ ] Scrape Metrics
  - [ ] Alerts Panel
  - [ ] Activity Log

### 4.3 Dashboard Público
- [ ] Ranking servers por:
  - [ ] Uptime
  - [ ] Jugadores
  - [ ] Crecimiento
- [ ] Tendencias semanales
- [ ] Top servers nuevos
- [ ] Filtros por versión

**Entregable**: Panel visual completo estilo NameMC Premium

---

## PHASE 5 — Data Science / Inteligencia del Sistema

**Objetivo**: Sistema inteligente comparable a NameMC Analytics

### 5.1 Modelos Predictivos
- [ ] Detectar servers en crecimiento
- [ ] Detectar servers que están por morir
- [ ] Clustering por tipo de comunidad
- [ ] Recomendación de servidores

### 5.2 Detectar Patrones Sospechosos
- [ ] Ejemplos:
  - [ ] Bots inflando player count
  - [ ] Redes ocultas bajo varios dominios
  - [ ] Servers que se renuevan para ocultar historial

### 5.3 Historial y Análisis Temporal
- [ ] Evolución del player count
- [ ] Cambios de MOTD
- [ ] Cambio de versión
- [ ] Migración de IP

### 5.4 Export y Data Layer
- [ ] Exportar CSVs
- [ ] Dataset público
- [ ] API para investigación (opcional)

**Entregable**: Un sistema inteligente comparable a NameMC Analytics

---

## PHASE 6 — Opcionales Premium

### 6.1 Integración con Discord
- [ ] Bot que muestra stats
- [ ] Alertas de duplicados
- [ ] Notificaciones de servers nuevos

### 6.2 Integración con Minecraft Directo
- [ ] Plugin para servidores para enviar metadatos opt-in
  - Versión
  - Categoría
  - Tags

### 6.3 Rate-Limiting a tu API
- [ ] Proteger contra scrapers externos

### 6.4 Caching Distribuido
- [ ] Cloudflare workers
- [ ] Edge caching por región

---

## 📊 Estado General por Fase

| Fase | Nombre | Estado | Prioridad |
|------|--------|--------|-----------|
| 0 | Infraestructura | 🟡 Parcial | Alta |
| 1 | Scraping | 🟡 Parcial | Alta |
| 2 | Detección | 🟡 Parcial | Media |
| 3 | Deduplicación | 🟢 Base completa | Media |
| 4 | Dashboard + API | 🟢 Base completa | Baja |
| 5 | Inteligencia | 🔴 No iniciado | Baja |
| 6 | Extras | 🔴 No iniciado | Baja |

---

## 🎯 Próximos Pasos Recomendados

1. **Completar Phase 0** - Solidificar la base del proyecto
2. **Mejorar Phase 1** - Resolver problemas de scraping con NameMC
3. **Refinar Phase 2** - Mejorar detección semi-premium
4. **Extender Phase 3** - Implementar features avanzados de deduplicación
