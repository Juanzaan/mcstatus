# Opción A - Quick Wins Implementation Plan

**Timeline**: Semana 1  
**Objetivo**: Desbloquear problemas inmediatos y mejorar estabilidad del sistema

---

## 🎯 Overview

Tres mejoras críticas de alto impacto:
1. **Scraping NameMC con Fallback Automático** - Resolver rate limiting de 429 errors
2. **Scoring Probabilístico para Semi-Premium** - Mejorar precisión de detección
3. **Dashboard de Métricas de Scraping** - Visibilidad del sistema

---

## Task 1: Scraping NameMC - Sistema de Fallback Automático

### Problema Actual
- Scraper simple con `requests` falla con 429 (rate limiting)
- Scraper Selenium existe pero no hay fallback automático
- No hay rotación inteligente de estrategias

### Solución Propuesta

```python
class AdaptiveScraper:
    def scrape_page(self, url):
        try:
            # Strategy 1: Fast requests-based
            return self.fast_scrape(url)
        except RateLimitError:
            # Strategy 2: Rotate proxy + retry
            self.rotate_proxy()
            return self.fast_scrape(url)
        except ScraperError:
            # Strategy 3: Selenium fallback
            return self.selenium_scrape(url)
```

### Implementación

#### 1.1 Crear `core/adaptive_scraper.py`
- [ ] Clase `AdaptiveScraper` con estrategias múltiples
- [ ] Método `fast_scrape()` usando requests + cloudscraper
- [ ] Método `selenium_scrape()` con headless browser
- [ ] Método `rotate_proxy()` integrando `proxy_manager.py`
- [ ] Sistema de backoff exponencial

#### 1.2 Excepciones personalizadas
```python
class RateLimitError(Exception): pass
class ScraperError(Exception): pass
```

#### 1.3 Integrar con scrapers existentes
- [ ] Refactorizar `scrape_namemc_600.py`
- [ ] Refactorizar `scrape_namemc_enterprise.py`
- [ ] Usar `AdaptiveScraper` en lugar de lógica directa

#### 1.4 Testing
- [ ] Crear `tests/test_adaptive_scraper.py`
- [ ] Test de fallback automático
- [ ] Test de rotación de proxy
- [ ] Test de Selenium fallback

### Archivos a Modificar/Crear
- **NUEVO**: `core/adaptive_scraper.py`
- **MODIFICAR**: `scrape_namemc_600.py`
- **MODIFICAR**: `scrape_namemc_enterprise.py`
- **NUEVO**: `tests/test_adaptive_scraper.py`

### Tiempo Estimado
2-3 días

---

## Task 2: Scoring Probabilístico para Semi-Premium

### Problema Actual
- Detección es binaria (sí/no) basada en heurísticas
- No hay confianza asociada a la clasificación
- Difícil auditar por qué un servidor fue clasificado de cierta forma

### Solución Propuesta

Sistema de scoring donde cada señal contribuye puntos:

```python
score = 0.0
evidence = []

# Señales positivas (incrementan probabilidad de semi-premium)
if has_auth_plugin: 
    score += 0.3
    evidence.append("AUTH_PLUGIN_DETECTED")
    
if is_known_network: 
    score += 0.4
    evidence.append("KNOWN_SEMI_PREMIUM_NETWORK")
    
if large_player_count and hybrid_keywords: 
    score += 0.2
    evidence.append("LARGE_HYBRID_SERVER")

# Señales negativas (reducen probabilidad)
if premium_protocol: 
    score -= 0.5
    evidence.append("PREMIUM_PROTOCOL")

# Clasificación final
if score >= 0.8: return PREMIUM
elif score >= 0.4: return SEMI_PREMIUM
else: return NON_PREMIUM
```

### Implementación

#### 2.1 Modificar `core/enterprise/detector.py`

**Añadir clase `DetectionEvidence`**:
```python
@dataclass
class DetectionEvidence:
    signal: str
    weight: float
    description: str
    timestamp: datetime
```

**Añadir método `_calculate_score()`**:
- [ ] Evaluar todas las señales
- [ ] Acumular score con pesos configurables
- [ ] Retornar score + lista de evidencias

#### 2.2 Configuración de pesos
- [ ] Crear `config/detection_weights.yaml`
- [ ] Definir pesos para cada señal
- [ ] Permitir ajuste manual

#### 2.3 Almacenar evidencias
- [ ] Modificar `detect()` para retornar evidencias
- [ ] Guardar en metadata del servidor
- [ ] Formato: `{"score": 0.7, "evidence": [...], "classification": "SEMI_PREMIUM"}`

#### 2.4 Testing
- [ ] Tests para scoring con diferentes combinaciones
- [ ] Test de umbrales
- [ ] Test de evidencias guardadas

### Archivos a Modificar/Crear
- **MODIFICAR**: `core/enterprise/detector.py`
- **NUEVO**: `config/detection_weights.yaml`
- **NUEVO**: `tests/test_detection_scoring.py`

### Tiempo Estimado
2-3 días

---

## Task 3: Dashboard de Métricas de Scraping

### Problema Actual
- No hay visibilidad de qué está pasando con los scrapers
- Difícil saber si hay problemas de rate limiting
- No se trackean servidores nuevos por día

### Solución Propuesta

Dashboard con métricas en tiempo real:
- Requests por minuto
- Tasa de éxito/error
- Servidores nuevos descubiertos hoy
- Errores por tipo (429, timeout, etc.)
- Último scrape exitoso

### Implementación

#### 3.1 Tabla de métricas en DB

```sql
CREATE TABLE scrape_metrics (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    requests_count INTEGER,
    success_count INTEGER,
    error_count INTEGER,
    error_type VARCHAR(50),
    new_servers_count INTEGER,
    duration_seconds FLOAT
);
```

#### 3.2 Logger de métricas
- [ ] Crear `core/scrape_metrics.py`
- [ ] Método `log_scrape_attempt(success, error_type, duration)`
- [ ] Método `get_metrics(timeframe='24h')`

#### 3.3 API Endpoint
- [ ] Añadir endpoint `/api/scraping/metrics`
- [ ] Retornar métricas agregadas
- [ ] Filtros por tiempo (1h, 24h, 7d)

#### 3.4 Dashboard UI
- [ ] Crear `web/static/scraping_metrics.html`
- [ ] Gráficos con Chart.js:
  - Requests/min (línea)
  - Tasa de éxito (gauge)
  - Nuevos servidores (barra)
  - Errores por tipo (pie)

#### 3.5 Integrar con scrapers
- [ ] Modificar `AdaptiveScraper` para loggear métricas
- [ ] Modificar scrapers existentes

### Archivos a Modificar/Crear
- **NUEVO**: `core/scrape_metrics.py`
- **NUEVO**: `scripts/migrations/002_scrape_metrics.sql`
- **MODIFICAR**: `core/api.py` (nuevo endpoint)
- **NUEVO**: `web/static/scraping_metrics.html`
- **NUEVO**: `web/static/scraping_metrics.js`
- **MODIFICAR**: `core/adaptive_scraper.py`

### Tiempo Estimado
3-4 días

---

## 📊 Resumen de Entregables

Al completar Opción A tendrás:

✅ **Sistema de scraping resiliente** que nunca se bloquea  
✅ **Detección semi-premium auditable** con scoring y evidencias  
✅ **Visibilidad completa** del sistema de scraping vía dashboard

---

## 🔄 Orden de Ejecución Sugerido

1. **Task 1** primero (desbloquea scraping inmediatamente)
2. **Task 3** segundo (te da visibilidad mientras trabajas en Task 2)
3. **Task 2** tercero (ya con datos fluyendo bien)

O alternativamente:

1. **Task 2** primero (si detección es más urgente)
2. **Task 1** segundo
3. **Task 3** tercero

---

## 🚦 Criterios de Completitud

### Task 1 - Scraping
- [ ] Scraper puede completar 600 páginas sin fallar
- [ ] Fallback a Selenium funciona automáticamente
- [ ] Tests pasan

### Task 2 - Scoring
- [ ] Cada servidor tiene score + evidencias
- [ ] Scores son consistentes y calibrados
- [ ] Tests pasan

### Task 3 - Métricas
- [ ] Dashboard muestra métricas en tiempo real
- [ ] API endpoint funciona correctamente
- [ ] Gráficos se actualizan automáticamente

---

## 🎯 Próximo Paso

**¿Qué task querés que empiece primero?**
- Task 1: Scraping con fallback
- Task 2: Scoring probabilístico
- Task 3: Dashboard de métricas
