#!/bin/bash
# Script de déploiement pour Eclipse_OZ Python sur Raspberry Pi
# Usage: ./deploy.sh pi@192.168.1.100

set -e

# Configuration
PI_ADDRESS=${1:-"pi@raspberrypi.local"}
REMOTE_DIR="eclipse_oz_python"
LOG_FILE="deploy.log"

echo "=== Déploiement Eclipse_OZ Python ==="
echo "Destination: $PI_ADDRESS"
echo "Répertoire distant: $REMOTE_DIR"
echo ""

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

# Vérification des prérequis locaux
log "Vérification des prérequis locaux..."

if ! command -v rsync &> /dev/null; then
    log "ERREUR: rsync n'est pas installé"
    exit 1
fi

if ! command -v ssh &> /dev/null; then
    log "ERREUR: ssh n'est pas installé"
    exit 1
fi

# Test de connexion SSH
log "Test de connexion SSH vers $PI_ADDRESS..."
if ! ssh -o ConnectTimeout=10 $PI_ADDRESS "echo 'Connexion SSH réussie'" &> /dev/null; then
    log "ERREUR: Impossible de se connecter à $PI_ADDRESS"
    log "Vérifiez l'adresse et les clés SSH"
    exit 1
fi

log "Connexion SSH confirmée"

# Synchronisation des fichiers
log "Synchronisation des fichiers..."

# Exclure les fichiers inutiles
EXCLUDES=(
    "--exclude=.git/"
    "--exclude=__pycache__/"
    "--exclude=.pytest_cache/"
    "--exclude=*.pyc"
    "--exclude=.venv/"
    "--exclude=venv/"
    "--exclude=*.log"
    "--exclude=.coverage"
    "--exclude=htmlcov/"
    "--exclude=.mypy_cache/"
)

rsync -avz --progress "${EXCLUDES[@]}" ./ $PI_ADDRESS:$REMOTE_DIR/

if [ $? -eq 0 ]; then
    log "Synchronisation réussie"
else
    log "ERREUR: Échec de la synchronisation"
    exit 1
fi

# Installation/mise à jour sur le Pi
log "Installation sur le Raspberry Pi..."

ssh $PI_ADDRESS << 'EOF'
set -e

cd eclipse_oz_python

echo "=== Installation Eclipse_OZ sur Raspberry Pi ==="

# Rendre le script d'installation exécutable
chmod +x install.sh

# Exécuter l'installation
./install.sh

echo ""
echo "=== Test de l'installation ==="

# Activer l'environnement virtuel
source ~/eclipse_env/bin/activate

# Test d'importation des modules
python3 -c "
try:
    from config import ConfigParser
    from hardware import MultiCameraManager
    from scheduling import TimeCalculator
    print('✅ Tous les modules importés avec succès')
except ImportError as e:
    print(f'❌ Erreur d\'importation: {e}')
    exit(1)
"

# Test de détection des caméras
echo ""
echo "Test de détection des caméras:"
gphoto2 --auto-detect || echo "Aucune caméra détectée (normal si pas de caméra connectée)"

# Test du script principal en mode aide
echo ""
echo "Test du script principal:"
python3 main.py --help

echo ""
echo "✅ Installation terminée avec succès!"
echo ""
echo "Pour utiliser Eclipse_OZ:"
echo "  source ~/eclipse_env/bin/activate"
echo "  python3 main.py config_eclipse.txt --test-mode"

EOF

if [ $? -eq 0 ]; then
    log "Installation sur Pi réussie"
else
    log "ERREUR: Échec de l'installation sur Pi"
    exit 1
fi

# Test final depuis la machine locale
log "Test final de déploiement..."

ssh $PI_ADDRESS "cd $REMOTE_DIR && source ~/eclipse_env/bin/activate && python3 -c 'import sys; print(f\"Python {sys.version}\"); from config import ConfigParser; print(\"✅ Eclipse_OZ prêt\")'"

if [ $? -eq 0 ]; then
    log "✅ Déploiement terminé avec succès!"
    echo ""
    echo "Eclipse_OZ Python est maintenant installé sur $PI_ADDRESS"
    echo ""
    echo "Commandes pour l'utiliser:"
    echo "  ssh $PI_ADDRESS"
    echo "  cd $REMOTE_DIR"
    echo "  source ~/eclipse_env/bin/activate"
    echo "  python3 main.py config_eclipse.txt --test-mode"
    echo ""
    echo "Logs de déploiement: $LOG_FILE"
else
    log "❌ Échec du test final"
    exit 1
fi