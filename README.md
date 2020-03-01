# eclipse_OZ
## Eclipse Magic Lantern  

Exécution d'un cycle de photos pour suivre une éclipse totale de Soleil.  
Inspiré du script eclipse_magic de Brian Greenberg.  
grnbrg@grnbrg.org http://www.grnbrg.org/

Préparation pour l'éclipse du 14 décembre 2020 au Chili ou Argentine.  
Qualifié avec un Canon 6D.  
## Magic Lantern

Installer Magic Lantern sur votre boitier.  
https://www.magiclantern.fm/index.html  
Attention ! Il faut activer le module lua  "Lua scripting" dans le menu Modules de MagicLantern.  
![Menu Modules](./images/Modules.png)  
Copier le script eclipse_OZ.lua dans le répertoire ML/SCRIPTS de la carte SD ainsi que le descriptif de la séquence, SOLARECL.TXT.
## Descriptif de la séquence
La séquence de photos est décrite dans un fichier texte SOLARECL.TXT.  
Chaque séquence est décrite sur une ligne composée de paramètres séparés par une virgule "," ou un double point ":".
Il faut respecter les règles suivantes
* Pas de ligne vide
* \# pour commenter une ligne
* Les séquences doivent se suivre temporellement. Le fichier n'est lu que dans un sens. 
### Syntaxe
Chaque ligne décrit une séquence de la manière suivante :
`Action,Hd:Md:Sd,Hf:Mf:Sf,Interval,Aperture,ISO,ShutterSpeed,MLUDelay`
Position|Nom|Valeur|Description
:---:|:---:|:---:|:---
1|Action|Boucle ou Photo|Suite de photos identiques ou photo unique
2|Hd|0-23|Heure de début de la séquence
3|Md|0-59|Minute de début de la séquence
4|Sd|0-59|Seconde de début de la séquence
5|Hf|0-23|Heure de fin de la séquence (*)
6|Mf|0-59|Minute de fin de la séquence (*)
7|Sf|0-59|Seconde de fin de la séquence (*)
8|Interval|Num.|Intervalle entre deux photos en seconde (*)
9|Aperture|Diaph.|Valeur du Diaphragme (2.8,8,11...)(**)
10|ISO|Num.|Sensibilité du capteur (100, 800, 6400,...)(**)
11|ShutterSpeed|Num.|Vitesse d'exposition en seconde (**)
12|MLUDelay|Num.|Délais d'attente entre la montée du mirroir et le déclenchement, en miliseconde. Si 0 pas de montée du mirroir avant le déclenchement. 

(*) Uniquement utilisé par l'action "Boucle"  
(**) Attention prendre des valeurs compatible avec votre équipement
#### Exemples

Série de 21:22:05 à 21:25:35, une photo toutes les 5s, Diaph=8, ISO=200, Vitesse 1/2000, pas de Mirror lockup.  
>`Boucle,21:22:05,21:25:35,5,8,200,0.0005,0`  

Ligne de commentaire.  
>`\# Commentaire`  

Photo à 21:22:40, Diaph=4, ISO=1600, Vitesse 1, Mirror lockup avec 0,5s de délais.
>`Photo,21:22:40,-,-,-,-,4,1600,1,500`

## Lancement de la séquence
* Choisir le menu script.  
* Déplacer la barre de sélection sur le choix Eclipse ML OZ.  
* Lancer la séquence avec la touche SET.

Menu Scripts  
![Menu Scripts](./images/Scripts.png)

# Paramétrage du boitier
Le boitier doit être en mode :
* Auto power off à  Disable
* Mode Manuel
* Auto Focus en off

## Mirror Lockup
Si le boitier le permet il est possible d'utiliser le Mirrorlockup. Cela permet d'éviter des vibrations pendant la prise de vue.  
Menu Shoot - Mirror Lockup  
![Menu Shoot-Mirror-Lockup](./images/Shoot-MirrorLockup.png)  
La configuration MLU Mirror Lockup est piloté par le script mais il est possible qu'elle ne soit pas acceptée. 
