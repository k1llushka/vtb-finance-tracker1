const API_BASE = "/transactions/api";

const Utils = {
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (const rawCookie of cookies) {
                const cookie = rawCookie.trim();
                if (cookie.startsWith(`${name}=`)) {
                    cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    },

    formatMoney(amount) {
        return new Intl.NumberFormat("ru-RU", {
            style: "currency",
            currency: "RUB",
            minimumFractionDigits: 2,
        }).format(Number(amount || 0));
    },

    showNotification(message, type = "success") {
        const alertDiv = document.createElement("div");
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
        alertDiv.style.zIndex = "9999";
        alertDiv.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
        document.body.appendChild(alertDiv);
        setTimeout(() => alertDiv.remove(), 5000);
    },

    renderLoading(target) {
        target.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status"></div>
            </div>
        `;
    },

    getDashboardParams() {
        const params = new URLSearchParams(window.location.search);
        return {
            card: params.get("card") || "",
            period: params.get("period") || "month",
        };
    },
};

const API = {
    async request(url, options = {}) {
        const response = await fetch(url, {
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": Utils.getCookie("csrftoken"),
                ...(options.headers || {}),
            },
            ...options,
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        if (response.status === 204) {
            return null;
        }
        return response.json();
    },

    getChartData(type, params = {}) {
        return this.request(`${API_BASE}/transactions/chart_data/?${new URLSearchParams({ type, ...params })}`);
    },

    getInsights(params = {}) {
        return this.request(`/ai/insights?${new URLSearchParams(params)}`);
    },

    categorizeExpense(payload) {
        return this.request("/ai/categorize", {
            method: "POST",
            body: JSON.stringify(payload),
        });
    },

    sendChatMessage(message, params = {}) {
        return this.request("/ai/chat", {
            method: "POST",
            body: JSON.stringify({ message, ...params }),
        });
    },
};

const Charts = {
    instances: {},

    async createMonthlyChart(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const params = Utils.getDashboardParams();
        const chartData = await API.getChartData("monthly", params);
        if (this.instances[canvasId]) {
            this.instances[canvasId].destroy();
        }

        const ctx = canvas.getContext("2d");
        const incomeGradient = ctx.createLinearGradient(0, 0, 0, 320);
        incomeGradient.addColorStop(0, "rgba(15, 160, 88, 0.35)");
        incomeGradient.addColorStop(1, "rgba(15, 160, 88, 0.03)");
        const expenseGradient = ctx.createLinearGradient(0, 0, 0, 320);
        expenseGradient.addColorStop(0, "rgba(220, 53, 69, 0.35)");
        expenseGradient.addColorStop(1, "rgba(220, 53, 69, 0.03)");

        const glowPlugin = {
            id: "glowPlugin",
            beforeDatasetDraw(chart, args) {
                const { ctx: chartCtx } = chart;
                chartCtx.save();
                chartCtx.shadowColor = args.index === 0 ? "rgba(25, 135, 84, 0.35)" : "rgba(220, 53, 69, 0.35)";
                chartCtx.shadowBlur = 14;
                chartCtx.shadowOffsetY = 4;
            },
            afterDatasetDraw(chart) {
                chart.ctx.restore();
            },
        };

        this.instances[canvasId] = new Chart(ctx, {
            type: "line",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        ...chartData.datasets[0],
                        backgroundColor: incomeGradient,
                        fill: true,
                        tension: 0.35,
                        borderWidth: 3,
                        pointRadius: 4,
                        pointHoverRadius: 7,
                    },
                    {
                        ...chartData.datasets[1],
                        backgroundColor: expenseGradient,
                        fill: true,
                        tension: 0.35,
                        borderWidth: 3,
                        pointRadius: 4,
                        pointHoverRadius: 7,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { usePointStyle: true, pointStyle: "circle", padding: 16 },
                    },
                    tooltip: {
                        backgroundColor: "rgba(12, 20, 37, 0.92)",
                        callbacks: {
                            label(context) {
                                return `${context.dataset.label}: ${Utils.formatMoney(context.raw)}`;
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(31, 51, 83, 0.08)" },
                        ticks: {
                            callback(value) {
                                return Utils.formatMoney(value);
                            },
                        },
                    },
                    x: {
                        grid: { display: false },
                    },
                },
            },
            plugins: [glowPlugin],
        });
    },

    async createCategoryChart(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const params = Utils.getDashboardParams();
        const chartData = await API.getChartData("category", params);
        if (this.instances[canvasId]) {
            this.instances[canvasId].destroy();
        }

        const ctx = canvas.getContext("2d");
        this.instances[canvasId] = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: chartData.labels,
                datasets: chartData.datasets.map((dataset) => ({
                    ...dataset,
                    borderWidth: 0,
                    hoverOffset: 10,
                    spacing: 3,
                    borderRadius: 6,
                })),
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "64%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            usePointStyle: true,
                            pointStyle: "circle",
                            boxWidth: 10,
                            padding: 18,
                        },
                    },
                    tooltip: {
                        callbacks: {
                            label(context) {
                                return `${context.label}: ${Utils.formatMoney(context.parsed)}`;
                            },
                        },
                    },
                },
            },
        });
    },
};

const AI = {
    async loadInsightsPanel() {
        const insightsContainer = document.getElementById("insights-container");
        const recommendationsContainer = document.getElementById("recommendations-container");
        const forecastContainer = document.getElementById("forecast-container");
        if (!insightsContainer || !recommendationsContainer || !forecastContainer) return;

        Utils.renderLoading(insightsContainer);
        Utils.renderLoading(recommendationsContainer);
        Utils.renderLoading(forecastContainer);

        try {
            const payload = await API.getInsights(Utils.getDashboardParams());

            insightsContainer.innerHTML = `
                <div class="row g-3">
                    ${payload.insights.map((item) => `
                        <div class="col-md-6">
                            <div class="dashboard-insight-card">
                                <div class="dashboard-insight-icon"><i class="${item.icon}"></i></div>
                                <div>
                                    <div class="dashboard-insight-title">${item.title}</div>
                                    <div class="dashboard-insight-value">${item.value}</div>
                                    <div class="dashboard-insight-text">${item.description}</div>
                                </div>
                            </div>
                        </div>
                    `).join("")}
                </div>
            `;

            recommendationsContainer.innerHTML = payload.recommendations.length
                ? payload.recommendations.map((item) => `
                    <div class="dashboard-rec-item ${item.priority === "high" ? "is-high" : ""}">
                        <div class="dashboard-rec-title">${item.title}</div>
                        <div class="dashboard-rec-text">${item.message}</div>
                    </div>
                `).join("")
                : `<div class="dashboard-empty-state">Пока рекомендаций нет: структура расходов выглядит стабильной.</div>`;

            forecastContainer.innerHTML = `
                <div class="forecast-panel">
                    <div class="small text-uppercase text-muted mb-1">Прогноз бюджета</div>
                    <div class="fs-4 fw-semibold mb-2">${Utils.formatMoney(payload.forecast.projected_expense_next_month)}</div>
                    <div class="small text-muted">${payload.forecast.method}</div>
                    <div class="small mt-2">Карта: <span class="fw-semibold">${payload.period.card}</span></div>
                    <div class="small">Период: <span class="fw-semibold">${payload.period.label}</span></div>
                    <div class="small">Уверенность: <span class="fw-semibold">${payload.forecast.confidence}</span></div>
                </div>
            `;
        } catch (error) {
            insightsContainer.innerHTML = `<div class="alert alert-danger">Не удалось загрузить инсайты.</div>`;
            recommendationsContainer.innerHTML = `<div class="alert alert-danger">Не удалось загрузить рекомендации.</div>`;
            forecastContainer.innerHTML = `<div class="alert alert-danger">Не удалось загрузить прогноз.</div>`;
        }
    },

    initChat() {
        const form = document.getElementById("ai-chat-form");
        const input = document.getElementById("ai-chat-input");
        const messages = document.getElementById("ai-chat-messages");
        const spinner = document.getElementById("ai-chat-spinner");
        const submitText = document.querySelector(".ai-chat-submit-text");
        if (!form || !input || !messages || !spinner || !submitText) return;

        const appendMessage = (text, role) => {
            const node = document.createElement("div");
            node.className = `ai-message ${role === "user" ? "ai-message-user" : "ai-message-assistant"}`;
            node.textContent = text;
            messages.appendChild(node);
            messages.scrollTop = messages.scrollHeight;
        };

        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const text = input.value.trim();
            if (!text) return;

            appendMessage(text, "user");
            input.value = "";
            spinner.classList.remove("d-none");
            submitText.textContent = "Отправка";

            try {
                const payload = await API.sendChatMessage(text, Utils.getDashboardParams());
                appendMessage(payload.answer, "assistant");
            } catch (error) {
                appendMessage("Не удалось получить ответ AI. Попробуйте ещё раз.", "assistant");
            } finally {
                spinner.classList.add("d-none");
                submitText.textContent = "Отправить";
            }
        });
    },

    initCategorization() {
        const button = document.getElementById("ai-categorize-btn");
        const descriptionField = document.getElementById("id_description");
        const amountField = document.getElementById("id_amount");
        const dateField = document.getElementById("id_date");
        const categoryField = document.getElementById("id_category");
        const typeField = document.getElementById("id_type");
        const statusNode = document.getElementById("ai-categorize-status");
        if (!button || !descriptionField || !categoryField || !statusNode || !typeField) return;

        button.addEventListener("click", async () => {
            if (typeField.value !== "expense") {
                statusNode.className = "alert alert-warning mt-3 mb-0";
                statusNode.textContent = "AI-категоризация доступна только для расходных транзакций.";
                return;
            }
            if (!descriptionField.value.trim()) {
                statusNode.className = "alert alert-warning mt-3 mb-0";
                statusNode.textContent = "Сначала заполните описание транзакции.";
                return;
            }

            button.disabled = true;
            statusNode.className = "alert alert-light border mt-3 mb-0";
            statusNode.textContent = "AI анализирует описание...";

            try {
                const payload = await API.categorizeExpense({
                    description: descriptionField.value,
                    amount: amountField?.value || null,
                    date: dateField?.value || null,
                });

                if (payload.applied && payload.category_id) {
                    categoryField.value = String(payload.category_id);
                    statusNode.className = "alert alert-success mt-3 mb-0";
                    statusNode.textContent = `Категория определена: ${payload.category_name} (confidence ${payload.confidence}).`;
                } else {
                    statusNode.className = "alert alert-warning mt-3 mb-0";
                    statusNode.textContent = `Уверенность ${payload.confidence} ниже порога ${payload.threshold}. Категория не применена.`;
                }
            } catch (error) {
                statusNode.className = "alert alert-danger mt-3 mb-0";
                statusNode.textContent = "Не удалось определить категорию.";
            } finally {
                button.disabled = false;
            }
        });
    },

    initTransactionCategoryFilter() {
        const typeField = document.getElementById("id_type");
        const categoryField = document.getElementById("id_category");
        if (!typeField || !categoryField) return;

        const incomeIds = JSON.parse(document.getElementById("income-category-ids")?.textContent || "[]").map(String);
        const expenseIds = JSON.parse(document.getElementById("expense-category-ids")?.textContent || "[]").map(String);
        const allOptions = Array.from(categoryField.querySelectorAll("option")).map((option) => option.cloneNode(true));

        const syncOptions = () => {
            const allowedIds = typeField.value === "income" ? incomeIds : expenseIds;
            const currentValue = categoryField.value;
            categoryField.innerHTML = "";

            allOptions.forEach((option) => {
                if (!option.value || allowedIds.includes(option.value)) {
                    categoryField.appendChild(option.cloneNode(true));
                }
            });

            if (allowedIds.includes(currentValue)) {
                categoryField.value = currentValue;
            } else if (typeField.value === "income" && incomeIds.length === 1) {
                categoryField.value = incomeIds[0];
            } else {
                categoryField.value = "";
            }
        };

        typeField.addEventListener("change", syncOptions);
        syncOptions();
    },
};

document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("monthlyChart")) {
        Charts.createMonthlyChart("monthlyChart");
    }
    if (document.getElementById("categoryChart")) {
        Charts.createCategoryChart("categoryChart");
    }

    AI.loadInsightsPanel();
    AI.initChat();
    AI.initCategorization();
    AI.initTransactionCategoryFilter();
});

window.VTBTracker = { API, Charts, AI, Utils };
