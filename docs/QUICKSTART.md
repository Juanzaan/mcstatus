# 🚀 Quick Start Guide

Get your Minecraft Scanner running in 3 minutes!

## Option 1: Quick Setup (Recommended)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database
python database.py

# 3. Fetch servers (1.21+ from minecraft-server-list.com)
python public_ip_fetcher.py

# 4. Run a scan
python escaner_completo.py

# 5. Open dashboard
# Open dashboard.html in your browser
```

## Option 2: Docker (Production)

```bash
# Start everything
docker-compose up -d

# Access dashboard at:
http://localhost:5000/dashboard.html
```

## Next Steps

### Configure Notifications (Optional)

Edit `settings.json`:

```json
{
  "notifications": {
    "discord": {
      "enabled": true,
      "webhook_url": "YOUR_WEBHOOK_URL_HERE"
    }
  }
}
```

Test: `python notifications.py`

### Start Automated Scanning

```bash
# Hourly scans
python scheduler.py
```

### Start API Server

```bash
# In another terminal
python api.py
```

Access at: `http://localhost:5000`

## Useful Commands

```bash
# Export data
python escaner_completo.py --export csv

# Run tests
pytest tests/ -v

# View logs
tail -f scheduler.log
```

## Need Help?

See [README.md](README.md) for full documentation.

---

**You're all set! 🎉**
