CVE Manager Dashboard 🛡️

Système de veille et de gestion des vulnérabilités (CVE) pour équipements réseau.

Installation : 
1. Cloner le projet.
2. Créer un environnement virtuel : 'python3 -m venv venv'.
3. Activer l'environnement : 'source venv/bin/activate' (Linux) ou 'venv\Scripts\activate' (Win).
4. Installer les dépendances : 'pip install fastapi uvicorn requests'.
5. Configuration des API (Crucial)
Le projet utilise deux couches d'API :
- API Externe (NVD NIST) : Utilisée par cve_fetcher.py pour récupérer les vulnérabilités mondiales.
	Il est fortement recommandé d'utiliser une clé API personnelle.
	Exportation de la clé (Linux/WSL) : export NVD_API_KEY="votre_cle_ici".
- Votre API Locale (FastAPI) : Créée par app.py, elle sert d'intermédiaire entre la base cve.db et 
le dashboard web.

Utilisation :
1. Importation : Lancer 'python3 import_inventory.py' pour charger vos équipements.
2. Collecte : Lancer 'python3 cve_fetcher.py' pour récupérer les dernières CVE du NIST.
3. Lancement : Exécuter 'uvicorn app:app --reload' ou lancer 'python3 app.py' pour lancer le dashboard.

Architecture : 
- Backend : FastAPI (Python)
- Frontend : HTML5 / CSS3 / Vanilla JS
- Base de données : SQLite (cve.db)

