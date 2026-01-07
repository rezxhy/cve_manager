import sqlite3
import json
import os

#base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#inventory_path = os.path.join(base_dir, 'data', 'inventory.json')

def import_from_json(json_file):
    # 1. Connexion DB
    conn = sqlite3.connect('cve.db')
    cursor = conn.cursor()

    # 2. Création de la table (si besoin)
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

    # 3. Lecture du fichier JSON
    if not os.path.exists(json_file):
        print(f"Erreur : Le fichier {json_file} est introuvable.")
        return

    with open(json_file, 'r', encoding='utf-8') as f:
        inventory = json.load(f)

    # 4. Insertion des données
    for item in inventory:
        cursor.execute('''
            INSERT OR IGNORE INTO equipments 
            (name, version, quantity, cpe, category)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            item["name"],
            item["version"],
            item.get("quantity", 1), # Utilise 1 si quantity manque
            item["cpe"],
            item["category"]
        ))

    conn.commit()
    conn.close()
    print(f"✅ Importation réussie : {len(inventory)} équipements traités.")

if __name__ == "__main__":
    import_from_json('inventory.json')