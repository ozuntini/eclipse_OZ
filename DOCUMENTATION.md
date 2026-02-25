**Vue D'ensemble**

Ce projet fournit un script Lua `eclipse_OZ.lua` conçu pour être exécuté depuis Magic Lantern (module "Lua scripting") sur un boîtier Canon. Il orchestre une série d'acquisitions photographiques planifiées (photos isolées, boucles ou intervalles) pour documenter une éclipse solaire totale en pilotant l'appareil selon un fichier de séquence `SOLARECL.TXT`.

Objectif principal : automatiser des prises de vue temporellement précises (absolues ou relatives à des instants de l'éclipse) avec des paramètres d'exposition et un support pour mirror-lockup et mode test.

Contexte d'utilisation : exécution directe sur un boîtier compatible Magic Lantern ou en émulation QEMU pour tests (scripts d'assistance fournis : `MLua_PIC.sh`, `MLua_mount_imgSD.sh`, `MLua_Test.sh`).

**Architecture**

- **Racine du projet**: ensemble de scripts et documentation.
- **Fichiers principaux**:
  - `eclipse_OZ.lua`: script principal Lua exécuté par Magic Lantern.
  - `SOLARECL.TXT`: template / fichier de configuration des séquences (CSV-like).
  - `README.md`, `Manuel d'utilisation.md`: documentation utilisateur.
  - `Changelog`: historique des évolutions.
  - `MLua_PIC.sh`, `MLua_mount_imgSD.sh`, `MLua_Test.sh`: utilitaires bash pour tests QEMU et déploiement sur cartes SD (macOS-centric).
  - `images/`: captures écran utilisées dans la documentation.

**Technologies utilisées**

- **Langages**: Lua (script principal), Bash (scripts utilitaires), Markdown (docs).
- **Environnements**: Magic Lantern (firmware alternatif pour boîtiers Canon), optionnellement QEMU (émulation Magic Lantern) pour tests.
- **Dépendances matérielles**: boîtier Canon compatible Magic Lantern, carte SD.

**Fonctionnalités principales**

- Exécution de séquences planifiées de prises de vue (actions `Photo`, `Boucle`, `Interval`).
- Mode `TestMode` pour exécuter la logique sans déclencher le capteur.
- Support du mirror lockup (MLU) avec délai configurable.
- Parsing simple de `SOLARECL.TXT` (séparateurs `,` et `:`) et conversion d'heures relatives (références `C1`, `C2`, `Max`, `C3`, `C4`).
- Vérification initiale de l'état du boîtier (`Verif`) : mode, AF, batterie, espace libre.
- Journalisation des événements dans un fichier `eclipse.log` (créé sur la carte SD).

**Points d'entrée**

- `eclipse_OZ.lua`: point d'entrée principal, expose un menu Magic Lantern (`Eclipse ML OZ`) et crée la tâche principale (`main`) qui exécute le planning.
- `SOLARECL.TXT`: point d'entrée pour décrire les séquences photographiques (format lisible par `read_script`).
- Scripts d'assistance (hors boîtier) :
  - `MLua_mount_imgSD.sh`: monter une image SD QEMU et copier le script.
  - `MLua_PIC.sh`: intégrer le script dans l'image QEMU et lancer l'émulation.
  - `MLua_Test.sh`: copier le script sur une carte SD montée et nettoyer le log.

**Configuration**

- `SOLARECL.TXT` contient les lignes de configuration possibles : `Verif`, `Config`, `Boucle`, `Interval`, `Photo`.
- Ligne `Config` : définit les cinq repères temporels `C1`, `C2`, `Max`, `C3`, `C4` au format `HH:MM:SS` et `TestMode` (`0` ou `1`).
- Ligne `Verif` : permet d'indiquer des valeurs attendues pour `Mode`, `AF`, `Battery (%)` et `Storage (Mo)`; si différent, le script s'arrête.
- Champs des actions (`Boucle`/`Interval`/`Photo`) : référence temporelle (`C1|C2|Max|C3|C4|-`), opérateurs `+|-`, heures, intervalle/nb photos, `Aperture`, `ISO`, `ShutterSpeed` (en secondes, float), `MLUDelay` (ms).

Points importants :
- `TestMode = 1` : aucune photo réelle n'est prise (`camera.shoot` est bypassé) — utile pour qualification.
- Le script ne gère pas explicitement la date (passage à minuit) : les heures sont traitées sur 24h et un passage au jour suivant risque d'entraîner des comportements inattendus.
- Intervalle minimal entre deux images : 1 seconde.

**Installation et déploiement**

- Prérequis matériels : boîtier Canon compatible, carte SD.
- Installer Magic Lantern et activer le module `Lua scripting`.
- Copier `eclipse_OZ.lua` dans `ML/SCRIPTS/` sur la carte SD et placer la séquence `SOLARECL.TXT` à côté.
- (Optionnel) Pour tests en environnement desktop : utiliser QEMU suivant les scripts `MLua_mount_imgSD.sh` et `MLua_PIC.sh` (les scripts sont testés principalement sous macOS).

Commandes utiles (exemples macOS):

```bash
# Copier le script sur la carte SD montée (macOS)
cp eclipse_OZ.lua /Volumes/EOS_DIGITAL/ML/scripts/

# Emuler avec QEMU (voir variables intégrées dans les scripts)
./MLua_PIC.sh 6D eclipse_OZ.lua
```

**Utilisation & Exemples**

- Exemple de `Config` :
  - `Config,14:41:05,16:02:49,16:03:53,16:04:58,17:31:03,1`
- Exemple `Boucle` en mode relatif :
  - `Boucle,C2,-,00:20:00,+,00:01:30,5,8,200,0.0005,0`
- Exemple `Interval` (50 photos sur un intervalle) :
  - `Interval,C2,-,00:01:00,+,00:00:30,50,8,200,0.0005,0`
- Exemple `Photo` :
  - `Photo,Max,-,00:00:10,-,-,-,-,-,4,1600,1,500`

**Structure du code (fichiers et fonctions clés)**

- `eclipse_OZ.lua` :
  - Rôle : orchestrer la lecture du schedule et piloter l'appareil via l'API Lua de Magic Lantern.
  - Fonctions principales :
    - `main()` : initialisation, lecture du script, boucle d'exécution des lignes.
    - `read_script(directory, filename)` : lit `SOLARECL.TXT` et renvoie un tableau de lignes (séparateurs `,` ou `:`).
    - `read_config(lineValue)` : convertit la ligne `Config` en repères temps en secondes.
    - `convert_second(h,m,s)` et `convert_time(reference, operation, timeIn, tableRef)` : conversions temporelles.
    - `do_action(action, timeStart, timeEnd, ...)` : synchronisation d'attente et exécution d'actions (`Boucle`/`Interval`/`Photo`).
    - `boucle(hFin, intervalle, iso, aperture, shutter_speed, mluDelay)` : réalise la série de prises.
    - `take_shoot(iso, aperture, shutter_speed, mluDelay)` : prépare l'exposition, gère MLU et déclenche (`camera.shoot`) ou log en test mode.
    - `verify_conf(lineValue)` : vérifie l'état du boîtier au démarrage.
  - Interactions : s'appuie sur les API de Magic Lantern (`camera`, `menu`, `key`, `display`, `dryos`, `logger`).

- `SOLARECL.TXT` :
  - Rôle : définir la séquence; simple format CSV-like commenté par `#`.
  - Particularité : tolère séparateurs `,` et `:` dans le parsing.

- `MLua_mount_imgSD.sh`, `MLua_PIC.sh`, `MLua_Test.sh` :
  - Rôle : automatiser la copie du script sur images SD QEMU ou sur carte SD physique et lancer/arrêter l'émulation; scripts pensés pour macOS (utilisent `hdiutil`, chemins utilisateur codés en dur dans les variables).

- `README.md`, `Manuel d'utilisation.md`, `Changelog` : documentation utilisateur et historique.

**Dépendances externes / Matériel requis**

- Magic Lantern avec `Lua scripting` activé.
- Boîtier Canon pris en charge par Magic Lantern (ex. Canon 6D, 60D mentionnés).
- Carte SD avec arborescence `ML/SCRIPTS/`.
- (Optionnel) QEMU build pour Magic Lantern si tests locaux requis.

**Points d'attention et limitations connues**

- Le script ne gère pas la date (passage minuit) — planifier les séquences sur une même journée ou adapter avant migration.
- Dépend fortement des APIs internes de Magic Lantern (objets `camera`, `dryos`, `key`, `menu`) — ces appels doivent être isolés si vous migrez vers un environnement différent.
- Scripts Bash utilitaires sont écrits pour macOS (utilisent `hdiutil`, chemins locaux). Adapter pour Linux/Windows si nécessaire.
- Parsing de `SOLARECL.TXT` est sommaire (utilise `string.gmatch` et ne valide pas fortement les champs) — erreurs de format peuvent provoquer des comportements inattendus.
- Mirror lockup configuration peut ne pas être supportée par tous les boîtiers ou toutes versions de Magic Lantern.

**Conseils pour une migration technique**

- Séparer la logique métier (planning, conversions temporelles, parsing de schedule, règles d'actions) des appels matériels (`camera.*`, `key.*`, `menu.*`, `dryos.*`). Créer une couche d'abstraction `hardware_adapter`.
- Remplacer le parsing maison par un parser robuste (CSV/ini) et ajouter validation stricte des champs.
- Ajouter gestion de la date et fuseau horaire, notamment pour séquences franchissant minuit.
- Ajouter tests unitaires pour : conversion d'heures, parsing de lignes, calcul d'intervalles, comportement `TestMode`.
- Documenter et externaliser les chemins et paramètres des scripts bash; proposer des versions multiplateformes (PowerShell pour Windows, adaptations Linux).
- Centraliser la journalisation et exporter logs sur hôte ou via fichiers rotatifs.

**Fichiers à examiner en priorité pour la migration**

- `eclipse_OZ.lua` : découper et tester chaque fonction, factoriser l'accès aux API ML.
- `SOLARECL.TXT` : définir un schéma (JSON/YAML) si on souhaite plus de robustesse.
- `MLua_*.sh` : adapter aux plateformes cibles ou remplacer par scripts Python multiplateformes.

---

Si vous le souhaitez, je peux :
- convertir ce document en `DOCUMENTATION.md` (créé),
- générer un plan de migration détaillé (tâches, priorités, fichiers à modifier),
- ou commencer une refactorisation minimale pour découpler la couche hardware dans `eclipse_OZ.lua`.