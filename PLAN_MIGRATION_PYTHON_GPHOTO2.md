# Plan de Migration : Eclipse_OZ de Lua/Magic Lantern vers Python/GPhoto2/Raspberry Pi

## CONTEXTE DE LA MIGRATION

**Situation actuelle :**
- Script Lua `eclipse_OZ.lua` exécuté sur Magic Lantern (firmware alternatif Canon)
- Contrôle d'UN SEUL appareil photo Canon via APIs Magic Lantern
- Séquences de prises de vue planifiées pour éclipses solaires
- Fichier de configuration `SOLARECL.TXT` format CSV-like

**Objectif de migration :**
- Migrer vers Python sur Raspberry Pi
- Contrôler PLUSIEURS appareils photo simultanément
- Utiliser obligatoirement la librairie **python-gphoto2**
- Maintenir toutes les fonctionnalités existantes

## ANALYSE DU CODE EXISTANT

### Fonctionnalités critiques à préserver :

1. **Système de planification temporelle**
   - Heures absolues (HH:MM:SS) et relatives (C1, C2, Max, C3, C4)
   - Conversions temps relatifs/absolus
   - Attente synchronisée jusqu'aux moments de déclenchement

2. **Types d'actions photographiques**
   - `Photo` : prise unique
   - `Boucle` : séries avec intervalle fixe
   - `Interval` : nombre de photos sur durée donnée

3. **Paramètres photographiques**
   - ISO, ouverture, vitesse d'obturation
   - Mirror lockup avec délai configurable
   - Mode test (simulation sans déclenchement)

4. **Vérifications et sécurités**
   - État batterie, espace stockage, mode appareil, autofocus
   - Logging détaillé des opérations

5. **Format de configuration**
   - Parsing du fichier `SOLARECL.TXT`
   - Lignes `Config`, `Verif`, `Photo`, `Boucle`, `Interval`

### Dépendances Magic Lantern à remplacer :

```lua
-- APIs à remplacer par GPhoto2 :
camera.iso.value = iso                    --> gp.gp_widget_set_value(iso_widget, str(iso))
camera.aperture.value = aperture          --> gp.gp_widget_set_value(aperture_widget, aperture_str)
camera.shutter.value = shutter_speed      --> gp.gp_widget_set_value(shutter_widget, shutter_str)
camera.shoot(false)                       --> gp.gp_camera_capture(camera, gp.GP_CAPTURE_IMAGE)

-- État appareil :
camera.mode                               --> gp.gp_camera_get_config() + parsing
lens.af                                   --> gp.gp_widget_get_value(af_widget)
battery.level                             --> gp.gp_widget_get_value(battery_widget)
dryos.shooting_card.free_space           --> os.statvfs() sur point de montage

-- Temps et interface :
dryos.date                                --> datetime.datetime.now()
display.notify_box()                      --> print() ou interface GPIO/LCD
key.wait()                                --> input() ou handler GPIO
```

## ARCHITECTURE DE LA NOUVELLE SOLUTION

### Structure du projet Python :

```
eclipse_oz_python/
├── main.py                              # Point d'entrée principal
├── config/
│   ├── __init__.py
│   ├── config_parser.py                 # Parser SOLARECL.TXT + validation
│   └── eclipse_config.py                # Classes de configuration
├── hardware/
│   ├── __init__.py
│   ├── camera_controller.py             # Abstraction GPhoto2
│   ├── multi_camera_manager.py          # Gestion plusieurs appareils
│   └── hardware_detection.py            # Détection auto appareils
├── scheduling/
│   ├── __init__.py
│   ├── time_calculator.py               # Conversions temporelles
│   ├── action_scheduler.py              # Planification et exécution
│   └── action_types.py                  # Classes Photo/Boucle/Interval
├── utils/
│   ├── __init__.py
│   ├── logger.py                        # Logging centralisé
│   ├── validation.py                    # Vérifications état
│   └── constants.py                     # Constantes et mappings
├── tests/
│   ├── __init__.py
│   ├── test_config_parser.py
│   ├── test_time_calculator.py
│   ├── test_camera_controller.py
│   └── test_integration.py
├── requirements.txt                     # Dépendances Python
├── config_eclipse.txt                   # Fichier config (rename)
└── README.md
```

## PLAN DE MIGRATION DÉTAILLÉ

### Phase 1 : Configuration de l'environnement (PRIORITÉ HAUTE)

**Tâches :**

1. **Installation dépendances sur Raspberry Pi**
```bash
# Installation GPhoto2 et bindings Python
sudo apt update
sudo apt install -y gphoto2 libgphoto2-dev python3-pip
pip3 install gphoto2 python-dateutil pyyaml
```

2. **Test détection multi-caméras**
```python
# Créer script test_detection.py
import gphoto2 as gp
import logging

def detect_cameras():
    cameras = []
    camera_list = gp.gp_camera_autodetect()
    for index, (name, addr) in enumerate(camera_list):
        camera = gp.gp_camera_new()
        gp.gp_camera_set_port_info(camera, gp.gp_port_info_list_get_info(port_info_list, gp.gp_port_info_list_lookup_path(port_info_list, addr)))
        cameras.append({'id': index, 'name': name, 'address': addr, 'camera': camera})
    return cameras
```

**Critères de validation :**
- [ ] GPhoto2 détecte tous les appareils connectés
- [ ] Connexion/déconnexion stable
- [ ] Pas de conflit USB/ressources

### Phase 2 : Parser de configuration (PRIORITÉ HAUTE)

**Tâche : Migrer la logique de `read_script()` et `read_config()`**

```python
# config/config_parser.py
import csv
from datetime import datetime, time
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class EclipseTimings:
    c1: time  # Premier contact
    c2: time  # Début totalité
    max: time # Maximum
    c3: time  # Fin totalité  
    c4: time  # Dernier contact
    test_mode: bool

@dataclass
class ActionConfig:
    action_type: str  # 'Photo', 'Boucle', 'Interval'
    time_ref: str     # 'C1', 'C2', 'Max', 'C3', 'C4', '-'
    start_operator: str  # '+', '-'
    start_time: time
    end_operator: str    # '+', '-' (pour Boucle/Interval)
    end_time: time       # (pour Boucle/Interval)
    interval_or_count: float  # secondes ou nombre
    aperture: float
    iso: int
    shutter_speed: float
    mlu_delay: int      # millisecondes

class ConfigParser:
    def parse_eclipse_config(self, filename: str) -> Dict[str, Any]:
        """Parse SOLARECL.TXT format"""
        config = {
            'verification': None,
            'eclipse_timings': None,
            'actions': []
        }
        
        with open(filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Split par ',' ET ':' comme dans le Lua original
                fields = []
                for field in line.split(','):
                    if ':' in field and len(field.split(':')) == 3:
                        # Time field HH:MM:SS
                        fields.append(field)
                    else:
                        fields.append(field)
                
                if fields[0] == 'Verif':
                    config['verification'] = self._parse_verification(fields)
                elif fields[0] == 'Config':
                    config['eclipse_timings'] = self._parse_config(fields)
                elif fields[0] in ['Photo', 'Boucle', 'Interval']:
                    config['actions'].append(self._parse_action(fields))
                    
        return config
```

**Critères de validation :**
- [ ] Parse correctement toutes les lignes de SOLARECL.TXT
- [ ] Validation des formats temps (HH:MM:SS)
- [ ] Gestion erreurs avec numéros de ligne
- [ ] Tests unitaires avec fichiers valides/invalides

### Phase 3 : Calculateur temporel (PRIORITÉ HAUTE)

**Tâche : Migrer `convert_second()`, `convert_time()`, `pretty_time()`**

```python
# scheduling/time_calculator.py
from datetime import datetime, time, timedelta
from typing import Optional

class TimeCalculator:
    def __init__(self, eclipse_timings: EclipseTimings):
        self.eclipse_timings = eclipse_timings
        
    def time_to_seconds(self, t: time) -> int:
        """Équivalent convert_second() du Lua"""
        return t.hour * 3600 + t.minute * 60 + t.second
    
    def seconds_to_time(self, seconds: int) -> time:
        """Équivalent pretty_time() du Lua"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return time(hours % 24, minutes, secs)
    
    def convert_relative_time(self, reference: str, operator: str, offset_time: time) -> time:
        """Équivalent convert_time() du Lua"""
        ref_times = {
            'C1': self.eclipse_timings.c1,
            'C2': self.eclipse_timings.c2,
            'Max': self.eclipse_timings.max,
            'C3': self.eclipse_timings.c3,
            'C4': self.eclipse_timings.c4
        }
        
        if reference not in ref_times:
            raise ValueError(f"Référence inconnue: {reference}")
            
        ref_seconds = self.time_to_seconds(ref_times[reference])
        offset_seconds = self.time_to_seconds(offset_time)
        
        if operator == '+':
            result_seconds = (ref_seconds + offset_seconds) % 86400
        elif operator == '-':
            result_seconds = (ref_seconds - offset_seconds) % 86400
        else:
            raise ValueError(f"Opérateur invalide: {operator}")
            
        return self.seconds_to_time(result_seconds)
    
    def wait_until(self, target_time: time, check_interval: float = 0.25):
        """Attente active jusqu'à l'heure cible"""
        import time as time_module
        
        while True:
            now = datetime.now().time()
            now_seconds = self.time_to_seconds(now)
            target_seconds = self.time_to_seconds(target_time)
            
            # Gestion passage minuit
            if target_seconds < now_seconds:
                target_seconds += 86400
                
            if now_seconds >= target_seconds:
                break
                
            remaining = target_seconds - now_seconds
            if remaining > 20:  # Affichage toutes les 20s si longue attente
                print(f"Attente: {remaining}s jusqu'à {target_time}")
                
            time_module.sleep(check_interval)
```

**Critères de validation :**
- [ ] Conversion temps bidirectionnelle exacte
- [ ] Calculs relatifs corrects pour tous les contacts (C1-C4)
- [ ] Gestion passage minuit
- [ ] Tests avec cas limites (23:59:59, 00:00:01)

### Phase 4 : Contrôleur caméra GPhoto2 (PRIORITÉ CRITIQUE)

**Tâche : Remplacer toutes les APIs Magic Lantern**

```python
# hardware/camera_controller.py
import gphoto2 as gp
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class CameraSettings:
    iso: int
    aperture: str      # "f/8", "f/11", etc.
    shutter: str       # "1/125", "2", etc.
    
@dataclass  
class CameraStatus:
    battery_level: Optional[int]
    free_space_mb: Optional[int]
    mode: str
    af_enabled: bool

class CameraController:
    def __init__(self, camera_id: int = 0):
        self.camera = None
        self.camera_id = camera_id
        self.logger = logging.getLogger(f'camera_{camera_id}')
        
    def connect(self) -> bool:
        """Connexion à l'appareil"""
        try:
            self.camera = gp.gp_camera_new()
            gp.gp_camera_init(self.camera)
            self.logger.info(f"Caméra {self.camera_id} connectée")
            return True
        except gp.GPhoto2Error as e:
            self.logger.error(f"Erreur connexion caméra {self.camera_id}: {e}")
            return False
            
    def disconnect(self):
        """Déconnexion propre"""
        if self.camera:
            gp.gp_camera_exit(self.camera)
            
    def get_status(self) -> CameraStatus:
        """Équivalent des vérifications ML"""
        config = gp.gp_camera_get_config(self.camera)
        
        # Batterie (si supportée)
        battery = None
        try:
            battery_widget = gp.gp_widget_get_child_by_name(config, 'batterylevel')[1]
            battery = int(gp.gp_widget_get_value(battery_widget))
        except:
            pass
            
        # Mode appareil
        mode = "Unknown"
        try:
            mode_widget = gp.gp_widget_get_child_by_name(config, 'capturetarget')[1]
            mode = gp.gp_widget_get_value(mode_widget)
        except:
            pass
            
        # AF status
        af_enabled = False
        try:
            af_widget = gp.gp_widget_get_child_by_name(config, 'autofocus')[1]
            af_enabled = gp.gp_widget_get_value(af_widget) == 'On'
        except:
            pass
            
        return CameraStatus(battery, None, mode, af_enabled)
    
    def configure_settings(self, settings: CameraSettings) -> bool:
        """Configuration ISO/Ouverture/Vitesse"""
        try:
            config = gp.gp_camera_get_config(self.camera)
            
            # ISO
            iso_widget = gp.gp_widget_get_child_by_name(config, 'iso')[1]
            gp.gp_widget_set_value(iso_widget, str(settings.iso))
            
            # Ouverture 
            aperture_widget = gp.gp_widget_get_child_by_name(config, 'f-number')[1]
            gp.gp_widget_set_value(aperture_widget, settings.aperture)
            
            # Vitesse
            shutter_widget = gp.gp_widget_get_child_by_name(config, 'shutterspeed')[1]
            gp.gp_widget_set_value(shutter_widget, settings.shutter)
            
            # Application de la config
            gp.gp_camera_set_config(self.camera, config)
            
            self.logger.info(f"Configuration: ISO {settings.iso}, f/{settings.aperture}, {settings.shutter}s")
            return True
            
        except gp.GPhoto2Error as e:
            self.logger.error(f"Erreur configuration: {e}")
            return False
    
    def capture_image(self, test_mode: bool = False) -> Optional[str]:
        """Prise de photo - équivalent camera.shoot()"""
        if test_mode:
            self.logger.info("TEST MODE: Photo simulée")
            return "test_image.jpg"
            
        try:
            file_path = gp.gp_camera_capture(self.camera, gp.GP_CAPTURE_IMAGE)
            self.logger.info(f"Photo capturée: {file_path.folder}/{file_path.name}")
            return f"{file_path.folder}/{file_path.name}"
            
        except gp.GPhoto2Error as e:
            self.logger.error(f"Erreur capture: {e}")
            return None
    
    def mirror_lockup(self, enabled: bool, delay_ms: int = 0):
        """Gestion du relevé de miroir si supporté"""
        # Implementation spécifique selon modèles Canon
        # Certains modèles via "eosremoterelease", d'autres via "bulb"
        if enabled and delay_ms > 0:
            self.logger.info(f"Mirror lockup activé, délai: {delay_ms}ms")
            # TODO: Implementation selon modèle détecté
        else:
            self.logger.info("Mirror lockup désactivé")
```

**Critères de validation :**
- [ ] Connexion stable à 1 appareil Canon
- [ ] Configuration ISO/Ouverture/Vitesse fonctionnelle
- [ ] Capture d'image réussie
- [ ] Gestion des erreurs GPhoto2
- [ ] Test avec plusieurs modèles Canon différents

### Phase 5 : Gestionnaire multi-caméras (PRIORITÉ MOYENNE)

**Tâche : Extension pour contrôle simultané**

```python
# hardware/multi_camera_manager.py
from typing import List, Dict
import threading
import time
from .camera_controller import CameraController, CameraSettings

class MultiCameraManager:
    def __init__(self):
        self.cameras: Dict[int, CameraController] = {}
        self.active_cameras: List[int] = []
        
    def discover_cameras(self) -> List[int]:
        """Détection automatique des appareils"""
        camera_list = gp.gp_camera_autodetect()
        camera_ids = []
        
        for index, (name, addr) in enumerate(camera_list):
            controller = CameraController(index)
            if controller.connect():
                self.cameras[index] = controller
                camera_ids.append(index)
                self.logger.info(f"Caméra {index} détectée: {name}")
            
        self.active_cameras = camera_ids
        return camera_ids
    
    def configure_all(self, settings: CameraSettings) -> Dict[int, bool]:
        """Configuration simultanée de tous les appareils"""
        results = {}
        for camera_id in self.active_cameras:
            results[camera_id] = self.cameras[camera_id].configure_settings(settings)
        return results
    
    def capture_all(self, test_mode: bool = False) -> Dict[int, Optional[str]]:
        """Capture simultanée - mode parallèle"""
        results = {}
        threads = []
        
        def capture_single(camera_id):
            results[camera_id] = self.cameras[camera_id].capture_image(test_mode)
        
        # Lancement parallèle
        for camera_id in self.active_cameras:
            thread = threading.Thread(target=capture_single, args=(camera_id,))
            threads.append(thread)
            thread.start()
        
        # Attente de toutes les captures
        for thread in threads:
            thread.join()
            
        return results
    
    def get_all_status(self) -> Dict[int, CameraStatus]:
        """Status de tous les appareils"""
        status = {}
        for camera_id in self.active_cameras:
            status[camera_id] = self.cameras[camera_id].get_status()
        return status
```

### Phase 6 : Scheduleur d'actions (PRIORITÉ HAUTE)

**Tâche : Migrer `do_action()`, `boucle()`, `take_shoot()`**

```python
# scheduling/action_scheduler.py
from typing import List
import time
import logging
from datetime import datetime

class ActionScheduler:
    def __init__(self, camera_manager, time_calculator, test_mode=False):
        self.camera_manager = camera_manager
        self.time_calculator = time_calculator
        self.test_mode = test_mode
        self.logger = logging.getLogger('scheduler')
        
    def execute_photo_action(self, action: ActionConfig):
        """Équivalent action Photo du Lua"""
        # Calcul heure de déclenchement
        if action.time_ref == '-':
            # Mode absolu
            trigger_time = action.start_time
        else:
            # Mode relatif
            trigger_time = self.time_calculator.convert_relative_time(
                action.time_ref, action.start_operator, action.start_time
            )
        
        # Configuration caméras
        settings = CameraSettings(
            iso=action.iso,
            aperture=f"f/{action.aperture}",
            shutter=self._format_shutter(action.shutter_speed)
        )
        
        self.camera_manager.configure_all(settings)
        
        # Gestion MLU si nécessaire
        if action.mlu_delay > 0:
            for camera_id in self.camera_manager.active_cameras:
                self.camera_manager.cameras[camera_id].mirror_lockup(True, action.mlu_delay)
        
        # Attente jusqu'à l'heure de déclenchement
        self.time_calculator.wait_until(trigger_time)
        
        # Capture
        self.logger.info(f"Déclenchement photo à {trigger_time}")
        results = self.camera_manager.capture_all(self.test_mode)
        
        # Log résultats
        for camera_id, result in results.items():
            if result:
                self.logger.info(f"Caméra {camera_id}: {result}")
            else:
                self.logger.error(f"Caméra {camera_id}: Échec capture")
    
    def execute_loop_action(self, action: ActionConfig):
        """Équivalent action Boucle du Lua"""
        # Calculs heures début/fin
        start_time = self._calculate_action_time(action, 'start')
        end_time = self._calculate_action_time(action, 'end')
        
        # Configuration caméras
        settings = CameraSettings(
            iso=action.iso,
            aperture=f"f/{action.aperture}",
            shutter=self._format_shutter(action.shutter_speed)
        )
        self.camera_manager.configure_all(settings)
        
        # Attente début
        self.time_calculator.wait_until(start_time)
        
        self.logger.info(f"Début boucle: {start_time} -> {end_time}, intervalle: {action.interval_or_count}s")
        
        # Boucle de captures
        next_shot_time = datetime.now().time()
        while self._time_to_seconds(datetime.now().time()) < self._time_to_seconds(end_time):
            # Capture toutes caméras
            results = self.camera_manager.capture_all(self.test_mode)
            
            # Calcul prochaine prise
            next_shot_seconds = self._time_to_seconds(next_shot_time) + action.interval_or_count
            next_shot_time = self.time_calculator.seconds_to_time(int(next_shot_seconds))
            
            # Attente intervalle
            while (self._time_to_seconds(datetime.now().time()) < next_shot_seconds and 
                   next_shot_seconds < self._time_to_seconds(end_time)):
                time.sleep(0.5)
        
        self.logger.info("Fin de boucle")
    
    def execute_interval_action(self, action: ActionConfig):
        """Équivalent action Interval du Lua"""
        start_time = self._calculate_action_time(action, 'start')
        end_time = self._calculate_action_time(action, 'end')
        
        # Calcul intervalle = durée totale / nombre de photos
        total_duration = self._time_to_seconds(end_time) - self._time_to_seconds(start_time)
        interval = total_duration / action.interval_or_count
        
        self.logger.info(f"Interval: {action.interval_or_count} photos sur {total_duration}s = intervalle {interval}s")
        
        # Utilisation logique boucle avec intervalle calculé
        modified_action = action
        modified_action.interval_or_count = interval
        self.execute_loop_action(modified_action)
```

### Phase 7 : Point d'entrée principal (PRIORITÉ MOYENNE)

```python
# main.py
#!/usr/bin/env python3
import argparse
import logging
from pathlib import Path

from config.config_parser import ConfigParser
from hardware.multi_camera_manager import MultiCameraManager
from scheduling.time_calculator import TimeCalculator
from scheduling.action_scheduler import ActionScheduler
from utils.logger import setup_logging
from utils.validation import SystemValidator

def main():
    parser = argparse.ArgumentParser(description='Eclipse Photography Controller')
    parser.add_argument('config_file', help='Fichier de configuration (ex: SOLARECL.TXT)')
    parser.add_argument('--test-mode', action='store_true', help='Mode simulation')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--cameras', nargs='+', type=int, help='IDs spécifiques des caméras à utiliser')
    
    args = parser.parse_args()
    
    # Configuration logging
    setup_logging(args.log_level)
    logger = logging.getLogger('main')
    
    logger.info("=== Eclipse Photography Controller v3.0 ===")
    logger.info(f"Mode test: {args.test_mode}")
    
    try:
        # 1. Parse configuration
        parser = ConfigParser()
        config = parser.parse_eclipse_config(args.config_file)
        logger.info(f"Configuration chargée: {len(config['actions'])} actions")
        
        # 2. Validation système
        validator = SystemValidator()
        if not validator.validate_system():
            logger.error("Validation système échouée")
            return 1
        
        # 3. Initialisation caméras
        camera_manager = MultiCameraManager()
        detected_cameras = camera_manager.discover_cameras()
        
        if not detected_cameras:
            logger.error("Aucune caméra détectée")
            return 1
            
        logger.info(f"Caméras détectées: {detected_cameras}")
        
        if args.cameras:
            # Filtrer selon IDs spécifiés
            camera_manager.active_cameras = [c for c in detected_cameras if c in args.cameras]
        
        # 4. Vérification configuration si demandée
        if config['verification']:
            validator.validate_cameras(camera_manager, config['verification'])
        
        # 5. Initialisation calculateur temps et scheduleur
        time_calc = TimeCalculator(config['eclipse_timings'])
        scheduler = ActionScheduler(camera_manager, time_calc, args.test_mode)
        
        # 6. Exécution séquence
        logger.info("Début d'exécution de la séquence")
        for i, action in enumerate(config['actions']):
            logger.info(f"=== Action {i+1}/{len(config['actions'])}: {action.action_type} ===")
            
            if action.action_type == 'Photo':
                scheduler.execute_photo_action(action)
            elif action.action_type == 'Boucle':
                scheduler.execute_loop_action(action)
            elif action.action_type == 'Interval':
                scheduler.execute_interval_action(action)
        
        logger.info("Séquence terminée avec succès")
        return 0
        
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        return 1
    
    finally:
        # Nettoyage
        if 'camera_manager' in locals():
            camera_manager.disconnect_all()

if __name__ == "__main__":
    exit(main())
```

### Phase 8 : Tests et validation (PRIORITÉ HAUTE)

**Tests unitaires critiques :**

```python
# tests/test_time_calculator.py
import unittest
from datetime import time
from scheduling.time_calculator import TimeCalculator
from config.eclipse_config import EclipseTimings

class TestTimeCalculator(unittest.TestCase):
    def setUp(self):
        self.timings = EclipseTimings(
            c1=time(14, 41, 5),
            c2=time(16, 2, 49), 
            max=time(16, 3, 53),
            c3=time(16, 4, 58),
            c4=time(17, 31, 3),
            test_mode=False
        )
        self.calc = TimeCalculator(self.timings)
    
    def test_time_to_seconds(self):
        """Test conversion HH:MM:SS vers secondes"""
        self.assertEqual(self.calc.time_to_seconds(time(1, 0, 0)), 3600)
        self.assertEqual(self.calc.time_to_seconds(time(0, 1, 0)), 60)
        self.assertEqual(self.calc.time_to_seconds(time(0, 0, 1)), 1)
    
    def test_relative_time_addition(self):
        """Test C2 + 00:01:00"""
        result = self.calc.convert_relative_time('C2', '+', time(0, 1, 0))
        expected = time(16, 3, 49)
        self.assertEqual(result, expected)
    
    def test_relative_time_subtraction(self):
        """Test C2 - 00:20:00"""
        result = self.calc.convert_relative_time('C2', '-', time(0, 20, 0))
        expected = time(15, 42, 49)
        self.assertEqual(result, expected)
    
    def test_midnight_crossing(self):
        """Test passage minuit"""
        # C4 + 7h devrait donner 00:31:03 le jour suivant
        result = self.calc.convert_relative_time('C4', '+', time(7, 0, 0))
        expected = time(0, 31, 3)
        self.assertEqual(result, expected)

# tests/test_config_parser.py  
class TestConfigParser(unittest.TestCase):
    def test_parse_valid_config(self):
        """Test parsing fichier valide"""
        # Test avec contenu SOLARECL.TXT réel
        
    def test_parse_invalid_time_format(self):
        """Test gestion erreurs format temps"""
        
    def test_parse_missing_fields(self):
        """Test gestion champs manquants"""

# tests/test_integration.py
class TestIntegration(unittest.TestCase):
    def test_full_sequence_test_mode(self):
        """Test séquence complète en mode test"""
        # Simulation sans déclenchement réel
```

## DÉPLOIEMENT ET CONFIGURATION RASPBERRY PI

### Configuration système recommandée :

```bash
# Installation complète sur Raspberry Pi
sudo apt update && sudo apt upgrade -y

# Dépendances système
sudo apt install -y python3-pip python3-venv git
sudo apt install -y gphoto2 libgphoto2-dev libgphoto2-port12

# Création environnement virtuel
python3 -m venv ~/eclipse_env
source ~/eclipse_env/bin/activate

# Installation dépendances Python
pip install gphoto2 python-dateutil pyyaml

# Configuration USB pour multi-caméras
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="04a9", MODE="0666"' | sudo tee /etc/udev/rules.d/99-canon-cameras.rules
sudo udevadm control --reload-rules

# Test détection
gphoto2 --auto-detect
```

### Script de lancement automatique :

```bash
#!/bin/bash
# start_eclipse.sh
cd /home/pi/eclipse_oz_python
source ~/eclipse_env/bin/activate

# Vérification caméras connectées
echo "Vérification des caméras..."
python3 -c "from hardware.multi_camera_manager import MultiCameraManager; mgr = MultiCameraManager(); print(f'Caméras détectées: {mgr.discover_cameras()}')"

# Lancement avec config par défaut
echo "Lancement séquence éclipse..."
python3 main.py config_eclipse.txt --log-level INFO

echo "Séquence terminée. Logs disponibles dans eclipse.log"
```

## PLAN DE TEST ET VALIDATION

### Tests par phase :

**Phase 1-2 (Configuration + Parser) :**
- [ ] Parse correctement SOLARECL.TXT existant
- [ ] Validation champs obligatoires
- [ ] Gestion erreurs format

**Phase 3 (Calculateur temps) :**
- [ ] Conversion temps bidirectionnelle
- [ ] Calculs relatifs exact vs fichier Lua original  
- [ ] Test passage minuit

**Phase 4 (Contrôleur caméra) :**
- [ ] Connexion Canon via GPhoto2
- [ ] Configuration ISO/Ouverture/Vitesse
- [ ] Capture photo réussie
- [ ] Gestion erreurs connexion

**Phase 5 (Multi-caméras) :**
- [ ] Détection de 2+ appareils simultanément
- [ ] Configuration synchronisée
- [ ] Capture parallèle fonctionnelle

**Phase 6-7 (Scheduleur + Main) :**
- [ ] Test mode simulation complet
- [ ] Exécution action Photo en temps réel
- [ ] Exécution boucle courte (5 photos / 10s)
- [ ] Logs détaillés équivalents au Lua

**Test final :**
- [ ] Séquence éclipse complète en mode test
- [ ] Validation timing précis (< 1s de dérive)
- [ ] Gestion déconnexion/reconnexion caméra
- [ ] Test durée longue (> 1h de séquence)

## MIGRATION DES FICHIERS DE CONFIGURATION

### Conversion format SOLARECL.TXT :

Le format existant reste **compatible** mais peut être enrichi :

```
# Ancien format (maintenu)
Config,20:20:30,20:25:05,20:26:15,20:27:55,20:30:03,1
Photo,Max,-,00:00:10,-,-,-,-,-,4,1600,1,500

# Nouveau format étendu (optionnel)
Config,C1=20:20:30,C2=20:25:05,Max=20:26:15,C3=20:27:55,C4=20:30:03,TestMode=1
Photo,time_ref=Max,start_offset=-00:00:10,camera_ids=[0,1,2],iso=1600,aperture=4,shutter=1,mlu=500
```

### Migration des scripts bash :

```python
# Équivalent MLua_Test.sh en Python
# deploy_to_pi.py
import subprocess
import shutil
from pathlib import Path

def deploy_to_raspberry_pi(pi_address: str, config_file: str):
    """Déploiement sur Raspberry Pi via SSH"""
    
    # Copie fichiers
    subprocess.run([
        'rsync', '-av', 
        '--exclude=tests/', 
        '--exclude=__pycache__/',
        './', 
        f'pi@{pi_address}:~/eclipse_oz_python/'
    ])
    
    # Installation/mise à jour sur Pi
    subprocess.run([
        'ssh', f'pi@{pi_address}',
        'cd ~/eclipse_oz_python && source ~/eclipse_env/bin/activate && pip install -r requirements.txt'
    ])
    
    print(f"Déployé sur {pi_address}")

if __name__ == "__main__":
    deploy_to_raspberry_pi('192.168.1.100', 'config_eclipse.txt')
```

## CHECKLIST DE MIGRATION FINALE

### Fonctionnalités Lua à valider dans Python :

- [ ] **Parser configuration** : lecture SOLARECL.TXT identique
- [ ] **Conversion temps** : calculs relatifs exacts (C1, C2, Max, C3, C4)
- [ ] **Actions photographiques** :
  - [ ] Photo unique avec timing précis
  - [ ] Boucle avec intervalle fixe
  - [ ] Interval avec nombre de photos sur durée
- [ ] **Paramètres caméra** : ISO, ouverture, vitesse d'obturation
- [ ] **Mirror lockup** : délai configurable
- [ ] **Mode test** : simulation sans déclenchement
- [ ] **Vérifications** : batterie, espace libre, mode caméra
- [ ] **Logging** : traçabilité complète équivalente

### Extensions multi-caméras :

- [ ] **Détection auto** : tous les appareils Canon USB
- [ ] **Configuration synchronisée** : paramètres identiques sur tous
- [ ] **Capture parallèle** : déclenchement simultané (< 100ms)
- [ ] **Gestion erreurs** : isolation des défaillances par appareil
- [ ] **Configuration individuelle** : paramètres spécifiques par caméra si nécessaire

### Performance et robustesse :

- [ ] **Timing précis** : dérive < 1s sur séquences longues (> 2h)
- [ ] **Récupération erreurs** : reconnexion auto après déconnexion USB
- [ ] **Ressources système** : utilisation CPU/mémoire acceptable sur Pi
- [ ] **Logging rotatif** : éviter saturation stockage sur longues séquences

---

## ESTIMATION EFFORT ET TIMELINE

**Phase 1-2 (Config + Parser)** : 3-5 jours
**Phase 3 (Calculateur temps)** : 2-3 jours  
**Phase 4 (Contrôleur caméra)** : 5-7 jours ⚠️ CRITIQUE
**Phase 5 (Multi-caméras)** : 3-4 jours
**Phase 6-7 (Scheduleur + Main)** : 4-5 jours
**Phase 8 (Tests + Validation)** : 5-6 jours
**Documentation et déploiement** : 2-3 jours

**TOTAL ESTIMÉ : 24-33 jours**

La **Phase 4** est la plus critique car elle dépend entièrement de la compatibilité GPhoto2 avec les modèles Canon utilisés. Il est essentiel de valider cette phase avec le matériel réel avant de procéder aux phases suivantes.

**Recommandation** : Commencer par un prototype minimal des Phases 1-4 pour validation matérielle avant développement complet.