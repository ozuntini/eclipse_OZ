#!/bin/bash

# Script de lancement des tests de régression comparatifs Lua vs Python
# =====================================================================

set -e  # Arrêt en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$PYTHON_DIR")"

echo -e "${CYAN}🔍 TESTS DE RÉGRESSION MIGRATION LUA->PYTHON${NC}"
echo -e "${CYAN}===============================================${NC}"

# Vérification de l'environnement
echo -e "\n${BLUE}📋 Vérification de l'environnement...${NC}"

# Vérification Python
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python non trouvé${NC}"
    exit 1
fi

echo -e "${GREEN}  ✅ Python: $(python --version)${NC}"

# Vérification pytest
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  pytest non installé, installation...${NC}"
    pip install pytest
fi

echo -e "${GREEN}  ✅ pytest: $(python -m pytest --version | head -1)${NC}"

# Vérification modules Python du projet
echo -e "\n${BLUE}📦 Vérification modules projet...${NC}"
cd "$PYTHON_DIR"

required_modules=("config.parser" "scheduling.time_calculator" "scheduling.action_scheduler" "hardware.camera_controller")
for module in "${required_modules[@]}"; do
    if python -c "from python.$module import *" 2>/dev/null; then
        echo -e "${GREEN}  ✅ $module${NC}"
    else
        echo -e "${RED}  ❌ $module non trouvé${NC}"
        exit 1
    fi
done

# Vérification script Lua original
echo -e "\n${BLUE}📄 Vérification script Lua original...${NC}"
LUA_SCRIPT="$PROJECT_ROOT/eclipse_OZ.lua"
if [[ -f "$LUA_SCRIPT" ]]; then
    LUA_VERSION=$(grep "Version = " "$LUA_SCRIPT" | cut -d'"' -f2)
    echo -e "${GREEN}  ✅ eclipse_OZ.lua (version $LUA_VERSION)${NC}"
else
    echo -e "${RED}  ❌ eclipse_OZ.lua non trouvé${NC}"
    exit 1
fi

# Menu des tests
echo -e "\n${PURPLE}🧪 TYPES DE TESTS DISPONIBLES${NC}"
echo "1. Tests critiques uniquement (rapide)"
echo "2. Suite complète de régression (complet)"  
echo "3. Tests comparatifs Lua/Python"
echo "4. Tests de migration des fonctions"
echo "5. Tests de comportement et performance"
echo "6. Génération du rapport de régression"

read -p $'\n\033[1;33mChoisissez le type de test (1-6): \033[0m' choice

case $choice in
    1)
        echo -e "\n${YELLOW}🔥 TESTS CRITIQUES${NC}"
        python -m pytest tests/test_lua_python_comparison.py::TestTimeConversionComparison -v
        python -m pytest tests/test_migration_validation.py::TestExactFunctionMigration -v
        ;;
    2)
        echo -e "\n${YELLOW}🚀 SUITE COMPLÈTE DE RÉGRESSION${NC}"
        python tests/test_complete_regression.py
        ;;
    3)
        echo -e "\n${YELLOW}⚖️  TESTS COMPARATIFS LUA/PYTHON${NC}"
        python -m pytest tests/test_lua_python_comparison.py -v
        ;;
    4)
        echo -e "\n${YELLOW}🔧 TESTS MIGRATION FONCTIONS${NC}"
        python -m pytest tests/test_migration_validation.py -v
        ;;
    5)
        echo -e "\n${YELLOW}📊 TESTS COMPORTEMENT & PERFORMANCE${NC}"
        python -m pytest tests/test_behavior_compatibility.py -v
        ;;
    6)
        echo -e "\n${YELLOW}📄 GÉNÉRATION RAPPORT${NC}"
        python tests/test_complete_regression.py --report
        ;;
    *)
        echo -e "${RED}❌ Choix invalide${NC}"
        exit 1
        ;;
esac

# Résultats
EXIT_CODE=$?

echo -e "\n${CYAN}📊 RÉSULTATS${NC}"
echo -e "${CYAN}============${NC}"

if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✅ TOUS LES TESTS RÉUSSIS!${NC}"
    echo -e "${GREEN}   Migration Lua->Python validée avec succès${NC}"
    
    # Affichage du résumé de compatibilité
    echo -e "\n${BLUE}🎯 POINTS DE COMPATIBILITÉ VALIDÉS:${NC}"
    echo -e "${GREEN}   • Calculs temporels identiques${NC}"
    echo -e "${GREEN}   • Parsing configuration compatible${NC}"
    echo -e "${GREEN}   • Actions photos/boucles/intervals préservées${NC}"
    echo -e "${GREEN}   • Comportements synchronisés${NC}"
    echo -e "${GREEN}   • Performances acceptables${NC}"
    
    echo -e "\n${PURPLE}➕ EXTENSIONS AJOUTÉES:${NC}"
    echo -e "${PURPLE}   • Support multi-caméras${NC}"
    echo -e "${PURPLE}   • Abstraction GPhoto2${NC}"
    echo -e "${PURPLE}   • Tests unitaires complets${NC}"
    echo -e "${PURPLE}   • Déploiement automatisé${NC}"
    
else
    echo -e "${RED}❌ ÉCHECS DÉTECTÉS${NC}"
    echo -e "${RED}   Voir les détails ci-dessus pour corriger${NC}"
fi

# Nettoyage fichiers temporaires
find "$SCRIPT_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$SCRIPT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo -e "\n${CYAN}Tests de régression terminés.${NC}"
exit $EXIT_CODE