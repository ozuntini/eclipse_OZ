#!/usr/bin/env python3
"""
Tests comparatifs entre l'implémentation Lua originale et la nouvelle implémentation Python.
Exécute les deux versions avec les mêmes paramètres et compare les résultats.
"""

import pytest
import os
import sys
import tempfile

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des modules Python
from config.parser import ConfigParser  # noqa: E402
from scheduling.time_calculator import TimeCalculator  # noqa: E402

# Import du simulateur Lua
from lua_simulator import run_lua_simulation, LuaSimulator  # noqa: E402



class TestLuaPythonComparison:
    """Tests de comparaison directe entre les implémentations Lua et Python"""
    
    @pytest.fixture
    def sample_config_file(self):
        """Crée un fichier de configuration temporaire pour les tests"""
        config_content = """# SOLARECL.TXT Test Configuration
# Version 2.2.1
#
# Verif,Mode,AF,Bat,SD
Verif,3,0,20,4000
#      C1       C2       Max      C3       C4       TestMode
Config,20,20,30,20,25,5,20,26,15,20,27,55,20,30,3,1
#
# Test actions
Photo,C1,-,0,2,0,-,-,-,8,800,0.0005,500
Boucle,C2,-,0,1,0,+,0,0,30,5,8,200,0.002,0
Interval,Max,-,0,0,30,+,0,0,30,10,4,1600,1,500
Photo,C4,+,0,1,0,-,-,-,8,400,0.001,0
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(config_content)
            return f.name
    
    def test_configuration_parsing_compatibility(self, sample_config_file):
        """Test que le parsing de configuration est identique"""
        
        # Exécution Lua
        lua_results = run_lua_simulation(sample_config_file, start_time_hms=(20, 15, 0))
        
        # Exécution Python
        config_parser = ConfigParser()
        config = config_parser.parse_eclipse_config(sample_config_file)
        
        # Comparaison des timings d'éclipse
        assert lua_results["config"]["C1"] == config.eclipse_timings.c1_seconds
        assert lua_results["config"]["C2"] == config.eclipse_timings.c2_seconds
        assert lua_results["config"]["Max"] == config.eclipse_timings.max_seconds
        assert lua_results["config"]["C3"] == config.eclipse_timings.c3_seconds
        assert lua_results["config"]["C4"] == config.eclipse_timings.c4_seconds
        
        # Test mode de test
        lua_test_mode = bool(lua_results["config"]["TestMode"])
        assert lua_test_mode == config.test_mode
        
        # Comparaison du nombre d'actions
        assert len(lua_results["actions_executed"]) == len(config.actions)
    
    def test_time_calculation_compatibility(self, sample_config_file):
        """Test que les calculs de temps sont identiques"""
        
        # Simulation Lua
        lua_results = run_lua_simulation(sample_config_file, start_time_hms=(20, 15, 0))
        
        # Configuration Python
        config_parser = ConfigParser()
        config = config_parser.parse_eclipse_config(sample_config_file)
        time_calc = TimeCalculator()
        
        # Comparaison des temps calculés pour chaque action
        for i, lua_action in enumerate(lua_results["actions_executed"]):
            if i < len(config.actions):
                py_action = config.actions[i]
                
                # Test temps de départ
                if lua_action["time_start"]:
                    if py_action.reference_point and py_action.reference_point != "-":
                        py_time_start = time_calc.convert_relative_time(
                            py_action.reference_point,
                            py_action.start_operation,
                            py_action.start_time_seconds,
                            config.eclipse_timings
                        )
                        
                        assert abs(py_time_start - lua_action["time_start"]) <= 1, \
                            f"Temps de départ différent pour action {i}: Lua={lua_action['time_start']}, Python={py_time_start}"
                
                # Test temps de fin pour les boucles
                if lua_action.get("time_end") and py_action.action_type in ["Boucle", "Interval"]:
                    py_time_end = time_calc.convert_relative_time(
                        py_action.reference_point,
                        py_action.end_operation,
                        py_action.end_time_seconds,
                        config.eclipse_timings
                    )
                    
                    assert abs(py_time_end - lua_action["time_end"]) <= 1, \
                        f"Temps de fin différent pour action {i}: Lua={lua_action['time_end']}, Python={py_time_end}"
    
    def test_camera_parameters_compatibility(self, sample_config_file):
        """Test que les paramètres caméra sont identiques"""
        
        # Simulation Lua
        lua_results = run_lua_simulation(sample_config_file)
        
        # Configuration Python
        config_parser = ConfigParser()
        config = config_parser.parse_eclipse_config(sample_config_file)
        
        # Comparaison des paramètres caméra pour chaque action
        for i, lua_action in enumerate(lua_results["actions_executed"]):
            if i < len(config.actions):
                py_action = config.actions[i]
                
                assert lua_action["aperture"] == py_action.aperture, \
                    f"Ouverture différente pour action {i}: Lua={lua_action['aperture']}, Python={py_action.aperture}"
                
                assert lua_action["iso"] == py_action.iso, \
                    f"ISO différent pour action {i}: Lua={lua_action['iso']}, Python={py_action.iso}"
                
                assert abs(lua_action["shutter_speed"] - py_action.shutter_speed) < 0.0001, \
                    f"Vitesse différente pour action {i}: Lua={lua_action['shutter_speed']}, Python={py_action.shutter_speed}"
                
                assert lua_action["mlu_delay"] == py_action.mirror_lockup_delay, \
                    f"MLU delay différent pour action {i}: Lua={lua_action['mlu_delay']}, Python={py_action.mirror_lockup_delay}"
    
    def test_interval_calculation_compatibility(self, sample_config_file):
        """Test que les calculs d'intervalles sont identiques"""
        
        # Simulation Lua
        lua_results = run_lua_simulation(sample_config_file)
        
        # Configuration Python
        config_parser = ConfigParser()
        config = config_parser.parse_eclipse_config(sample_config_file)
        
        for lua_action in lua_results["actions_executed"]:
            if lua_action["action"] == "Interval":
                # Trouve l'action Interval correspondante dans Python
                for py_action in config.actions:
                    if py_action.action_type == "Interval":
                        # Le calcul Lua: interval = (timeEnd - timeStart) / count
                        lua_interval = lua_action["interval"]
                        
                        # Le calcul Python équivalent
                        duration = py_action.end_time_seconds - py_action.start_time_seconds
                        py_interval = duration / py_action.interval_or_count
                        
                        assert abs(lua_interval - py_interval) < 0.1, \
                            f"Calcul d'intervalle différent: Lua={lua_interval}, Python={py_interval}"
                        break
    
    def test_pretty_time_formatting(self):
        """Test que le formatage de temps est identique"""
        
        simulator = LuaSimulator("dummy.txt")
        time_calc = TimeCalculator()
        
        test_times = [
            0,      # 00:00:00
            3661,   # 01:01:01
            43200,  # 12:00:00
            73575,  # 20:26:15
            86399   # 23:59:59
        ]
        
        for time_seconds in test_times:
            lua_formatted = simulator.pretty_time(time_seconds)
            python_formatted = time_calc.format_time(time_seconds)
            
            assert lua_formatted == python_formatted, \
                f"Formatage temps différent pour {time_seconds}s: Lua='{lua_formatted}', Python='{python_formatted}'"
    
    def test_error_handling_compatibility(self):
        """Test que la gestion d'erreurs est cohérente"""
        
        # Test avec fichier inexistant
        lua_results = run_lua_simulation("fichier_inexistant.txt")
        assert lua_results.get("error") or not lua_results.get("actions_executed", [])
        
        # Test Python équivalent
        config_parser = ConfigParser()
        
        with pytest.raises((FileNotFoundError, ValueError)):
            config_parser.parse_eclipse_config("fichier_inexistant.txt")
    
    def test_log_structure_compatibility(self, sample_config_file):
        """Test que la structure des logs est similaire"""
        
        # Simulation Lua
        lua_results = run_lua_simulation(sample_config_file)
        lua_logs = lua_results.get("logs", [])
        
        # Vérifications de structure des logs Lua
        assert len(lua_logs) > 0, "Aucun log Lua généré"
        
        # Vérifier la présence de logs clés
        log_content = " ".join(lua_logs)
        assert "Script" in log_content and "loading" in log_content
        assert "Configuration" in log_content
        assert "Normal exit" in log_content
        
        # Test Python - vérifie qu'il peut générer des logs similaires
        try:
            controller = EclipsePhotographyController(
                config_file=sample_config_file,
                test_mode=True,
                mock_cameras=True
            )
            assert controller.config is not None
        except Exception as e:
            pytest.fail(f"Erreur Python lors de l'initialisation: {e}")
    
    def teardown_method(self, method):
        """Nettoyage après chaque test"""
        pass
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self, sample_config_file):
        """Setup et cleanup automatiques"""
        yield
        # Nettoyage du fichier temporaire
        try:
            os.unlink(sample_config_file)
        except (OSError, FileNotFoundError):
            pass


def run_comparative_test(config_file: str) -> Dict[str, Any]:
    """
    Lance un test comparatif complet entre Lua et Python
    
    Args:
        config_file: Chemin vers le fichier de configuration
    
    Returns:
        Dictionnaire avec les résultats de la comparaison
    """
    
    print(f"🔄 Lancement du test comparatif avec {config_file}")
    
    # Vérification existence du fichier
    if not os.path.exists(config_file):
        return {"error": f"Fichier {config_file} non trouvé", "success": False}
    
    try:
        # Exécution Lua
        print("📋 Exécution simulation Lua...")
        lua_results = run_lua_simulation(config_file, start_time_hms=(20, 15, 0))
        
        # Exécution Python
        print("🐍 Exécution implémentation Python...")
        config_parser = ConfigParser()
        config = config_parser.parse_eclipse_config(config_file)
        
        # Préparation des résultats de comparaison
        comparison = {
            "lua_results": lua_results,
            "python_config": {
                "actions_count": len(config.actions),
                "test_mode": config.test_mode,
                "eclipse_timings": {
                    "C1": config.eclipse_timings.c1_seconds,
                    "C2": config.eclipse_timings.c2_seconds,
                    "Max": config.eclipse_timings.max_seconds,
                    "C3": config.eclipse_timings.c3_seconds,
                    "C4": config.eclipse_timings.c4_seconds
                }
            },
            "differences": [],
            "compatibility_score": 100.0,
            "success": True
        }
        
        # Analyse des différences
        lua_config = lua_results.get("config", {})
        python_timings = comparison["python_config"]["eclipse_timings"]
        
        # Comparaison des timings d'éclipse
        for key in ["C1", "C2", "Max", "C3", "C4"]:
            lua_val = lua_config.get(key)
            python_val = python_timings.get(key)
            if lua_val != python_val:
                comparison["differences"].append(f"Timing {key}: Lua={lua_val}, Python={python_val}")
                comparison["compatibility_score"] -= 15.0
        
        # Comparaison test mode
        lua_test_mode = bool(lua_config.get("TestMode", 0))
        if lua_test_mode != config.test_mode:
            comparison["differences"].append(f"Test mode: Lua={lua_test_mode}, Python={config.test_mode}")
            comparison["compatibility_score"] -= 10.0
        
        # Comparaison nombre d'actions
        lua_actions_count = len(lua_results.get("actions_executed", []))
        python_actions_count = len(config.actions)
        if lua_actions_count != python_actions_count:
            comparison["differences"].append(f"Nombre d'actions: Lua={lua_actions_count}, Python={python_actions_count}")
            comparison["compatibility_score"] -= 20.0
        
        # Comparaison des paramètres des actions
        for i, lua_action in enumerate(lua_results.get("actions_executed", [])):
            if i < len(config.actions):
                py_action = config.actions[i]
                
                # Vérification des paramètres caméra
                if lua_action.get("aperture") != py_action.aperture:
                    comparison["differences"].append(f"Action {i} aperture: Lua={lua_action['aperture']}, Python={py_action.aperture}")
                    comparison["compatibility_score"] -= 5.0
                
                if lua_action.get("iso") != py_action.iso:
                    comparison["differences"].append(f"Action {i} ISO: Lua={lua_action['iso']}, Python={py_action.iso}")
                    comparison["compatibility_score"] -= 5.0
        
        comparison["compatibility_score"] = max(0.0, comparison["compatibility_score"])
        
        return comparison
        
    except Exception as e:
        return {
            "error": str(e),
            "success": False,
            "compatibility_score": 0.0
        }


def print_comparison_results(results: Dict[str, Any]):
    """Affiche les résultats de la comparaison"""
    
    if not results.get("success", False):
        print(f"❌ Erreur lors de la comparaison: {results.get('error', 'Erreur inconnue')}")
        return
    
    score = results.get("compatibility_score", 0.0)
    differences = results.get("differences", [])
    
    print(f"\n📊 Score de compatibilité: {score:.1f}%")
    
    if score >= 90.0:
        print("✅ Les implémentations sont hautement compatibles!")
        status = "EXCELLENT"
    elif score >= 70.0:
        print("⚠️  Compatibilité acceptable mais améliorable.")
        status = "BON"
    elif score >= 50.0:
        print("⚠️  Compatibilité modérée, révision recommandée.")
        status = "MOYEN"
    else:
        print("❌ Compatibilité faible, révision nécessaire.")
        status = "FAIBLE"
    
    if differences:
        print(f"\n📝 Différences détectées ({len(differences)}):")
        for diff in differences:
            print(f"   • {diff}")
    else:
        print("\n🎉 Aucune différence majeure détectée!")
    
    # Statistiques
    lua_results = results.get("lua_results", {})
    python_config = results.get("python_config", {})
    
    print(f"\n📈 Statistiques:")
    print(f"   • Actions Lua exécutées: {len(lua_results.get('actions_executed', []))}")
    print(f"   • Actions Python parsées: {python_config.get('actions_count', 0)}")
    print(f"   • Logs Lua générés: {len(lua_results.get('logs', []))}")
    print(f"   • Mode test Lua: {bool(lua_results.get('config', {}).get('TestMode', 0))}")
    print(f"   • Mode test Python: {python_config.get('test_mode', False)}")
    
    return status


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        # Utilise le fichier par défaut
        config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "SOLARECL.TXT")
    
    print("🔍 Tests comparatifs Lua vs Python")
    print("=" * 50)
    
    if os.path.exists(config_file):
        results = run_comparative_test(config_file)
        status = print_comparison_results(results)
        
        # Code de sortie basé sur le statut
        if status == "EXCELLENT":
            sys.exit(0)
        elif status in ["BON", "MOYEN"]:
            sys.exit(1)
        else:
            sys.exit(2)
    else:
        print(f"❌ Fichier de configuration non trouvé: {config_file}")
        print("\nUtilisation:")
        print(f"  python {__file__} [fichier_config.txt]")
        sys.exit(3)