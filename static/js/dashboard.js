let monthlyChart = null;
let balanceChart = null;
let categoryPieChart = null;
let allCategories = { credit: [], debit: [] };
let currentModalData = null;
let currentModalType = null;

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const CHART_COLORS = [
    '#0B9F6F', '#3B82F6', '#EF4444', '#F59E0B', '#8B5CF6',
    '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1',
    '#14B8A6', '#E11D48', '#A855F7', '#0EA5E9', '#D946EF',
];

document.addEventListener('DOMContentLoaded', async () => {
    // Load categories for editing
    try {
        const catResp = await fetch('/api/categories');
        allCategories = await catResp.json();
    } catch (e) {}
    loadDashboard();
});

// Close category dropdowns when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.cat-edit-wrapper')) {
        document.querySelectorAll('.cat-dropdown').forEach(d => d.remove());
    }
});

async function loadDashboard() {
    try {
        const response = await fetch('/api/monthly-summary');
        const data = await response.json();

        document.getElementById('loading').classList.add('d-none');

        if (data.length === 0) {
            document.getElementById('emptyState').classList.remove('d-none');
            return;
        }

        document.getElementById('dashboardContent').classList.remove('d-none');
        renderOverview(data);
        renderMonthlyChart(data);
        renderBalanceChart(data);
        renderMonthlyCards(data);
    } catch (error) {
        document.getElementById('loading').innerHTML =
            '<p style="color: var(--red-500); margin-top: 16px;">Failed to load dashboard. Please try again.</p>';
    }
}

function fmt(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency', currency: 'INR',
        minimumFractionDigits: 0, maximumFractionDigits: 0,
    }).format(amount);
}

function renderOverview(data) {
    const totalCredit = data.reduce((s, d) => s + d.credit, 0);
    const totalDebit = data.reduce((s, d) => s + d.debit, 0);
    const netBalance = totalCredit - totalDebit;
    const creditCount = data.reduce((s, d) => s + (d.credit_count || 0), 0);
    const debitCount = data.reduce((s, d) => s + (d.debit_count || 0), 0);
    const totalTxns = creditCount + debitCount;

    document.getElementById('totalCredit').textContent = fmt(totalCredit);
    document.getElementById('totalDebit').textContent = fmt(totalDebit);
    document.getElementById('netBalance').textContent = fmt(netBalance);
    document.getElementById('totalTransactions').textContent = totalTxns.toLocaleString('en-IN');
    document.getElementById('creditCount').textContent = `${creditCount} transactions`;
    document.getElementById('debitCount').textContent = `${debitCount} transactions`;
}

function renderMonthlyChart(data) {
    const labels = data.map(d => `${MONTH_NAMES[d.month - 1]} ${d.year}`);
    const ctx = document.getElementById('monthlyChart').getContext('2d');
    if (monthlyChart) monthlyChart.destroy();

    monthlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Credit',
                    data: data.map(d => d.credit),
                    backgroundColor: '#0B9F6F',
                    borderRadius: 6,
                    borderSkipped: false,
                    barPercentage: 0.7,
                },
                {
                    label: 'Debit',
                    data: data.map(d => d.debit),
                    backgroundColor: '#EF4444',
                    borderRadius: 6,
                    borderSkipped: false,
                    barPercentage: 0.7,
                },
            ],
        },
        options: {
            responsive: true,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: { labels: { usePointStyle: true, padding: 20, font: { size: 12, weight: '500' } } },
                tooltip: {
                    backgroundColor: '#0F172A', titleFont: { weight: '600' }, padding: 14, cornerRadius: 8,
                    callbacks: { label: (c) => ` ${c.dataset.label}: ${fmt(c.raw)}` },
                },
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#F1F5F9' }, ticks: { callback: v => fmt(v), font: { size: 11 } } },
                x: { grid: { display: false }, ticks: { font: { size: 11, weight: '500' } } },
            },
        },
    });
}

function renderBalanceChart(data) {
    const labels = data.map(d => MONTH_NAMES[d.month - 1]);
    let bal = 0;
    const balances = data.map(d => { bal += d.credit - d.debit; return bal; });
    const ctx = document.getElementById('balanceChart').getContext('2d');
    if (balanceChart) balanceChart.destroy();

    const grad = ctx.createLinearGradient(0, 0, 0, 250);
    grad.addColorStop(0, 'rgba(11, 159, 111, 0.2)');
    grad.addColorStop(1, 'rgba(11, 159, 111, 0.01)');

    balanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Balance', data: balances,
                borderColor: '#0B9F6F', backgroundColor: grad,
                fill: true, tension: 0.4,
                pointBackgroundColor: '#0B9F6F', pointBorderColor: '#fff',
                pointBorderWidth: 2, pointRadius: 5, pointHoverRadius: 7,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#0F172A', padding: 12, cornerRadius: 8,
                    callbacks: { label: (c) => `Balance: ${fmt(c.raw)}` },
                },
            },
            scales: {
                y: { grid: { color: '#F1F5F9' }, ticks: { callback: v => fmt(v), font: { size: 10 } } },
                x: { grid: { display: false }, ticks: { font: { size: 11, weight: '500' } } },
            },
        },
    });
}

function renderMonthlyCards(data) {
    const container = document.getElementById('monthlyCards');
    container.innerHTML = '';

    data.slice().reverse().forEach(d => {
        const name = `${MONTH_NAMES[d.month - 1]} ${d.year}`;
        const bal = d.credit - d.debit;
        const el = document.createElement('div');
        el.innerHTML = `
            <div class="month-card">
                <div class="month-header">
                    <h6>${name}</h6>
                    <span class="badge-balance ${bal >= 0 ? 'badge-positive' : 'badge-negative'}">
                        ${bal >= 0 ? '+' : ''}${fmt(bal)}
                    </span>
                </div>
                <div class="month-body">
                    <div class="month-row">
                        <span class="label credit-label" onclick="showDetails(${d.year}, ${d.month}, 'credit')">
                            <i class="bi bi-arrow-down-circle-fill"></i> Credit
                        </span>
                        <span class="value credit-val" onclick="showDetails(${d.year}, ${d.month}, 'credit')">${fmt(d.credit)}</span>
                    </div>
                    <div class="month-row">
                        <span class="label debit-label" onclick="showDetails(${d.year}, ${d.month}, 'debit')">
                            <i class="bi bi-arrow-up-circle-fill"></i> Debit
                        </span>
                        <span class="value debit-val" onclick="showDetails(${d.year}, ${d.month}, 'debit')">${fmt(d.debit)}</span>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(el);
    });
}

async function showDetails(year, month, txnType) {
    const name = `${MONTH_NAMES[month - 1]} ${year}`;
    const label = txnType === 'credit' ? 'Credit (Income)' : 'Debit (Expenses)';
    document.getElementById('modalTitle').innerHTML = `<i class="bi bi-list-columns-reverse"></i> ${label} - ${name}`;
    document.getElementById('exportLink').href = `/export?year=${year}&month=${month}&type=${txnType}`;
    currentModalType = txnType;

    try {
        const resp = await fetch(`/api/transactions/${year}/${month}/${txnType}`);
        const data = await resp.json();
        currentModalData = data;

        renderCategoryPie(data.category_summary);
        renderCategoryBreakdown(data.category_summary, data.total);
        renderTransactionsTable(data.transactions);

        const search = document.getElementById('searchTransactions');
        search.value = '';
        search.oninput = () => {
            const q = search.value.toLowerCase();
            const filtered = data.transactions.filter(t =>
                t.description.toLowerCase().includes(q) || t.category.toLowerCase().includes(q)
            );
            renderTransactionsTable(filtered);
        };

        new bootstrap.Modal(document.getElementById('detailsModal')).show();
    } catch (e) {
        showToast('Failed to load transaction details.', 'error');
    }
}

function renderCategoryPie(summary) {
    const labels = Object.keys(summary);
    const values = Object.values(summary);
    const ctx = document.getElementById('categoryPieChart').getContext('2d');
    if (categoryPieChart) categoryPieChart.destroy();

    categoryPieChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: CHART_COLORS.slice(0, labels.length),
                borderWidth: 3, borderColor: '#fff', hoverOffset: 6,
            }],
        },
        options: {
            responsive: true, cutout: '62%',
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 10, padding: 14, font: { size: 11.5, weight: '500' } } },
                tooltip: {
                    backgroundColor: '#0F172A', padding: 12, cornerRadius: 8,
                    callbacks: { label: (c) => ` ${c.label}: ${fmt(c.raw)}` },
                },
            },
        },
    });
}

function renderCategoryBreakdown(summary, total) {
    const container = document.getElementById('categoryBreakdown');
    const sorted = Object.entries(summary).sort((a, b) => b[1] - a[1]);

    container.innerHTML = '<h6 style="font-weight: 600; margin-bottom: 16px; color: var(--slate-800);"><i class="bi bi-tag me-1"></i> Category Breakdown</h6>';
    sorted.forEach(([cat, amount], i) => {
        const pct = ((amount / total) * 100).toFixed(1);
        const color = CHART_COLORS[i % CHART_COLORS.length];
        container.innerHTML += `
            <div class="cat-breakdown-item">
                <div class="cat-row">
                    <span class="cat-name">${cat}</span>
                    <span class="cat-amount">${fmt(amount)}<span class="cat-pct">${pct}%</span></span>
                </div>
                <div class="cat-bar">
                    <div class="cat-bar-fill" style="width: ${pct}%; background: ${color};"></div>
                </div>
            </div>
        `;
    });
}

function renderTransactionsTable(transactions) {
    const tbody = document.getElementById('transactionsBody');
    tbody.innerHTML = '';

    if (transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--slate-400); padding: 32px;">No transactions found</td></tr>';
        return;
    }

    transactions.forEach(t => {
        const row = document.createElement('tr');
        const cats = currentModalType === 'credit' ? allCategories.credit : allCategories.debit;
        row.innerHTML = `
            <td style="white-space: nowrap;">${new Date(t.date).toLocaleDateString('en-IN', {day: '2-digit', month: 'short', year: 'numeric'})}</td>
            <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${t.description}">${t.description}</td>
            <td>
                <div class="cat-edit-wrapper">
                    <span class="cat-badge" data-txn-id="${t.id}" data-current="${t.category}" onclick="openCategoryDropdown(this, '${currentModalType}')">
                        ${t.category} <i class="bi bi-pencil-fill"></i>
                    </span>
                </div>
            </td>
            <td class="text-end">${fmt(t.amount)}</td>
        `;
        tbody.appendChild(row);
    });
}

function openCategoryDropdown(badge, txnType) {
    // Remove any existing dropdowns
    document.querySelectorAll('.cat-dropdown').forEach(d => d.remove());

    const wrapper = badge.closest('.cat-edit-wrapper');
    const currentCat = badge.dataset.current;
    const cats = txnType === 'credit' ? allCategories.credit : allCategories.debit;

    const dropdown = document.createElement('div');
    dropdown.className = 'cat-dropdown';

    cats.forEach(cat => {
        const option = document.createElement('div');
        option.className = `cat-option ${cat === currentCat ? 'active' : ''}`;
        option.textContent = cat;
        option.onclick = async (e) => {
            e.stopPropagation();
            if (cat === currentCat) { dropdown.remove(); return; }

            const txnId = badge.dataset.txnId;
            try {
                const resp = await fetch(`/api/transactions/${txnId}/category`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ category: cat }),
                });
                const result = await resp.json();
                if (result.success) {
                    badge.dataset.current = cat;
                    badge.innerHTML = `${cat} <i class="bi bi-pencil-fill"></i>`;
                    showToast(`Category updated to "${cat}"`);

                    // Update the transaction in currentModalData
                    if (currentModalData) {
                        const txn = currentModalData.transactions.find(t => t.id == txnId);
                        if (txn) {
                            // Recalculate category summary
                            currentModalData.category_summary[currentCat] -= txn.amount;
                            if (currentModalData.category_summary[currentCat] <= 0) {
                                delete currentModalData.category_summary[currentCat];
                            }
                            if (!currentModalData.category_summary[cat]) {
                                currentModalData.category_summary[cat] = 0;
                            }
                            currentModalData.category_summary[cat] += txn.amount;
                            txn.category = cat;

                            renderCategoryPie(currentModalData.category_summary);
                            renderCategoryBreakdown(currentModalData.category_summary, currentModalData.total);
                        }
                    }
                } else {
                    showToast('Failed to update category', 'error');
                }
            } catch (e) {
                showToast('Failed to update category', 'error');
            }
            dropdown.remove();
        };
        dropdown.appendChild(option);
    });

    wrapper.appendChild(dropdown);
}
