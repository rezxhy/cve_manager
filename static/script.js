const API_URL = "http://127.0.0.1:8000/api";
document.addEventListener('DOMContentLoaded', () => {
    refreshAll();
});

function refreshAll() {
    loadEquipments();
    loadDashboard();
}

// 1. Récupérer les équipements
async function loadEquipments() {
    const res = await fetch(`${API_URL}/equipments`);
    const data = await res.json();
    const tbody = document.getElementById('equipments-body');
    tbody.innerHTML = '';
    data.equipments.forEach(eq => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
        <td>
            <strong>${eq.name}</strong>
            <br><small class="text-muted">${eq.quantity || 1} unité(s)</small>
        </td>
        <td><small>${eq.cpe}</small></td>
            <td id="count-${eq.id}">...</td>
            <td id="crit-${eq.id}">...</td>
            <td>
                <button onclick="showDetails('${eq.cpe}', '${eq.name}')">Détails</button>
                <button style="color:red" onclick="deleteEquipment(${eq.id})">Suppr.</button>
            </td>
        `;
        tbody.appendChild(tr);
        fetchCveForEquip(eq.cpe, eq.id);
    });
    document.getElementById('total-equip').innerText = data.equipments.length;
}

// 2. Récupérer les CVE spécifiques pour un CPE
async function fetchCveForEquip(cpe, id) {
    const res = await fetch(`${API_URL}/cves/${encodeURIComponent(cpe)}`);
    const data = await res.json();
    document.getElementById(`count-${id}`).innerText = data.cves.length;

    // On cherche la pire criticité
    const severities = data.cves.map(c => c.severity || 'UNKNOWN');

    const worst = severities.includes('CRITICAL') ? 'CRITICAL' : 
                  severities.includes('HIGH') ? 'HIGH' : 
                  severities.includes('MEDIUM') ? 'MEDIUM' : 'LOW';
    const critSpan = document.getElementById(`crit-${id}`);
    critSpan.innerText = worst;
    critSpan.className = `badge badge-${worst.toLowerCase()}`;
}

async function triggerRefresh() {
    const btn = document.getElementById('refresh-btn');
    const originalText = btn.innerHTML;
    
    btn.innerHTML = "⏳ Synchronisation en cours...";
    btn.disabled = true;
    btn.style.opacity = "0.7";

    try {
        const res = await fetch(`${API_URL}/refresh-cves`, { method: 'POST' });
        if (res.ok) {
            alert("Mise à jour lancée ! Les données de 2026 apparaîtront dans quelques instants.");
            // On rafraîchit le dashboard après un petit délai
            setTimeout(loadDashboard, 5000);
        }
    } catch (error) {
        alert("Erreur lors de la connexion au serveur.");
        console.error("Erreur refresh:", error);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
        btn.style.opacity = "1";
    }
}

// 3. Charger le Dashboard
async function loadDashboard() {
    try {
        const res = await fetch(`${API_URL}/dashboard`);
        const data = await res.json();
        
        document.getElementById('total-cves').innerText = data.total_cves || 0;

        // Top 10 avec vérification d'existence
        const topDiv = document.getElementById('top-critical');
	if (topDiv && data.top_10_critical) {
    		topDiv.innerHTML = data.top_10_critical.map(c => {
        		// On récupère un nom lisible à partir du CPE pour la modale
        		const displayName = c.cpe_related ? c.cpe_related.split(':')[4] : "Équipement";
        	return `
            		<div style="border-bottom:1px solid #eee; margin-bottom:8px; padding: 10px; display: flex; justify-content: space-between; align-items: center;">
                	<div>
                    		<strong style="color: #1e293b;">${c.cve_id}</strong> 
                    		<span style="color: #dc2626; font-weight: bold;">(${c.cvss_score || 'N/A'})</span>
                    		<div style="font-size: 0.75em; color: #64748b;">${displayName}</div>
                	</div>
                	<button onclick="showDetails('${c.cpe_related}', '${displayName}')" 
                        	style="padding: 4px 8px; font-size: 0.75rem; cursor: pointer; background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 4px;">
                    	Détails
                	</button>
            	</div>`;
    		}).join('');
	}

        // Historique 7 jours avec vérification d'existence
        const recentDiv = document.getElementById('recent-cves');
if (recentDiv) {
    if (data.recent_cves && data.recent_cves.length > 0) {
        recentDiv.innerHTML = data.recent_cves.map(c => {
            let dateStr = "Date inconnue";
            if (c.published) {
                dateStr = c.published.includes('T') ? c.published.split('T')[0] : c.published.substring(0, 10);
            }
            return `
                <div style="padding: 8px; border-bottom: 1px solid #f1f5f9; display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.1em;">🔔</span>
                    <div>
                        <div style="font-weight: bold; color: #1e293b; font-size: 0.85rem;">${c.cve_id}</div>
                        <div style="font-size: 0.75em; color: #64748b;">Publié : ${dateStr}</div>
                    </div>
                </div>`;
        }).join('');
    } else {
        recentDiv.innerHTML = "<p style='text-align:center; padding:20px; color:#94a3b8; font-size:0.8rem;'>Aucune alerte mondiale ces 7 derniers jours.</p>";
    }
}

	if (data.severity_distribution) {
            updateChart(data.severity_distribution);
        }

    } catch (error) {
        console.error("Erreur lors du chargement du dashboard:", error);
    }
}

// 4. Ajouter / Supprimer
async function addEquipment() {
    const name = document.getElementById('name').value;
    const cpe = document.getElementById('cpe').value;
    await fetch(`${API_URL}/equipments`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, cpe})
    });
    refreshAll();
}

async function deleteEquipment(id) {
    if(confirm("Supprimer ?")) {
        await fetch(`${API_URL}/equipments/${id}`, { method: 'DELETE' });
        refreshAll();
    }
}

// Graphique
function updateChart(dist) {
    const ctx = document.getElementById('severityChart');
    if (window.myChart) window.myChart.destroy();
    window.myChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(dist),
            datasets: [{ data: Object.values(dist), backgroundColor: ['#000','#ef4444','#f59e0b','#10b981','#64748b'] }]
        }
    });
}

function updateRecentAlerts(alerts) {
    const recentDiv = document.getElementById('recent-cves');
    if (!recentDiv) return;

    if (alerts.length === 0) {
        recentDiv.innerHTML = '<p style="text-align:center; padding:20px;">Aucune alerte cette semaine.</p>';
        return;
    }

    recentDiv.innerHTML = alerts.map(c => {
        // Détermination de la couleur du point selon la sévérité
        let dotColor = "#94a3b8"; // Défaut
        if (c.severity === 'CRITICAL' || c.severity === 'HIGH') dotColor = "#ef4444";
        else if (c.severity === 'MEDIUM') dotColor = "#f59e0b";
        else if (c.severity === 'LOW') dotColor = "#10b981";
        return `

            <div style="padding: 12px; border-bottom: 1px solid #f1f5f9; display: flex; align-items: start; gap: 12px;">
                <span style="height: 10px; width: 10px; background-color: ${dotColor}; border-radius: 50%; margin-top: 5px; flex-shrink: 0;"></span>
                <div>
                    <div style="font-weight: 700; color: #1e293b; font-size: 0.85rem;">${c.cve_id}</div>
                    <div style="font-size: 0.75rem; color: #64748b;">${c.published.substring(0, 10)}</div>
                </div>
            </div>
        `;
    }).join('');
}

function filterBySeverity() {
    const filterValue = document.getElementById('severity-filter').value;
    const rows = document.querySelectorAll('#equipment-table-body tr');

    rows.forEach(row => {
        const severity = row.getAttribute('data-max-severity'); // On va ajouter cet attribut

        if (filterValue === "ALL" || severity === filterValue) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });
}

// Modale
async function showDetails(cpe, name) {
    const modal = document.getElementById('cve-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body-area');

    if (!modal || !modalBody) {
        alert("Erreur technique : La structure de la modale est introuvable.");
        return;
    }

    modalTitle.innerText = name;
    modalBody.innerHTML = '<p style="text-align:center;">🔍 Recherche des vulnérabilités actives...</p>';
    modal.style.display = 'block';

    try {
        const baseUrl = typeof API !== 'undefined' ? API : API_URL;
        const response = await fetch(`${baseUrl}/cves/${encodeURIComponent(cpe)}`);
        const data = await response.json();

        if (!data.cves || data.cves.length === 0) {
            modalBody.innerHTML = '<div style="text-align:center; color:green; padding:20px;">✅ Aucune vulnérabilité active détectée pour cette version.</div>';
            return;
        }

        // 1. TRI : Les scores les plus élevés en premier
        const sortedCves = data.cves.sort((a, b) => (b.cvss_score || 0) - (a.cvss_score || 0));

        let html = `
            <table style="width:100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0; text-align: left;">
                        <th style="padding:10px;">Statut / ID</th>
                        <th style="padding:10px;">Score</th>
                        <th style="padding:10px;">Action</th>
                        <th style="padding:10px;">Description technique</th>
                    </tr>
                </thead>
                <tbody>`;

        sortedCves.forEach(c => {
    const score = parseFloat(c.cvss_score) || 0;
    
    // 1. LOGIQUE DES COULEURS
    let bgColor = "#94a3b8"; // Gris Ardoise par défaut
    let scoreText = "Non classé";
    let statusLabel = "PUBLIÉE / EN ANALYSE";
    let statusColor = "#475569"; // Gris texte
    let statusBg = "#f1f5f9";   // Gris fond

    if (score >= 9.0) {
        bgColor = "#7f1d1d"; scoreText = score.toFixed(1);
        statusLabel = "CRITIQUE"; statusColor = "#991b1b"; statusBg = "#fee2e2";
    } else if (score >= 7.0) {
        bgColor = "#dc2626"; scoreText = score.toFixed(1);
        statusLabel = "ÉLEVÉE"; statusColor = "#991b1b"; statusBg = "#fee2e2";
    } else if (score >= 4.0) {
        bgColor = "#f59e0b"; scoreText = score.toFixed(1);
        statusLabel = "MOYENNE"; statusColor = "#92400e"; statusBg = "#fef3c7";
    } else if (score > 0) {
        bgColor = "#10b981"; scoreText = score.toFixed(1);
        statusLabel = "FAIBLE"; statusColor = "#065f46"; statusBg = "#d1fae5";
    }

    // 2. GÉNÉRATION DE LA LIGNE
    html += `
        <tr style="border-bottom: 1px solid #eee; background-color: ${score === 0 ? '#fafafa' : 'transparent'};">
            <td style="padding:12px; vertical-align: top; white-space: nowrap;">
                <div style="color: #1e293b; font-weight: bold; margin-bottom: 4px;">🆔 ${c.cve_id}</div>
                <span style="font-size:0.65em; background:${statusBg}; color:${statusColor}; padding:2px 6px; border-radius:4px; font-weight:800; border: 1px solid ${statusColor}44;">
                    ${statusLabel}
                </span>
            </td>
            <td style="padding:12px; vertical-align: top;">
                <div title="${score === 0 ? 'Le NIST n\'a pas encore évalué cette faille' : 'Score CVSS v3.1'}" 
                     style="
                        background-color: ${bgColor} !important; 
                        color: white !important; 
                        padding: 4px 10px; 
                        border-radius: 4px; 
                        font-weight: bold; 
                        display: inline-block; 
                        min-width: 85px; 
                        text-align: center;
                        font-size: 0.75rem;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                ">
                    ${scoreText}
                </div>
            </td>
            <td style="padding:12px; vertical-align: top;">
                <button onclick="markAsFixed('${c.cve_id}', '${cpe}', '${name}')" 
                        style="cursor:pointer; font-size:0.75rem; padding:5px 10px; border-radius:4px; border:1px solid #cbd5e1; background:#fff; font-weight:500; transition: 0.2s;"
                        onmouseover="this.style.background='#f8fafc'"
                        onmouseout="this.style.background='#fff'">
                    Résoudre
                </button>
            </td>
            <td style="padding:12px; font-size:0.85rem; line-height:1.5; color: #334155;">
                ${c.description || "<i style='color:#94a3b8'>Aucune description disponible.</i>"}
            </td>
        </tr>`;
});

html += '</tbody></table>';
modalBody.innerHTML = html;
} catch (error) { // Ferme le try et commence le catch
        console.error("Erreur détails:", error);
        modalBody.innerHTML = '<p style="color:red; text-align:center;">⚠️ Erreur lors du chargement des données.</p>';
    }
}

function closeModal() { document.getElementById('cve-modal').style.display = 'none'; }