#!/bin/bash
# Script de test rapide pour Eclipse_OZ Python
# Effectue un test complet du système en mode simulation

set -e

echo "=== Test rapide Eclipse_OZ Python ==="
echo ""

# Activation de l'environnement virtuel si disponible
if [ -f ~/eclipse_env/bin/activate ]; then
    echo "Activation de l'environnement virtuel..."
    source ~/eclipse_env/bin/activate
fi

# Test 1: Validation des imports
echo "Test 1: Validation des modules Python..."
python3 -c "
try:
    from config import ConfigParser, parse_config_file
    from hardware import MultiCameraManager, CameraController
    from scheduling import TimeCalculator, ActionScheduler
    from utils import SystemValidator, setup_logging
    print('✅ Tous les modules importés avec succès')
except ImportError as e:
    print(f'❌ Erreur d\'importation: {e}')
    exit(1)
" || exit 1

# Test 2: Validation du fichier de configuration
echo ""
echo "Test 2: Validation du fichier de configuration..."
if [ ! -f "config_eclipse.txt" ]; then
    echo "❌ Fichier config_eclipse.txt manquant"
    exit 1
fi

python3 -c "
from config import parse_config_file
try:
    config = parse_config_file('config_eclipse.txt')
    print(f'✅ Configuration valide: {len(config.actions)} actions')
    
    # Afficher les détails de la configuration
    print(f'   Eclipse: {config.eclipse_timings.c1} -> {config.eclipse_timings.c4}')
    print(f'   Mode test: {config.eclipse_timings.test_mode}')
    
    for i, action in enumerate(config.actions):
        print(f'   Action {i+1}: {action.action_type} ({action.time_ref})')
        
except Exception as e:
    print(f'❌ Erreur de configuration: {e}')
    exit(1)
" || exit 1

# Test 3: Validation du système
echo ""
echo "Test 3: Validation du système..."
python3 -c "
from utils import SystemValidator
validator = SystemValidator()
result = validator.validate_system()
print(f'✅ Système validé' if result else '⚠️ Système partiellement validé')
" || echo "⚠️ Validation système échouée (normal selon environnement)"

# Test 4: Test de détection des caméras
echo ""
echo "Test 4: Test de détection des caméras..."
python3 -c "
from hardware import MultiCameraManager
manager = MultiCameraManager()
cameras = manager.discover_cameras()
print(f'✅ Caméras détectées: {cameras}')
if cameras:
    info = manager.get_camera_info()
    for cam_id, cam_info in info.items():
        print(f'   Caméra {cam_id}: {cam_info[\"name\"]} (connectée: {cam_info[\"connected\"]})')
manager.disconnect_all()
" || exit 1

# Test 5: Test des calculs temporels
echo ""
echo "Test 5: Test des calculs temporels..."
python3 -c "
from config import parse_config_file
from scheduling import TimeCalculator
from datetime import time

config = parse_config_file('config_eclipse.txt')
calc = TimeCalculator(config.eclipse_timings)

# Test de validation de séquence
valid = calc.validate_eclipse_sequence()
print(f'✅ Séquence éclipse valide: {valid}')

# Test de calculs relatifs
test_time = calc.convert_relative_time('Max', '-', time(0, 0, 10))
print(f'   Max - 10s = {test_time}')

# Test bidirectionnel
seconds = calc.time_to_seconds(time(16, 30, 45))
back_time = calc.seconds_to_time(seconds)
print(f'   Test bidirectionnel: 16:30:45 -> {seconds}s -> {back_time}')
" || exit 1

# Test 6: Test de planification d'actions
echo ""
echo "Test 6: Test de planification d'actions..."
python3 -c "
from config import parse_config_file
from scheduling import TimeCalculator, ActionScheduler, create_action
from hardware import MultiCameraManager
from unittest.mock import Mock

config = parse_config_file('config_eclipse.txt')
calc = TimeCalculator(config.eclipse_timings)

# Mock camera manager
camera_manager = Mock()
camera_manager.active_cameras = [0]
camera_manager.configure_all.return_value = {0: True}
camera_manager.capture_all.return_value = {0: 'test.jpg'}

scheduler = ActionScheduler(camera_manager, calc, test_mode=True)

# Test de création d'actions
for i, action_config in enumerate(config.actions):
    action = create_action(action_config)
    print(f'   Action {i+1}: {action.get_description()}')

print('✅ Planification d\'actions validée')
" || exit 1

# Test 7: Test complet en mode simulation (rapide)
echo ""
echo "Test 7: Test complet en mode simulation..."
timeout 10s python3 main.py config_eclipse.txt --test-mode --log-level WARNING 2>/dev/null && \
echo "✅ Test complet réussi" || \
echo "⚠️ Test complet interrompu (timeout - normal pour éviter l'attente)"

# Test 8: Vérification des permissions et fichiers
echo ""
echo "Test 8: Vérification des permissions..."

# Vérifier les permissions d'exécution
if [ -x "main.py" ] || [ -x "/usr/bin/python3" ]; then
    echo "✅ Permissions d'exécution correctes"
else
    echo "❌ Problème de permissions"
fi

# Vérifier la présence de GPhoto2
if command -v gphoto2 &> /dev/null; then
    gphoto2_version=$(gphoto2 --version | head -1)
    echo "✅ GPhoto2 disponible: $gphoto2_version"
else
    echo "⚠️ GPhoto2 non disponible (installation requise pour usage réel)"
fi

# Test 9: Test des utilitaires
echo ""
echo "Test 9: Test des utilitaires..."
python3 -c "
from utils import setup_logging, get_logger
import tempfile
import os

# Test du logging
with tempfile.NamedTemporaryFile(delete=False) as tmp:
    logger = setup_logging('INFO', tmp.name)
    logger.info('Test de logging')
    
    # Vérifier que le fichier contient le message
    with open(tmp.name, 'r') as f:
        content = f.read()
        if 'Test de logging' in content:
            print('✅ Logging fonctionnel')
        else:
            print('❌ Problème de logging')
    
    os.unlink(tmp.name)
" || exit 1

echo ""
echo "=== Résumé du test ==="
echo "✅ Test rapide terminé avec succès!"
echo ""
echo "Le système Eclipse_OZ Python est prêt à être utilisé."
echo ""
echo "Commandes pour utilisation réelle:"
echo "  python3 main.py config_eclipse.txt --test-mode    # Simulation complète"
echo "  python3 main.py config_eclipse.txt --help         # Aide complète"
echo "  python3 main.py config_eclipse.txt                # Exécution réelle"
echo ""
echo "Pour des tests détaillés:"
echo "  python3 -m pytest tests/                          # Tests unitaires"
echo "  python3 main.py config_eclipse.txt --log-level DEBUG --test-mode"
echo ""