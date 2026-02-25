#!/usr/bin/env python3
"""
Test de comparaison direct entre Lua et Python avec SOLARECL.TXT
"""

import sys
import os
sys.path.append('.')
sys.path.append('./config')
sys.path.append('./scheduling')

from lua_simulator import run_lua_simulation

# Import avec gestion d'erreur
try:
    from config.parser import ConfigParser
    from scheduling.time_calculator import TimeCalculator
except ImportError:
    # Import alternatif si module path ne fonctionne pas
    import importlib.util
    
    spec = importlib.util.spec_from_file_location("parser", "./config/parser.py")
    parser_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser_module)
    ConfigParser = parser_module.ConfigParser
    
    spec = importlib.util.spec_from_file_location("time_calculator", "./scheduling/time_calculator.py")
    calc_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(calc_module)
    TimeCalculator = calc_module.TimeCalculator

def compare_lua_vs_python():
    """Compare les résultats Lua et Python avec le même fichier"""
    
    config_file = "../SOLARECL.TXT"
    
    print("🔍 Comparaison Lua vs Python avec SOLARECL.TXT")
    print("=" * 60)
    
    # 1. Exécution Lua
    print("📋 1. Simulation Lua...")
    lua_results = run_lua_simulation(config_file, start_time_hms=(20, 15, 0))
    
    print(f"   Actions Lua: {len(lua_results.get('actions_executed', []))}")
    print(f"   Logs Lua: {len(lua_results.get('logs', []))}")
    print(f"   Config C1: {lua_results['config']['C1']}s ({lua_results['config']['C1']//3600:02d}:{(lua_results['config']['C1']%3600)//60:02d}:{lua_results['config']['C1']%60:02d})")
    
    # 2. Exécution Python
    print("\n🐍 2. Parsing Python...")
    try:
        config_parser = ConfigParser()
        config = config_parser.parse_eclipse_config(config_file)
        
        print(f"   Actions Python: {len(config.actions)}")
        print(f"   Test mode Python: {config.test_mode}")
        print(f"   Config C1: {config.eclipse_timings.c1_seconds}s ({config.eclipse_timings.c1_seconds//3600:02d}:{(config.eclipse_timings.c1_seconds%3600)//60:02d}:{config.eclipse_timings.c1_seconds%60:02d})")
        
    except Exception as e:
        print(f"   ❌ Erreur Python: {e}")
        return False
    
    # 3. Comparaison
    print("\n📊 3. Comparaison des résultats:")
    
    # Comparaison timings éclipse
    timings_match = True
    for key in ["C1", "C2", "Max", "C3", "C4"]:
        lua_val = lua_results['config'][key]
        if key == "C1":
            python_val = config.eclipse_timings.c1_seconds
        elif key == "C2":
            python_val = config.eclipse_timings.c2_seconds
        elif key == "Max":
            python_val = config.eclipse_timings.max_seconds
        elif key == "C3":
            python_val = config.eclipse_timings.c3_seconds
        elif key == "C4":
            python_val = config.eclipse_timings.c4_seconds
        
        if lua_val == python_val:
            print(f"   ✅ {key}: {lua_val}s (identique)")
        else:
            print(f"   ❌ {key}: Lua={lua_val}s vs Python={python_val}s")
            timings_match = False
    
    # Comparaison test mode
    lua_test_mode = bool(lua_results['config']['TestMode'])
    if lua_test_mode == config.test_mode:
        print(f"   ✅ Test mode: {lua_test_mode} (identique)")
    else:
        print(f"   ❌ Test mode: Lua={lua_test_mode} vs Python={config.test_mode}")
        timings_match = False
    
    # Comparaison nombre d'actions
    lua_actions_count = len(lua_results['actions_executed'])
    python_actions_count = len(config.actions)
    if lua_actions_count == python_actions_count:
        print(f"   ✅ Nombre d'actions: {lua_actions_count} (identique)")
    else:
        print(f"   ❌ Nombre d'actions: Lua={lua_actions_count} vs Python={python_actions_count}")
        timings_match = False
    
    # 4. Comparaison détaillée des actions
    print("\n🎯 4. Comparaison des actions:")
    for i, lua_action in enumerate(lua_results['actions_executed']):
        if i < len(config.actions):
            py_action = config.actions[i]
            
            print(f"   Action {i+1}: {lua_action['action']}")
            
            # Comparaison des paramètres
            params_match = True
            if lua_action['aperture'] != py_action.aperture:
                print(f"     ❌ Aperture: Lua={lua_action['aperture']} vs Python={py_action.aperture}")
                params_match = False
            
            if lua_action['iso'] != py_action.iso:
                print(f"     ❌ ISO: Lua={lua_action['iso']} vs Python={py_action.iso}")
                params_match = False
            
            if abs(lua_action['shutter_speed'] - py_action.shutter_speed) > 0.0001:
                print(f"     ❌ Shutter: Lua={lua_action['shutter_speed']} vs Python={py_action.shutter_speed}")
                params_match = False
            
            if lua_action['mlu_delay'] != py_action.mirror_lockup_delay:
                print(f"     ❌ MLU Delay: Lua={lua_action['mlu_delay']} vs Python={py_action.mirror_lockup_delay}")
                params_match = False
            
            if params_match:
                print(f"     ✅ Paramètres identiques")
    
    # 5. Résultat final
    print("\n🎯 Résultat de la comparaison:")
    if timings_match:
        print("   🎉 PARFAIT! Les implémentations Lua et Python sont identiques")
        print("   ✅ Migration réussie avec compatibilité complète")
        return True
    else:
        print("   ⚠️  Différences détectées entre Lua et Python")
        print("   🔧 Ajustements nécessaires pour une compatibilité parfaite")
        return False


def show_detailed_comparison():
    """Affiche une comparaison détaillée des calculs de temps"""
    
    config_file = "../SOLARECL.TXT"
    
    print("\n📐 Analyse détaillée des calculs de temps:")
    print("=" * 50)
    
    # Simulation Lua
    lua_results = run_lua_simulation(config_file, start_time_hms=(20, 15, 0))
    
    # Configuration Python
    config_parser = ConfigParser()
    config = config_parser.parse_eclipse_config(config_file)
    
    from scheduling.time_calculator import TimeCalculator
    time_calc = TimeCalculator()
    
    # Analyse action par action
    for i, lua_action in enumerate(lua_results['actions_executed']):
        if i < len(config.actions):
            py_action = config.actions[i]
            
            print(f"\nAction {i+1}: {lua_action['action']}")
            
            # Temps de départ
            lua_start = lua_action['time_start']
            lua_start_str = f"{lua_start//3600:02d}:{(lua_start%3600)//60:02d}:{lua_start%60:02d}"
            
            if py_action.reference_point and py_action.reference_point != "-":
                py_start = time_calc.convert_relative_time(
                    py_action.reference_point,
                    py_action.start_operation,
                    py_action.start_time_seconds,
                    config.eclipse_timings
                )
                py_start_str = f"{py_start//3600:02d}:{(py_start%3600)//60:02d}:{py_start%60:02d}"
                
                if lua_start == py_start:
                    print(f"   ✅ Temps début: {lua_start_str} (identique)")
                else:
                    print(f"   ❌ Temps début: Lua={lua_start_str} vs Python={py_start_str}")
            
            # Temps de fin pour boucles
            if lua_action.get('time_end') and py_action.action_type in ["Boucle", "Interval"]:
                lua_end = lua_action['time_end']
                lua_end_str = f"{lua_end//3600:02d}:{(lua_end%3600)//60:02d}:{lua_end%60:02d}"
                
                py_end = time_calc.convert_relative_time(
                    py_action.reference_point,
                    py_action.end_operation,
                    py_action.end_time_seconds,
                    config.eclipse_timings
                )
                py_end_str = f"{py_end//3600:02d}:{(py_end%3600)//60:02d}:{py_end%60:02d}"
                
                if lua_end == py_end:
                    print(f"   ✅ Temps fin: {lua_end_str} (identique)")
                else:
                    print(f"   ❌ Temps fin: Lua={lua_end_str} vs Python={py_end_str}")


if __name__ == "__main__":
    success = compare_lua_vs_python()
    
    if "--detailed" in sys.argv:
        show_detailed_comparison()
    
    if success:
        print("\n🎉 TEST RÉUSSI: Les deux implémentations sont compatibles!")
        sys.exit(0)
    else:
        print("\n⚠️  TEST PARTIELLEMENT RÉUSSI: Quelques ajustements nécessaires.")
        sys.exit(1)