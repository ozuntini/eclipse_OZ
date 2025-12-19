#!/usr/bin/env python3
"""
Script de test comparatif entre les implementations Lua et Python.
Exécute les deux versions avec le même fichier de configuration et compare les résultats.
"""

import os
import sys
import subprocess
from pathlib import Path

# Ajouter le répertoire python au path
current_dir = Path(__file__).parent
python_dir = current_dir.parent
sys.path.insert(0, str(python_dir))
sys.path.insert(0, str(current_dir))

from lua_simulator import run_lua_simulation
from tests.test_lua_python_comparison_new import run_comparative_test, print_comparison_results


def test_with_original_config():
    """Test avec le fichier SOLARECL.TXT original"""
    
    config_file = current_dir.parent.parent / "SOLARECL.TXT"
    
    if not config_file.exists():
        print(f"❌ Fichier SOLARECL.TXT non trouvé: {config_file}")
        return False
    
    print("🔍 Test avec le fichier de configuration original SOLARECL.TXT")
    print("=" * 70)
    
    # Exécution du test comparatif
    results = run_comparative_test(str(config_file))
    status = print_comparison_results(results)
    
    return status in ["EXCELLENT", "BON"]


def test_with_sample_config():
    """Test avec une configuration d'exemple"""
    
    sample_config = """# Configuration test comparatif Lua vs Python
# Test avec éclipse du 8 avril 2024
#
# Vérification configuration caméra
Verif,3,0,50,2000
#
# Configuration des temps d'éclipse (C1, C2, Max, C3, C4, TestMode)
Config,18,10,29,19,27,3,19,28,23,19,29,43,20,46,31,1
#
# Actions de test
Photo,C1,-,0,5,0,-,-,-,8,100,4,0
Boucle,C2,-,0,1,0,+,0,0,30,10,8,200,0.002,0
Photo,Max,-,-,-,-,-,-,-,5.6,800,1,1000
Interval,C3,+,0,0,30,+,0,1,0,5,8,400,0.001,500
Photo,C4,+,0,2,0,-,-,-,8,100,2,0
"""
    
    # Créer fichier temporaire
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(sample_config)
        temp_config = f.name
    
    try:
        print("\n🔍 Test avec configuration d'exemple")
        print("=" * 50)
        
        results = run_comparative_test(temp_config)
        status = print_comparison_results(results)
        
        return status in ["EXCELLENT", "BON"]
        
    finally:
        os.unlink(temp_config)


def run_individual_tests():
    """Lance les tests individuels avec pytest"""
    
    print("\n🧪 Exécution des tests unitaires")
    print("=" * 40)
    
    test_file = current_dir / "test_lua_python_comparison_new.py"
    
    try:
        # Lancer pytest sur le fichier de tests
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            str(test_file), 
            "-v", 
            "--tb=short"
        ], capture_output=True, text=True, cwd=str(python_dir))
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution des tests: {e}")
        return False


def demo_lua_simulation():
    """Démonstration du simulateur Lua"""
    
    print("\n🎭 Démonstration du simulateur Lua")
    print("=" * 45)
    
    # Configuration simple pour démonstration
    demo_config = """# Configuration démo
Config,20,20,0,20,25,0,20,26,0,20,27,0,20,30,0,1
Verif,3,0,80,5000
Photo,C1,-,0,1,0,-,-,-,8,200,1,0
Photo,Max,-,-,-,-,-,-,-,5.6,800,2,1000
"""
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(demo_config)
        demo_file = f.name
    
    try:
        print("📋 Configuration démo:")
        print(demo_config)
        
        # Simulation Lua
        results = run_lua_simulation(demo_file, start_time_hms=(20, 15, 0))
        
        print("📊 Résultats de la simulation Lua:")
        print(f"   • Erreur: {results.get('error', 'Aucune')}")
        print(f"   • Actions exécutées: {len(results.get('actions_executed', []))}")
        print(f"   • Logs générés: {len(results.get('logs', []))}")
        
        if results.get('config'):
            print("   • Configuration éclipse:")
            for key, value in results['config'].items():
                if key != 'TestMode':
                    hours = value // 3600
                    minutes = (value % 3600) // 60
                    seconds = value % 60
                    print(f"     - {key}: {hours:02d}:{minutes:02d}:{seconds:02d}")
                else:
                    print(f"     - {key}: {value}")
        
        if results.get('actions_executed'):
            print("   • Actions:")
            for i, action in enumerate(results['actions_executed']):
                print(f"     - {i+1}. {action['action']} - ISO:{action['iso']} Aperture:{action['aperture']}")
        
        print("\n📝 Logs Lua (dernières 5 lignes):")
        for log in results.get('logs', [])[-5:]:
            print(f"   {log}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la démonstration: {e}")
        return False
        
    finally:
        os.unlink(demo_file)


def main():
    """Point d'entrée principal"""
    
    print("🚀 Tests comparatifs implémentations Lua vs Python")
    print("=" * 60)
    print("Objectif: Vérifier que Python produit les mêmes résultats que Lua")
    print()
    
    all_passed = True
    
    # 1. Démonstration du simulateur
    print("1️⃣ Démonstration du simulateur Lua")
    demo_ok = demo_lua_simulation()
    if not demo_ok:
        all_passed = False
        print("❌ Démonstration échouée")
    else:
        print("✅ Démonstration réussie")
    
    # 2. Test avec configuration originale
    print("\n2️⃣ Test avec SOLARECL.TXT original")
    original_ok = test_with_original_config()
    if not original_ok:
        all_passed = False
        print("❌ Test original échoué")
    else:
        print("✅ Test original réussi")
    
    # 3. Test avec configuration d'exemple
    print("\n3️⃣ Test avec configuration d'exemple")
    sample_ok = test_with_sample_config()
    if not sample_ok:
        all_passed = False
        print("❌ Test exemple échoué")
    else:
        print("✅ Test exemple réussi")
    
    # 4. Tests unitaires
    print("\n4️⃣ Tests unitaires pytest")
    unit_tests_ok = run_individual_tests()
    if not unit_tests_ok:
        all_passed = False
        print("❌ Tests unitaires échoués")
    else:
        print("✅ Tests unitaires réussis")
    
    # Résultat final
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 TOUS LES TESTS SONT PASSÉS!")
        print("✅ Les implémentations Lua et Python sont compatibles")
        return 0
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("⚠️  Révision nécessaire pour assurer la compatibilité")
        return 1


if __name__ == "__main__":
    sys.exit(main())