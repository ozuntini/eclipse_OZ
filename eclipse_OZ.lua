-- Eclipse Magic Lantern
-- Version 1.0
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
logToFile = 1
loggingFile = nil

-- Choix de l'ouverture
-- Si l'ouverture est pilotée par le boitier (téléobjecitf) la valeur doit être 1
-- Si l'ouverture est fixe (téléscope) la valeur doit être 0
setAperture = 1

-- Mode test
-- Le mode test ne déclenche pas dans ce cas il faut que la valeur soit 1
testMode = 1

-- Log to stdout and optionally to a file
function log(s, ...)
	local str = string.format (s, ...)
	str = str .. "\n"
	if (logToFile == 0 or loggingFile == nil)
	then
		io.write (str)
	else
		loggingFile:write (str)
	end
	return
end

-- Open log file
function log_start()
	if (logToFile ~= 0)
	then
		local cur_time = dryos.date
		local filename = string.format("eclipse.log")
		print (string.format ("Open log file %s", filename))
		loggingFile = logger (filename)
	else
		print (string.format ("Logging not configured"))
	end
end

-- Close log file
function log_stop()
	if (logToFile ~= 0)
	then
		print (string.format ("Close log file"))
		loggingFile:close ()
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
    log ("%s - Lecture du script %s.", pretty_time(get_cur_secs()), directory..filename)
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
                    for word in string.gmatch(line, "[^;]+") -- Chargement du tableau avec les valeurs entre les ;
                    do
                        tableau[row][col] = word
                        col=col+1
                    end
                    row=row+1
                end
            until (line == nil)
        end
    end
    log ("%s - Tableau de %s lignes de %s colonnes chargé.", pretty_time(get_cur_secs()), row-1, col-1)
    return tableau 
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
    if (testMode == 1)
    then
        log ("%s - NO Shoot! ISO: %s Aperture: %s shutter: %s Test Mode",pretty_time(get_cur_secs()), tostring(camera.iso.value), tostring(camera.aperture.value), pretty_shutter(camera.shutter.value))
    else
        log ("%s - Shoot! ISO: %s Aperture: %s shutter: %s",pretty_time(get_cur_secs()), tostring(camera.iso.value), tostring(camera.aperture.value), pretty_shutter(camera.shutter.value))
        camera.shoot(false) -- Shoot a picture
    end
    task.yield(10)      -- sleep 10 ms
    if (mluDelay > 0)
    then
        key.press(KEY.UNPRESS_HALFSHUTTER)
        key.press(KEY.UNPRESS_FULLSHUTTER)
    end
end

-- Boucle de prises de vue (hFin et intervalle en seconde)
function boucle(hFin, intervalle, iso, aperture, shutter_speed, mluDelay)
    log ("%s - Boucle: hFin: %s Intervalle: %s s", pretty_time(get_cur_secs()), pretty_time(hFin), intervalle)
    local shootTime = get_cur_secs()
    while (get_cur_secs() <= hFin) and ((shootTime + intervalle) <= hFin)
    do
        shootTime = get_cur_secs()
        take_shoot(iso, aperture, shutter_speed, mluDelay)
        while ((shootTime + intervalle -1) >= get_cur_secs()) and ((shootTime + intervalle) <= hFin) -- intervalle -1 pour prendre en compte le délais de prise de vue
        do
            msleep(500) -- Wait 1/4 s
        end
    end
    log ("%s - Fin de boucle",pretty_time(get_cur_secs()))
end

-- Fonction principale de pilotage du processus de photograpie de l'éclispe
function main()
    menu.close()
    console.show()
    console.clear()

    log_start () -- Open log file
    log ("%s - Log begin.",pretty_time(get_cur_secs()))
	print ("------------------------------------------------")
	print (" Eclipse ML OZ")
	print (" https://github.com/ozuntini/eclipse_OZ")
	print (" Released under the GNU GPL")
	print ("------------------------------------------------")

    print ("Chargement du script")
    local scheduleTable = read_script("ML/SCRIPTS/", "SOLARECL.TXT")

    print ("Démarrage du cycle de photos")
    for key,value in ipairs(scheduleTable)
    do  -- Chargement des parametres
        local action = value[1]
        local timeStart = convert_second(value[2], value[3], value[4])
        local timeEnd = convert_second(value[5], value[6], value[7])
        local interval = tonumber(value[8])
        local aperture = tonumber(value[9])
        local iso = tonumber(value[10])
        local shutterSpeed = tonumber(value[11])
        local mluDelay = tonumber(value[12])
        log ("%s - Action: %s TimeStart: %s:%s:%s/%ss TimeEnd: %s:%s:%s/%ss Interval: %ss Aperture %s ISO %s ShutterSpeed: %ss MluDelay: %ss",pretty_time(get_cur_secs()), 
        action, value[2], value[3], value[4], timeStart, value[5], value[6], value[7], timeEnd, interval, aperture, iso, shutterSpeed, mluDelay)
        -- Les paramètres sont chargés on gère le mirror lockup
        set_mirror_lockup(mluDelay)

        -- On boucle tant que nous ne sommes pas dans le bon créneau horaire
        local counter = 0
        while (get_cur_secs() < timeStart)
        do  -- Pas encore l'heure on attend 0.5 seconde
            counter = counter +1
            if (counter >= 40) -- Affiche Waiting toutes les 20s
            then
                display.notify_box("Waiting !", 2000)
                counter = 0
            end
            msleep(500)
        end
        if (action == "Boucle") -- Traitement d'une ligne d'action Boucle
        then
            if (get_cur_secs() <= timeEnd ) -- On vérifie que l'on ne soit pas après l'heure
            then
                -- Lancement de la boucle de prises de vues
                boucle(timeEnd, interval, iso, aperture, shutterSpeed, mluDelay)
            else
                log ("%s - Trop tard ! TimeEnd: %ss soit %s", pretty_time(get_cur_secs()), timeEnd, pretty_time(timeEnd))
            end
        elseif (action == "Photo") -- Traitement d'une ligne de Photo
        then
            -- Lancement de la prises de vues
            take_shoot(iso, aperture, shutterSpeed, mluDelay)
        end
        -- Ligne traitée on passe à la suivante
        log ("%s - Ligne %s traitée on passe à la suivante.", pretty_time(get_cur_secs()), key)
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