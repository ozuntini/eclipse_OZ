-- Eclipse Magic Lantern
Version = "2.2.1"
-- Exécution d'un cycle de photos pour suivre une éclipse
-- Adapté du script eclipse_magic de Brian Greenberg, grnbrg@grnbrg.org.
--		http://www.grnbrg.org/
--
-- Préparation pour Eclipse du 14 december 2020 in Chili for Canon 6D
--
-- Attention ! il faut activer le module lua  "Lua scripting" dans le menu Modules de MagicLantern
-- et copier ce script dans le répertoire M/SCRIPTS de la carte SD
--
-- Le boitier doit être en mode manuel, AF off

-- Load module logger
require ("logger")

-- Activation du mode log
LogToFile = 1
LoggingFile = nil
LoggingFilename = "mlecl.log"

-- Mode test
-- Le mode test ne déclenche pas dans ce cas il faut que la valeur soit 1
-- Il est possible de configurer le TestMode dans la ligne de config du script de schedule
TestMode = 0

-- Répertoire et Nom du script de schedule
Directory = "ML/SCRIPTS/"
Filename = "SOLARECL.TXT"

-- Log to stdout and optionally to a file
function log(s, ...)
	local str = string.format (s, ...)
	str = str .. "\n"
	if (LogToFile == 0 or LoggingFile == nil)
	then
		io.write (str)
	else
		LoggingFile:write (str)
	end
	return
end

-- Open log file
function log_start()
	if (LogToFile ~= 0)
	then
		local cur_time = dryos.date
		local filename = string.format("eclipse.log")
		print (string.format ("Open log file %s", filename))
		LoggingFile = logger (filename)
	else
		print (string.format ("Logging not configured"))
	end
end

-- Close log file
function log_stop()
	if (LogToFile ~= 0)
	then
		print (string.format ("Close log file"))
		LoggingFile:close ()
	end
end

-- Get the current time (in seconds) from the camera's clock.
function get_cur_secs()
	local cur_time = dryos.date
	local cur_secs = (cur_time.hour * 3600 + cur_time.min * 60 + cur_time.sec)
	return cur_secs
end

-- Take a time variable expressed in seconds (which is what all times are stored as) and convert it back to HH:MM:SS
function pretty_time(time_secs)
	local text_time = ""
	local hrs = 0
	local mins = 0
	local secs = 0
	hrs =  math.floor(time_secs / 3600)
    mins = math.floor((time_secs - (hrs * 3600)) / 60)
	secs = (time_secs - (hrs*3600) - (mins * 60))
	text_time = string.format("%02d:%02d:%02d", hrs, mins, secs)
	return text_time
end

-- Take a time expressed in hrs, min, sec and convert it to seconds
function convert_second(hrs, mins, secs)
    local seconds = (hrs * 3600 + mins * 60 + secs)
    return seconds
end

-- Take a shutter speed expressed in (fractional) seconds and convert it to 1/x.
function pretty_shutter(shutter_speed)
	local text_time = ""
	if (shutter_speed >= 1.0)
	then
		text_time = tostring (shutter_speed)
	else
		text_time = string.format ("1/%s", tostring (1/shutter_speed))
	end
	return text_time
end

-- Mirror lockup function
function set_mirror_lockup(mirrorLockupDelay)
    if (mirrorLockupDelay > 0)
    then
        menu.set("Mirror Lockup", "MLU mode", "Handheld")
        menu.set("Mirror Lockup", "Handheld Shutter", "All values")
        menu.set("Mirror Lockup", "Handheld Delay", "1s")
        menu.set("Shoot", "Mirror Lockup", "Handheld")
        log ("%s - Set mirror lockup ON. Delay = %s",pretty_time(get_cur_secs()), mirrorLockupDelay)
    else
        menu.set("Shoot", "Mirror Lockup", "OFF")
        log ("%s - Set mirror lockup OFF.",pretty_time(get_cur_secs()))
    end
end

-- Read and parse a script function
function read_script(directory, filename)
    -- Ouverture du fichier directory/filename et l'analyse pour charger un tableau avec pour chaque lignes une action à réaliser
    -- Le fichier filename est un CSV avec comme séparateur le ; et # pour commenter les lignes
    -- Le tableau est retourné par la fonction
    log ("%s - Script %s loading.", pretty_time(get_cur_secs()), directory..filename)
    local tableau = {}
    local mydir = dryos.directory(directory)    -- Liste l'ensemble des fichiers dans le répertoire
    local row = 1
    local col = 1
    for i,v in ipairs(mydir:files())            -- Parcours l'iterateur
    do
        if (v == directory..filename)           -- S'arrête sur filename
        then
            row = 1
            col = 1
            local fichier = io.open(v,"r")      -- Ouverture du fichier
            repeat
                local line = fichier:read("l")  -- Lecture ligne par ligne
                if ( line ~= nil) and (string.sub(line,1,1) ~= "#") -- Ne tient pas compte des lignes commentaires # et des lignes vides
                then
                    tableau[row]={}
                    col = 1
                    for word in string.gmatch(line, "[^,^:]+") -- Chargement du tableau avec les valeurs entre les "," et les ":"
                    do
                        tableau[row][col] = word
                        col=col+1
                    end
                    row=row+1
                end
            until (line == nil)
        end
    end
    log ("%s - Table of %s lines and %s columns loaded.", pretty_time(get_cur_secs()), row-1, col-1)
    return tableau 
end

-- Conversion temps relatif en absolu en fct de la référence de l'opérande et de l'heure en entrée => retourne une heure absolue en seconde
function convert_time(reference, operation, timeIn, tableRef)
    local timeRef = 0
    local timeOut = 0
    if (reference == "C1") then  -- Identification de la référence et chargement de la table de référence
        timeRef = tableRef[1]
    elseif (reference == "C2") then
        timeRef = tableRef[2]
    elseif (reference == "Max") then
        timeRef = tableRef[3]
    elseif (reference == "C3") then
        timeRef = tableRef[4]
    elseif (reference == "C4") then
        timeRef = tableRef[5]
    else
        log ("%s - Erreur dans la déclaration de la ref : %s",pretty_time(get_cur_secs()), reference)
    end
    if (operation == "-")  -- En fonction de l'opérande et en tenant compte du passage à 0 heure
    then
        timeOut = timeRef - timeIn
        if (timeOut < 0)
        then
            timeOut = 86400 + timeOut
        end
    elseif (operation == "+")
    then
        timeOut = timeRef + timeIn
        if (timeOut > 86400)
        then
            timeOut = timeOut - 86400
        end
    else
        log ("%s - Erreur dans la déclaration de l'opérande : %s",pretty_time(get_cur_secs()), operation)
    end
    log ("%s - Conversion : %s soit %s %s %s = %s soit %s",pretty_time(get_cur_secs()), reference, timeRef, operation, timeIn, timeOut, pretty_time(timeOut))
    return timeOut
end

-- Take a picture function
function take_shoot(iso, aperture, shutter_speed, mluDelay) -- mluDelay = delay to wait after mirror lockup in ms
    camera.iso.value = iso
    camera.aperture.value = aperture
    camera.shutter.value = shutter_speed
    if (mluDelay > 0)
    then
        key.press(KEY.HALFSHUTTER)
        key.press(KEY.FULLSHUTTER)
        log ("%s - Mirror Up",pretty_time(get_cur_secs()))
        msleep(mluDelay)
    end
    if (TestMode == 1)
    then
        log ("%s - NO Shoot! ISO: %s Aperture: %s shutter: %s Test Mode",pretty_time(get_cur_secs()), tostring(camera.iso.value), tostring(camera.aperture.value), pretty_shutter(camera.shutter.value))
    else
        camera.shoot(false) -- Shoot a picture
        log ("%s - Shoot! ISO: %s Aperture: %s shutter: %s",pretty_time(get_cur_secs()), tostring(camera.iso.value), tostring(camera.aperture.value), pretty_shutter(camera.shutter.value))
    end
    if (mluDelay > 0)
    then
        key.press(KEY.UNPRESS_HALFSHUTTER)
        key.press(KEY.UNPRESS_FULLSHUTTER)
    end
end

-- Boucle de prises de vue (hFin et intervalle en seconde)
function boucle(hFin, intervalle, iso, aperture, shutter_speed, mluDelay)
    intervalle = math.ceil(intervalle - 0.5)
    if (intervalle < 1) then
        intervalle = 1  -- impossible d'avoir un intervalle < à 1s
        log ("%s - action Boucle ou Interval : set interval to 1s.",pretty_time(get_cur_secs()))
    end
    log ("%s - Boucle: hFin: %s Intervalle: %s s", pretty_time(get_cur_secs()), pretty_time(hFin), intervalle)
    local shootTime = get_cur_secs()
    while (get_cur_secs() <= hFin) and ((shootTime + intervalle) <= hFin)
    do
        shootTime = get_cur_secs()
        take_shoot(iso, aperture, shutter_speed, mluDelay)
        while ((shootTime + intervalle -1) >= get_cur_secs()) and ((shootTime + intervalle) <= hFin) -- intervalle -1 pour prendre en compte le délais de prise de vue
        do
            msleep(500) -- Wait 1/2 s
        end
    end
    log ("%s - End of boucle",pretty_time(get_cur_secs()))
end

-- Verify some camera properties
function verify_conf(lineValue)
    local refMode = lineValue[2]
    local refAF = lineValue[3]
    local refBat = lineValue[4]
    local refFS = lineValue[5]
    -- Configuration du boitier
    local localMode = tostring(camera.mode)
    local localAF = lens.af
    if localAF then localAF = "1" else localAF = "0" end -- Conversion boolean en string
    local localBat = battery.level
    local localCard = dryos.shooting_card -- recup référence de la carte utilisée
    local localFS = math.ceil(localCard.free_space/1000 - 0.5)
    --
    log ("%s - Should: Model: %s Mode: %s AF: %s Bat.: %s %% Card: %s M°",pretty_time(get_cur_secs()), camera.model, refMode, refAF, refBat, refFS)
    log ("%s - Have  : Model: %s Mode: %s AF: %s Bat.: %s %% Card: %s M°",pretty_time(get_cur_secs()), camera.model, localMode, localAF, localBat, localFS)
    local verifResult = "go"
    local verifError = ""
    if (refMode ~= "-") and (refMode ~= localMode) then verifResult = "nogo"
        verifError = "Incorect Mode"
    elseif (refAF ~= "-") and (localAF ~= refAF) then verifResult = "nogo"
        verifError = "AF On"
    elseif (refBat~= "-") and (tonumber(refBat) > localBat) then verifResult = "nogo"
        verifError = "Battery low"
    elseif (refFS ~= "-") and (tonumber(refFS) > localFS) then verifResult = "nogo"
        verifError = "Card full"
    end
    if (verifError ~= "") then
        display.notify_box(verifError, 5000)  -- affichage de la cause
        log ("%s - Error : %s",pretty_time(get_cur_secs()) , verifError)
    end
    return verifResult
end

-- Read Config line and set C1, C2, Max, C3, C4 and TestMode
function read_config(lineValue)
    local action = lineValue[1]
    local timeC1 = convert_second(lineValue[2], lineValue[3], lineValue[4])
    local timeC2 = convert_second(lineValue[5], lineValue[6], lineValue[7])
    local timeMax = convert_second(lineValue[8], lineValue[9], lineValue[10])
    local timeC3 = convert_second(lineValue[11], lineValue[12], lineValue[13])
    local timeC4 = convert_second(lineValue[14], lineValue[15], lineValue[16])
    local testMode = tonumber(lineValue[17])
    log ("%s - Action: %s C1: %s:%s:%s/%ss C2: %s:%s:%s/%ss Max: %s:%s:%s/%ss C3: %s:%s:%s/%ss C4: %s:%s:%s/%ss TestMode: %s",pretty_time(get_cur_secs()), 
    action, lineValue[2], lineValue[3], lineValue[4], timeC1, lineValue[5], lineValue[6], lineValue[7], timeC2, lineValue[8], lineValue[9], lineValue[10], timeMax,
    lineValue[11], lineValue[12], lineValue[13], timeC3, lineValue[14], lineValue[15], lineValue[16], timeC4, testMode)
    return timeC1, timeC2, timeMax, timeC3, timeC4, testMode
end

-- Read Boucle and Photo line and do action
function do_action(action, timeStart, timeEnd, interval, aperture, iso, shutterSpeed, mluDelay)
    
    -- Les paramètres sont chargés on gère le mirror lockup
    set_mirror_lockup(mluDelay)

    -- On boucle tant que nous ne sommes pas dans le bon créneau horaire
    local counter = 0
    while (get_cur_secs() < (timeStart - (mluDelay/1000)))
    do  -- Pas encore l'heure on attend 0.25 seconde
        counter = counter +1
        if (counter >= 80) -- Affiche Waiting toutes les 20s
        then
            display.notify_box("Waiting "..(timeStart - get_cur_secs()), 2000)
            counter = 0
        end
        msleep(250)
    end
    if (action == "Boucle") or (action == "Interval") -- Traitement d'une ligne d'action Boucle ou Interval
    then
        if (get_cur_secs() <= timeEnd ) -- On vérifie que l'on ne soit pas après l'heure
        then
            -- Lancement de la boucle de prises de vues
            boucle(timeEnd, interval, iso, aperture, shutterSpeed, mluDelay)
        else
            log ("%s - Too last ! TimeEnd: %ss soit %s", pretty_time(get_cur_secs()), timeEnd, pretty_time(timeEnd))
        end
    elseif (action == "Photo") -- Traitement d'une ligne de Photo
    then
        -- Lancement de la prises de vues
        take_shoot(iso, aperture, shutterSpeed, mluDelay)
    end
end

-- Fonction principale de pilotage du processus de photograpie de l'éclispe
function main()
    menu.close()
    console.show()
    console.clear()

    log_start () -- Open log file
    log ("==> eclipse_OZ.lua - Version : %s", Version)
    log ("%s - Log begin.",pretty_time(get_cur_secs()))
	print ("---------------------------------------------------")
	print (" Eclipse ML OZ")
	print (" https://github.com/ozuntini/eclipse_OZ")
	print (" Released under the GNU GPL")
	print ("---------------------------------------------------")

    print ("Script loading.")
    local scheduleTable = read_script(Directory, Filename)

    print ("Start photos schedule.")
    local configTable = {}
    for key,value in ipairs(scheduleTable)
    do  -- Chargement des parametres
        local action = value[1]
        -- Verify --
        if (action == "Verif") -- Traitement de la ligne de vérification
        then
            local ready2go = verify_conf(value)
            if ready2go == "nogo"
            then
                -- No Go affichage de l'alerte et sortie
                print("Launch not accepted verify configuration !")
                log ("%s - Configuration not accepted the sequence is stoped !", pretty_time(get_cur_secs()))
                break
            else
                -- Go la séquence continue
                log ("%s - Configuration accepted.", pretty_time(get_cur_secs()))
            end
        -- Load Config --
        elseif (action == "Config") -- Traitement d'une ligne de set_config
        then
            configTable = {read_config(value)}
            TestMode = configTable[6]
            log ("%s - Set test mode : %s", pretty_time(get_cur_secs()), TestMode)
        -- Make action --
        elseif (action == "Boucle") or (action == "Interval") or (action == "Photo")
        then
            local refTime = value[2]
            local operStart = value[3] -- Opérande pour le timeStart
            local operEnd = value[7]   -- Opérande pour le timeEnd
            local timeStart = 0
            local timeEnd = 0
            if (refTime == "-")
            then  -- Mode absolu
                timeStart = convert_second(value[4], value[5], value[6])
                timeEnd = convert_second(value[8], value[9], value[10])
            else  -- Mode relatif
                timeStart = convert_time(refTime, operStart, convert_second(value[4], value[5], value[6]), configTable)
                if (action == "Boucle") or (action == "Interval") -- Le timeEnd n'est utilisé que pour les Boucle et pour les Interval
                then
                    timeEnd = convert_time(refTime, operEnd, convert_second(value[8], value[9], value[10]), configTable)
                else
                    timeEnd = ""
                end
            end
            local interval = 0
            -- Gestion du mode Boucle ou interval, dans le 1er la valeur [11] correspond à l'intervalle en seconde entre 2 photos,
            -- dans le 2éme il indique le nombre de photos entre le début et la fin.
            if (action == "Interval")
            then
                interval = (timeEnd - timeStart) / tonumber(value[11]) -- Conversion du nombre de photos en intervalle
            else
                interval = tonumber(value[11])
            end
            local aperture = tonumber(value[12])
            local iso = tonumber(value[13])
            local shutterSpeed = tonumber(value[14])
            local mluDelay = tonumber(value[15])
            log ("%s - Action: %s TimeRef: %s OperStart: %s TimeStart: %s %s %s:%s:%s=%ss OperEnd: %s TimeEnd: %s %s %s:%s:%s=%ss Interval: %ss Aperture %s ISO %s ShutterSpeed: %ss MluDelay: %sms",pretty_time(get_cur_secs()), 
            action, refTime, operStart, refTime, operStart, value[4], value[5], value[6], timeStart, operEnd, refTime, operEnd, value[8], value[9], value[10], timeEnd, interval, aperture, iso, shutterSpeed, mluDelay)
            -- Lancement de l'action, Boucle ou Photo
            do_action(action, timeStart, timeEnd, interval, aperture, iso, shutterSpeed, mluDelay)
        end
        -- Ligne traitée on passe à la suivante
        log ("%s - Line %s finish go to the next line.", pretty_time(get_cur_secs()), key)
    end

    print ("Press any key to exit.")
    key.wait()
    console.clear()
    console.hide()
    log ("%s - Normal exit.",pretty_time(get_cur_secs()))
	log_stop () -- close log file
end

keymenu = menu.new
{
    name   = "Eclipse ML OZ",
    help   = "Photographier une Eclipse totale de Soleil",
    select = function(this) task.create(main) end,
}