# Minecraft Server Dashboard

A modern, real-time dashboard for tracking and monitoring Minecraft servers. Features automated scanning, server status tracking, and an intuitive web interface with advanced filtering and search capabilities.

## Features

- 🎮 **Real-time Server Monitoring** - Track 1700+ Minecraft servers
- 📊 **Statistics Dashboard** - View player counts, server status, and trends
- 🔍 **Advanced Filtering** - Filter by premium/cracked, player count, version
- 🔄 **Auto Background Scanning** - Automated server updates every 30 minutes
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile
- 🚀 **Backend Pagination** - Fast loading for large server lists
- 💾 **Export Functionality** - Export data to JSON/CSV
- ⚡ **Health Monitoring** - Built-in health check endpoints

## Quick Start

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mcstatus
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment (optional)**
   
   Copy `.env.example` to `.env` and customize:
   ```bash
   cp .env.example .env
   ```

4. **Run the API server**
   ```bash
   python core/api.py
   ```

5. **Access the dashboard**
   
   Open your browser to: `http://localhost:5000/`

## Environment Variables

Create a `.env` file in the root directory to customize configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `5000` | API server port |
| `DEBUG` | `False` | Enable debug mode |
| `DATA_DIR` | `./data` | Directory for data files |
| `SCHEDULER_ENABLED` | `True` | Enable background scanning |
| `REFRESH_INTERVAL_MINUTES` | `30` | Status refresh interval |
| `FULL_SCAN_INTERVAL_HOURS` | `6` | Full scan interval |
| `CORS_ORIGINS` | `*` | CORS allowed origins |
| `DEFAULT_PAGE_SIZE` | `50` | Default pagination size |
| `MAX_PAGE_SIZE` | `200` | Maximum pagination size |

## Scanner Configuration (`config/scraper_config.yaml`)

The Enterprise Scanner uses a YAML file for advanced configuration.

| Section | Parameter | Default | Description |
|---------|-----------|---------|-------------|
| **logging** | `level` | `INFO` | Log verbosity (DEBUG, INFO, WARNING) |
| | `json_format` | `true` | Enable structured JSON logging |
| **resources** | `max_workers_global` | `500` | Maximum concurrent threads |
| | `auto_tune` | `true` | Auto-adjust workers based on CPU/RAM |
| **rate_limiting** | `global_rpm` | `300` | Global requests per minute limit |
| | `adaptive` | `true` | Slow down on errors (Auto-throttle) |
| **proxies** | `enabled` | `false` | Enable proxy rotation |
| | `mode` | `round_robin` | Rotation mode (round_robin, weighted) |
| | `cooldown_seconds` | `300` | Cooldown for failed proxies |

## API Endpoints

### Server Endpoints

**GET `/api/servers`** - Get paginated list of servers
- Query params: `page`, `limit`, `category`, `search`, `sort`, `min_players`, `max_players`, `version`
- Returns: Paginated server list with metadata

**GET `/api/servers/all`** - Get all servers (unpaginated)
- Returns: Complete server list

**GET `/api/servers/<ip>`** - Get specific server details
- Returns: Detailed server information

**GET `/api/stats`** - Get global statistics
- Returns: Total servers, players, premium/cracked counts

### Health & Monitoring

**GET `/health`** - Basic health check
- Returns: `{ "status": "healthy" }`

**GET `/api/health`** - Detailed health check
- Returns: System health with data file, scheduler, and loading checks

### Scheduler

**GET `/api/scheduler/status`** - Get scheduler status
- Returns: Scheduler running state and job information

**POST `/api/scheduler/run_now?type=<type>`** - Trigger manual scan
- Types: `refresh_status`, `full_scan`

For detailed API documentation, see [docs/API.md](docs/API.md)

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=core --cov-report=html

# Run specific test file
pytest tests/test_api_servers.py -v

# Use the convenience script (Windows)
run_tests.bat
```

Current test coverage: 13+ tests covering all major endpoints

## Docker Deployment

### Prerequisites
- Docker 20.10+ 
- Docker Compose 2.0+

### Quick Start with Docker

**Development Mode:**
```bash
# Build and run
docker-compose up

# Access dashboard at http://localhost:5000
```

**Production Mode:**
```bash
# Build and run production image
docker-compose -f docker-compose.prod.yml up -d

# Access dashboard at http://localhost:8000
```

### Manual Docker Commands

**Build Development Image:**
```bash
docker build --target development -t mcstatus:dev .
```

**Build Production Image:**
```bash
docker build --target production -t mcstatus:prod .
```

**Run Container:**
```bash
# Development
docker run -d -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  --name mcstatus mcstatus:dev

# Production
docker run -d -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e DEBUG=False \
  -e WORKERS=4 \
  --name mcstatus-prod mcstatus:prod
```

### Environment Variables for Docker

Set in `docker-compose.yml` or pass with `-e`:

| Variable | Development | Production |
|----------|-------------|------------|
| `DEBUG` | `True` | `False` |
| `API_PORT` | `5000` | `8000` |
| `WORKERS` | `1` | `4` |
| `SCHEDULER_ENABLED` | `True` | `True` |

### Health Checks

Docker includes automatic health checks:
```bash
docker ps  # Shows health status
docker inspect mcstatus | grep Health -A 10
```

### Testing in Docker

Run tests inside container:
```bash
# Windows
scripts\test_in_docker.bat

# Or manually
docker run --rm mcstatus:dev pytest tests/ -v
```

### Logs

View container logs:
```bash
docker logs -f mcstatus
```

## Project Structure

```
mcstatus/
├── core/
│   ├── api.py              # Flask API server
│   ├── config.py           # Configuration management
│   ├── scheduler.py        # Background task scheduler
│   └── server_merger.py    # Server data merging logic
├── web/
│   ├── dashboard.html      # Main dashboard page
│   └── static/
│       └── dashboard.js    # Frontend JavaScript
├── tests/
│   ├── test_api_servers.py # Server endpoint tests
│   ├── test_api_stats.py   # Stats endpoint tests
│   └── test_health.py      # Health check tests
├── data/
│   └── unified_servers.json # Server database
├── .env.example            # Environment template
├── requirements.txt        # Python dependencies
└── run_tests.bat          # Test runner script
```

## Development

### Running in Development Mode

```bash
# Enable debug mode in .env
DEBUG=True

# Run the server
python core/api.py
```

### Code Quality

```bash
# Install development dependencies
pip install flake8 black

# Run linter
flake8 core/ --max-line-length=120

# Format code
black core/
```

## Deployment

### Docker (Recommended)

Coming soon - Docker support is planned after pre-production improvements are complete.

### Manual Deployment

1. Set up a production server (Ubuntu, Debian, etc.)
2. Install Python 3.11+
3. Install dependencies: `pip install -r requirements.txt`
4. Configure environment variables for production
5. Use a process manager (systemd, supervisor) to run `core/api.py`
6. Set up Nginx as reverse proxy (recommended)
7. Enable HTTPS with Let's Encrypt

## Troubleshooting

### Dashboard not loading

- Check API server is running: `curl http://localhost:5000/api/stats`
- Verify data file exists: `ls data/unified_servers.json`
- Check health endpoint: `curl http://localhost:5000/api/health`

### No servers appearing

- Run manual scan: `curl -X POST http://localhost:5000/api/scheduler/run_now?type=refresh_status`
- Check scheduler status: `curl http://localhost:5000/api/scheduler/status`

### Tests failing

- Ensure API server is NOT running while testing
- Clear cache: `pytest --cache-clear`
- Check Python version: `python --version` (requires 3.11+)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Submit a pull request

## License

[Add your license here]

## Acknowledgments

- Built with Flask, APScheduler, and mcstatus
- Dashboard UI inspired by modern web design best practices
