#!/usr/bin/env bash
#Script de montage des images des cartes SD pour Qemu et de copie d'un fichier

repQemu="/Users/olivierzuntini/Documents/Projects/qemu-eos"

if [ "$1" == "" ] || [ -d "$1" ] || [ "$1" == "-h" ]; then
    echo "usage: MLua_PIC.sh Nom_du_fichier"
    exit
else
    if [ -s "$1" ]; then
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

echo "Montage des images de SD : et copie de " $nameScript "."

echo "-> Déplacement dans le répertoir Qemu-eos"
cd $repQemu

echo "-> Montage de la pseudo carte SD"
./mount.sh

echo "-> Copie du script " $nameScript " sur la carte 1"
cp /Users/olivierzuntini/Documents/Projects/MagicLantern/ML_Eclipse/"$nameScript" /Volumes/EOS_DIGITAL/ML/scripts/

echo "-> Copie du script " $nameScript " sur la carte 2"
cp /Users/olivierzuntini/Documents/Projects/MagicLantern/ML_Eclipse/"$nameScript" /Volumes/EOS_DIGITA1/ML/scripts/

echo "-> Fermeture des cartes 1 et 2"
hdiutil detach "/Volumes/EOS_DIGITAL"
hdiutil detach "/Volumes/EOS_DIGITA1"

echo "-> Retour sur le répertoire initial"
cd -

echo "Fin du script de copie."