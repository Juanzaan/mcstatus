"""Flask server for Minecraft Server Status Dashboard"""
from flask import Flask, render_template, jsonify, request, send_from_directory
from pathlib import Path
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.server_merger import merge_all_servers

app = Flask(__name__, 
            template_folder=str(Path(__file__).parent),
            static_folder=str(Path(__file__).parent / 'static'))

# Path to data directory
DATA_DIR = Path(__file__).parent.parent / 'data'

def load_unified_servers():
    """Load unified server data, regenerate if missing"""
    unified_file = DATA_DIR / 'unified_servers.json'
    
    if not unified_file.exists():
        print("🔄 Unified servers file not found, regenerating...")
        merge_all_servers()
    
    try:
        with open(unified_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading unified servers: {e}")
        return {
            "premium": [],
            "non_premium": [],
            "offline": [],
            "stats": {
                "total_premium": 0,
                "total_non_premium": 0,
                "total_offline": 0,
                "total_players": 0
            }
        }

@app.route('/')
def dashboard():
    """Render dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/servers/all')
def get_all_servers():
    """Get all servers with optional filtering"""
    data = load_unified_servers()
    filter_type = request.args.get('filter', 'all')
    search = request.args.get('search', '').lower()
    sort_by = request.args.get('sort', 'players')  # players, name, status
    
    # Select category
    if filter_type == 'premium':
        servers = data['premium']
    elif filter_type == 'non_premium':
        servers = data['non_premium']
    elif filter_type == 'offline':
        servers = data['offline']
    else:  # 'all'
        servers = data['premium'] + data['non_premium'] + data['offline']
    
    # Apply search filter
    if search:
        servers = [s for s in servers if 
                   search in s['ip'].lower() or 
                   search in s.get('name', '').lower()]
    
    # Apply sorting
    if sort_by == 'players':
        servers.sort(key=lambda x: x.get('online', 0), reverse=True)
    elif sort_by == 'name':
        servers.sort(key=lambda x: x.get('name', x['ip']).lower())
    elif sort_by == 'status':
        servers.sort(key=lambda x: x.get('status', 'offline'))
    
    return jsonify({
        'servers': servers,
        'count': len(servers)
    })

@app.route('/api/servers/stats')
def get_stats():
    """Get server statistics"""
    data = load_unified_servers()
    return jsonify(data['stats'])

@app.route('/api/servers/refresh')
def refresh_servers():
    """Regenerate unified server list"""
    try:
        merge_all_servers()
        return jsonify({
            'success': True,
            'message': 'Server list refreshed successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    print("🚀 Starting Minecraft Server Status Dashboard...")
    print(f"📁 Data directory: {DATA_DIR}")
    print(f"🌐 Dashboard: http://localhost:5000")
    print("=" * 60)
    
    # Ensure unified data exists
    load_unified_servers()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
