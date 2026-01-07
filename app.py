import sys
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from datetime import datetime, timedelta

#sys.path.append(os.path.join(os.path.dirname(__file__), 'script'))

from cve_fetcher import get_db_connection, fetch_cves_for_cpe, store_cves, sync_all_inventory
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI()

# === AJOUT DU MIDDLEWARE CORS (juste après app = FastAPI()) ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost",
        "http://127.0.0.1",
        "*"  # ← wildcard pour tester facilement (à restreindre en prod)
    ],
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, DELETE, etc.
    allow_headers=["*"],
)

class Equipment(BaseModel):
    name: str
    cpe: str

# === Mise à jour automatique === 

def fetch_and_store_all():
    print("Début de la synchronisation NVD...")
    try:
        sync_all_inventory() 
        print("Synchronisation terminée avec succès.")
    except Exception as e:
        print(f"Erreur lors de la synchronisation : {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_and_store_all, trigger="interval", hours=24)
scheduler.start()

@app.post("/api/refresh-cves")
async def refresh_cves(background_tasks: BackgroundTasks):
    background_tasks.add_task(fetch_and_store_all) 
    return {"message": "Mise à jour lancée en arrière-plan"}

# === TOUTES LES ROUTES API AVANT LE MONTAGE STATIQUE ===

@app.get("/api/equipments")
def get_equipments():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipments")
    equipments = cursor.fetchall()
    conn.close()
    return {"equipments": [dict(eq) for eq in equipments]}

@app.post("/api/equipments")
def add_equipment(equipment: Equipment):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO equipments (name, cpe) VALUES (?, ?)",
                       (equipment.name, equipment.cpe))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="CPE déjà existant")
    finally:
        conn.close()
    return {"message": "Ajouté"}

@app.delete("/api/equipments/{equipment_id}")
def delete_equipment(equipment_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM equipments WHERE id = ?", (equipment_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Équipement non trouvé")
    conn.commit()
    conn.close()
    return {"message": "Supprimé"}

@app.get("/api/cves/{cpe:path}")
def get_cves_for_cpe(cpe: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Étape 1 : On cherche dans notre base locale (uniquement les non-résolues)
    # On utilise cpe_related qui est le nom de la colonne dans votre nouvelle table
    cursor.execute("SELECT * FROM cves WHERE cpe_related = ? AND is_fixed = 0", (cpe,))
    cves = cursor.fetchall()
    conn.close()

    # Étape 2 : Si on n'a rien en local, on tente un fetch spécifique
    if not cves:
        try:
            # On utilise le nouveau nom de fonction : fetch_cves_for_cpe
            vulns = fetch_cves_for_cpe(cpe) 
            if vulns:
                store_cves(vulns, cpe)
                
                # On relit la base
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM cves WHERE cpe_related = ? AND is_fixed = 0", (cpe,))
                cves = cursor.fetchall()
                conn.close()
        except Exception as e:
            print(f"Erreur fetch direct pour {cpe}: {e}")

    return {"cves": [dict(cve) for cve in cves]}

# === ROUTE DASHBOARD (celle qui manquait) ===
@app.get("/api/dashboard")
def get_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Total CVE Actives
    query_total = """
        SELECT COUNT(*) 
        FROM cves 
        WHERE is_fixed = 0 
        AND cpe_related IN (SELECT cpe FROM equipments)
    """
    cursor.execute(query_total)
    total_cves = cursor.fetchone()[0]

    # 2. Répartition par sévérité
    query_severity = """
    	SELECT 
        	CASE 
            		WHEN severity IS NULL OR severity = '' OR severity = 'UNKNOWN' THEN 'NON CLASSÉ'
            		ELSE severity 
        	END as clean_severity, 
        	COUNT(*) as count 
    	FROM cves 
    	WHERE is_fixed = 0 
    	AND cpe_related IN (SELECT cpe FROM equipments)
    	GROUP BY clean_severity
    """
    cursor.execute(query_severity)
    severity_dist = {row['clean_severity']: row['count'] for row in cursor.fetchall()}

    # 3. Top 10 des CVE les plus critiques en 2025
    query_top = """
    	SELECT cve_id, cvss_score, cpe_related, severity 
    	FROM cves 
    	WHERE published LIKE '2025%' -- Garde uniquement les CVE commençant par 2025
    	AND is_fixed = 0 
    	ORDER BY cvss_score DESC, published DESC 
    	LIMIT 10
    """
    cursor.execute(query_top)
    top_10 = [dict(row) for row in cursor.fetchall()]

    # 4. Historique 7 jours (Pour ton .map() dans le JS)
    seven_days_ago = (datetime.now() - timedelta(days=30)).isoformat()

    # REQUÊTE GLOBALE : On prend tout ce qui est récent dans la base
    query_recent = """
        SELECT cve_id, published, severity, cvss_score, cpe_related
        FROM cves 
        WHERE cpe_related IN (SELECT cpe FROM equipments)
        AND published >= date('now', '-7 days')
        ORDER BY published DESC
    """
    cursor.execute(query_recent)
    recent = [dict(row) for row in cursor.fetchall()]

    # 2. Sécurité : Si aucune CVE cette semaine, on prend les 10 dernières
    if not recent:
        query_fallback = """
            SELECT cve_id, published, severity
            FROM cves 
            WHERE cpe_related IN (SELECT cpe FROM equipments)
            ORDER BY published DESC
            LIMIT 10
        """
        cursor.execute(query_fallback)
        recent = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "total_cves": total_cves,
        "severity_distribution": severity_dist,
        "top_10_critical": top_10,
        "recent_cves": recent
    }

# === MONTAGE DES FICHIERS STATIQUES (EN DERNIER !) ===
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Route test (facultative)
@app.get("/test")
def test():
    return {"status": "API fonctionne !"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)