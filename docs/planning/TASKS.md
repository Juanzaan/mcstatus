# MCStatus Project Tasks

## PHASE 0 — Infraestructura y Base Sólida
- [ ] 0.1 Limpieza general del repo
  - [ ] Evaluar estructura actual de carpetas
  - [ ] Crear documento ARCHITECTURE.md
  - [ ] Normalizar imports y dependencias
- [ ] 0.2 Ambiente y dependencias
  - [ ] Evaluar migración a poetry/uv
  - [ ] Configurar pre-commit hooks
  - [ ] Añadir type hints con mypy
- [ ] 0.3 Base de datos
  - [ ] Evaluar migración a PostgreSQL
  - [ ] Configurar Alembic para migraciones
  - [ ] Documentar esquema de tablas

## PHASE 1 — Scraping Profesional
- [ ] 1.1 Proxy Pool + Rotación
  - [ ] Implementar sistema de rotación de proxies
  - [ ] Configurar backoff exponencial
- [ ] 1.2 Scraper Dual
  - [ ] Mejorar scraper requests existente
  - [ ] Completar scraper Selenium
  - [ ] Implementar sistema de fallback automático
- [ ] 1.3 Sistema de Colas
  - [ ] Crear worker pool con límite de concurrencia
  - [ ] Implementar sistema de prioridad
- [ ] 1.4 Métricas del Scraper
  - [ ] Crear tabla de métricas
  - [ ] Dashboard de scraping stats

## PHASE 2 — Detección Premium/Semi-Premium/Cracked
- [/] 2.1 Fingerprinting por protocolo (EN PROGRESO)
  - [x] Implementar DeepProtocolAnalyzer básico
  - [ ] Añadir análisis de timing
  - [ ] Capturar byte signatures
- [/] 2.2 Heurísticas basadas en plugins (PARCIAL)
  - [x] Detectar plugins de auth básicos
  - [ ] Añadir BungeeCord, Geyser, etc.
- [ ] 2.3 Scoring probabilístico
  - [ ] Implementar sistema de scoring
  - [ ] Calibrar umbrales
- [ ] 2.4 Registro de evidencia
  - [ ] Guardar raw handshakes
  - [ ] Log de heurísticas disparadas
- [ ] 2.5 Revisión manual
  - [ ] Panel de inspección de servidor
  - [ ] Botones de relabel/flag

## PHASE 3 — Deduplicación Enterprise
- [x] 3.0 Base de deduplicación (COMPLETADO)
- [ ] 3.1 Nuevas estrategias
  - [ ] Player Sample Matching
  - [ ] MOTD Fuzzy Matching
  - [ ] Geolocalización
  - [ ] Fingerprint temporal
- [ ] 3.2 Motor de canonicalización
  - [ ] Implementar reglas de selección
- [ ] 3.3 UI de Dedup Admin
  - [ ] Panel de gestión de duplicados
  - [ ] Historial de merges
- [ ] 3.4 Dedupe Pipeline
  - [ ] Pipeline diario automatizado
  - [ ] Sistema de reportes

## PHASE 4 — API + Dashboard PRO
- [x] 4.0 API básica (COMPLETADO)
- [ ] 4.1 Mejoras API
  - [ ] Nuevos endpoints (history, aliases, conflicts)
  - [ ] Implementar Redis cache
  - [ ] Filtros avanzados
- [ ] 4.2 Dashboard Admin
  - [ ] Servers Explorer
  - [ ] Deduplication Center
  - [ ] Detection Analyzer
  - [ ] Scrape Metrics
- [ ] 4.3 Dashboard Público
  - [ ] Rankings y tendencias
  - [ ] Filtros avanzados

## PHASE 5 — Data Science / Inteligencia
- [ ] 5.1 Modelos predictivos
  - [ ] Detección de crecimiento
  - [ ] Clustering por tipo
- [ ] 5.2 Patrones sospechosos
  - [ ] Detección de bots
  - [ ] Redes ocultas
- [ ] 5.3 Historial temporal
  - [ ] Análisis de evolución
- [ ] 5.4 Export y Data Layer
  - [ ] CSV/JSON exports
  - [ ] Dataset público

## PHASE 6 — Opcionales Premium
- [ ] 6.1 Discord bot
- [ ] 6.2 Plugin Minecraft
- [ ] 6.3 Rate-limiting API
- [ ] 6.4 Caching distribuido

## 🔥 OPCIÓN A - QUICK WINS (Semana 1) - PRIORIDAD ALTA

### Task 1: Sistema de Fallback Automático para Scraping
- [ ] 1.1 Crear `core/adaptive_scraper.py`
  - [ ] Clase AdaptiveScraper con estrategias múltiples
  - [ ] Método fast_scrape() con requests
  - [ ] Método selenium_scrape() con headless browser
  - [ ] Método rotate_proxy() integrando proxy_manager
  - [ ] Sistema de backoff exponencial
- [ ] 1.2 Crear excepciones personalizadas (RateLimitError, ScraperError)
- [ ] 1.3 Refactorizar scrapers existentes
  - [ ] scrape_namemc_600.py
  - [ ] scrape_namemc_enterprise.py
- [ ] 1.4 Crear tests/test_adaptive_scraper.py

### Task 2: Scoring Probabilístico Semi-Premium
- [ ] 2.1 Modificar core/enterprise/detector.py
  - [ ] Añadir clase DetectionEvidence
  - [ ] Añadir método _calculate_score()
  - [ ] Modificar detect() para retornar evidencias
- [ ] 2.2 Crear config/detection_weights.yaml
- [ ] 2.3 Implementar almacenamiento de evidencias en metadata
- [ ] 2.4 Crear tests/test_detection_scoring.py

### Task 3: Dashboard de Métricas de Scraping
- [ ] 3.1 Crear migración 002_scrape_metrics.sql
- [ ] 3.2 Crear core/scrape_metrics.py
  - [ ] Método log_scrape_attempt()
  - [ ] Método get_metrics()
- [ ] 3.3 Añadir endpoint /api/scraping/metrics en core/api.py
- [ ] 3.4 Crear web/static/scraping_metrics.html
- [ ] 3.5 Crear web/static/scraping_metrics.js con Chart.js
- [ ] 3.6 Integrar logging en AdaptiveScraper

## 🎯 Decisión Inmediata Requerida
**¿Qué task de Opción A empezamos primero?**
- [ ] Task 1: Scraping con fallback (desbloquea scraping inmediatamente)
- [ ] Task 2: Scoring probabilístico (mejora detección YA)
- [ ] Task 3: Dashboard métricas (visibilidad del sistema)
