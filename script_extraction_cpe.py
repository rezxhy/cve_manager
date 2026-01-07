import sqlite3
import os

#base_dir = os.path.dirname(os.path.dirname(__file__))
#db_path = os.path.join(base_dir, 'cve.db')

def extract_all_cpes():
    conn = sqlite3.connect('cve.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, cpe FROM equipments")
    equipments = cursor.fetchall()
    
    print(f"{'NOM':<20} | {'CPE VALIDE ?':<10} | {'CPE STRING'}")
    print("-" * 70)
    
    cpe_list = []
    for eq in equipments:
        name = eq['name']
        cpe = eq['cpe']
        cpe_list.append(cpe)
        
        # Vérification rapide du format
        is_valid = "OUI" if cpe.startswith("cpe:2.3:") else "NON"
        print(f"{name:<20} | {is_valid:<10} | {cpe}")
    
    conn.close()
    return cpe_list

if __name__ == "__main__":
    all_cpes = extract_all_cpes()
    # Optionnel : Sauvegarder dans un fichier texte pour vérification
    with open("cpe_check.txt", "w") as f:
        for c in all_cpes:
            f.write(c + "\n")