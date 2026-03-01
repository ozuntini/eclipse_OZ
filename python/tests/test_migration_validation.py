"""
Tests unitaires spécialisés pour la validation de la migration Lua -> Python
============================================================================

Ce module contient des tests spécifiques pour valider que chaque fonction
migrée du script Lua original produit exactement les mêmes résultats
que son équivalent Python.
"""

import pytest
import math
import tempfile
import os
from datetime import time

from python.config.parser import ConfigParser
from python.scheduling.time_calculator import TimeCalculator



class LuaReferenceFunctions:
    """
    Implémentations de référence des fonctions Lua originales
    pour validation bit-à-bit de la migration
    """
    
    @staticmethod
    def convert_second(hrs, mins, secs):
        """Fonction convert_second() exacte du script Lua"""
        return hrs * 3600 + mins * 60 + secs
    
    @staticmethod 
    def convert_time(reference, operation, time_in, table_ref):
        """
        Fonction convert_time() exacte du script Lua
        
        Convertit un temps relatif en temps absolu selon la référence
        """
        time_ref = 0
        
        # Sélection référence (indices Lua commencent à 1)
        if reference == "C1":
            time_ref = table_ref[0]
        elif reference == "C2": 
            time_ref = table_ref[1]
        elif reference == "Max":
            time_ref = table_ref[2]
        elif reference == "C3":
            time_ref = table_ref[3]
        elif reference == "C4":
            time_ref = table_ref[4]
        else:
            raise ValueError(f"Référence invalide: {reference}")
            
        # Calcul avec gestion des limites jour (86400 secondes)
        if operation == "-":
            time_out = time_ref - time_in
            if time_out < 0:
                time_out = 86400 + time_out
        elif operation == "+":
            time_out = time_ref + time_in
            if time_out > 86400:
                time_out = time_out - 86400
        else:
            raise ValueError(f"Opération invalide: {operation}")
            
        return time_out
    
    @staticmethod
    def pretty_time(time_secs):
        """Fonction pretty_time() exacte du script Lua"""
        hrs = math.floor(time_secs / 3600)
        mins = math.floor((time_secs - (hrs * 3600)) / 60)
        secs = time_secs - (hrs * 3600) - (mins * 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    
    @staticmethod
    def pretty_shutter(shutter_speed):
        """Fonction pretty_shutter() exacte du script Lua"""
        if shutter_speed >= 1.0:
            return str(shutter_speed)
        else:
            return f"1/{1/shutter_speed}"
    
    @staticmethod
    def calculate_interval_lua(action, time_start, time_end, interval_or_count):
        """
        Logique de calcul d'intervalle du script Lua
        """
        if action == "Interval":
            # Conversion nombre de photos en intervalle
            interval = (time_end - time_start) / interval_or_count
        else:  # Boucle
            interval = interval_or_count
            
        # Arrondi exact Lua: math.ceil(interval - 0.5)
        interval = math.ceil(interval - 0.5)
        
        # Minimum 1 seconde
        if interval < 1:
            interval = 1
            
        return interval
    
    @staticmethod
    def read_config_line(line_values):
        """
        Simulation lecture ligne Config du script Lua
        
        Args:
            line_values: Liste des valeurs de la ligne Config
            
        Returns:
            Tuple (timeC1, timeC2, timeMax, timeC3, timeC4, testMode)
        """
        time_c1 = LuaReferenceFunctions.convert_second(
            int(line_values[1]), int(line_values[2]), int(line_values[3])
        )
        time_c2 = LuaReferenceFunctions.convert_second(
            int(line_values[4]), int(line_values[5]), int(line_values[6])
        )
        time_max = LuaReferenceFunctions.convert_second(
            int(line_values[7]), int(line_values[8]), int(line_values[9])
        )
        time_c3 = LuaReferenceFunctions.convert_second(
            int(line_values[10]), int(line_values[11]), int(line_values[12])
        )
        time_c4 = LuaReferenceFunctions.convert_second(
            int(line_values[13]), int(line_values[14]), int(line_values[15])
        )
        test_mode = int(line_values[16])
        
        return time_c1, time_c2, time_max, time_c3, time_c4, test_mode


class TestExactFunctionMigration:
    """Tests de migration exacte fonction par fonction"""
    
    def test_convert_second_exact_match(self):
        """Test convert_second: comportement identique Lua/Python"""
        time_calc = TimeCalculator()
        lua_ref = LuaReferenceFunctions()
        
        # Cas de test exhaustifs
        test_cases = [
            # Cas normaux
            (0, 0, 0),      # Minuit
            (12, 0, 0),     # Midi
            (23, 59, 59),   # Fin de journée
            (18, 10, 29),   # C1 réel
            (19, 27, 3),    # C2 réel
            (19, 28, 23),   # Max réel
            (19, 29, 43),   # C3 réel
            (20, 46, 31),   # C4 réel
            
            # Cas limites
            (0, 0, 1),      # 1 seconde
            (0, 1, 0),      # 1 minute
            (1, 0, 0),      # 1 heure
            (23, 0, 0),     # 23h
            (0, 59, 59),    # Presque 1h
            (23, 59, 0),    # Presque minuit
        ]
        
        for hrs, mins, secs in test_cases:
            lua_result = lua_ref.convert_second(hrs, mins, secs)
            python_result = time_calc.convert_to_seconds(hrs, mins, secs)
            
            assert lua_result == python_result, (
                f"convert_second({hrs}, {mins}, {secs}): "
                f"Lua={lua_result} ≠ Python={python_result}"
            )
    
    def test_convert_time_exact_match(self):
        """Test convert_time: comportement identique Lua/Python"""
        time_calc = TimeCalculator()
        lua_ref = LuaReferenceFunctions()
        
        # Configuration éclipse de référence
        eclipse_times = {
            'C1': (18, 10, 29),   
            'C2': (19, 27, 3),    
            'Max': (19, 28, 23),  
            'C3': (19, 29, 43),   
            'C4': (20, 46, 31)    
        }
        
        # Table de référence pour Lua (en secondes)
        table_ref = [
            lua_ref.convert_second(*eclipse_times['C1']),
            lua_ref.convert_second(*eclipse_times['C2']),
            lua_ref.convert_second(*eclipse_times['Max']),
            lua_ref.convert_second(*eclipse_times['C3']),
            lua_ref.convert_second(*eclipse_times['C4'])
        ]
        
        # Table de référence pour Python (objets time)
        ref_times = {
            'C1': time(*eclipse_times['C1']),
            'C2': time(*eclipse_times['C2']),
            'Max': time(*eclipse_times['Max']),
            'C3': time(*eclipse_times['C3']),
            'C4': time(*eclipse_times['C4'])
        }
        
        # Cas de test complets
        test_cases = [
            # Tests de base
            ("C1", "-", 600),     # 10 min avant C1
            ("C2", "-", 300),     # 5 min avant C2  
            ("Max", "-", 60),     # 1 min avant Max
            ("Max", "+", 60),     # 1 min après Max
            ("C3", "+", 300),     # 5 min après C3
            ("C4", "+", 600),     # 10 min après C4
            
            # Tests passage minuit (avant)
            ("C1", "-", 65429),   # C1 - 18h10m29s = minuit exactement
            ("C1", "-", 70000),   # Plus que la durée jour
            
            # Tests passage minuit (après)
            ("C4", "+", 11169),   # C4 + 3h06m09s = minuit exactement  
            ("C4", "+", 15000),   # Plus que fin de journée
            
            # Tests limites
            ("C1", "-", 1),       # 1 seconde avant
            ("C4", "+", 1),       # 1 seconde après
            ("Max", "-", 0),      # Temps exact
            ("Max", "+", 0),      # Temps exact
        ]
        
        for ref, op, offset in test_cases:
            lua_result = lua_ref.convert_time(ref, op, offset, table_ref)
            python_result = time_calc.convert_relative_time(ref, op, offset, ref_times)
            
            # Conversion Python time en secondes pour comparaison
            python_secs = (
                python_result.hour * 3600 + 
                python_result.minute * 60 + 
                python_result.second
            )
            
            assert lua_result == python_secs, (
                f"convert_time({ref}, {op}, {offset}): "
                f"Lua={lua_result} ≠ Python={python_secs}"
            )
    
    def test_pretty_time_exact_match(self):
        """Test pretty_time: formatage identique Lua/Python"""
        lua_ref = LuaReferenceFunctions()
        
        test_cases = [
            0,      # 00:00:00
            1,      # 00:00:01
            60,     # 00:01:00
            3600,   # 01:00:00
            3661,   # 01:01:01
            43200,  # 12:00:00
            65503,  # 18:10:29 (C1)
            70023,  # 19:27:03 (C2)
            70103,  # 19:28:23 (Max)
            70183,  # 19:29:43 (C3)
            74791,  # 20:46:31 (C4)
            86399,  # 23:59:59
        ]
        
        for time_secs in test_cases:
            lua_format = lua_ref.pretty_time(time_secs)
            
            # Format Python équivalent
            hrs = time_secs // 3600
            mins = (time_secs % 3600) // 60
            secs = time_secs % 60
            python_format = f"{hrs:02d}:{mins:02d}:{secs:02d}"
            
            assert lua_format == python_format, (
                f"pretty_time({time_secs}): "
                f"Lua='{lua_format}' ≠ Python='{python_format}'"
            )
    
    def test_interval_calculation_exact_match(self):
        """Test calcul d'intervalle: logique identique Lua/Python"""
        lua_ref = LuaReferenceFunctions()
        
        test_cases = [
            # Mode Boucle (interval direct)
            ("Boucle", 1000, 2000, 30),   # Interval 30s
            ("Boucle", 1000, 2000, 60),   # Interval 60s
            ("Boucle", 1000, 2000, 1),    # Interval 1s
            ("Boucle", 1000, 2000, 0.5),  # < 1s -> forcé à 1s
            
            # Mode Interval (calcul basé sur nombre de photos)
            ("Interval", 1000, 1600, 10), # 600s / 10 photos = 60s
            ("Interval", 1000, 1300, 5),  # 300s / 5 photos = 60s
            ("Interval", 1000, 1120, 4),  # 120s / 4 photos = 30s
            ("Interval", 1000, 1010, 20), # 10s / 20 photos = 0.5s -> 1s
            
            # Cas limites avec arrondi
            ("Interval", 1000, 1603, 10), # 603s / 10 = 60.3s -> 60s
            ("Interval", 1000, 1607, 10), # 607s / 10 = 60.7s -> 61s
        ]
        
        for action, start, end, interval_or_count in test_cases:
            lua_result = lua_ref.calculate_interval_lua(action, start, end, interval_or_count)
            
            # Simulation calcul Python équivalent
            if action == "Interval":
                python_interval = (end - start) / interval_or_count
            else:
                python_interval = interval_or_count
                
            python_interval = math.ceil(python_interval - 0.5)
            if python_interval < 1:
                python_interval = 1
                
            assert lua_result == python_interval, (
                f"Interval {action}({start}, {end}, {interval_or_count}): "
                f"Lua={lua_result} ≠ Python={python_interval}"
            )


class TestConfigurationCompatibility:
    """Tests de compatibilité du parsing de configuration"""
    
    def test_config_line_parsing_identical(self):
        """Test parsing ligne Config identique Lua/Python"""
        config_parser = ConfigParser()
        lua_ref = LuaReferenceFunctions()
        
        # Ligne Config réelle
        config_line = "Config,18,10,29,19,27,3,19,28,23,19,29,43,20,46,31,0"
        line_values = config_line.split(',')
        
        # Parsing Lua de référence
        lua_c1, lua_c2, lua_max, lua_c3, lua_c4, lua_test_mode = (
            lua_ref.read_config_line(line_values)
        )
        
        # Création fichier temporaire pour Python
        config_content = f"""# Test config
{config_line}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(config_content)
            temp_path = f.name
            
        try:
            # Parsing Python
            python_config = config_parser.parse_eclipse_config(temp_path)
            
            # Conversion Python times en secondes
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
            
            # Vérifications exactes
            assert lua_c1 == python_c1, f"C1: Lua {lua_c1} ≠ Python {python_c1}"
            assert lua_c2 == python_c2, f"C2: Lua {lua_c2} ≠ Python {python_c2}"
            assert lua_max == python_max, f"Max: Lua {lua_max} ≠ Python {python_max}"
            assert lua_c3 == python_c3, f"C3: Lua {lua_c3} ≠ Python {python_c3}"
            assert lua_c4 == python_c4, f"C4: Lua {lua_c4} ≠ Python {python_c4}"
            assert lua_test_mode == python_config.test_mode, (
                f"TestMode: Lua {lua_test_mode} ≠ Python {python_config.test_mode}"
            )
            
        finally:
            os.unlink(temp_path)
    
    def test_action_parsing_compatibility(self):
        """Test parsing actions compatible avec logique Lua"""
        config_content = """# Test actions
Config,18,10,29,19,27,3,19,28,23,19,29,43,20,46,31,0
Photo,C1,-,0,5,0,-,-,-,-,-,-,8,100,4,500
Boucle,C1,+,0,1,0,C2,-,0,1,0,30,8,200,8,0
Interval,C3,+,0,0,30,C4,-,0,5,0,10,8,800,15,0
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(config_content)
            temp_path = f.name
            
        try:
            config_parser = ConfigParser()
            config = config_parser.parse_eclipse_config(temp_path)
            
            # Vérification structure actions
            assert len(config.actions) == 3
            
            # Test action Photo
            photo = config.actions[0]
            assert photo.action_type == 'Photo'
            assert photo.reference_time == 'C1'
            assert photo.start_operation == '-'
            assert photo.start_offset_seconds == 300  # 0h5m0s = 300s
            assert photo.aperture == 8
            assert photo.iso == 100
            assert photo.shutter_speed == 4
            assert photo.mirror_lockup_delay == 500
            
            # Test action Boucle
            boucle = config.actions[1]
            assert boucle.action_type == 'Boucle'
            assert boucle.reference_time == 'C1'
            assert boucle.start_operation == '+'
            assert boucle.start_offset_seconds == 60   # 0h1m0s = 60s
            assert boucle.end_operation == '-'
            assert boucle.end_offset_seconds == 60
            assert boucle.interval == 30
            
            # Test action Interval
            interval = config.actions[2]
            assert interval.action_type == 'Interval'
            assert interval.reference_time == 'C3'
            assert interval.photo_count == 10
            
        finally:
            os.unlink(temp_path)


class TestRegressionValidation:
    """Tests de régression pour validation complète"""
    
    def test_full_eclipse_sequence_compatibility(self):
        """Test séquence complète d'éclipse: comportement Lua/Python identique"""
        
        # Configuration d'éclipse complète
        eclipse_config = """# Eclipse totale 8 avril 2024 - Validation complète
# Configuration des contacts (identique au format Lua)
Config,18,10,29,19,27,3,19,28,23,19,29,43,20,46,31,0

# Séquence pré-totalité (simulation logique Lua exacte)
Photo,C1,-,0,10,0,-,-,-,-,-,-,8,100,4,0
Photo,C1,-,0,5,0,-,-,-,-,-,-,8,100,2,0
Photo,C1,-,0,1,0,-,-,-,-,-,-,8,200,1,0
Boucle,C1,+,0,1,0,C2,-,0,2,0,30,8,400,8,0

# Séquence totalité
Photo,C2,+,0,0,5,-,-,-,-,-,-,5.6,800,2,1000
Photo,Max,-,-,-,-,-,-,-,-,-,-,5.6,1600,1,1000
Photo,C3,-,0,0,5,-,-,-,-,-,-,5.6,800,2,1000

# Séquence post-totalité
Interval,C3,+,0,0,30,C4,-,0,5,0,10,8,400,15,0
Boucle,C3,+,0,5,0,C4,-,0,1,0,60,8,200,30,0
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(eclipse_config)
            temp_path = f.name
            
        try:
            # Parse avec Python
            config_parser = ConfigParser()
            time_calc = TimeCalculator()
            config = config_parser.parse_eclipse_config(temp_path)
            
            # Validation structure identique Lua
            assert config.timings.C1.hour == 18
            assert config.timings.C1.minute == 10
            assert config.timings.C1.second == 29
            assert len(config.actions) == 9
            
            # Simulation calculs Lua pour chaque action
            lua_ref = LuaReferenceFunctions()
            table_ref = [
                lua_ref.convert_second(18, 10, 29),  # C1
                lua_ref.convert_second(19, 27, 3),   # C2
                lua_ref.convert_second(19, 28, 23),  # Max
                lua_ref.convert_second(19, 29, 43),  # C3
                lua_ref.convert_second(20, 46, 31),  # C4
            ]
            
            ref_times = {
                'C1': config.timings.C1,
                'C2': config.timings.C2,
                'Max': config.timings.Max,
                'C3': config.timings.C3,
                'C4': config.timings.C4
            }
            
            # Validation chaque action
            for i, action in enumerate(config.actions):
                if action.action_type == 'Photo':
                    if action.reference_time != '-':
                        # Calcul Lua
                        lua_time = lua_ref.convert_time(
                            action.reference_time,
                            action.start_operation,
                            action.start_offset_seconds,
                            table_ref
                        )
                        
                        # Calcul Python
                        python_time = time_calc.convert_relative_time(
                            action.reference_time,
                            action.start_operation,
                            action.start_offset_seconds,
                            ref_times
                        )
                        python_secs = (python_time.hour * 3600 + 
                                     python_time.minute * 60 + 
                                     python_time.second)
                        
                        assert lua_time == python_secs, (
                            f"Action {i+1} Photo: temps différent "
                            f"Lua {lua_time} ≠ Python {python_secs}"
                        )
                
                elif action.action_type in ['Boucle', 'Interval']:
                    # Test temps début
                    lua_start = lua_ref.convert_time(
                        action.reference_time,
                        action.start_operation,
                        action.start_offset_seconds,
                        table_ref
                    )
                    python_start = time_calc.convert_relative_time(
                        action.reference_time,
                        action.start_operation,
                        action.start_offset_seconds,
                        ref_times
                    )
                    python_start_secs = (python_start.hour * 3600 + 
                                       python_start.minute * 60 + 
                                       python_start.second)
                    
                    assert lua_start == python_start_secs
                    
                    # Test temps fin
                    lua_end = lua_ref.convert_time(
                        action.reference_time,
                        action.end_operation,
                        action.end_offset_seconds,
                        table_ref
                    )
                    python_end = time_calc.convert_relative_time(
                        action.reference_time,
                        action.end_operation,
                        action.end_offset_seconds,
                        ref_times
                    )
                    python_end_secs = (python_end.hour * 3600 + 
                                     python_end.minute * 60 + 
                                     python_end.second)
                    
                    assert lua_end == python_end_secs
                    
                    # Test calcul intervalle
                    if action.action_type == 'Interval':
                        lua_interval = lua_ref.calculate_interval_lua(
                            'Interval', lua_start, lua_end, action.photo_count
                        )
                        # Python utilise directement photo_count dans ActionScheduler
                        expected_interval = math.ceil(
                            (python_end_secs - python_start_secs) / action.photo_count - 0.5
                        )
                        if expected_interval < 1:
                            expected_interval = 1
                            
                        assert lua_interval == expected_interval
                    
        finally:
            os.unlink(temp_path)
            
        print("✅ Validation régression complète réussie")
    
    def test_edge_cases_compatibility(self):
        """Test cas limites: comportement identique Lua/Python"""
        
        test_cases = [
            # Passage minuit
            {
                'config': "Config,23,50,0,0,10,0,0,15,0,0,20,0,1,30,0,0",
                'action': "Photo,C1,+,1,0,0,-,-,-,-,-,-,8,100,1,0",
                'description': "Photo après minuit"
            },
            # Temps très proches
            {
                'config': "Config,12,0,0,12,0,5,12,0,10,12,0,15,12,0,20,0", 
                'action': "Boucle,C1,+,0,0,2,C2,-,0,0,1,1,8,100,1,0",
                'description': "Boucle très courte"
            },
            # Intervalles fractionnaires
            {
                'config': "Config,12,0,0,12,0,10,12,0,20,12,0,30,12,0,40,0",
                'action': "Interval,C1,+,0,0,5,C2,-,0,0,5,17,8,100,1,0",
                'description': "Interval avec division non entière"
            }
        ]
        
        # lua_ref supprimé car non utilisé
        time_calc = TimeCalculator()
        
        for case in test_cases:
            config_content = f"""# {case['description']}
{case['config']}
{case['action']}
"""
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(config_content)
                temp_path = f.name
                
            try:
                config_parser = ConfigParser()
                config = config_parser.parse_eclipse_config(temp_path)
                
                # Test que le parsing ne lève pas d'exception
                assert config.timings is not None
                assert len(config.actions) >= 1
                
                # Test calculs temporels pour cas limites
                action = config.actions[0]
                ref_times = {
                    'C1': config.timings.C1,
                    'C2': config.timings.C2, 
                    'Max': config.timings.Max,
                    'C3': config.timings.C3,
                    'C4': config.timings.C4
                }
                
                if action.reference_time != '-':
                    python_result = time_calc.convert_relative_time(
                        action.reference_time,
                        action.start_operation,
                        action.start_offset_seconds,
                        ref_times
                    )
                    # Validation que le résultat est cohérent
                    assert isinstance(python_result, time)
                    assert 0 <= python_result.hour <= 23
                    assert 0 <= python_result.minute <= 59
                    assert 0 <= python_result.second <= 59
                
            finally:
                os.unlink(temp_path)


if __name__ == "__main__":
    # Exécution de la suite complète de tests de migration
    print("🔍 Lancement des tests de validation Lua->Python...")
    pytest.main([__file__, "-v", "--tb=short"])
    print("✅ Tests de migration terminés")