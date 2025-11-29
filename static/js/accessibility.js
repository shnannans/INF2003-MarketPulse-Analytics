/**
 * Accessibility Handler (Task 67: Accessibility Requirements)
 */

document.addEventListener('DOMContentLoaded', function() {
    initAccessibilityFeatures();
});

function initAccessibilityFeatures() {
    // Add skip to main content link
    addSkipToMainLink();
    
    // Enhance keyboard navigation
    enhanceKeyboardNavigation();
    
    // Add ARIA labels where missing
    addAriaLabels();
    
    // Initialize focus management
    initFocusManagement();
    
    // Add live regions
    addLiveRegions();
    
    // High contrast mode removed per user request
    // Remove any existing high contrast toggle from DOM
    const existingToggle = document.getElementById('highContrastToggle');
    if (existingToggle) {
        existingToggle.remove();
    }
    
    // Also check after a short delay in case it's created dynamically
    setTimeout(() => {
        const toggle = document.getElementById('highContrastToggle');
        if (toggle) {
            toggle.remove();
        }
    }, 100);
    
    // Enhance form accessibility
    enhanceFormAccessibility();
    
    // Add keyboard shortcuts
    addKeyboardShortcuts();
}

function addSkipToMainLink() {
    if (document.getElementById('skipToMain')) return;
    
    const skipLink = document.createElement('a');
    skipLink.id = 'skipToMain';
    skipLink.className = 'skip-to-main';
    skipLink.href = '#main-content';
    skipLink.textContent = 'Skip to main content';
    document.body.insertBefore(skipLink, document.body.firstChild);
    
    // Add main content ID if it doesn't exist
    const main = document.querySelector('main, .content-area, #main-content');
    if (main && !main.id) {
        main.id = 'main-content';
    }
}

function enhanceKeyboardNavigation() {
    // Add keyboard navigation to custom components
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(dropdown => {
        const toggle = dropdown.querySelector('.dropdown-toggle');
        if (toggle && !toggle.getAttribute('aria-haspopup')) {
            toggle.setAttribute('aria-haspopup', 'true');
            toggle.setAttribute('aria-expanded', 'false');
        }
    });
    
    // Enhance modal keyboard navigation
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (!modal.getAttribute('role')) {
            modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-modal', 'true');
        }
    });
}

function addAriaLabels() {
    // Add ARIA labels to icon-only buttons
    const iconButtons = document.querySelectorAll('button:not([aria-label]):not([aria-labelledby])');
    iconButtons.forEach(button => {
        const icon = button.querySelector('i[class*="bi-"]');
        if (icon && !button.textContent.trim()) {
            const iconClass = Array.from(icon.classList).find(c => c.startsWith('bi-'));
            if (iconClass) {
                const label = iconClass.replace('bi-', '').replace(/-/g, ' ');
                button.setAttribute('aria-label', label);
            }
        }
    });
    
    // Add ARIA labels to images without alt text
    const images = document.querySelectorAll('img:not([alt])');
    images.forEach(img => {
        if (!img.getAttribute('alt')) {
            img.setAttribute('alt', '');
            img.setAttribute('aria-hidden', 'true');
        }
    });
    
    // Add ARIA labels to form inputs
    const inputs = document.querySelectorAll('input:not([aria-label]):not([aria-labelledby])');
    inputs.forEach(input => {
        const label = document.querySelector(`label[for="${input.id}"]`);
        if (label && !input.getAttribute('aria-labelledby')) {
            input.setAttribute('aria-labelledby', label.id || `label-${input.id}`);
        }
    });
}

function initFocusManagement() {
    // Trap focus in modals
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('shown.bs.modal', function() {
            const focusableElements = modal.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            if (focusableElements.length > 0) {
                focusableElements[0].focus();
            }
        });
    });
    
    // Return focus to trigger after closing modal
    document.addEventListener('hidden.bs.modal', function(e) {
        const trigger = document.querySelector(`[data-bs-target="#${e.target.id}"]`);
        if (trigger) {
            trigger.focus();
        }
    });
}

function addLiveRegions() {
    // Add live region for announcements
    if (!document.getElementById('liveRegion')) {
        const liveRegion = document.createElement('div');
        liveRegion.id = 'liveRegion';
        liveRegion.setAttribute('role', 'status');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'sr-only';
        document.body.appendChild(liveRegion);
    }
    
    // Add alert region
    if (!document.getElementById('alertRegion')) {
        const alertRegion = document.createElement('div');
        alertRegion.id = 'alertRegion';
        alertRegion.setAttribute('role', 'alert');
        alertRegion.setAttribute('aria-live', 'assertive');
        alertRegion.setAttribute('aria-atomic', 'true');
        alertRegion.className = 'sr-only';
        document.body.appendChild(alertRegion);
    }
}

function announceToScreenReader(message, priority = 'polite') {
    const region = priority === 'assertive' 
        ? document.getElementById('alertRegion')
        : document.getElementById('liveRegion');
    
    if (region) {
        region.textContent = message;
        // Clear after announcement
        setTimeout(() => {
            region.textContent = '';
        }, 1000);
    }
}

// Font size controls completely removed per user request
// No font size functionality remains

// Font size function removed per user request

// High contrast mode removed per user request

function enhanceFormAccessibility() {
    // Add required indicators
    const requiredInputs = document.querySelectorAll('input[required], select[required], textarea[required]');
    requiredInputs.forEach(input => {
        const label = document.querySelector(`label[for="${input.id}"]`);
        if (label && !label.querySelector('.required')) {
            label.classList.add('required');
        }
    });
    
    // Add error announcements
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('invalid', function(e) {
            e.preventDefault();
            const firstInvalid = form.querySelector(':invalid');
            if (firstInvalid) {
                firstInvalid.focus();
                const label = document.querySelector(`label[for="${firstInvalid.id}"]`);
                const message = label ? `${label.textContent} is required` : 'Please fill in all required fields';
                announceToScreenReader(message, 'assertive');
            }
        }, true);
    });
}

function addKeyboardShortcuts() {
    // Add keyboard shortcuts help
    document.addEventListener('keydown', function(e) {
        // Alt + H: Show help
        if (e.altKey && e.key === 'h') {
            e.preventDefault();
            showKeyboardShortcuts();
        }
        
        // Alt + M: Toggle mobile menu
        if (e.altKey && e.key === 'm' && window.innerWidth <= 767.98) {
            e.preventDefault();
            const menuBtn = document.getElementById('mobileMenuBtn');
            if (menuBtn) {
                menuBtn.click();
            }
        }
        
        // Alt + S: Skip to main content
        if (e.altKey && e.key === 's') {
            e.preventDefault();
            const main = document.getElementById('main-content');
            if (main) {
                main.focus();
                main.scrollIntoView({ behavior: 'smooth' });
            }
        }
    });
}

function showKeyboardShortcuts() {
    const shortcuts = [
        { key: 'Alt + H', action: 'Show keyboard shortcuts' },
        { key: 'Alt + S', action: 'Skip to main content' },
        { key: 'Alt + M', action: 'Toggle mobile menu (mobile only)' },
        { key: 'Escape', action: 'Close modal/sidebar' },
        { key: 'Tab', action: 'Navigate through interactive elements' },
        { key: 'Enter/Space', action: 'Activate button/link' }
    ];
    
    const modal = document.createElement('div');
    modal.className = 'modal fade show';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Keyboard Shortcuts</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Shortcut</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${shortcuts.map(s => `
                                <tr>
                                    <td><kbd>${s.key}</kbd></td>
                                    <td>${s.action}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    modal.addEventListener('hidden.bs.modal', function() {
        modal.remove();
    });
}

// Export for use in other modules
window.accessibility = {
    announceToScreenReader,
    showKeyboardShortcuts
};

// Make functions globally available
window.showKeyboardShortcuts = showKeyboardShortcuts;

