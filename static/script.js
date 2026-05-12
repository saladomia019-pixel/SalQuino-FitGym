/* ================= SHARED UTILITIES ================= */

// Sidebar Toggle (used by both dashboards)
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('active');
    document.getElementById('overlay').classList.toggle('active');
    document.getElementById('mainContent').classList.toggle('shifted');
}

// Section Switching
function showSection(name) {
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    document.getElementById(name + 'Section').classList.add('active');
    document.querySelectorAll('.sidebar-nav a').forEach(a => a.classList.remove('active'));
    if (event && event.target) {
        const link = event.target.closest('a');
        if (link) link.classList.add('active');
    }
    // Close sidebar on mobile
    if (window.innerWidth < 768) {
        document.getElementById('sidebar').classList.remove('active');
        document.getElementById('overlay').classList.remove('active');
        document.getElementById('mainContent').classList.remove('shifted');
    }
}

// Modal Management
function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

// Close modal on overlay click
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
    }
});

// Toast Notifications
function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i> ${message}`;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 50);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, 3500);
}

// Format Currency (Philippine Peso)
function formatPeso(amount) {
    return '₱' + Number(amount).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Format Date
function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' });
}

// Format Description — converts newlines and bullet markers into an HTML list
function formatDescription(desc) {
    if (!desc) return '';
    const lines = desc.split('\n').map(l => l.trim()).filter(l => l.length > 0);
    if (lines.length <= 1 && !/^[-*•]/.test(lines[0] || '')) return desc;
    const items = lines.map(l => l.replace(/^[-*•]\s*/, ''));
    return '<ul style="list-style:none;padding:0;margin:8px 0 0 0;">' +
        items.map(item => `<li style="position:relative;padding-left:16px;margin-bottom:4px;line-height:1.5;"><span style="position:absolute;left:0;color:#f97316;">•</span>${item}</li>`).join('') +
        '</ul>';
}

// Smooth scroll for landing page
function scrollToSection(id) {
    document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
}

async function loadPublicPlans() {
    const container = document.getElementById('plansPreviewContainer');
    if (!container) return;

    try {
        const res = await fetch('/api/public/plans');
        const data = await res.json();
        const plans = data.plans || [];

        if (!plans.length) {
            container.innerHTML = '<div class="empty-state"><p>No membership plans are available yet.</p></div>';
            return;
        }

        container.innerHTML = plans.map((plan, index) => {
            const durationLabel = plan.type ? `${plan.type} • ${plan.duration_days} days` : `${plan.duration_days} days`;
            const descriptionHtml = plan.description
                ? `<div style="color:#cbd5e1;margin-top:18px;line-height:1.6;font-size:15px;">${formatDescription(plan.description)}</div>`
                : '';
            const popularClass = index === 0 ? ' popular' : '';
            const badge = index === 0 ? '<div class="pop-badge">BEST VALUE</div>' : '';
            return `
                <div class="plan-preview-card${popularClass}">
                    ${badge}
                    <h3>${plan.plan_name}</h3>
                    <div class="price">${formatPeso(plan.price)} <span>/ ${plan.type ? plan.type.toLowerCase() : 'plan'}</span></div>
                    <ul>
                        <li><i class="fas fa-check"></i> ${durationLabel}</li>
                    </ul>
                    ${descriptionHtml}
                </div>
            `;
        }).join('');
    } catch (error) {
        container.innerHTML = '<div class="empty-state"><p>Failed to load plans. Please try again later.</p></div>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadPublicPlans();

    // Auto-dismiss flash messages after 2 seconds
    document.querySelectorAll('.flash-msg').forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-10px)';
            setTimeout(() => msg.remove(), 500);
        }, 3000);
    });
});