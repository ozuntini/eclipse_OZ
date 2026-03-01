#!/usr/bin/env python3
"""Test simple du simulateur Lua"""

import sys
import os
sys.path.append('.')

from lua_simulator import run_lua_simulation

def test_lua_simulator():
    """Test basique du simulateur"""
    
    config_file = "../SOLARECL.TXT"
    
    if not os.path.exists(config_file):
        print("❌ Fichier SOLARECL.TXT non trouvé")
        return False
    
    print("🔄 Test du simulateur Lua...")
    
    try:
        results = run_lua_simulation(config_file, start_time_hms=(20, 15, 0))
        
        print("=== Résultats Simulation Lua ===")
        error = results.get("error", "Aucune")
        print(f"Erreur: {error}")
        
        actions = results.get("actions_executed", [])
        print(f"Actions exécutées: {len(actions)}")
        
        logs = results.get("logs", [])
        print(f"Logs générés: {len(logs)}")
        
        config = results.get("config", {})
        if config:
            print("Configuration eclipse:")
            for k, v in config.items():
                print(f"  {k}: {v}")
        
        if actions:
            print("\nPremières actions:")
            for i, action in enumerate(actions[:3]):
                print(f"  {i+1}. {action['action']} - ISO:{action['iso']} F/{action['aperture']}")
        
        if logs:
            print("\nPremiers logs:")
            for log in logs[:3]:
                print(f"  {log}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


if __name__ == "__main__":
    success = test_lua_simulator()
    sys.exit(0 if success else 1)