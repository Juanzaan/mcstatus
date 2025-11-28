# Contributing to MCStatus

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- pip or poetry
- PostgreSQL (for production) or SQLite (for development)

### Development Setup

```bash
# Clone and navigate to repo
cd mcstatus

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run the API server
python run_api.py
```

## 🏗️ Project Structure

```
mcstatus/
├── core/               # Core business logic
│   ├── enterprise/    # Detection & protocol analysis
│   ├── api.py        # Flask API server
│   ├── database.py   # Database operations
│   ├── scheduler.py  # Background jobs
│   └── ...
├── web/               # Frontend dashboard
├── api/               # API modules
├── scrapers/          # NameMC scrapers
├── scripts/           # Utility scripts
├── tests/             # Test suite
└── data/              # Server data storage
```

## 🔧 Running Components

### Run API Server
```bash
python run_api.py
# Access at http://localhost:5000
```

### Run Background Scanning
```bash
# The scheduler runs automatically with the API
# Or trigger manually:
curl -X POST "http://localhost:5000/api/scheduler/run_now?type=refresh_status"
```

### Run Scrapers

**NameMC Scraper (Simple)**
```bash
python scrape_namemc_600.py
```

**NameMC Scraper (Selenium - for rate-limited scenarios)**
```bash
python scrape_namemc_selenium.py
```

**Enterprise Scanner**
```bash
python scrape_namemc_enterprise.py
```

### Run Tests
```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=core --cov-report=html

# Windows convenience script
run_tests.bat
```

## 🧪 Testing Your Changes

1. **Write tests** for new features in `tests/`
2. **Run linting** before committing
3. **Check coverage** to ensure critical paths are tested

## 📝 Code Style

We use:
- **Black** for formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

```bash
# Format code
black core/ api/ web/

# Sort imports
isort core/ api/ web/

# Check linting
flake8 core/ --max-line-length=120

# Type check
mypy core/
```

## 🔀 Workflow

1. **Create a branch** for your feature
2. **Make your changes** following the code style
3. **Test thoroughly**
4. **Commit with clear messages**
5. **Push and create PR**

## 🐛 Debugging

### API Issues
```bash
# Check health
curl http://localhost:5000/api/health

# Check scheduler status
curl http://localhost:5000/api/scheduler/status
```

### Database Issues
```bash
# Check database integrity
python check_integrity.py

# View server stats
python verify_stats.py
```

## 📊 Common Tasks

### Add a New Server Type Detection
1. Edit `core/enterprise/detector.py`
2. Add signature/heuristic to appropriate list
3. Test with `validate_detection.py`

### Add a New API Endpoint
1. Edit `core/api.py`
2. Add route and handler
3. Add test in `tests/test_api_*.py`
4. Update `docs/API.md`

### Improve Deduplication
1. Edit `core/deduplication_engine.py`
2. Add new strategy method
3. Update confidence scoring
4. Test with `scripts/master_dedup.py --mode dry-run`

## 🎯 Current Priorities

See [ROADMAP.md](ROADMAP.md) and [task.md](task.md) for current priorities.

Currently focusing on:
- **Phase 1**: Scraping robustness (fallback system, proxy rotation)
- **Phase 2**: Semi-premium detection improvements
- **Phase 3**: Deduplication UI and advanced matching

## 💡 Tips

- **Always run tests** before pushing
- **Check existing code** for patterns to follow
- **Ask questions** if architecture is unclear
- **Document complex logic** with inline comments
- **Keep PRs focused** - one feature/fix per PR

## ⚠️ Important Notes

- Never commit to `main` directly
- Never commit `.env` file
- Always update tests when changing API
- Keep data files in `.gitignore`
