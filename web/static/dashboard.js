/**
 * Enhanced Dashboard JavaScript with Performance & UX Improvements
 * Features: Icon caching, lazy loading, pagination, advanced filters, favorites, export
 */

// ============= STATE MANAGEMENT =============
let currentFilter = 'all';
let currentSearch = '';
let currentSort = 'players';
let allServers = [];
let displayedServers = [];
let currentPage = 1;
const ITEMS_PER_PAGE = 50;

// Advanced filters
let minPlayers = 0;
let maxPlayers = 10000;
let selectedVersion = '';
let favorites = JSON.parse(localStorage.getItem('favorites') || '[]');

// ============= ICON CACHE =============
const iconCache = {
    get(ip) {
        const cached = localStorage.getItem(`icon_${ip}`);
        if (cached) {
            const { url, timestamp } = JSON.parse(cached);
            // Cache for 7 days
            if (Date.now() - timestamp < 7 * 24 * 60 * 60 * 1000) {
                return url;
            }
        }
        return null;
    },
    set(ip, url) {
        try {
            localStorage.setItem(`icon_${ip}`, JSON.stringify({
                url,
                timestamp: Date.now()
            }));
        } catch (e) {
            // Storage full, clear old icons
            this.cleanup();
        }
    },
    cleanup() {
        const keys = Object.keys(localStorage).filter(k => k.startsWith('icon_'));
        keys.slice(0, keys.length / 2).forEach(k => localStorage.removeItem(k));
    }
};

// ============= PHASE 11: ALIAS RESOLUTION =============

/**
 * Show toast notification when search resolves via alias
 * @param {string} canonical - The canonical server IP
 * @param {string} alias - The alias that was searched
 */
function showAliasToast(canonical, alias) {
    // Remove any existing toast
    const existingToast = document.querySelector('.alias-toast');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = 'alias-toast';
    toast.innerHTML = `
        <div class="toast-icon">🔍</div>
        <div class="toast-content">
            <strong>Redirección inteligente</strong><br>
            Mostrando resultados para <strong>${canonical}</strong><br>
            <small>(Buscaste: ${alias})</small>
        </div>
    `;
    document.body.appendChild(toast);

    // Auto-remove after 5 seconds with fade out
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

/**
 * Create "Also known as" section for server cards
 * @param {object} server - Server object with known_aliases
 * @returns {HTMLElement|null} - Aliases div or null
 */
function createAliasesSection(server) {
    if (!server.known_aliases || server.known_aliases.length === 0) {
        return null;
    }

    const aliasesDiv = document.createElement('div');
    aliasesDiv.className = 'server-aliases';

    // Get up to 5 aliases
    const displayAliases = server.known_aliases.slice(0, 5);

    // Format aliases with contextual highlighting
    const aliasesList = displayAliases.map(alias => {
        // Highlight the searched alias (matched_alias)
        if (server.matched_alias && alias.toLowerCase() === server.matched_alias.toLowerCase()) {
            return `<strong class="matched-alias">${alias}</strong>`;
        }
        return alias;
    }).join(', ');

    const moreText = server.known_aliases.length > 5
        ? ` <span class="more-aliases">+${server.known_aliases.length - 5} more</span>`
        : '';

    aliasesDiv.innerHTML = `
        <div class="aliases-label">También conocido como:</div>
        <div class="aliases-list">${aliasesList}${moreText}</div>
    `;

    return aliasesDiv;
}

let lazyLoadObserver;

function initLazyLoading() {
    lazyLoadObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                const src = img.dataset.src;
                if (src) {
                    img.src = src;
                    img.removeAttribute('data-src');
                    lazyLoadObserver.unobserve(img);
                }
            }
        });
    }, {
        rootMargin: '50px'
    });
}

// ============= INITIALIZATION =============
document.addEventListener('DOMContentLoaded', () => {
    initLazyLoading();
    loadStats();
    loadServers();
    setupEventListeners();
    setupKeyboardShortcuts();
    createBackToTopButton();
});

function setupEventListeners() {
    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentFilter = e.target.dataset.filter;
            loadServers(true);
        });
    });

    // Search box
    const searchInput = document.getElementById('search-input');
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentSearch = e.target.value;
            loadServers(true);
        }, 300);
    });

    // Sort select
    const sortSelect = document.getElementById('sort-select');
    sortSelect.addEventListener('change', (e) => {
        currentSort = e.target.value;
        loadServers(true);
    });

    // Infinite scroll
    window.addEventListener('scroll', () => {
        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 500) {
            loadServers();
        }
    });
}

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // 'f' or '/' to focus search
        if ((e.key === 'f' || e.key === '/') && !e.ctrlKey && !e.metaKey) {
            const searchInput = document.getElementById('search-input');
            if (document.activeElement !== searchInput) {
                e.preventDefault();
                searchInput.focus();
            }
        }
        // 'Esc' to clear search
        if (e.key === 'Escape') {
            document.getElementById('search-input').value = '';
            currentSearch = '';
            renderServers();
        }
    });
}

function createBackToTopButton() {
    const button = document.createElement('button');
    button.id = 'back-to-top';
    button.innerHTML = '↑';
    button.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        font-size: 1.5rem;
        cursor: pointer;
        opacity: 0;
        transition: opacity 0.3s, transform 0.3s;
        z-index: 1000;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    `;

    button.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            button.style.opacity = '1';
            button.style.transform = 'scale(1)';
        } else {
            button.style.opacity = '0';
            button.style.transform = 'scale(0.8)';
        }
    });
    document.body.appendChild(button);
}

// ============= DATA LOADING =============
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        if (data.success) {
            const totalServers = (data.stats.total_premium || 0) + (data.stats.total_non_premium || 0) + (data.stats.total_offline || 0);
            animateNumber('stat-total', totalServers);
            animateNumber('stat-players', data.stats.total_players);
            animateNumber('stat-premium', data.stats.total_premium);
            animateNumber('stat-non-premium', data.stats.total_non_premium);

            // Add last refresh timestamp
            updateLastRefresh();
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        showError('Failed to load statistics');
    }
}

function updateLastRefresh() {
    const timestamp = document.createElement('div');
    timestamp.id = 'last-refresh';
    timestamp.style.cssText = 'text-align: center; color: #a0a0b0; font-size: 0.9rem; margin-top: 1rem;';
    timestamp.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;

    const existing = document.getElementById('last-refresh');
    if (existing) {
        existing.replaceWith(timestamp);
    } else {
        document.querySelector('.stats-grid').after(timestamp);
    }
}

// ============= DATA LOADING =============
let isLoading = false;
let hasMore = true;

async function loadServers(reset = false) {
    if (isLoading || (!hasMore && !reset)) return;

    isLoading = true;
    const grid = document.getElementById('servers-grid');

    if (reset) {
        currentPage = 1;
        hasMore = true;
        allServers = [];
        grid.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                Loading servers...
            </div>
        `;
    } else {
        // Show loading indicator at bottom
        const loader = document.createElement('div');
        loader.className = 'loading-more';
        loader.innerHTML = '<div class="spinner-small"></div> Loading more...';
        grid.appendChild(loader);
    }

    try {
        // Build query string
        const params = new URLSearchParams({
            page: currentPage,
            limit: ITEMS_PER_PAGE,
            category: currentFilter,
            search: currentSearch,
            sort: currentSort,
            min_players: minPlayers,
            max_players: maxPlayers,
            version: selectedVersion,
            t: Date.now() // Cache busting
        });

        const response = await fetch(`/api/servers?${params.toString()}`);
        const data = await response.json();

        if (data.success) {
            // PHASE 11: Check if search resolved via alias and show toast
            if (currentSearch && data.servers && data.servers.length > 0 && data.servers[0].matched_alias) {
                showAliasToast(data.servers[0].ip, data.servers[0].matched_alias);
            }

            if (reset) {
                grid.innerHTML = '';
                allServers = data.servers;
            } else {
                // Remove loading indicator
                const loader = grid.querySelector('.loading-more');
                if (loader) loader.remove();
                allServers = [...allServers, ...data.servers];
            }

            if (data.servers.length < ITEMS_PER_PAGE) {
                hasMore = false;
            }

            renderServers(data.servers, reset);
            currentPage++;
        } else {
            grid.innerHTML = '<div class="error">Failed to load servers</div>';
        }
    } catch (error) {
        console.error('Error loading servers:', error);
        if (reset) {
            grid.innerHTML = '<div class="error">Error loading servers. Please try refreshing.</div>';
        }
    } finally {
        isLoading = false;
    }
}

// ============= RENDERING =============
function renderServers(servers, reset = false) {
    const grid = document.getElementById('servers-grid');

    if (!servers || !Array.isArray(servers)) {
        console.error('Invalid servers data:', servers);
        return;
    }

    if (servers.length === 0 && reset) {
        grid.innerHTML = '<div class="no-results">No servers found matching your criteria</div>';
        return;
    }

    const fragment = document.createDocumentFragment();

    servers.forEach(server => {
        try {
            if (!server || !server.ip) {
                console.warn('Skipping invalid server object:', server);
                return;
            }
            const card = createServerCard(server);
            fragment.appendChild(card);
        } catch (e) {
            console.error('Error creating server card:', e, server);
        }
    });

    grid.appendChild(fragment);
    updateResultCount(allServers.length);
}


function getCategory(server) {
    if (server.status === 'offline') return 'Offline';
    if (server.premium) return 'Premium';
    return 'Non-Premium';
}

// ============= RENDERING =============


function updateResultCount(count) {
    let countEl = document.getElementById('result-count');
    if (!countEl) {
        countEl = document.createElement('div');
        countEl.id = 'result-count';
        countEl.style.cssText = 'text-align: center; color: #a0a0b0; margin-bottom: 1rem; font-size: 0.95rem;';
        document.getElementById('servers-grid').before(countEl);
    }
    // If we have total_items from API, use that. For now, just show current count.
    // Ideally, we should pass total count from loadServers
    countEl.textContent = `Showing ${allServers.length} servers`;
}

function createServerCard(server) {
    const row = document.createElement('div');
    row.className = 'server-row';

    const category = getCategory(server);
    const badgeClass = category === 'Premium' ? 'badge-premium' :
        category === 'Non-Premium' ? 'badge-cracked' : 'badge-offline';

    // Get server icon with caching
    const cachedIcon = iconCache.get(server.ip);
    const serverIcon = cachedIcon || getServerIcon(server.ip);

    // Cache icon URL
    if (!cachedIcon) {
        iconCache.set(server.ip, serverIcon);
    }

    // Format alternate IPs
    const hasAlternateIps = server.alternate_ips && server.alternate_ips.length > 0;
    const alternateIpsText = hasAlternateIps ? server.alternate_ips.join(' - ') : '';

    // Format description
    const description = server.description ? stripMinecraftColors(server.description) : 'No description available';

    // Check if favorite
    const isFavorite = favorites.includes(server.ip);

    row.innerHTML = `
        <div class="server-main">
            <img class="server-icon" data-src="${serverIcon}" alt="Server icon" 
                 src="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22><rect fill=%22%23333%22 width=%2264%22 height=%2264%22/><text x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%23999%22 font-size=%2224%22>MC</text></svg>"
                 onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22><rect fill=%22%23333%22 width=%2264%22 height=%2264%22/><text x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%23999%22 font-size=%2224%22>MC</text></svg>'">
            <div class="server-info">
                <h3 class="server-name">
                    <button class="favorite-btn ${isFavorite ? 'active' : ''}" 
                            onclick="toggleFavorite(event, '${server.ip}')" 
                            title="${isFavorite ? 'Remove from favorites' : 'Add to favorites'}">
                        ${isFavorite ? '⭐' : '☆'}
                    </button>
                    ${server.name || server.ip}
                </h3>
                <p class="server-desc">${description}</p>
            </div>
            <div class="server-stats">
                <div class="player-count-section">
                    <div class="player-count">👥 ${server.online || 0}${server.max ? `/${server.max}` : ''}</div>
                    <div class="player-label">Players</div>
                </div>
                <span class="badge ${badgeClass}" title="${category} server">${category}</span>
            </div>
            <div class="server-ip-section">
                <span class="ip-text">${server.ip}</span>
                <button class="copy-btn" onclick="copyIP(event, '${server.ip}')" title="Copy IP">📋</button>
                <button class="details-btn" onclick="showDetails(event, ${JSON.stringify(server).replace(/"/g, '&quot;')})" title="View details">ℹ️</button>
            </div>
        </div>
        ${hasAlternateIps ? `
        <div class="server-expanded">
            <div class="expand-content">
                <div class="alternate-ips">
                    <div class="alternate-ips-label">🔀 Alternate IPs:</div>
                    <div class="alternate-ips-list">
                        ${server.alternate_ips.map(alt => `
                            <span class="alt-ip-item">
                                <span class="alt-ip-text">${alt}</span>
                                <button class="copy-alt-btn" onclick="copyIP(event, '${alt}')" title="Copy ${alt}">📋</button>
                            </span>
                        `).join('')}
                    </div>
                </div>
            </div>
        </div>` : ''}
    `;

    // Lazy load image
    const img = row.querySelector('.server-icon');
    if (lazyLoadObserver) {
        lazyLoadObserver.observe(img);
    } else {
        img.src = img.dataset.src;
    }

    // Add click to expand
    if (hasAlternateIps) {
        row.addEventListener('click', (e) => {
            if (e.target.classList.contains('copy-btn') ||
                e.target.classList.contains('details-btn') ||
                e.target.classList.contains('favorite-btn')) return;
            row.classList.toggle('expanded');
        });
    }

    // PHASE 11: Add aliases section if server has known_aliases
    const aliasesSection = createAliasesSection(server);
    if (aliasesSection) {
        row.appendChild(aliasesSection);
    }

    return row;
}

function getServerIcon(ip) {
    const cleanIp = ip.split(':')[0];
    return `https://eu.mc-api.net/v3/server/favicon/${encodeURIComponent(cleanIp)}`;
}

// ============= FAVORITES =============
function toggleFavorite(event, ip) {
    event.stopPropagation();

    const index = favorites.indexOf(ip);
    if (index > -1) {
        favorites.splice(index, 1);
    } else {
        favorites.push(ip);
    }

    localStorage.setItem('favorites', JSON.stringify(favorites));
    renderServers(); // Re-render to update star icons
}

// ============= EXPORT =============
function exportServers(format = 'json') {
    const filtered = filterAndSortServers();

    if (format === 'json') {
        const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: 'application/json' });
        downloadBlob(blob, `servers_${Date.now()}.json`);
    } else if (format === 'csv') {
        const csv = serversToCsv(filtered);
        const blob = new Blob([csv], { type: 'text/csv' });
        downloadBlob(blob, `servers_${Date.now()}.csv`);
    }
}

function serversToCsv(servers) {
    const headers = ['IP', 'Name', 'Players', 'Max Players', 'Version', 'Status', 'Type'];
    const rows = servers.map(s => [
        s.ip,
        s.name || '',
        s.online || 0,
        s.max || 0,
        s.version || '',
        s.status || '',
        getCategory(s)
    ]);

    return [headers, ...rows].map(row =>
        row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')
    ).join('\n');
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ============= DETAILS MODAL =============
function showDetails(event, serverData) {
    event.stopPropagation();

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <h2>${serverData.name || serverData.ip}</h2>
            <div class="detail-grid">
                <div class="detail-item"><strong>IP:</strong> ${serverData.ip}</div>
                <div class="detail-item"><strong>Players:</strong> ${serverData.online || 0}/${serverData.max || 0}</div>
                <div class="detail-item"><strong>Version:</strong> ${serverData.version || 'Unknown'}</div>
                <div class="detail-item"><strong>Auth:</strong> ${serverData.auth_mode || 'Unknown'}</div>
                <div class="detail-item"><strong>Status:</strong> ${serverData.status || 'Unknown'}</div>
                <div class="detail-item"><strong>Type:</strong> ${getCategory(serverData)}</div>
            </div>
            ${serverData.alternate_ips && serverData.alternate_ips.length > 0 ? `
                <h3>Alternate IPs</h3>
                <ul class="alt-ip-list">
                    ${serverData.alternate_ips.map(ip => `<li>${ip}</li>`).join('')}
                </ul>
            ` : ''}
            ${serverData.description ? `
                <h3>Description</h3>
                <p>${stripMinecraftColors(serverData.description)}</p>
            ` : ''}
        </div>
    `;

    document.body.appendChild(modal);

    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    // Close on Escape
    document.addEventListener('keydown', function escHandler(e) {
        if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', escHandler);
        }
    });
}

function closeModal() {
    const modal = document.querySelector('.modal-overlay');
    if (modal) modal.remove();
}

// ============= UTILITIES =============
function stripMinecraftColors(text) {
    if (!text) return '';
    if (typeof text === 'object') {
        if (text.text) return stripMinecraftColors(text.text);
        if (text.extra) {
            return text.extra.map(part => stripMinecraftColors(part)).join('');
        }
        return String(text);
    }
    return String(text).replace(/§[0-9a-fk-or]/gi, '').trim();
}

function copyIP(event, ip) {
    event.stopPropagation();
    const button = event.currentTarget;

    navigator.clipboard.writeText(ip).then(() => {
        button.classList.add('copied');
        button.textContent = '✓';
        setTimeout(() => {
            button.classList.remove('copied');
            button.textContent = '📋';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        showError('Failed to copy IP');
    });
}

function resetFilters() {
    currentFilter = 'all';
    currentSearch = '';
    currentSort = 'players';
    minPlayers = 0;
    maxPlayers = 10000;
    selectedVersion = '';

    document.getElementById('search-input').value = '';
    document.querySelector('.filter-btn[data-filter="all"]').click();
    renderServers();
}

function showError(message) {
    const error = document.createElement('div');
    error.className = 'error-toast';
    error.textContent = message;
    error.style.cssText = `
        position: fixed;
        top: 2rem;
        right: 2rem;
        background: #ff4444;
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    document.body.appendChild(error);
    setTimeout(() => error.remove(), 3000);
}

function animateNumber(id, target) {
    const element = document.getElementById(id);
    if (!element) return;

    const duration = 1000;
    const start = parseInt(element.textContent.replace(/,/g, '')) || 0;
    const startTime = Date.now();

    const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const current = Math.floor(start + (target - start) * easeOutQuad(progress));
        element.textContent = current.toLocaleString();

        if (progress < 1) {
            requestAnimationFrame(animate);
        }
    };

    requestAnimationFrame(animate);
}

function easeOutQuad(t) {
    return t * (2 - t);
}

// Auto-refresh every 5 minutes
setInterval(() => {
    loadStats();
    loadServers();
}, 5 * 60 * 1000);

// Expose functions to global scope for onclick handlers
window.toggleFavorite = toggleFavorite;
window.copyIP = copyIP;
window.showDetails = showDetails;
window.closeModal = closeModal;
window.resetFilters = resetFilters;
window.exportServers = exportServers;
