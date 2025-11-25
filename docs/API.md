# API Documentation

Complete reference for all API endpoints in the Minecraft Server Dashboard.

## Base URL

```
http://localhost:5000
```

## Authentication

Currently, the API does not require authentication. For production deployments, consider adding API keys or OAuth.

---

## Server Endpoints

### GET `/api/servers`

Get a paginated list of servers with optional filtering and sorting.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `1` | Page number (1-indexed) |
| `limit` | integer | `50` | Items per page (max: 200) |
| `category` | string | `all` | Filter by category: `all`, `premium`, `non_premium`, `offline`, `favorites` |
| `search` | string | - | Search in server name, IP, or description |
| `min_players` | integer | - | Minimum online player count |
| `max_players` | integer | - | Maximum online player count |
| `version` | string | - | Filter by Minecraft version |
| `sort` | string | `players` | Sort by: `players`, `name`, `status` |

**Example Request:**

```bash
curl "http://localhost:5000/api/servers?page=1&limit=10&category=premium&sort=players"
```

**Response Format:**

```json
{
  "success": true,
  "servers": [
    {
      "ip": "hypixel.net",
      "name": "Hypixel",
      "description": "The largest Minecraft server",
      "online": 50000,
      "max": 200000,
      "version": "1.8-1.20",
      "premium": true,
      "status": "online",
      "auth_mode": "PREMIUM",
      "alternate_ips": ["mc.hypixel.net"],
      "last_seen": "2025-11-22 02:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total_items": 111,
    "total_pages": 12
  }
}
```

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid parameters

---

### GET `/api/servers/all`

Get the complete list of all servers without pagination.

**Example Request:**

```bash
curl "http://localhost:5000/api/servers/all"
```

**Response Format:**

```json
{
  "success": true,
  "count": 1712,
  "servers": [...]
}
```

**Status Codes:**
- `200 OK` - Success

---

### GET `/api/servers/<ip>`

Get detailed information about a specific server.

**Path Parameters:**
- `ip` - Server IP address or hostname

**Example Request:**

```bash
curl "http://localhost:5000/api/servers/hypixel.net"
```

**Response Format:**

```json
{
  "success": true,
  "server": {
    "ip": "hypixel.net",
    "name": "Hypixel",
    "description": "The largest Minecraft server",
    "online": 50000,
    "max": 200000,
    "version": "1.8-1.20",
    "premium": true,
    "status": "online",
    "auth_mode": "PREMIUM",
    "alternate_ips": ["mc.hypixel.net"],
    "last_seen": "2025-11-22 02:00:00"
  }
}
```

**Status Codes:**
- `200 OK` - Success
- `404 Not Found` - Server not found

---

## Statistics Endpoints

### GET `/api/stats`

Get global statistics for all servers.

**Example Request:**

```bash
curl "http://localhost:5000/api/stats"
```

**Response Format:**

```json
{
  "success": true,
  "stats": {
    "total_servers": 1712,
    "total_players": 204970,
    "premium_count": 111,
    "cracked_count": 659
  }
}
```

**Status Codes:**
- `200 OK` - Success

---

## Health & Monitoring Endpoints

### GET `/health`

Basic health check endpoint for load balancers and monitoring systems.

**Example Request:**

```bash
curl "http://localhost:5000/health"
```

**Response Format:**

```json
{
  "status": "healthy",
  "service": "mc-scanner-api"
}
```

**Status Codes:**
- `200 OK` - Service is healthy

---

### GET `/api/health`

Detailed health check with system information and diagnostics.

**Example Request:**

```bash
curl "http://localhost:5000/api/health"
```

**Response Format:**

```json
{
  "status": "healthy",
  "service": "mc-scanner-api",
  "timestamp": "2025-11-22T02:51:06.515410",
  "checks": {
    "data_file": {
      "status": "ok",
      "path": "C:\\Users\\...\\data\\unified_servers.json",
      "exists": true
    },
    "data_freshness": {
      "status": "ok",
      "last_updated": "2025-11-22T02:30:00",
      "age_minutes": 21.10
    },
    "scheduler": {
      "status": "ok",
      "details": {
        "running": true,
        "jobs": 2
      }
    },
    "data_loading": {
      "status": "ok",
      "server_count": 1712,
      "stats": {
        "total_servers": 1712,
        "total_players": 204970,
        "premium_count": 111,
        "cracked_count": 659
      }
    }
  }
}
```

**Health Status Values:**
- `healthy` - All checks passed
- `degraded` - Some checks returned warnings
- `unhealthy` - One or more checks failed

**Status Codes:**
- `200 OK` - Service is healthy or degraded
- `503 Service Unavailable` - Service is unhealthy

---

## Scheduler Endpoints

### GET `/api/scheduler/status`

Get the current status of the background scheduler.

**Example Request:**

```bash
curl "http://localhost:5000/api/scheduler/status"
```

**Response Format:**

```json
{
  "success": true,
  "status": {
    "running": true,
    "jobs": [
      {
        "id": "refresh_status",
        "name": "Refresh Server Status",
        "next_run": "2025-11-22T03:00:00"
      },
      {
        "id": "full_scan",
        "name": "Full Server Merge",
        "next_run": "2025-11-22T08:00:00"
      }
    ],
    "last_run": {
      "refresh_status": "2025-11-22T02:30:00",
      "full_scan": "2025-11-22T02:00:00"
    }
  }
}
```

**Status Codes:**
- `200 OK` - Success

---

### POST `/api/scheduler/run_now`

Manually trigger a background task.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | Yes | Task type: `refresh_status` or `full_scan` |

**Example Request:**

```bash
curl -X POST "http://localhost:5000/api/scheduler/run_now?type=refresh_status"
```

**Response Format:**

```json
{
  "success": true,
  "message": "Triggered refresh_status"
}
```

**Status Codes:**
- `200 OK` - Task triggered successfully
- `400 Bad Request` - Invalid task type

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "success": false,
  "error": "Error message description"
}
```

**Common Error Status Codes:**
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service unhealthy

---

## Rate Limiting

Currently, there is no rate limiting implemented. For production deployments, consider implementing rate limiting to prevent abuse.

## CORS

By default, CORS is enabled for all origins (`*`). Configure the `CORS_ORIGINS` environment variable to restrict access in production.

## Pagination Best Practices

- Use reasonable `limit` values (recommended: 50-100)
- Maximum `limit` is capped at 200
- Always check `pagination.total_pages` to know when to stop
- Cache results when possible to reduce load

## Example Client Implementation

```javascript
// Fetch servers with pagination
async function fetchServers(page = 1, filters = {}) {
  const params = new URLSearchParams({
    page,
    limit: 50,
    ...filters
  });
  
  const response = await fetch(`/api/servers?${params}`);
  const data = await response.json();
  
  return data;
}

// Usage
const result = await fetchServers(1, {
  category: 'premium',
  min_players: 100,
  sort: 'players'
});

console.log(`Showing ${result.servers.length} of ${result.pagination.total_items} servers`);
```
