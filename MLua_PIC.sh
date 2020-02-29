#!/usr/bin/env bash
#Script de copie du script Lua sur les pseudo SD Qemu et lancement du virtualiseur

repQemu="/Users/olivierzuntini/Documents/Projects/qemu-eos"

if [ "$1" == "" ] || [ -d "$1" ] || [ "$1" == "-h" ]; then
    echo "usage: MLua_PIC.sh Nom_du_script [-log]"
    echo "       -log récupération des .LOG"
    exit
else
    if [ -s "$1" ]; then
        if [ -n "$2" ] && [ "$2" == "-log" ]; then
            recupLog="1"
        else
            recupLog="0"
        fi
        nameScript=$1
    else
        echo "Fichier "$1" introuvable !"
        exit 1
    fi
fi

if [ -d /Volumes/EOS_DIGITAL ]; then
    echo "Carte SD EOS_DIGITAL présente."
    echo "Veuillez la démonter."
    exit 1
fi

echo "Intégration du script : " $nameScript "et lancement de ML."

echo "-> Déplacement dans le répertoir Qemu-eos"
cd $repQemu

echo "-> Montage de la pseudo carte SD"
./mount.sh

echo "-> Copie du script sur la carte 1"
cp /Users/olivierzuntini/Documents/Projects/MagicLantern/ML_Eclipse/$nameScript /Volumes/EOS_DIGITAL/ML/scripts/

echo "-> Nettoyage du log carte 1"
echo `date`"---- Nouvelle version du script ! -----------------------------" >> /Volumes/EOS_DIGITAL/ECLIPSE.LOG

echo "-> Copie du script sur la carte 2"
cp /Users/olivierzuntini/Documents/Projects/MagicLantern/ML_Eclipse/$nameScript /Volumes/EOS_DIGITA1/ML/scripts/

echo "-> Nettoyage du log carte 2"
echo `date`"---- Nouvelle version du script ! -----------------------------" >> /Volumes/EOS_DIGITA1/ECLIPSE.LOG

echo "-> Fermeture des cartes 1 et 2"
hdiutil detach "/Volumes/EOS_DIGITAL"
hdiutil detach "/Volumes/EOS_DIGITA1"

echo "-> Démarrage de l'émulation ML"
./run_canon_fw.sh 6D,firmware="boot=1"

if [ "$recupLog" == "1" ]; then
    echo "-> Montage de la pseudo carte SD"
    ./mount.sh
    echo "-> Recup du .LOG"
    cp /Volumes/EOS_DIGITAL/*.LOG /Users/olivierzuntini/Documents/Projects/MagicLantern/ML_Eclipse/tmp/SD0/
    echo "-> Recup du .LOG"
    cp /Volumes/EOS_DIGITA1/*.LOG /Users/olivierzuntini/Documents/Projects/MagicLantern/ML_Eclipse/tmp/SD1/
    echo "-> Fermeture des cartes 1 et 2"
    hdiutil detach "/Volumes/EOS_DIGITAL"
    hdiutil detach "/Volumes/EOS_DIGITA1"
fi

echo "-> Retour sur le répertoire initial"
cd -

echo "Fin du script d'intégration automatique."