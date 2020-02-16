#!/usr/bin/env bash

repQemu="/Users/olivierzuntini/Documents/Projects/qemu-eos"

if [ "$1" == "" ] || [ -d "$1" ]; then
    echo "usage: MLua_PIC.sh Nom_du_script"
    exit
else
    nameScript=$1
fi

echo "Intégration du script : " $nameScript "et lancement de ML."

echo "-> Déplacement dans le répertoir Qemu-eos"
cd $repQemu

echo "-> Montage de la pseudo carte SD"
./mount.sh

echo "-> Copie du script sur la carte 1"
cp /Users/olivierzuntini/Documents/Projects/MagicLantern/ML_Eclipse/$nameScript /Volumes/EOS_DIGITAL/ML/scripts/

echo "-> Copie du script sur la carte 2"
cp /Users/olivierzuntini/Documents/Projects/MagicLantern/ML_Eclipse/$nameScript /Volumes/EOS_DIGITA1/ML/scripts/

echo "-> Fermeture des cartes 1 et 2"
hdiutil detach "/Volumes/EOS_DIGITAL"
hdiutil detach "/Volumes/EOS_DIGITA1"

echo "-> Démarrage de l'émulation ML"
./run_canon_fw.sh 6D,firmware="boot=1"

echo "-> Retour sur le répertoire initial"
cd -

echo "Fin du script d'intégration automatique."