#!/usr/bin/env bash
#Copie du fichier sur la carte SD et démontage de celle-ci

if [ "$1" == "" ] || [ -d "$1" ]; then
    echo "usage: MLua_Test.sh Nom_du_script"
    exit
else
    nameScript=$1
fi

if [ -d /Volumes/EOS_DIGITAL ]; then
    echo "Carte SD EOS_DIGITAL présente."
else
    echo "Installer la carte SD EOS_DIGITAL"
    exit 1
fi

echo "Copie du script : " $nameScript "sur la carte SD."

cp /Users/olivierzuntini/Documents/Projects/MagicLantern/ML_Eclipse/$nameScript /Volumes/EOS_DIGITAL/ML/scripts/
echo "-> Script :" $nameScript "copié sur la carte."
echo "-> Nettoyage du log"
echo `date`"---- Nouvelle version du script ! -----------------------------" >> /Volumes/EOS_DIGITAL/ECLIPSE.LOG

echo "-> Démontage de la carte."
hdiutil detach "/Volumes/EOS_DIGITAL"

echo "Fin du script vous pouvez retirer la carte."