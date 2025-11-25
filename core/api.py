from flask import Flask, jsonify, request, send_file, render_template, send_from_directory
from flask_cors import CORS
import subprocess
import sqlite3
import io
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
import sys
import psutil
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Prometheus Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP Request Latency', ['endpoint'])
SYSTEM_CPU = Gauge('system_cpu_usage_percent', 'System CPU Usage Percent')
SYSTEM_MEMORY = Gauge('system_memory_usage_percent', 'System Memory Usage Percent')

# Add parent directory to path for imports
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# Import configuration and database
from core import config
from core import database as db

# Configure paths for Flask
WEB_DIR = BASE_DIR / 'web'
TEMPLATE_DIR = WEB_DIR
STATIC_DIR = WEB_DIR / 'static'

print(f"TEMPLATE_DIR: {TEMPLATE_DIR.resolve()}")
print(f"STATIC_DIR: {STATIC_DIR.resolve()}")
print(f"DATA_DIR: {config.DATA_DIR.resolve()}")
print(f"API will run on {config.API_HOST}:{config.API_PORT}")
print(f"Debug mode: {config.DEBUG}")

app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))
CORS(app, origins=config.CORS_ORIGINS if hasattr(config, 'CORS_ORIGINS') else '*')

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Not found", "status": 404}), 404
    return render_template('dashboard.html'), 404

@app.errorhandler(405)
def method_not_allowed(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Method not allowed", "status": 405}), 405
    return "Method Not Allowed", 405

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(request, 'start_time'):
        latency = time.time() - request.start_time
        REQUEST_LATENCY.labels(endpoint=request.endpoint).observe(latency)
    
    REQUEST_COUNT.labels(
        method=request.method, 
        endpoint=request.endpoint, 
        status=response.status_code
    ).inc()
    
    return response

@app.route('/metrics')
def metrics():
    """Expose Prometheus metrics."""
    SYSTEM_CPU.set(psutil.cpu_percent())
    SYSTEM_MEMORY.set(psutil.virtual_memory().percent)
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# Cache for loaded server data
_cached_servers = None
_cached_stats = None

def load_unified_servers():
    """Load servers from SQLite database"""
    global _cached_servers, _cached_stats
    
    try:
        # Get servers from database
        all_servers = db.get_latest_scan_data()
        
        # Get stats from database
        stats_data = db.get_stats()
        
        # Format stats to match expected structure
        final_stats = {
            'total_servers': stats_data.get('total_servers', 0),
            'total_players': stats_data.get('total_players', 0),
            'premium_count': stats_data.get('premium_count', 0),
            'cracked_count': stats_data.get('cracked_count', 0)
        }
        
        # Add status and premium fields for compatibility
        for server in all_servers:
            if 'status' not in server:
                server['status'] = 'online'  # All servers are online now
            server['premium'] = server.get('auth_mode') == 'PREMIUM'
        
        _cached_servers = all_servers
        _cached_stats = final_stats
        
        return all_servers, final_stats
    except Exception as e:
        import traceback
        traceback.print_exc()
        return [], {'total_servers': 0, 'total_players': 0, 'premium_count': 0, 'cracked_count': 0}

@app.route('/')
def dashboard():
    """Render dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/servers', methods=['GET'])
def get_servers():
    """Return paginated and filtered list of servers."""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', config.DEFAULT_PAGE_SIZE, type=int)
    
    # Validation
    if page < 1: page = 1
    if limit < 1: limit = config.DEFAULT_PAGE_SIZE
    if limit > config.MAX_PAGE_SIZE: limit = config.MAX_PAGE_SIZE
    
    # Filters
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').lower()
    min_players = request.args.get('min_players', type=int)
    max_players = request.args.get('max_players', type=int)
    version = request.args.get('version', '').lower()
    sort_by = request.args.get('sort', 'players')
    
    servers, _ = load_unified_servers()
    filtered = servers
    
    # Filter by Category
    if category == 'premium':
        filtered = [s for s in filtered if s.get('premium')]
    elif category == 'non_premium':
        filtered = [s for s in filtered if not s.get('premium')]
    elif category == 'favorites':
        # Favorites are filtered client-side, return all (or let other filters apply)
        pass
    
    # Filter by Search (PHASE 11: Enhanced with alias resolution)
    matched_alias = None  # Track if search matched an alias
    if search:
        # PHASE 11: Check if search term is an alias FIRST
        canonical_ip = db.resolve_alias_to_canonical(search)
        
        if canonical_ip:
            # Search term IS an alias - find and return the canonical server
            canonical_server = next((s for s in filtered if s['ip'].lower() == canonical_ip.lower()), None)
            if canonical_server:
                # Get aliases with contextual priority
                canonical_server['known_aliases'] = db.get_aliases_for_server(
                    canonical_ip, 
                    prioritize=search,  # Enhancement 1: Searched alias appears first
                    limit=5
                )
                canonical_server['matched_alias'] = search  # Metadata for frontend
                filtered = [canonical_server]
                matched_alias = search
            else:
                filtered = []
        else:
            # Not an alias - do normal search in canonical servers
            filtered_by_search = []
            for s in filtered:
                # Check main IP
                if search in s.get('ip', '').lower():
                    filtered_by_search.append(s)
                    continue
                
                # Check name
                if s.get('name') and search in s.get('name', '').lower():
                    filtered_by_search.append(s)
                    continue
                
                # Check description
                if s.get('description') and search in s.get('description', '').lower():
                    filtered_by_search.append(s)
                    continue
                
                # Search in alternate IPs
                if s.get('alternate_ips'):
                    for alt_ip in s.get('alternate_ips', []):
                        if search in str(alt_ip).lower():
                            filtered_by_search.append(s)
                            break
            
            filtered = filtered_by_search
    
    # Filter by Player Count
    if min_players is not None:
        filtered = [s for s in filtered if s.get('online', 0) >= min_players]
    if max_players is not None:
        filtered = [s for s in filtered if s.get('online', 0) <= max_players]
    
    # Filter by Version
    if version:
        filtered = [s for s in filtered if version in s.get('version', '').lower()]
    
    # Sort
    if sort_by == 'players':
        filtered.sort(key=lambda x: x.get('online', 0), reverse=True)
    elif sort_by == 'name':
        filtered.sort(key=lambda x: x.get('name', x.get('ip', '')).lower())
    elif sort_by == 'status':
        filtered.sort(key=lambda x: (x.get('status') == 'online', x.get('online', 0)), reverse=True)
    
    # Paginate
    total_items = len(filtered)
    total_pages = (total_items + limit - 1) // limit
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    start = (page - 1) * limit
    end = start + limit
    paginated_data = filtered[start:end]
    
    return jsonify({
        'success': True,
        'servers': paginated_data,
        'pagination': {
            'page': page,
            'limit': limit,
            'total_items': total_items,
            'total_pages': total_pages
        }
    })

@app.route('/api/servers/all', methods=['GET'])
def get_all_servers():
    """Return the complete list of servers without any filtering."""
    servers, _ = load_unified_servers()
    return jsonify({'success': True, 'count': len(servers), 'servers': servers})

@app.route('/api/server/<path:ip>', methods=['GET'])
def get_server_detail(ip):
    """
    PHASE 11: Return detailed info for a specific server with alias resolution.
    Enhancement 3: Smart redirect - if IP is an alias, return canonical with metadata.
    """
    # Check if requested IP is an alias
    canonical_ip = db.resolve_alias_to_canonical(ip)
    
    if canonical_ip:
        # It's an alias - fetch canonical server
        server = db.get_server_by_ip(canonical_ip)
        if server:
            # Get all aliases with contextual priority
            server['known_aliases'] = db.get_aliases_for_server(
                canonical_ip,
                prioritize=ip,  # Requested alias appears first
                limit=5
            )
            return jsonify({
                'success': True,
                'server': server,
                'is_alias_redirect': True,  # Enhancement 3: Flag for frontend
                'redirect_to': canonical_ip,  # Enhancement 3: Canonical IP
                'requested_alias': ip
            })
    
    # Not an alias - fetch directly
    server = db.get_server_by_ip(ip)
    if server:
        # Get aliases for canonical server
        server['known_aliases'] = db.get_aliases_for_server(ip, limit=5)
        return jsonify({
            'success': True,
            'server': server,
            'is_alias_redirect': False
        })
    
    return jsonify({'success': False, 'error': 'Server not found'}), 404

@app.route('/api/admin/aliases', methods=['GET'])
def get_admin_aliases():
    """
    PHASE 11: Admin endpoint to view all alias relationships.
    Returns complete server_aliases table for auditing.
    """
    try:
        conn = db.get_connection() if hasattr(db, 'get_connection') else sqlite3.connect(db.DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                alias_ip,
                canonical_ip,
                detection_method,
                confidence_score,
                created_at
            FROM server_aliases
            ORDER BY canonical_ip, confidence_score DESC
        """)
        
        aliases = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'aliases': aliases,
            'total': len(aliases)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
@app.route('/api/stats/', methods=['GET'])
def get_stats():
    """Return global statistics for the dashboard."""
    _, stats = load_unified_servers()
    return jsonify({'success': True, 'stats': stats})

@app.route('/api/trends', methods=['GET'])
def get_trends():
    """Return historical trend data for all servers."""
    hours = request.args.get('hours', 24, type=int)
    trend_data = db.get_global_trend(hours=hours)
    return jsonify({'success': True, 'trend': trend_data})

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """Export server data as CSV file."""
    servers = db.get_latest_scan_data()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['IP', 'Country', 'ISP', 'Auth Mode', 'Version', 'Online', 'Max',
                     'Sample Size', 'Premium', 'Cracked', 'New Players', 'Icon'])
    for s in servers:
        writer.writerow([
            s.get('ip'), s.get('country'), s.get('isp'), s.get('auth_mode'), s.get('version'),
            s.get('online'), s.get('max'), s.get('sample_size'), s.get('premium'),
            s.get('cracked'), s.get('new_players'), s.get('icon', '')
        ])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')),
                    mimetype='text/csv', as_attachment=True,
                    download_name='servers_export.csv')

@app.route('/api/export/json', methods=['GET'])
def export_json():
    """Export server data as JSON file."""
    data = db.export_for_dashboard()
    return send_file(io.BytesIO(json.dumps(data, indent=2).encode('utf-8')),
                    mimetype='application/json', as_attachment=True,
                    download_name='servers_export.json')

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    """Return all data needed for the dashboard in one request."""
    data = db.export_for_dashboard()
    return jsonify({'success': True, 'data': data})

@app.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint for load balancers"""
    return jsonify({'status': 'healthy', 'service': 'mc-scanner-api'})

@app.route('/api/health', methods=['GET'])
def detailed_health():
    """Detailed health check with system information"""
    health_status = {
        'status': 'healthy',
        'service': 'mc-scanner-api',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    # Check if database exists
    db_exists = Path(db.DB_FILE).exists()
    health_status['checks']['database'] = {
        'status': 'ok' if db_exists else 'error',
        'path': db.DB_FILE,
        'exists': db_exists
    }
    
    # Check data freshness (last scan)
    try:
        stats = db.get_stats()
        health_status['checks']['data'] = {
            'status': 'ok',
            'total_servers': stats.get('total_servers', 0)
        }
    except Exception as e:
        health_status['checks']['data'] = {'status': 'error', 'error': str(e)}
    
    # System Resources
    try:
        health_status['checks']['system'] = {
            'status': 'ok',
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        }
    except Exception as e:
        health_status['checks']['system'] = {'status': 'warning', 'error': str(e)}
    
    # Check scheduler status
    try:
        from core.scheduler import scheduler_manager
        scheduler_status = scheduler_manager.get_status()
        health_status['checks']['scheduler'] = {
            'status': 'ok' if scheduler_status.get('running') else 'warning',
            'details': scheduler_status
        }
    except Exception as e:
        health_status['checks']['scheduler'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # Overall health determination
    error_checks = [k for k, v in health_status['checks'].items() if v.get('status') == 'error']
    if error_checks:
        health_status['status'] = 'unhealthy'
    elif any(v.get('status') == 'warning' for v in health_status['checks'].values()):
        health_status['status'] = 'degraded'
    
    status_code = 200 if health_status['status'] in ['healthy', 'degraded'] else 503
    return jsonify(health_status), status_code

# Scheduler Integration
from core.scheduler import scheduler_manager

@app.route('/api/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """Get the status of the background scheduler."""
    return jsonify({'success': True, 'status': scheduler_manager.get_status()})

@app.route('/api/scheduler/run_now', methods=['POST'])
def trigger_manual_run():
    """Manually trigger a background task."""
    task_type = request.args.get('type', 'refresh_status')
    
    if task_type == 'refresh_status':
        scheduler_manager.scheduler.add_job(
            func=scheduler_manager.refresh_server_status,
            trigger='date',
            run_date=datetime.now(),
            id=f'manual_refresh_{int(time.time())}',
            name='Manual Status Refresh'
        )
    elif task_type == 'full_scan':
        scheduler_manager.scheduler.add_job(
            func=scheduler_manager.run_full_merge,
            trigger='date',
            run_date=datetime.now(),
            id=f'manual_full_{int(time.time())}',
            name='Manual Full Merge'
        )
    elif task_type == 'priority_scan':
        scheduler_manager.scheduler.add_job(
            func=scheduler_manager.run_priority_scan_job,
            trigger='date',
            run_date=datetime.now(),
            id=f'manual_priority_{int(time.time())}',
            name='Manual Priority Scan'
        )
    else:
        return jsonify({'success': False, 'error': 'Invalid task type'}), 400
        
    return jsonify({'success': True, 'message': f'Triggered {task_type}'})

if __name__ == '__main__':
    # Start scheduler
    if config.SCHEDULER_ENABLED:
        try:
            scheduler_manager.start()
            print("Scheduler started successfully")
            
            # Run priority scan immediately on startup
            scheduler_manager.run_priority_scan_job()
        except Exception as e:
            print(f"Failed to start scheduler: {e}")
    else:
        print("Scheduler disabled via configuration")
    
    print(f"Starting API server on {config.API_HOST}:{config.API_PORT}")
    print(f"Debug mode: {config.DEBUG}")
    
    try:
        app.run(host=config.API_HOST, port=config.API_PORT, debug=config.DEBUG, use_reloader=False)
    finally:
        if config.SCHEDULER_ENABLED:
            scheduler_manager.stop()
