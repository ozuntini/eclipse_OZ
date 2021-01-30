#!/usr/bin/env bash
#Script de copie du script Lua sur les pseudo SD Qemu et lancement du virtualiseur
#Utilisation de l'émulation Qemu avec ML https://bitbucket.org/hudson/magic-lantern/src/qemu/contrib/qemu/README.rst
#Testé uniquement sur Mac

repQemu="/Users/olivierzuntini/Documents/Projects/qemu-eos"

if [ "$1" == "" ] || [ -d "$1" ] || [ "$1" == "-h" ] || [ "$#" -lt 2 ]; then
    echo "usage: MLua_PIC.sh <Modèle> <Nom_du_script> [-log]"
    echo "       6D ou 60D"
    echo "       script.lua"
    echo "       -log récupération des .LOG"
    exit
else
    if [ $1 != "6D" ] && [ $1 != "60D" ]; then
        echo $1" n'est pas un modèle connu"
        exit 1
    else
        model=$1
    fi
    if [ -s "$2" ]; then
        if [ -n "$3" ] && [ "$3" == "-log" ]; then
            recupLog="1"
        else
            recupLog="0"
        fi
        dirScript=`pwd`
        nameScript=$2
    else
        echo "Fichier "$2" introuvable !"
        exit 2
    fi
fi

nameLog=`grep "LoggingFilename =" $nameScript | cut -d \" -f2 | tr '[:lower:]' '[:upper:]'`
echo "Fichier log = "$nameLog

if [ -d /Volumes/EOS_DIGITAL ]; then
    echo "Carte SD EOS_DIGITAL présente."
    echo "Veuillez la démonter."
    exit 1
fi

echo "Intégration du script : " $nameScript "et lancement de ML."

echo "-> Déplacement dans le répertoir Qemu-eos"
cd $repQemu

echo "-> Activation de la pseudo carte du modèle :"$model
cp -v ./sd-$model.img ./sd.img
cp -v ./cf-$model.img ./cf.img

echo "-> Montage de la pseudo carte SD"
./mount.sh

echo "-> Copie du script sur la carte 1"
cp $dirScript'/'$nameScript /Volumes/EOS_DIGITAL/ML/scripts/

if [ -n $nameLog ]; then
    echo "-> Nettoyage du log carte 1 : "$nameLog
    echo -e "\n"`date`"---- Nouvelle version du script ! -----------------------------" >> /Volumes/EOS_DIGITAL/$nameLog
fi

echo "-> Copie du script sur la carte 2"
cp $dirScript'/'$nameScript /Volumes/EOS_DIGITA1/ML/scripts/

if [ -n $nameLog ]; then
    echo "-> Nettoyage du log carte 2 : "$nameLog
    echo -e "\n"`date`"---- Nouvelle version du script ! -----------------------------" >> /Volumes/EOS_DIGITA1/$nameLog
fi

sleep 5
echo "-> Fermeture des cartes 1 et 2"
hdiutil detach "/Volumes/EOS_DIGITAL"

hdiutil detach "/Volumes/EOS_DIGITA1"

sleep 5

echo "-> Démarrage de l'émulation ML pour le "$model
./run_canon_fw.sh $model,firmware="boot=1"

if [ "$recupLog" == "1" ]; then
    echo "-> Montage de la pseudo carte SD"
    ./mount.sh
    echo "-> Recup du .LOG"
    cp /Volumes/EOS_DIGITAL/*.LOG $dirScript/tmp/SD0/
    echo "-> Recup du .LOG"
    cp /Volumes/EOS_DIGITA1/*.LOG $dirScript/tmp/SD1/
    echo "-> Fermeture des cartes 1 et 2"
    hdiutil detach "/Volumes/EOS_DIGITAL"
    hdiutil detach "/Volumes/EOS_DIGITA1"
fi

echo "-> Sauvegarde de la pseudo carte du modèle :"$model
cp -v ./sd.img ./sd-$model.img
cp -v ./cf.img ./cf-$model.img

echo "-> Retour sur le répertoire initial"
cd -

echo "Fin du script d'intégration automatique."