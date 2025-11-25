# 🎮 Minecraft Server Scanner - Professional Monitoring Platform

A comprehensive, production-ready Minecraft server monitoring and analytics platform with automated scanning, historical tracking, real-time notifications, and an advanced web dashboard.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

### Core Functionality
- 🔍 **Automated Server Discovery** - Scrapes multiple public sources including minecraft-server-list.com for 1.21+ servers
- 📊 **SQLite Historical Database** - Track server stats, player trends, and changes over time
- ⏱️ **Scheduled Scanning** - Hourly automated scans with configurable schedule
- 🌍 **Geolocation Cache** - Smart caching to avoid API rate limits
- 🔐 **Authentication Detection** - Low-level socket handshake to detect Premium/Cracked servers
- 👥 **Player Tracking** - Premium vs Cracked player classification, new player detection

### Advanced Features
- 📈 **Progress Bars** - Real-time scanning progress with `tqdm`
- 🔄 **Retry Logic** - Exponential backoff for failed requests
- 🔔 **Discord/Email Notifications** - Alerts for server offline, player spikes, new premium servers
- 📤 **CSV/JSON Export** - Export data for external analysis
- 🎨 **Dark/Light Mode Dashboard** - Beautiful glassmorphic UI with theme toggle
- 🗺️ **Interactive Map** - Leaflet.js map with marker clustering
- 📊 **Trend Charts** - Chart.js visualizations for player count trends
- 🐳 **Docker Support** - One-command deployment with docker-compose

### REST API
- `GET /api/servers` - List servers with filtering
- `GET /api/servers/<ip>` - Server details with trends
- `GET /api/stats` - Global statistics
- `GET /api/trends` - Historical trend data
- `POST /api/refresh` - Trigger IP fetcher
- `GET /api/export/csv` - Download CSV export
- `GET /api/export/json` - Download JSON export

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and navigate
git clone <your-repo>
cd mcstatus

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

Access dashboard at `http://localhost:5000/dashboard.html`

### Option 2: Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python database.py

# Fetch server IPs
python public_ip_fetcher.py

# Run a single scan
python escaner_completo.py

# Start scheduler for automated scans
python scheduler.py

# (In another terminal) Start API server
python api.py

# Open dashboard.html in browser
```

## ⚙️ Configuration

Edit `settings.json` to customize:

```json
{
  "scan_schedule": "0 * * * *",
  "scanner": {
    "max_workers": 50,
    "timeout": 3,
    "show_progress": true
  },
  "rate_limits": {
    "geolocation_delay": 0.1,
    "max_retries": 3,
    "retry_backoff": 2
  },
  "notifications": {
    "enabled": true,
    "discord": {
      "enabled": false,
      "webhook_url": "YOUR_DISCORD_WEBHOOK_URL"
    }
  },
  "alerts": {
    "player_spike": {
      "enabled": true,
      "threshold_percent": 50
    }
  }
}
```

## 🔔 Setting Up Notifications

### Discord
1. Create a webhook in your Discord server (Server Settings → Integrations → Webhooks)
2. Copy the webhook URL
3. Update `settings.json`:
   ```json
   {
     "notifications": {
       "enabled": true,
       "discord": {
         "enabled": true,
         "webhook_url": "https://discord.com/api/webhooks/..."
       }
     }
   }
   ```
4. Test: `python notifications.py`

### Email (SMTP)
```json
{
  "notifications": {
    "enabled": true,
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "from_email": "your-email@gmail.com",
      "to_email": "recipient@gmail.com",
      "password": "your-app-password"
    }
  }
}
```

## 📊 Dashboard Features

- **Stats Grid** - Total servers, players, premium %
- **Player Trend Chart** - 24-hour player count visualization
- **Geographic Map** - Server distribution with clustering
- **Search & Filters** - By IP, country, auth mode, player count
- **Dark/Light Mode** - Toggle with localStorage persistence
- **Export** - Download data as CSV or JSON

## 🗂️ Project Structure

```
mcstatus/
├── escaner_completo.py     # Main scanner with enhanced features
├── database.py             # SQLite layer with caching
├── public_ip_fetcher.py    # IP discovery from public sources
├── scheduler.py            # Automated hourly scanning
├── api.py                  # Flask REST API
├── notifications.py        # Discord/Email alerts
├── dashboard.html          # Interactive web dashboard
├── settings.json           # Configuration file
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container definition
├── docker-compose.yml     # Multi-service orchestration
└── README.md              # This file
```

## 🧪 CLI Usage

```bash
# Run scanner with progress bar
python escaner_completo.py

# Disable progress bar
python escaner_completo.py --no-progress

# Export to CSV
python escaner_completo.py --export csv

# Export to JSON
python escaner_completo.py --export json

# Fetch new IPs
python public_ip_fetcher.py
```

## 📈 API Examples

```bash
# Get all premium servers with 100+ players
curl "http://localhost:5000/api/servers?auth_mode=PREMIUM&min_players=100"

# Get server details
curl "http://localhost:5000/api/servers/hypixel.net"

# Get global stats
curl "http://localhost:5000/api/stats"

# Trigger IP refresh
curl -X POST "http://localhost:5000/api/refresh"

# Download CSV export
curl "http://localhost:5000/api/export/csv" -O
```

## 🛠️ Development

### Running Tests
```bash
pytest tests/ -v
```

### Adding New IP Sources
Edit `public_ip_fetcher.py` and add to `SOURCES` dict:

```python
SOURCES = {
    "your_source": {
        "enabled": True,
        "urls": ["https://api.example.com/servers"]
    }
}
```

## 📝 Database Schema

### Tables
- `scans` - Scan timestamps
- `servers` - Unique server registry
- `server_snapshots` - Point-in-time server data
- `players` - Unique player UUIDs
- `geo_cache` - Geolocation cache with TTL

## 🎯 Roadmap

- [ ] WebSocket support for real-time updates
- [ ] Grafana dashboard integration
- [ ] Player name history tracking
- [ ] Server uptime percentage
- [ ] Custom alert rules via UI
- [ ] Mod/plugin detection
- [ ] Multi-language support

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - feel free to use this project for any purpose.

## 🙏 Acknowledgments

- [mcstatus](https://github.com/py-mine/mcstatus) - Minecraft server status library
- [ip-api.com](https://ip-api.com/) - Geolocation API
- [Chart.js](https://www.chartjs.org/) - Charting library
- [Leaflet](https://leafletjs.com/) - Mapping library
- [Tailwind CSS](https://tailwindcss.com/) - Styling framework

## ⚠️ Disclaimer

This tool is for educational and monitoring purposes. Always respect server owners' privacy and follow rate limits when scanning public servers.

---

Made with ❤️ for the Minecraft community
