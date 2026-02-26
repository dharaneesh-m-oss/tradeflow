let currentData = null;

function checkSession() {
    const path = window.location.pathname;
    const profile = localStorage.getItem('tradeflow_profile');

    // Allow public pages
    if (path === '/' || path === '/login' || path.includes('about.html') || path === '/about') return;

    if (!profile) {
        window.location.href = '/login';
    }
}

function loadProfile() {
    const profileStr = localStorage.getItem('tradeflow_profile');
    if (profileStr) {
        const profile = JSON.parse(profileStr);
        const el = document.getElementById("userProfileInfo");
        if (el) {
            el.innerHTML = `
                <div class="user-badge">
                    <span class="company-tag">${profile.name}</span>
                    <span class="iec-tag">IEC: ${profile.iec}</span>
                    <a class="logout-link" onclick="logout()" data-i18n="logout_link">Logout</a>
                </div>
            `;
        }
    }
}

function logout() {
    localStorage.removeItem('tradeflow_profile');
    window.location.href = '/login';
}

function toggleChat() {
    const chat = document.getElementById("chatWidget");
    chat.classList.toggle("active");
}

let chatHistory = [];

async function sendMessage() {
    const input = document.getElementById("chatInput");
    const container = document.getElementById("chatMessages");
    const message = input.value.trim();

    if (!message) return;

    // Add user message to UI
    const userDiv = document.createElement("div");
    userDiv.className = "message message-user";
    userDiv.innerText = message;
    container.appendChild(userDiv);

    input.value = "";
    container.scrollTop = container.scrollHeight;

    // Add loading indicator
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "message message-ai";
    loadingDiv.innerText = "...";
    container.appendChild(loadingDiv);
    container.scrollTop = container.scrollHeight;

    try {
        const response = await fetch("/chat/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: message,
                context: currentData,
                history: chatHistory
            })
        });

        const result = await response.json();
        container.removeChild(loadingDiv);

        if (!response.ok) throw new Error(result.detail || "Chat failed");

        // Add user message and AI response to history
        chatHistory.push({ "role": "user", "content": message });
        chatHistory.push({ "role": "assistant", "content": result.response });

        // Keep history manageable (last 10 interactions)
        if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);

        const aiDiv = document.createElement("div");
        aiDiv.className = "message message-ai";
        aiDiv.innerText = result.response;
        container.appendChild(aiDiv);
        container.scrollTop = container.scrollHeight;

    } catch (err) {
        if (loadingDiv.parentNode) container.removeChild(loadingDiv);
        const errorDiv = document.createElement("div");
        errorDiv.className = "message message-ai";
        errorDiv.innerText = "Error: " + err.message;
        container.appendChild(errorDiv);
    }
}

async function handleUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    const spinner = document.getElementById("loadingSpinner");
    const statusText = document.getElementById("statusText");

    if (spinner) spinner.classList.remove("hidden");
    if (statusText) statusText.innerText = "Extracting intelligence...";

    try {
        const response = await fetch("/upload/", {
            method: "POST",
            body: formData
        });
        const result = await response.json();

        if (!response.ok) throw new Error(result.detail || "Upload failed");

        currentData = result.data;
        displayResults(result);

        if (spinner) spinner.classList.add("hidden");
        if (statusText) statusText.innerText = "Processing Complete!";

    } catch (err) {
        alert("Error: " + err.message);
        if (spinner) spinner.classList.add("hidden");
        if (statusText) statusText.innerText = "Extraction Failed";
    }
}

function displayResults(result) {
    const dashboard = document.getElementById("mainDashboard");
    if (dashboard) dashboard.classList.remove("hidden");

    // Smooth scroll to results
    dashboard.scrollIntoView({ behavior: 'smooth' });

    const data = result.data;

    // Update individual fields
    const fields = {
        "hsCode": data.hs_code,
        "importerCodeExtracted": data.importer_code,
        "invoiceValue": `${data.invoice_value || ''} ${data.currency || ''}`,
        "date": data.date,
        "importer": data.importer_name,
        "consignee": data.consignee_name,
        "exporter": data.exporter_name,
        "vessel": data.vessel_name,
        "containerNo": data.container_number,
        "loadingPort": data.port_of_loading,
        "port": data.arrival_port,
        "netWeight": data.net_weight,
        "grossWeight": data.gross_weight,
        "origin": data.country_of_origin,
        "goodsDescription": data.goods_description
    };

    for (const [id, val] of Object.entries(fields)) {
        const el = document.getElementById(id);
        if (el) el.innerText = val || 'Not found';
    }

    const confidenceEl = document.getElementById("overallConfidence");
    if (confidenceEl) {
        const score = data.confidence_score || 85;
        confidenceEl.innerText = `Confidence: ${score}%`;
    }

    const complianceGrid = document.getElementById("complianceGrid");
    if (complianceGrid) {
        complianceGrid.innerHTML = "";
        for (const [country, status] of Object.entries(result.compliance)) {
            const card = document.createElement("div");
            card.className = "card compliance-card"; // Match app.html style
            const statusClass = `status-${status.status.toLowerCase()}`;

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <h4 style="margin: 0;">${country.toUpperCase()}</h4>
                    <div class="compliance-badge ${statusClass}">${status.status}</div>
                </div>
                <div class="risk-score" style="margin-top: 15px; color: var(--text-muted); font-size: 14px;">
                    Risk Score: <strong>${status.risk_score}/100</strong>
                </div>
            `;
            complianceGrid.appendChild(card);
        }
    }
}

async function loadRulesUpdates() {
    const container = document.getElementById("updatesTimeline");
    if (!container) return;

    try {
        const response = await fetch("/api/rules-updates/");
        const updates = await response.json();

        if (!response.ok) throw new Error("Failed to fetch updates");

        container.innerHTML = "";

        if (updates.length === 0) {
            container.innerHTML = '<div style="text-align: center; color: var(--text-muted);">No recent updates found.</div>';
            return;
        }

        updates.forEach(update => {
            const item = document.createElement("div");
            item.className = "timeline-item";
            const impactClass = `impact-${update.impact.toLowerCase()}`;

            item.innerHTML = `
                <div class="timeline-header">
                    <span class="timeline-date">${update.date}</span>
                    <span class="impact-badge ${impactClass}">${update.impact} Impact</span>
                </div>
                <div class="timeline-content">
                    <h3>${update.title}</h3>
                    <p>${update.description}</p>
                    <span class="timeline-country">${update.country} Customs</span>
                </div>
            `;
            container.appendChild(item);
        });
    } catch (err) {
        container.innerHTML = `<div style="text-align: center; color: var(--danger);">Error loading updates: ${err.message}</div>`;
    }
}

// ===============================
// MANUAL ENTRY
// ===============================

async function submitManualEntry(event) {
    event.preventDefault();

    const data = {
        hs_code: document.getElementById("hsCode").value,
        goods_description: document.getElementById("goodsDescription").value,
        invoice_value: document.getElementById("invoiceValue").value,
        currency: document.getElementById("currency").value,
        date: document.getElementById("dateInput").value,
        importer_name: document.getElementById("importerName").value,
        exporter_name: document.getElementById("exporterName").value,
        importer_code: document.getElementById("importerCode").value,
        consignee_name: document.getElementById("importerName").value,
        consignee_location: document.getElementById("consigneeLocation").value,
        vessel_name: document.getElementById("vesselName").value,
        port_of_loading: document.getElementById("loadingPort").value,
        arrival_port: document.getElementById("arrivalPortInput").value,
        country_of_origin: document.getElementById("originCountry").value,
        target_country: document.getElementById("targetCountry").value,
        container_number: document.getElementById("containerNo").value,
        net_weight: document.getElementById("netWeight").value + " KG",
        gross_weight: document.getElementById("grossWeight").value + " KG"
    };

    const resultContainer = document.getElementById("manualResult");
    resultContainer.innerHTML = '<div class="spinner"></div> Analysing compliance and generating official documents...';
    resultContainer.classList.remove("hidden");

    try {
        // 1. Check Compliance
        const compResponse = await fetch("/api/manual-entry/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });

        const compResult = await compResponse.json();
        if (!compResponse.ok) throw new Error(compResult.detail || "Compliance check failed");

        const targetCountry = data.target_country;
        const compliance = compResult.compliance[targetCountry] || { status: "UNKNOWN", risk_score: 50, factors: [] };

        // 2. Generate Documents
        const genResponse = await fetch(`/generate/999`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                country: targetCountry,
                data: data
            })
        });

        const genResult = await genResponse.json();
        if (!genResponse.ok) throw new Error(genResult.detail || "Generation failed");

        const statusClass = `status-${compliance.status.toLowerCase()}`;

        let factorsHtml = "";
        if (compliance.factors && compliance.factors.length > 0) {
            factorsHtml = `
                <div style="margin-top: 20px; padding: 15px; background: rgba(239, 68, 68, 0.1); border-radius: 12px; border: 1px solid rgba(239, 68, 68, 0.2);">
                    <h4 style="color: var(--danger); margin-bottom: 5px;">Customs Risk Factors:</h4>
                    <ul style="margin-left: 20px; color: var(--text-muted); font-size: 14px;">
                        ${compliance.factors.map(f => `<li>${f}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        resultContainer.innerHTML = `
            <div class="glass-form" style="padding: 40px; border-top: 4px solid var(--primary);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 40px;">
                    <div>
                        <h3 style="font-size: 24px;">Generation Complete</h3>
                        <p style="color: var(--text-muted);">Declarations successfully generated for ${targetCountry.toUpperCase()}</p>
                    </div>
                    <div class="compliance-badge ${statusClass}" style="font-size: 16px;">${compliance.status} Entry</div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 40px;">
                    <a href="${genResult.pdf_url}" target="_blank" class="download-card" style="text-decoration: none; color: inherit;">
                        <div style="font-size: 24px; margin-bottom: 10px;">📄</div>
                        <div style="font-weight: 600;">Download PDF</div>
                        <div style="font-size: 12px; color: var(--text-muted); margin-top: 5px;">Official Declaration</div>
                    </a>
                    <a href="${genResult.docx_url}" target="_blank" class="download-card" style="text-decoration: none; color: inherit;">
                        <div style="font-size: 24px; margin-bottom: 10px;">📝</div>
                        <div style="font-weight: 600;">Download DOCX</div>
                        <div style="font-size: 12px; color: var(--text-muted); margin-top: 5px;">Editable Document</div>
                    </a>
                </div>

                <div style="padding: 25px; background: rgba(255,255,255,0.03); border-radius: 16px; border: 1px solid rgba(255,255,255,0.05);">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span style="font-size: 14px; color: var(--text-muted);">Compliance Confidence Score</span>
                        <span style="font-weight: 800; color: ${compliance.risk_score > 40 ? 'var(--danger)' : 'var(--accent)'}">${100 - compliance.risk_score}%</span>
                    </div>
                    <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;">
                        <div style="width: ${100 - compliance.risk_score}%; height: 100%; background: ${compliance.risk_score > 40 ? 'var(--danger)' : 'var(--primary)'}; border-radius: 3px;"></div>
                    </div>
                    ${factorsHtml}
                </div>
            </div>
        `;
        resultContainer.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        resultContainer.innerHTML = `<div class="glass-form" style="color: var(--danger); padding: 30px; text-align: center;">⚠️ Error: ${err.message}</div>`;
    }
}

// ===============================
// MULTI-LANGUAGE (i18n)
// ===============================

let translations = {};

async function initTranslations() {
    try {
        const response = await fetch("/static/translations.json");
        translations = await response.json();
        const savedLang = localStorage.getItem("preferredLang") || "en";
        switchLanguage(savedLang);
    } catch (err) {
        console.error("Failed to load translations:", err);
    }
}

async function generateDocuments() {
    const country = document.getElementById("countrySelect").value;
    if (!country) {
        alert("Please select a target authority/country first.");
        return;
    }

    const requestData = {
        country: country,
        importer_code: document.getElementById("importerCode").value,
        arrival_port: document.getElementById("arrivalPortInput").value,
        country_of_origin: document.getElementById("originInput").value,
        data: currentData
    };

    const btn = document.querySelector("button[onclick='generateDocuments()']");
    const originalText = btn.innerText;
    btn.innerText = "Syncing & Generating...";
    btn.disabled = true;

    try {
        const docId = 1; // Default for now
        const response = await fetch(`/generate/${docId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Generation failed");

        const downloadSection = document.getElementById("downloadSection");
        const docxLink = document.getElementById("docxLink");
        const pdfLink = document.getElementById("pdfLink");

        if (downloadSection) downloadSection.classList.remove("hidden");
        if (docxLink) docxLink.href = result.docx_url;
        if (pdfLink) pdfLink.href = result.pdf_url;

        btn.innerText = "Documents Ready!";
        setTimeout(() => {
            btn.innerText = originalText;
            btn.disabled = false;
        }, 3000);

    } catch (err) {
        alert("Error: " + err.message);
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

function switchLanguage(lang) {
    if (!translations[lang]) return;
    localStorage.setItem("preferredLang", lang);
    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        if (translations[lang][key]) {
            el.innerText = translations[lang][key];
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    checkSession();
    initTranslations();
    loadRulesUpdates();
    loadProfile();
});
