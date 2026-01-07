import requests
import sqlite3
from datetime import datetime, timedelta
import os
import time

API_KEY = os.getenv("NVD_API_KEY")

def get_db_connection():

    #base_dir = os.path.dirname(os.path.dirname(__file__))
    #db_path = os.path.join(base_dir, 'cve.db')

    conn = sqlite3.connect('cve.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Table Equipements
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            version TEXT,
            quantity INTEGER DEFAULT 1,
            cpe TEXT UNIQUE,
            category TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Table CVEs (Mise à jour avec la colonne is_fixed pour ton dashboard)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cves (
            cve_id TEXT PRIMARY KEY,
            description TEXT,
            published TEXT,
            last_modified TEXT,
            cvss_score REAL,
            severity TEXT,
            cpe_related TEXT,
            is_fixed BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def fetch_cves_for_cpe(cpe):
    """Récupère les CVE spécifiquement pour un CPE donné."""
    url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    
    # Pour une recherche par CPE, on simplifie les paramètres pour éviter l'erreur 404
    params = {
        "cpeName": cpe,
        "resultsPerPage": 50
    }

    headers = {}
    if API_KEY:
        headers["apiKey"] = API_KEY
    
    try:
        # Respect du Rate Limit : Pause de 6 secondes si pas de clé API
        if not API_KEY:
            time.sleep(6) 
            
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 404:
            print(f"⚠️ Aucune CVE trouvée ou erreur de format pour : {cpe}")
            return []
            
        response.raise_for_status()
        data = response.json()
        return data.get("vulnerabilities", [])

    except Exception as e:
        print(f"❌ Erreur lors de la récupération pour {cpe}: {e}")
        return []

def store_cves(vulnerabilities, source_cpe):
    if not vulnerabilities:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    for vuln in vulnerabilities:
        cve_data = vuln.get("cve", {})
        cve_id = cve_data.get("id")
        
        description = next(
            (d.get("value", "") for d in cve_data.get("descriptions", []) if d.get("lang") == "en"),
            "Pas de description."
        )

        metrics = cve_data.get("metrics", {})
        cvss_score = None
        severity = "UNKNOWN"
        
        # Extraction du score V3.1
        if "cvssMetricV31" in metrics:
            m = metrics["cvssMetricV31"][0].get("cvssData", {})
            cvss_score = m.get("baseScore")
            severity = m.get("baseSeverity")
        elif "cvssMetricV2" in metrics:
            m = metrics["cvssMetricV2"][0].get("cvssData", {})
            cvss_score = m.get("baseScore")
            severity = m.get("baseSeverity")

        cursor.execute('''
            INSERT OR IGNORE INTO cves 
            (cve_id, description, published, last_modified, cvss_score, severity, cpe_related)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (cve_id, description, cve_data.get("published"), cve_data.get("lastModified"), 
              cvss_score, severity, source_cpe))

    conn.commit()
    conn.close()

def sync_all_inventory():
    """Parcourt l'inventaire et met à jour les CVE pour chaque équipement."""
    conn = get_db_connection()
    equipments = conn.execute("SELECT name, cpe FROM equipments").fetchall()
    conn.close()

    print(f"🚀 Début de la synchronisation pour {len(equipments)} équipements...")
    
    for eq in equipments:
        print(f"🔍 Analyse de {eq['name']}...")
        vulns = fetch_cves_for_cpe(eq['cpe'])
        if vulns:
            store_cves(vulns, eq['cpe'])
            print(f" ✅ {len(vulns)} CVE ajoutées/vérifiées.")
        else:
            print(f" ℹ️ Aucune nouvelle vulnérabilité.")

if __name__ == "__main__":
    init_db()
    sync_all_inventory()
    print("✨ Synchronisation terminée !")