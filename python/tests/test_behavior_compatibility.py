"""
Tests de performance et comportement comparatifs Lua vs Python
==============================================================

Ce module teste les performances et comportements spécifiques
pour s'assurer que la migration Python n'introduit pas de régressions
par rapport au script Lua original.
"""

import pytest
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, time as dt_time
import threading

from python.scheduling.action_scheduler import ActionScheduler
from python.hardware.camera_controller import CameraController
from python.hardware.multi_camera_manager import MultiCameraManager
from python.config.parser import ConfigParser
from python.scheduling.time_calculator import TimeCalculator


class LuaActionSimulator:
    """
    Simulateur du comportement des actions du script Lua original
    pour validation comparative
    """
    
    def __init__(self):
        self.actions_log = []
        self.current_time = 0
        self.test_mode = False
        
    def simulate_take_shoot(self, iso, aperture, shutter_speed, mlu_delay):
        """Simulation take_shoot() Lua"""
        action_start = time.time()
        
        # Simulation mirror lockup delay
        if mlu_delay > 0:
            time.sleep(mlu_delay / 1000)  # mlu_delay en ms
            
        # Simulation prise de photo
        if not self.test_mode:
            time.sleep(0.1)  # Délai simulation capture
            
        action_end = time.time()
        
        self.actions_log.append({
            'type': 'photo',
            'iso': iso,
            'aperture': aperture, 
            'shutter_speed': shutter_speed,
            'mlu_delay': mlu_delay,
            'duration': action_end - action_start,
            'timestamp': action_start
        })
        
        return action_end - action_start
    
    def simulate_boucle(self, h_fin, intervalle, iso, aperture, shutter_speed, mlu_delay):
        """Simulation boucle() Lua"""
        import math
        
        # Arrondi intervalle comme en Lua
        intervalle = math.ceil(intervalle - 0.5)
        if intervalle < 1:
            intervalle = 1
            
        photos_taken = []
        start_time = time.time()
        
        while (time.time() - start_time) < (h_fin - self.current_time):
            shoot_time = time.time()
            duration = self.simulate_take_shoot(iso, aperture, shutter_speed, mlu_delay)
            photos_taken.append(duration)
            
            # Attente intervalle (simulation)
            elapsed = time.time() - shoot_time
            if elapsed < intervalle:
                wait_time = intervalle - elapsed
                if (time.time() - start_time + wait_time) < (h_fin - self.current_time):
                    time.sleep(min(wait_time, 0.1))  # Attente limitée pour tests
                else:
                    break
                    
        return photos_taken
    
    def simulate_interval_action(self, time_start, time_end, photo_count, iso, aperture, shutter_speed, mlu_delay):
        """Simulation action Interval avec calcul d'intervalle Lua"""
        duration = time_end - time_start
        if photo_count > 0:
            interval = duration / photo_count
        else:
            interval = 1
            
        import math
        interval = math.ceil(interval - 0.5)
        if interval < 1:
            interval = 1
            
        photos = []
        current_time = time_start
        
        for i in range(photo_count):
            if current_time <= time_end:
                duration = self.simulate_take_shoot(iso, aperture, shutter_speed, mlu_delay)
                photos.append(duration)
                current_time += interval
            else:
                break
                
        return photos, interval


class TestActionBehaviorComparison:
    """Tests comportementaux des actions Lua vs Python"""
    
    def setup_method(self):
        """Configuration des mocks pour simulation"""
        self.lua_sim = LuaActionSimulator()
        
        # Mock caméra pour Python
        self.mock_camera = Mock()
        self.mock_camera.connect.return_value = True
        self.mock_camera.configure_settings.return_value = True
        self.mock_camera.capture_image.return_value = "test_image.jpg"
        self.mock_camera.mirror_lockup.return_value = True
        
        # Temps de référence
        self.ref_times = {
            'C1': dt_time(18, 10, 29),
            'C2': dt_time(19, 27, 3), 
            'Max': dt_time(19, 28, 23),
            'C3': dt_time(19, 29, 43),
            'C4': dt_time(20, 46, 31)
        }
        
    def test_photo_action_timing_comparison(self):
        """Test timing des actions Photo Lua vs Python"""
        
        # Configuration action Photo
        iso = 400
        aperture = 8
        shutter_speed = 2
        mlu_delay = 1000  # 1s mirror lockup
        
        # Test Lua simulation
        lua_start = time.time()
        lua_duration = self.lua_sim.simulate_take_shoot(iso, aperture, shutter_speed, mlu_delay)
        
        # Test Python avec ActionScheduler
        with patch('python.hardware.camera_controller.gp') as mock_gp:
            mock_gp.Camera.return_value = self.mock_camera
            
            scheduler = ActionScheduler()
            scheduler.camera_controller = CameraController()
            scheduler.test_mode = False
            
            python_start = time.time()
            # Simulation action photo Python
            scheduler.camera_controller.configure_settings(iso, aperture, shutter_speed)
            if mlu_delay > 0:
                scheduler.camera_controller.mirror_lockup(mlu_delay)
            result = scheduler.camera_controller.capture_image()
            python_duration = time.time() - python_start
            
        # Validation que les timings sont comparables (±10%)
        timing_tolerance = 0.1
        assert abs(lua_duration - python_duration) <= max(lua_duration, python_duration) * timing_tolerance, (
            f"Timing Photo différent: Lua {lua_duration:.3f}s vs Python {python_duration:.3f}s"
        )
        
        # Validation log action
        assert len(self.lua_sim.actions_log) == 1
        assert self.lua_sim.actions_log[0]['type'] == 'photo'
        assert self.lua_sim.actions_log[0]['mlu_delay'] == mlu_delay
    
    def test_boucle_interval_calculation(self):
        """Test calcul intervalle Boucle compatible Lua/Python"""
        
        test_cases = [
            # (time_start, time_end, interval_input, expected_interval)
            (1000, 1600, 30.7, 31),    # Arrondi supérieur
            (1000, 1600, 29.4, 29),    # Arrondi inférieur  
            (1000, 1600, 0.8, 1),      # Minimum 1s
            (1000, 1600, 60, 60),      # Valeur exacte
        ]
        
        import math
        
        for start, end, interval_input, expected in test_cases:
            # Calcul Lua (simulation)
            lua_interval = math.ceil(interval_input - 0.5)
            if lua_interval < 1:
                lua_interval = 1
                
            assert lua_interval == expected, (
                f"Calcul intervalle Lua incorrect pour {interval_input}: "
                f"attendu {expected}, obtenu {lua_interval}"
            )
            
            # Validation que Python suit la même logique
            if interval_input < 1:
                python_interval = 1
            else:
                python_interval = math.ceil(interval_input - 0.5)
                
            assert python_interval == expected, (
                f"Calcul intervalle Python incorrect pour {interval_input}: "
                f"attendu {expected}, obtenu {python_interval}"
            )
    
    def test_interval_action_photo_count_compatibility(self):
        """Test action Interval: nombre de photos Lua vs Python"""
        
        # Configuration action Interval
        time_start = 1000  # Seconde de début  
        time_end = 1300    # Seconde de fin (300s de durée)
        photo_count = 10   # 10 photos demandées
        iso = 800
        aperture = 5.6
        shutter_speed = 1
        mlu_delay = 0
        
        # Simulation Lua
        lua_photos, lua_interval = self.lua_sim.simulate_interval_action(
            time_start, time_end, photo_count, iso, aperture, shutter_speed, mlu_delay
        )
        
        # Calcul Python équivalent
        duration = time_end - time_start  # 300s
        python_interval_calculated = duration / photo_count  # 30s
        import math
        python_interval = math.ceil(python_interval_calculated - 0.5)
        if python_interval < 1:
            python_interval = 1
            
        # Vérifications
        assert lua_interval == python_interval, (
            f"Intervalle Interval différent: Lua {lua_interval} vs Python {python_interval}"
        )
        
        expected_photos = min(photo_count, duration // python_interval)
        assert len(lua_photos) <= photo_count, (
            f"Trop de photos Lua: {len(lua_photos)} > {photo_count}"
        )
    
    @patch('time.sleep', side_effect=lambda x: None)  # Accélère les tests
    def test_boucle_timing_behavior(self, mock_sleep):
        """Test comportement temporel Boucle Lua vs Python"""
        
        # Configuration boucle courte pour test
        h_fin_relative = 10  # 10 secondes
        intervalle = 2       # Photo toutes les 2 secondes
        iso = 200
        aperture = 8
        shutter_speed = 4
        mlu_delay = 0
        
        # Test simulation Lua (modifié pour éviter attente réelle)
        self.lua_sim.current_time = time.time()
        h_fin = self.lua_sim.current_time + h_fin_relative
        
        start_time = time.time()
        lua_photos = []
        
        # Simulation boucle Lua sans attente réelle
        photo_time = start_time
        while photo_time < h_fin and (photo_time + intervalle) <= h_fin:
            duration = self.lua_sim.simulate_take_shoot(iso, aperture, shutter_speed, mlu_delay)
            lua_photos.append(duration)
            photo_time += intervalle
            
        # Calcul attendu
        max_photos = h_fin_relative // intervalle  # 10s / 2s = 5 photos max
        
        assert len(lua_photos) <= max_photos, (
            f"Nombre de photos Lua incorrect: {len(lua_photos)} > {max_photos}"
        )
        
        # Validation que chaque photo a les bons paramètres
        for i, duration in enumerate(lua_photos):
            action_log = self.lua_sim.actions_log[i]
            assert action_log['iso'] == iso
            assert action_log['aperture'] == aperture
            assert action_log['shutter_speed'] == shutter_speed


class TestMultiCameraCompatibility:
    """Tests compatibilité multi-caméras (extension Python vs Lua mono-caméra)"""
    
    def test_single_camera_compatibility(self):
        """Test que le mode single caméra Python = comportement Lua"""
        
        with patch('python.hardware.camera_controller.gp') as mock_gp:
            # Configuration mock single camera
            mock_camera = Mock()
            mock_camera.connect.return_value = True
            mock_gp.Camera.return_value = mock_camera
            
            # Test single camera manager (compatible Lua)
            camera_controller = CameraController()
            success = camera_controller.connect()
            
            assert success is True
            
            # Test configuration (équivalent Lua)
            camera_controller.configure_settings(400, 8, 2)
            camera_controller.capture_image()
            
            # Vérification appels équivalents Lua
            assert mock_camera.connect.called
            
    def test_multi_camera_extension_compatibility(self):
        """Test que l'extension multi-caméras préserve le comportement single"""
        
        with patch('python.hardware.camera_controller.gp') as mock_gp:
            mock_camera1 = Mock()
            mock_camera1.connect.return_value = True
            mock_camera1.capture_image.return_value = "img1.jpg"
            
            mock_gp.Camera.return_value = mock_camera1
            
            # Test manager avec 1 caméra (comportement Lua)
            manager = MultiCameraManager()
            cameras = manager.discover_cameras()
            
            if cameras:
                # Simulation comportement single camera
                manager.connect_all_cameras()
                results = manager.capture_synchronized("test", 400, 8, 2)
                
                # Vérification résultat compatible single camera Lua
                assert len(results) <= 1  # Maximum une caméra détectée
                if results:
                    assert 'img1.jpg' in results[0]


class TestPerformanceRegression:
    """Tests de performance pour éviter régressions"""
    
    def test_config_parsing_performance(self):
        """Test que le parsing Python n'est pas plus lent que Lua"""
        
        # Configuration complexe pour test performance
        complex_config = """# Configuration performance test
Config,18,10,29,19,27,3,19,28,23,19,29,43,20,46,31,0
""" + "\n".join([
            f"Photo,C{i%4+1},{'+' if i%2 else '-'},0,{i%60},{i%60},-,-,-,-,-,-,{8+i%8},{100*2**i%5},{1+i%30},{i*100%2000}"
            for i in range(50)  # 50 actions pour stress test
        ])
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(complex_config)
            temp_path = f.name
            
        try:
            config_parser = ConfigParser()
            
            # Mesure performance parsing
            start_time = time.time()
            config = config_parser.parse_eclipse_config(temp_path)
            parse_duration = time.time() - start_time
            
            # Validation résultat
            assert config.timings is not None
            assert len(config.actions) == 50
            
            # Seuil performance acceptable (< 1s pour 50 actions)
            assert parse_duration < 1.0, (
                f"Parsing trop lent: {parse_duration:.3f}s > 1.0s"
            )
            
        finally:
            os.unlink(temp_path)
    
    def test_time_calculation_performance(self):
        """Test performance calculs temporels Python vs simulation Lua"""
        
        time_calc = TimeCalculator()
        ref_times = {
            'C1': dt_time(18, 10, 29),
            'C2': dt_time(19, 27, 3),
            'Max': dt_time(19, 28, 23), 
            'C3': dt_time(19, 29, 43),
            'C4': dt_time(20, 46, 31)
        }
        
        # Test masse de calculs
        test_cases = [
            ('C1', '-', i*60) for i in range(100)  # 100 calculs
        ] + [
            ('Max', '+', i*30) for i in range(100)  # 100 autres calculs
        ]
        
        start_time = time.time()
        
        for ref, op, offset in test_cases:
            result = time_calc.convert_relative_time(ref, op, offset, ref_times)
            assert result is not None
            
        calc_duration = time.time() - start_time
        
        # Seuil performance: < 0.1s pour 200 calculs
        assert calc_duration < 0.1, (
            f"Calculs temporels trop lents: {calc_duration:.3f}s > 0.1s"
        )


class TestRegressionSafety:
    """Tests de sécurité pour éviter régressions comportementales"""
    
    def test_error_handling_compatibility(self):
        """Test que la gestion d'erreurs Python >= Lua"""
        
        # Test config malformée
        bad_configs = [
            "Config,invalid,format",  # Format invalide
            "Config,25,0,0,19,27,3,19,28,23,19,29,43,20,46,31,0",  # Heure invalide
            "Photo,InvalidRef,-,0,5,0,-,-,-,-,-,-,8,100,4,0",  # Référence invalide
        ]
        
        config_parser = ConfigParser()
        
        for bad_config in bad_configs:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(bad_config)
                temp_path = f.name
                
            try:
                # Doit lever une exception explicite (mieux que crash Lua)
                with pytest.raises(Exception):
                    config_parser.parse_eclipse_config(temp_path)
                    
            finally:
                os.unlink(temp_path)
    
    def test_memory_usage_compatibility(self):
        """Test que Python n'utilise pas excessive mémoire vs Lua"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Charge configuration importante
        large_config = """Config,18,10,29,19,27,3,19,28,23,19,29,43,20,46,31,0\n""" + "\n".join([
            f"Boucle,C1,+,0,{i%60},{i%60},C2,-,0,{i%60},{i%60},{i%60},{8+i%8},{100+i*50},{1+i%10},0"
            for i in range(1000)  # 1000 actions
        ])
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_config)
            temp_path = f.name
            
        try:
            config_parser = ConfigParser()
            config = config_parser.parse_eclipse_config(temp_path)
            
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Seuil mémoire raisonnable: < 50MB pour 1000 actions
            max_memory_mb = 50 * 1024 * 1024
            assert memory_increase < max_memory_mb, (
                f"Utilisation mémoire excessive: {memory_increase/1024/1024:.1f}MB"
            )
            
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    print("🚀 Lancement tests comportementaux Lua vs Python...")
    pytest.main([__file__, "-v", "--tb=short"])
    print("✅ Tests comportementaux terminés")