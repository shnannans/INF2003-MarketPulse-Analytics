/**
 * Mobile Responsiveness Handler (Task 66: Mobile Responsiveness)
 */

document.addEventListener('DOMContentLoaded', function() {
    initMobileFeatures();
});

function initMobileFeatures() {
    // Initialize mobile menu
    initMobileMenu();
    
    // Initialize touch gestures
    initTouchGestures();
    
    // Initialize responsive tables
    initResponsiveTables();
    
    // Initialize bottom navigation
    initBottomNavigation();
    
    // Handle orientation changes
    handleOrientationChange();
    
    // Initialize swipe gestures
    initSwipeGestures();
}

function initMobileMenu() {
    // Create mobile menu button if it doesn't exist
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    
    let menuBtn = document.getElementById('mobileMenuBtn');
    if (!menuBtn) {
        menuBtn = document.createElement('button');
        menuBtn.id = 'mobileMenuBtn';
        menuBtn.className = 'btn btn-outline-light mobile-menu-btn d-none';
        menuBtn.innerHTML = '<i class="bi bi-list"></i>';
        menuBtn.setAttribute('aria-label', 'Toggle navigation menu');
        menuBtn.setAttribute('aria-expanded', 'false');
        
        const navbarToggler = navbar.querySelector('.navbar-toggler');
        if (navbarToggler) {
            navbarToggler.parentNode.insertBefore(menuBtn, navbarToggler);
        } else {
            navbar.insertBefore(menuBtn, navbar.firstChild);
        }
    }
    
    // Toggle sidebar
    menuBtn.addEventListener('click', function() {
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.querySelector('.sidebar-overlay');
        
        if (sidebar) {
            sidebar.classList.toggle('open');
            menuBtn.setAttribute('aria-expanded', sidebar.classList.contains('open'));
            
            if (overlay) {
                overlay.classList.toggle('show');
            }
        }
    });
    
    // Close sidebar when clicking overlay
    const overlay = document.querySelector('.sidebar-overlay');
    if (overlay) {
        overlay.addEventListener('click', function() {
            const sidebar = document.querySelector('.sidebar');
            if (sidebar) {
                sidebar.classList.remove('open');
                menuBtn.setAttribute('aria-expanded', 'false');
                overlay.classList.remove('show');
            }
        });
    }
    
    // Close sidebar on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const sidebar = document.querySelector('.sidebar');
            if (sidebar && sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
                menuBtn.setAttribute('aria-expanded', 'false');
                const overlay = document.querySelector('.sidebar-overlay');
                if (overlay) {
                    overlay.classList.remove('show');
                }
            }
        }
    });
}

function initTouchGestures() {
    // Add touch-friendly classes
    const buttons = document.querySelectorAll('.btn, a, button');
    buttons.forEach(btn => {
        if (!btn.classList.contains('touch-optimized')) {
            btn.classList.add('touch-optimized');
        }
    });
}

function initResponsiveTables() {
    // Convert tables to mobile cards on small screens
    const tables = document.querySelectorAll('.table');
    
    tables.forEach(table => {
        if (window.innerWidth <= 767.98) {
            convertTableToCards(table);
        }
    });
    
    // Re-convert on resize
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            tables.forEach(table => {
                if (window.innerWidth <= 767.98) {
                    convertTableToCards(table);
                } else {
                    restoreTable(table);
                }
            });
        }, 250);
    });
}

function convertTableToCards(table) {
    if (table.classList.contains('mobile-converted')) return;
    
    table.classList.add('table-mobile-card', 'mobile-converted');
    
    const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
    const rows = table.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        cells.forEach((cell, index) => {
            if (headers[index]) {
                cell.setAttribute('data-label', headers[index]);
            }
        });
    });
}

function restoreTable(table) {
    table.classList.remove('table-mobile-card', 'mobile-converted');
    const cells = table.querySelectorAll('td');
    cells.forEach(cell => {
        cell.removeAttribute('data-label');
    });
}

function initBottomNavigation() {
    // Create bottom navigation for mobile if it doesn't exist
    if (window.innerWidth <= 767.98) {
        const bottomNav = document.getElementById('bottomNav');
        if (!bottomNav) {
            const nav = document.createElement('nav');
            nav.id = 'bottomNav';
            nav.className = 'bottom-nav';
            nav.setAttribute('aria-label', 'Main navigation');
            nav.innerHTML = `
                <div class="d-flex">
                    <a href="index.html" class="bottom-nav-item" aria-label="Dashboard">
                        <i class="bi bi-house"></i>
                        <span>Dashboard</span>
                    </a>
                    <a href="profile.html" class="bottom-nav-item" aria-label="Profile">
                        <i class="bi bi-person"></i>
                        <span>Profile</span>
                    </a>
                    <a href="admin.html" class="bottom-nav-item admin-only" aria-label="Admin" style="display: none;">
                        <i class="bi bi-shield-check"></i>
                        <span>Admin</span>
                    </a>
                </div>
            `;
            document.body.appendChild(nav);
            
            // Set active item
            const currentPath = window.location.pathname;
            nav.querySelectorAll('.bottom-nav-item').forEach(item => {
                if (item.getAttribute('href') === currentPath || 
                    (currentPath === '/' && item.getAttribute('href') === 'index.html')) {
                    item.classList.add('active');
                }
            });
        }
    }
}

function handleOrientationChange() {
    window.addEventListener('orientationchange', function() {
        // Reload on orientation change to adjust layouts
        setTimeout(function() {
            window.location.reload();
        }, 100);
    });
}

function initSwipeGestures() {
    // Basic swipe detection for mobile
    let touchStartX = 0;
    let touchEndX = 0;
    
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });
    
    document.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });
    
    function handleSwipe() {
        const swipeThreshold = 50;
        const diff = touchStartX - touchEndX;
        
        if (Math.abs(diff) > swipeThreshold) {
            if (diff > 0) {
                // Swipe left
                const sidebar = document.querySelector('.sidebar');
                if (sidebar && !sidebar.classList.contains('open')) {
                    // Could open sidebar or navigate forward
                }
            } else {
                // Swipe right
                const sidebar = document.querySelector('.sidebar');
                if (sidebar && sidebar.classList.contains('open')) {
                    sidebar.classList.remove('open');
                    const overlay = document.querySelector('.sidebar-overlay');
                    if (overlay) {
                        overlay.classList.remove('show');
                    }
                }
            }
        }
    }
}

// Export for use in other modules
window.mobileResponsive = {
    initMobileMenu,
    initTouchGestures,
    initResponsiveTables,
    initBottomNavigation
};

