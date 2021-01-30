#!/usr/bin/env bash
#Script de montage des images des cartes SD pour Qemu et de copie d'un fichier
#Testé uniquement sur Mac

repQemu="/Users/olivierzuntini/Documents/Projects/qemu-eos"

if [ "$1" == "" ] || [ -d "$1" ] || [ "$1" == "-h" ] || [ "$#" -lt 2 ]; then
    echo "usage: MLua_mount_imgSD.sh <Modèle> <Nom_du_script>"
    echo "       6D ou 60D"
    echo "       script.schedule"
    exit
else
    if [ $1 != "6D" ] && [ $1 != "60D" ]; then
        echo $1" n'est pas un modèle connu"
        exit 1
    else
        model=$1
    fi
    if [ -s "$2" ]; then
        dirScript=`pwd`
        nameScript=$2
    else
        echo "Fichier "$2" introuvable !"
        exit 2
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

echo "-> Activation de la pseudo carte du modèle :"$model
cp -v ./sd-$model.img ./sd.img
cp -v ./cf-$model.img ./cf.img

echo "-> Montage de la pseudo carte SD"
./mount.sh

echo "-> Copie du script " $nameScript " sur la carte 1"
cp $dirScript'/'$nameScript /Volumes/EOS_DIGITAL/ML/scripts/

echo "-> Copie du script " $nameScript " sur la carte 2"
cp $dirScript'/'$nameScript /Volumes/EOS_DIGITA1/ML/scripts/

echo "-> Fermeture des cartes 1 et 2"
hdiutil detach "/Volumes/EOS_DIGITAL"
hdiutil detach "/Volumes/EOS_DIGITA1"

echo "-> Sauvegarde de la pseudo carte du modèle :"$model
cp -v ./sd.img ./sd-$model.img
cp -v ./cf.img ./cf-$model.img

echo "-> Retour sur le répertoire initial"
cd -

echo "Fin du script de copie."