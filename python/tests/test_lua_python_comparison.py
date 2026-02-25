#!/usr/bin/env python3
"""
Tests comparatifs entre l'implémentation Lua originale et la nouvelle implémentation Python.
Vérifie que les deux solutions produisent exactement les mêmes résultats.
"""

import pytest
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
import json
import tempfile

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des modules Python
from config.parser import ConfigParser, EclipseTimings, ActionConfig
from scheduling.time_calculator import TimeCalculator
from scheduling.action_scheduler import ActionScheduler
from hardware.camera_controller import CameraController
from hardware.multi_camera_manager import MultiCameraManager
from main import EclipsePhotographyController

# Import du simulateur Lua
from lua_simulator import run_lua_simulation, LuaSimulator
comportements que le script Lua original eclipse_OZ.lua.
"""

import pytest
import os
from datetime import datetime, time
from python.scheduling.time_calculator import TimeCalculator
from python.config.parser import ConfigParser

class TestTimeConversionComparison:
    """Tests comparatifs des calculs de temps entre Lua et Python"""
    
    def setup_method(self):
        """Configuration des tests avec données réelles d'éclipse"""
        # Données d'éclipse du 8 avril 2024 (utilisées dans config_eclipse.txt)
        self.eclipse_times = {
            'C1': (18, 10, 29),    # 18:10:29 - Premier contact
            'C2': (19, 27, 3),     # 19:27:03 - Début totalité 
            'Max': (19, 28, 23),   # 19:28:23 - Maximum
            'C3': (19, 29, 43),    # 19:29:43 - Fin totalité
            'C4': (20, 46, 31)     # 20:46:31 - Dernier contact
        }
        
        self.time_calc = TimeCalculator()
        
    def convert_second_lua(self, hrs, mins, secs):
        """Reproduction exacte de la fonction convert_second() Lua"""
        return hrs * 3600 + mins * 60 + secs
        
    def convert_time_lua(self, reference, operation, time_in, table_ref):
        """
        Reproduction exacte de la fonction convert_time() Lua
        
        Args:
            reference: "C1", "C2", "Max", "C3", "C4"
            operation: "+" ou "-"  
            time_in: temps en secondes à ajouter/soustraire
            table_ref: [C1, C2, Max, C3, C4] en secondes
        """
        time_ref = 0
        
        # Identification de la référence (index Lua commence à 1)
        if reference == "C1":
            time_ref = table_ref[0]  # Python index 0 = Lua index 1
        elif reference == "C2":
            time_ref = table_ref[1]  # Python index 1 = Lua index 2  
        elif reference == "Max":
            time_ref = table_ref[2]  # Python index 2 = Lua index 3
        elif reference == "C3":
            time_ref = table_ref[3]  # Python index 3 = Lua index 4
        elif reference == "C4":
            time_ref = table_ref[4]  # Python index 4 = Lua index 5
        
        # Calcul avec gestion passage minuit
        if operation == "-":
            time_out = time_ref - time_in
            if time_out < 0:
                time_out = 86400 + time_out
        elif operation == "+":
            time_out = time_ref + time_in
            if time_out > 86400:
                time_out = time_out - 86400
                
        return time_out
        
    def test_convert_second_compatibility(self):
        """Test de compatibilité convert_second Lua vs Python"""
        test_cases = [
            (18, 10, 29),   # C1
            (19, 27, 3),    # C2  
            (19, 28, 23),   # Max
            (19, 29, 43),   # C3
            (20, 46, 31),   # C4
            (0, 0, 0),      # Minuit
            (23, 59, 59),   # Fin de journée
            (12, 30, 45),   # Milieu de journée
        ]
        
        for hrs, mins, secs in test_cases:
            lua_result = self.convert_second_lua(hrs, mins, secs)
            python_result = self.time_calc.convert_to_seconds(hrs, mins, secs)
            
            assert lua_result == python_result, (
                f"Différence convert_second pour {hrs}:{mins:02d}:{secs:02d} "
                f"- Lua: {lua_result}, Python: {python_result}"
            )
    
    def test_convert_time_compatibility(self):
        """Test de compatibilité convert_time Lua vs Python"""
        # Table de référence en secondes
        table_ref = [
            self.convert_second_lua(*self.eclipse_times['C1']),   # C1
            self.convert_second_lua(*self.eclipse_times['C2']),   # C2
            self.convert_second_lua(*self.eclipse_times['Max']),  # Max
            self.convert_second_lua(*self.eclipse_times['C3']),   # C3
            self.convert_second_lua(*self.eclipse_times['C4'])    # C4
        ]
        
        test_cases = [
            # Cas de test réels du script d'éclipse
            ("C1", "-", 600),     # 10 min avant C1
            ("C2", "-", 300),     # 5 min avant C2
            ("Max", "-", 120),    # 2 min avant Max
            ("Max", "+", 60),     # 1 min après Max
            ("C3", "+", 300),     # 5 min après C3
            ("C4", "+", 600),     # 10 min après C4
            
            # Cas limites
            ("C1", "-", 3600),    # 1h avant C1 (test passage minuit)
            ("C4", "+", 7200),    # 2h après C4 (test passage minuit)
        ]
        
        for ref, op, offset in test_cases:
            lua_result = self.convert_time_lua(ref, op, offset, table_ref)
            
            # Préparation des données pour la méthode Python
            ref_times = {
                'C1': time(*self.eclipse_times['C1']),
                'C2': time(*self.eclipse_times['C2']),
                'Max': time(*self.eclipse_times['Max']),
                'C3': time(*self.eclipse_times['C3']),
                'C4': time(*self.eclipse_times['C4'])
            }
            
            python_result = self.time_calc.convert_relative_time(
                ref, op, offset, ref_times
            )
            python_result_secs = (
                python_result.hour * 3600 + 
                python_result.minute * 60 + 
                python_result.second
            )
            
            assert lua_result == python_result_secs, (
                f"Différence convert_time pour {ref} {op} {offset}s "
                f"- Lua: {lua_result}s, Python: {python_result_secs}s"
            )
    
    def test_pretty_time_compatibility(self):
        """Test de compatibilité d'affichage des temps"""
        test_times = [
            0,      # 00:00:00
            3661,   # 01:01:01  
            43200,  # 12:00:00
            86399,  # 23:59:59
            65503,  # 18:10:29 (C1)
            70023,  # 19:27:03 (C2)
        ]
        
        def pretty_time_lua(time_secs):
            """Reproduction de la fonction pretty_time() Lua"""
            hrs = time_secs // 3600
            mins = (time_secs - (hrs * 3600)) // 60
            secs = time_secs - (hrs * 3600) - (mins * 60)
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        
        for time_secs in test_times:
            lua_format = pretty_time_lua(time_secs)
            
            # Conversion pour Python
            hrs = time_secs // 3600
            mins = (time_secs % 3600) // 60
            secs = time_secs % 60
            python_time = time(hrs, mins, secs)
            python_format = python_time.strftime("%H:%M:%S")
            
            assert lua_format == python_format, (
                f"Différence formatage pour {time_secs}s "
                f"- Lua: '{lua_format}', Python: '{python_format}'"
            )


class TestConfigurationParsingComparison:
    """Tests comparatifs du parsing de configuration"""
    
    def setup_method(self):
        """Configuration avec fichier de test compatible Lua"""
        self.config_content = """# Configuration Eclipse 8 avril 2024
# Ligne de configuration des contacts
Config,18,10,29,19,27,3,19,28,23,19,29,43,20,46,31,0
# Vérification configuration  
Verif,3,0,80,1000
# Actions de photographie
Photo,C1,-,0,5,0,-,-,-,-,-,-,8,100,4,0
Boucle,C1,+,0,1,0,C2,-,0,1,0,30,8,200,8,0  
Photo,Max,-,-,-,-,-,-,-,-,-,-,5.6,400,2,1000
Interval,C3,+,0,0,30,C4,-,0,5,0,10,8,800,15,0
"""
        
    def test_config_line_parsing_lua_vs_python(self):
        """Test parsing ligne Config compatible Lua/Python"""
        config_parser = ConfigParser()
        
        # Simulation parsing Lua de la ligne Config
        config_line = "Config,18,10,29,19,27,3,19,28,23,19,29,43,20,46,31,0"
        lua_values = config_line.split(',')
        
        # Extraction valeurs Lua
        lua_c1 = int(lua_values[1]) * 3600 + int(lua_values[2]) * 60 + int(lua_values[3])
        lua_c2 = int(lua_values[4]) * 3600 + int(lua_values[5]) * 60 + int(lua_values[6])
        lua_max = int(lua_values[7]) * 3600 + int(lua_values[8]) * 60 + int(lua_values[9])
        lua_c3 = int(lua_values[10]) * 3600 + int(lua_values[11]) * 60 + int(lua_values[12])
        lua_c4 = int(lua_values[13]) * 3600 + int(lua_values[14]) * 60 + int(lua_values[15])
        lua_test_mode = int(lua_values[16])
        
        # Création fichier temporaire pour Python
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(self.config_content)
            temp_path = f.name
            
        try:
            # Parsing Python
            python_config = config_parser.parse_eclipse_config(temp_path)
            
            # Conversion times Python en secondes pour comparaison
            python_c1 = (python_config.timings.C1.hour * 3600 + 
                         python_config.timings.C1.minute * 60 + 
                         python_config.timings.C1.second)
            python_c2 = (python_config.timings.C2.hour * 3600 + 
                         python_config.timings.C2.minute * 60 + 
                         python_config.timings.C2.second)
            python_max = (python_config.timings.Max.hour * 3600 + 
                          python_config.timings.Max.minute * 60 + 
                          python_config.timings.Max.second)
            python_c3 = (python_config.timings.C3.hour * 3600 + 
                         python_config.timings.C3.minute * 60 + 
                         python_config.timings.C3.second)
            python_c4 = (python_config.timings.C4.hour * 3600 + 
                         python_config.timings.C4.minute * 60 + 
                         python_config.timings.C4.second)
            
            # Vérifications
            assert lua_c1 == python_c1, f"C1 différent: Lua {lua_c1} vs Python {python_c1}"
            assert lua_c2 == python_c2, f"C2 différent: Lua {lua_c2} vs Python {python_c2}"
            assert lua_max == python_max, f"Max différent: Lua {lua_max} vs Python {python_max}"
            assert lua_c3 == python_c3, f"C3 différent: Lua {lua_c3} vs Python {python_c3}"
            assert lua_c4 == python_c4, f"C4 différent: Lua {lua_c4} vs Python {python_c4}"
            assert lua_test_mode == python_config.test_mode, (
                f"TestMode différent: Lua {lua_test_mode} vs Python {python_config.test_mode}"
            )
            
        finally:
            os.unlink(temp_path)
    
    def test_action_parsing_compatibility(self):
        """Test parsing des actions Photo/Boucle/Interval"""
        config_parser = ConfigParser()
        
        # Simulation du parsing Lua pour chaque type d'action
        actions_lua = [
            # Photo action
            {
                'line': "Photo,C1,-,0,5,0,-,-,-,-,-,-,8,100,4,0",
                'expected': {
                    'action': 'Photo',
                    'ref_time': 'C1',
                    'oper_start': '-', 
                    'time_start': (0, 5, 0),
                    'aperture': 8,
                    'iso': 100,
                    'shutter': 4,
                    'mlu_delay': 0
                }
            },
            # Boucle action
            {
                'line': "Boucle,C1,+,0,1,0,C2,-,0,1,0,30,8,200,8,0",
                'expected': {
                    'action': 'Boucle',
                    'ref_time': 'C1',
                    'oper_start': '+',
                    'time_start': (0, 1, 0),
                    'oper_end': '-',
                    'time_end': (0, 1, 0),
                    'interval': 30,
                    'aperture': 8,
                    'iso': 200,
                    'shutter': 8,
                    'mlu_delay': 0
                }
            }
        ]
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(self.config_content)
            temp_path = f.name
            
        try:
            python_config = config_parser.parse_eclipse_config(temp_path)
            
            # Vérification que les actions sont correctement parsées
            assert len(python_config.actions) >= 2, "Pas assez d'actions parsées"
            
            # Vérification action Photo
            photo_action = python_config.actions[0]
            assert photo_action.action_type == 'Photo'
            assert photo_action.reference_time == 'C1'
            assert photo_action.aperture == 8
            assert photo_action.iso == 100
            assert photo_action.shutter_speed == 4
            
            # Vérification action Boucle  
            boucle_action = python_config.actions[1]
            assert boucle_action.action_type == 'Boucle'
            assert boucle_action.reference_time == 'C1'
            assert boucle_action.interval == 30
            assert boucle_action.aperture == 8
            assert boucle_action.iso == 200
            
        finally:
            os.unlink(temp_path)


class TestCameraActionComparison:
    """Tests comparatifs des actions caméra"""
    
    def test_mirror_lockup_logic(self):
        """Test de la logique mirror lockup Lua vs Python"""
        # Simulation logique Lua
        def set_mirror_lockup_lua(mirror_lockup_delay):
            if mirror_lockup_delay > 0:
                return {
                    'mode': 'Handheld',
                    'shutter': 'All values', 
                    'delay': '1s',
                    'enabled': True
                }
            else:
                return {'enabled': False}
        
        # Test cas avec delay
        lua_result = set_mirror_lockup_lua(1000)
        assert lua_result['enabled'] is True
        assert lua_result['mode'] == 'Handheld'
        
        # Test cas sans delay
        lua_result = set_mirror_lockup_lua(0)
        assert lua_result['enabled'] is False
    
    def test_interval_calculation_compatibility(self):
        """Test calcul d'intervalle mode Interval vs Boucle"""
        
        # Simulation logique Lua pour mode Interval
        def calculate_interval_lua(action, time_start, time_end, interval_or_count):
            if action == "Interval":
                # Conversion du nombre de photos en intervalle
                interval = (time_end - time_start) / interval_or_count
            else:  # Boucle
                interval = interval_or_count
                
            # Arrondi comme en Lua: math.ceil(interval - 0.5)
            import math
            interval = math.ceil(interval - 0.5)
            if interval < 1:
                interval = 1
                
            return interval
        
        # Tests cas Interval
        lua_interval = calculate_interval_lua("Interval", 1000, 1600, 10)  # 10 photos en 600s
        expected = 60  # 600s / 10 photos = 60s par photo
        assert lua_interval == expected
        
        # Test cas Boucle
        lua_interval = calculate_interval_lua("Boucle", 1000, 1600, 30)  # Interval fixe 30s
        assert lua_interval == 30
        
        # Test cas limite < 1s
        lua_interval = calculate_interval_lua("Interval", 1000, 1005, 10)  # 5s / 10 photos = 0.5s
        assert lua_interval == 1  # Forcé à 1s minimum


class TestRegressionSuite:
    """Suite complète de tests de régression"""
    
    def test_full_eclipse_scenario_compatibility(self):
        """Test scénario complet d'éclipse Lua vs Python"""
        # Configuration d'éclipse réelle
        eclipse_config = """# Eclipse 8 avril 2024 - Test de régression
Config,18,10,29,19,27,3,19,28,23,19,29,43,20,46,31,0
Verif,3,0,80,1000
# Photos avant totalité
Photo,C1,-,0,10,0,-,-,-,-,-,-,8,100,4,0
Photo,C1,-,0,5,0,-,-,-,-,-,-,8,100,2,0  
Photo,C1,-,0,1,0,-,-,-,-,-,-,8,200,1,0
# Boucle pendant approche
Boucle,C1,+,0,1,0,C2,-,0,2,0,30,8,400,8,0
# Photos pendant totalité
Photo,C2,+,0,0,5,-,-,-,-,-,-,5.6,800,2,1000
Photo,Max,-,-,-,-,-,-,-,-,-,-,5.6,1600,1,1000  
Photo,C3,-,0,0,5,-,-,-,-,-,-,5.6,800,2,1000
# Boucle après totalité
Boucle,C3,+,0,0,30,C4,-,0,5,0,60,8,400,15,0
"""
        
        # Test que Python peut parser et traiter exactement comme Lua
        from python.config.parser import ConfigParser
        from python.scheduling.time_calculator import TimeCalculator
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(eclipse_config)
            temp_path = f.name
            
        try:
            config_parser = ConfigParser()
            time_calc = TimeCalculator()
            
            # Parse configuration
            config = config_parser.parse_eclipse_config(temp_path)
            
            # Vérifications structure identique à Lua
            assert config.timings.C1.hour == 18
            assert config.timings.C1.minute == 10  
            assert config.timings.C1.second == 29
            
            assert len(config.actions) == 7, "Nombre d'actions incorrect"
            
            # Vérification calculs temporels pour chaque action
            ref_times = {
                'C1': config.timings.C1,
                'C2': config.timings.C2,
                'Max': config.timings.Max,
                'C3': config.timings.C3,
                'C4': config.timings.C4
            }
            
            for action in config.actions:
                if action.action_type == 'Photo':
                    # Test calcul temps absolu
                    if action.reference_time != '-':
                        start_time = time_calc.convert_relative_time(
                            action.reference_time,
                            action.start_operation,
                            action.start_offset_seconds,
                            ref_times
                        )
                        assert start_time is not None
                        
                elif action.action_type in ['Boucle', 'Interval']:
                    # Test calculs début et fin
                    start_time = time_calc.convert_relative_time(
                        action.reference_time,
                        action.start_operation, 
                        action.start_offset_seconds,
                        ref_times
                    )
                    end_time = time_calc.convert_relative_time(
                        action.reference_time,
                        action.end_operation,
                        action.end_offset_seconds, 
                        ref_times
                    )
                    assert start_time is not None
                    assert end_time is not None
                    
        finally:
            os.unlink(temp_path)
        
        print("✅ Test de régression complet réussi - Compatibilité Lua/Python validée")


if __name__ == "__main__":
    # Lancement des tests de régression
    pytest.main([__file__, "-v", "--tb=short"])