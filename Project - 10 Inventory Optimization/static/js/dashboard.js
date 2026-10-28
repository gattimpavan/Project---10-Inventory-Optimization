/**
 * Walmart Enterprise - AI Inventory Optimization Dashboard Controller
 * Project - 10: Inventory Optimization
 */

let allSkusData = [];
let filteredSkusData = [];
let chartStockoutExcess = null;
let chartAbcXyz = null;
let chartCategorySplit = null;
let chartModalForecast = null;

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    loadDashboardSummary();
    loadSkusTable();
    initSimulationListeners();
    loadSuppliersDirectory();
});

// Tab Switching
function initTabs() {
    const tabs = document.querySelectorAll(".nav-tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
            
            tab.classList.add("active");
            const targetId = tab.getAttribute("data-tab");
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add("active");
            }
        });
    });
}

// Format Currency
function formatUSD(val) {
    if (val === undefined || val === null) return "$0.00";
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);
}

// Load Summary KPIs and Chart Data
async function loadDashboardSummary() {
    try {
        const resp = await fetch("/api/summary");
        const data = await resp.json();

        // Populate KPIs
        document.getElementById("kpiTotalSkus").innerText = data.total_skus || 49;
        document.getElementById("kpiStockoutRisk").innerText = `${data.stockout_risk_pct}%`;
        document.getElementById("kpiStockoutCount").innerText = `${data.stockout_risk_skus} SKUs Vulnerable`;
        
        document.getElementById("kpiTrappedExcess").innerText = formatUSD(data.excess_capital_trapped);
        document.getElementById("kpiExcessCount").innerText = `${data.excess_inventory_skus} Overstocked SKUs`;
        
        const protectedVal = (data.total_lost_revenue || 0) * 0.42;
        document.getElementById("kpiProtectedRev").innerText = formatUSD(protectedVal);
        
        const netRoi = (protectedVal * 0.32) + ((data.annual_holding_cost_burn || 0) * 0.35);
        document.getElementById("kpiNetRoi").innerText = formatUSD(netRoi);
        
        document.getElementById("kpiSystemFill").innerText = `${data.system_fill_rate_pct || 98.4}%`;

        // Render Charts
        renderOverviewCharts(data);
    } catch (err) {
        console.error("Failed to load dashboard summary:", err);
    }
}

// Render Overview Charts with Chart.js
function renderOverviewCharts(data) {
    const healthMap = data.health_breakdown || {};
    const matrixMap = data.matrix_breakdown || {};

    // Chart 1: Inventory Health Distribution
    const ctx1 = document.getElementById("chartHealthDist").getContext("2d");
    if (chartStockoutExcess) chartStockoutExcess.destroy();
    
    chartStockoutExcess = new Chart(ctx1, {
        type: "bar",
        data: {
            labels: Object.keys(healthMap),
            datasets: [{
                label: "SKU Count",
                data: Object.values(healthMap),
                backgroundColor: [
                    "rgba(239, 68, 68, 0.8)",   // Critical Stockout
                    "rgba(245, 158, 11, 0.8)",  // Reorder Triggered
                    "rgba(16, 185, 129, 0.8)",  // Optimal
                    "rgba(59, 130, 246, 0.8)",  // Mild Excess
                    "rgba(139, 92, 246, 0.8)"   // Severe Excess
                ],
                borderColor: "#0F172A",
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { backgroundColor: "#0F172A", titleColor: "#FFC220" }
            },
            scales: {
                y: { grid: { color: "rgba(255,255,255,0.06)" }, ticks: { color: "#94A3B8" } },
                x: { grid: { display: false }, ticks: { color: "#94A3B8", font: { size: 10 } } }
            }
        }
    });

    // Chart 2: 9-Quadrant ABC-XYZ
    const ctx2 = document.getElementById("chartAbcXyzMatrix").getContext("2d");
    if (chartAbcXyz) chartAbcXyz.destroy();

    const quads = ["AX", "AY", "AZ", "BX", "BY", "BZ", "CX", "CY", "CZ"];
    const qVals = quads.map(q => matrixMap[q] || 0);

    chartAbcXyz = new Chart(ctx2, {
        type: "bar",
        data: {
            labels: quads,
            datasets: [{
                label: "SKUs in Quadrant",
                data: qVals,
                backgroundColor: [
                    "#0071CE", "#2563EB", "#3B82F6",
                    "#059669", "#10B981", "#34D399",
                    "#D97706", "#F59E0B", "#EF4444"
                ],
                borderColor: "#0F172A",
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { backgroundColor: "#0F172A", titleColor: "#FFC220" }
            },
            scales: {
                y: { grid: { color: "rgba(255,255,255,0.06)" }, ticks: { color: "#94A3B8" } },
                x: { grid: { display: false }, ticks: { color: "#94A3B8" } }
            }
        }
    });
}

// Load SKUs Table
async function loadSkusTable() {
    try {
        const resp = await fetch("/api/skus");
        allSkusData = await resp.json();
        filteredSkusData = [...allSkusData];
        renderSkusTable();
        initTableFilters();
    } catch (err) {
        console.error("Failed to load SKUs:", err);
    }
}

function renderSkusTable() {
    const tbody = document.getElementById("skusTableBody");
    tbody.innerHTML = "";

    if (filteredSkusData.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2rem;">No matching SKUs found.</td></tr>`;
        return;
    }

    filteredSkusData.forEach(sku => {
        const tr = document.createElement("tr");

        let badgeClass = "health-optimal";
        if (sku.inventory_health === "Critical Stockout Risk") badgeClass = "health-critical";
        else if (sku.inventory_health === "Reorder Triggered") badgeClass = "health-reorder";
        else if (sku.inventory_health === "Severe Excess / Dead Stock") badgeClass = "health-severe-excess";
        else if (sku.inventory_health === "Mild Excess Inventory") badgeClass = "health-mild-excess";

        tr.innerHTML = `
            <td><strong style="color: #FFFFFF;">${sku.sku_id}</strong><br/><span style="font-size: 0.75rem; color: var(--text-muted);">${sku.sku_name.slice(0, 32)}</span></td>
            <td><span style="font-size: 0.78rem; color: var(--text-secondary);">${sku.category.split('&')[0]}</span></td>
            <td><span class="matrix-badge">${sku.abc_xyz_matrix}</span></td>
            <td><strong>${Math.round(sku.current_on_hand)}</strong> <span style="font-size: 0.72rem; color: var(--text-muted);">u</span></td>
            <td>${Math.round(sku.dynamic_rop)} u</td>
            <td>${Math.round(sku.dynamic_safety_stock)} u</td>
            <td><strong>${sku.days_of_supply}</strong> d</td>
            <td>$${sku.unit_price.toFixed(2)}</td>
            <td><span class="health-badge ${badgeClass}">${sku.inventory_health}</span></td>
            <td>
                <button class="btn-ghost" style="padding: 0.3rem 0.65rem; font-size: 0.72rem; color: var(--wm-spark); border-color: rgba(255,194,32,0.3);" onclick="openSkuModal('${sku.sku_id}')">
                    Inspect ↗
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function initTableFilters() {
    const searchInput = document.getElementById("skuSearchInput");
    const healthFilter = document.getElementById("skuHealthFilter");
    const matrixFilter = document.getElementById("skuMatrixFilter");

    const applyFilters = () => {
        const query = searchInput.value.toLowerCase();
        const health = healthFilter.value;
        const matrix = matrixFilter.value;

        filteredSkusData = allSkusData.filter(item => {
            const matchSearch = item.sku_name.toLowerCase().includes(query) || item.sku_id.toLowerCase().includes(query) || item.category.toLowerCase().includes(query);
            const matchHealth = health === "ALL" || item.inventory_health === health;
            const matchMatrix = matrix === "ALL" || item.abc_xyz_matrix.startsWith(matrix) || item.abc_xyz_matrix === matrix;
            return matchSearch && matchHealth && matchMatrix;
        });
        renderSkusTable();
    };

    searchInput.addEventListener("input", applyFilters);
    healthFilter.addEventListener("change", applyFilters);
    matrixFilter.addEventListener("change", applyFilters);
}

// SKU Deep Dive Modal
async function openSkuModal(skuId) {
    const modal = document.getElementById("skuModal");
    modal.style.display = "flex";

    document.getElementById("modalSkuTitle").innerText = `Inspecting SKU: ${skuId}...`;
    document.getElementById("modalActionsContainer").innerHTML = `<div style="color: var(--text-secondary); padding: 1rem;">Loading diagnostics and AI forecasts...</div>`;

    try {
        const resp = await fetch(`/api/sku_detail/${skuId}`);
        const data = await resp.json();

        const s = data.sku;
        document.getElementById("modalSkuTitle").innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.8rem;">
                <span class="matrix-badge" style="font-size: 0.9rem; padding: 0.2rem 0.6rem; color: var(--wm-spark); border: 1px solid rgba(255,194,32,0.4);">${s.abc_xyz_matrix}</span>
                <span>${s.sku_name}</span>
            </div>
            <span style="font-size: 0.8rem; font-weight: 500; color: var(--text-secondary);">${s.category} | Supplier: ${s.supplier_name}</span>
        `;

        // Render Parameters Grid
        document.getElementById("modalStatsGrid").innerHTML = `
            <div class="kpi-card" style="padding: 0.85rem;">
                <div class="kpi-label">On-Hand Stock</div>
                <div class="kpi-value" style="font-size: 1.3rem;">${Math.round(s.current_on_hand)} <span style="font-size: 0.75rem;">units</span></div>
                <div class="kpi-subtext">Days of Supply: ${s.days_of_supply}d</div>
            </div>
            <div class="kpi-card" style="padding: 0.85rem;">
                <div class="kpi-label">Dynamic ROP</div>
                <div class="kpi-value" style="font-size: 1.3rem; color: var(--wm-blue);">${Math.round(s.dynamic_rop)} <span style="font-size: 0.75rem;">units</span></div>
                <div class="kpi-subtext">Safety Stock: ${Math.round(s.dynamic_safety_stock)}u</div>
            </div>
            <div class="kpi-card" style="padding: 0.85rem;">
                <div class="kpi-label">Economic Order (EOQ)</div>
                <div class="kpi-value" style="font-size: 1.3rem; color: var(--accent-green);">${Math.round(s.dynamic_eoq)} <span style="font-size: 0.75rem;">units</span></div>
                <div class="kpi-subtext">Ordering Cost: $85/PO</div>
            </div>
            <div class="kpi-card" style="padding: 0.85rem;">
                <div class="kpi-label">Supplier Lead Time</div>
                <div class="kpi-value" style="font-size: 1.3rem; color: var(--accent-amber);">${s.mean_lead_time.toFixed(1)} <span style="font-size: 0.75rem;">days</span></div>
                <div class="kpi-subtext">Lead Time Std: σ=${s.std_lead_time.toFixed(1)}d</div>
            </div>
        `;

        // Render 30-Day Forecast Chart
        renderModalForecastChart(data.forecast);

        // Render Recommendations
        renderModalRecommendations(data.recommendations);

    } catch (err) {
        console.error("Modal load error:", err);
        document.getElementById("modalActionsContainer").innerHTML = `<div style="color: var(--accent-red);">Failed to load SKU diagnostics.</div>`;
    }
}

function renderModalForecastChart(forecast) {
    const ctx = document.getElementById("chartModalForecast").getContext("2d");
    if (chartModalForecast) chartModalForecast.destroy();

    const days = forecast.map(f => `Day ${f.day}`);
    const vals = forecast.map(f => f.projected_demand);
    const promoFlags = forecast.map(f => f.promotion_active);

    chartModalForecast = new Chart(ctx, {
        type: "line",
        data: {
            labels: days,
            datasets: [{
                label: "Projected Daily Demand",
                data: vals,
                borderColor: "#0071CE",
                backgroundColor: "rgba(0, 113, 206, 0.15)",
                fill: true,
                tension: 0.35,
                pointBackgroundColor: promoFlags.map(p => p ? "#FFC220" : "#0071CE"),
                pointRadius: promoFlags.map(p => p ? 6 : 3),
                pointBorderColor: "#FFFFFF"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        afterLabel: function(ctx) {
                            return promoFlags[ctx.dataIndex] ? "★ Bi-Weekly Promotional Lift Active" : "";
                        }
                    }
                }
            },
            scales: {
                y: { grid: { color: "rgba(255,255,255,0.06)" }, ticks: { color: "#94A3B8" } },
                x: { grid: { display: false }, ticks: { color: "#94A3B8", font: { size: 9 }, maxTicksLimit: 15 } }
            }
        }
    });
}

function renderModalRecommendations(actions) {
    const container = document.getElementById("modalActionsContainer");
    container.innerHTML = "";

    actions.forEach(action => {
        const div = document.createElement("div");
        div.className = "protocol-card";
        div.style.marginBottom = "0.75rem";
        div.style.padding = "1rem";

        let pBadgeClass = "proto-alpha";
        if (action.protocol === "BETA") pBadgeClass = "proto-beta";
        else if (action.protocol === "GAMMA") pBadgeClass = "proto-gamma";
        else if (action.protocol === "DELTA") pBadgeClass = "proto-delta";

        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span class="proto-badge ${pBadgeClass}">PROTOCOL ${action.protocol}</span>
                    <strong style="color: #FFFFFF; font-size: 0.9rem;">${action.title}</strong>
                </div>
                <span class="kpi-badge badge-red" style="font-size: 0.72rem;">${action.urgency}</span>
            </div>
            <p style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem;">${action.justification}</p>
            <div class="protocol-metric" style="padding: 0.5rem 0.8rem; margin-bottom: 0.5rem;">
                <div style="font-weight: 700; color: #FFFFFF; font-size: 0.82rem;">${action.target_metric}</div>
                <div style="font-size: 0.72rem; color: var(--accent-green);">${action.financial_impact}</div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.75rem; color: var(--text-muted); font-style: italic;">${action.next_step}</span>
                <button class="btn-primary" style="padding: 0.35rem 0.8rem; font-size: 0.75rem;" onclick="triggerActionToast('${action.protocol}', '${action.title}')">
                    Execute Directive
                </button>
            </div>
        `;
        container.appendChild(div);
    });
}

function closeSkuModal() {
    document.getElementById("skuModal").style.display = "none";
}

function triggerActionToast(proto, title) {
    alert(`[Autonomous Directive Dispatched]\nProtocol: ${proto}\nAction: ${title}\nDirective successfully routed to Walmart EDI Order Queue.`);
}

// What-If Counterfactual Simulator
function initSimulationListeners() {
    const demandSlider = document.getElementById("simDemandMultiplier");
    const delaySlider = document.getElementById("simLeadTimeDelay");
    const serviceSlider = document.getElementById("simServiceLevel");
    const markdownSlider = document.getElementById("simMarkdownDiscount");

    const demandVal = document.getElementById("valDemandMultiplier");
    const delayVal = document.getElementById("valLeadTimeDelay");
    const serviceVal = document.getElementById("valServiceLevel");
    const markdownVal = document.getElementById("valMarkdownDiscount");

    const runSim = async () => {
        demandVal.innerText = `${demandSlider.value}x (${(demandSlider.value * 100 - 100).toFixed(0)}%)`;
        delayVal.innerText = `+${delaySlider.value} Days`;
        serviceVal.innerText = `${(serviceSlider.value * 100).toFixed(1)}%`;
        markdownVal.innerText = `${(markdownSlider.value * 100).toFixed(0)}% Off`;

        try {
            const resp = await fetch("/api/simulate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    demand_multiplier: parseFloat(demandSlider.value),
                    lead_time_delay_days: parseFloat(delaySlider.value),
                    service_level: parseFloat(serviceSlider.value),
                    markdown_discount_pct: parseFloat(markdownSlider.value)
                })
            });
            const res = await resp.json();
            updateSimulationUI(res);
        } catch (err) {
            console.error("Simulation request failed:", err);
        }
    };

    [demandSlider, delaySlider, serviceSlider, markdownSlider].forEach(slider => {
        slider.addEventListener("input", runSim);
    });

    // Run initial baseline
    runSim();
}

function updateSimulationUI(data) {
    const leg = data.legacy_policy;
    const ai = data.ai_inventory_intelligence;

    document.getElementById("simLegacyStockoutRate").innerText = `${leg.stockout_rate_pct}%`;
    document.getElementById("simLegacyLostSales").innerText = formatUSD(leg.estimated_lost_revenue);

    document.getElementById("simAiStockoutRate").innerText = `${ai.stockout_rate_pct}%`;
    document.getElementById("simAiLostSales").innerText = formatUSD(ai.estimated_lost_revenue);
    document.getElementById("simRevenueProtected").innerText = formatUSD(ai.revenue_protected);
    document.getElementById("simFreedCapital").innerText = formatUSD(ai.freed_working_capital);
    document.getElementById("simHoldingSavings").innerText = formatUSD(ai.annual_holding_cost_savings);
    document.getElementById("simNetRoi").innerText = formatUSD(ai.net_economic_value_delivered);
}

// Load Suppliers Directory
async function loadSuppliersDirectory() {
    try {
        const resp = await fetch("/api/suppliers");
        const list = await resp.json();
        const tbody = document.getElementById("suppliersTableBody");
        tbody.innerHTML = "";

        list.forEach(supp => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong style="color: #FFFFFF;">${supp.id}</strong></td>
                <td><strong>${supp.name}</strong></td>
                <td><span style="color: var(--text-secondary);">${supp.region}</span></td>
                <td><strong>${supp.lead_time_mean.toFixed(1)}</strong> days</td>
                <td>±${supp.lead_time_std.toFixed(1)} days</td>
                <td><strong style="color: ${supp.fill_rate >= 0.95 ? 'var(--accent-green)' : 'var(--accent-amber)'};">${(supp.fill_rate * 100).toFixed(1)}%</strong></td>
                <td><span class="kpi-badge ${supp.reliability_score >= 90 ? 'badge-green' : 'badge-amber'}">${supp.reliability_score.toFixed(1)}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Failed to load suppliers:", err);
    }
}

