"""
Reconstruct the missing sections of core/api.py for filtering and search.
This is a reference/backup of the expected logic.
"""

# Expected structure for /api/servers endpoint (lines 124-190 approximately)

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
        filtered = [s for s in filtered if not s.get('premium') and s.get('status') == 'online']
    elif category == 'offline':
        filtered = [s for s in filtered if s.get('status') == 'offline']
    
    # Filter by Search (ENHANCED: includes alternate_ips)
    if search:
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
            
            # NEW: Search in alternate IPs
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
