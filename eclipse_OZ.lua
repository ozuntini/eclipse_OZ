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

-- Définition des variables
deb = {}
c1 = {}
c2 = {}
max = {}
c3 = {}
c4 = {}
fin = {}

-- Activation du mode log
logToFile = 1
loggingFile = nil

-- Saisir les heures, minutes et secondes des chacun des contacts
deb.hr = 19; deb.min = 00; deb.sec = 00;
c1.hr = 19; c1.min = 00; c1.sec = 00;
c2.hr = 20; c2.min = 38; c2.sec = 37;
max.hr = 19; max.min = 00; max.sec = 00;
c3.hr = 20; c3.min = 41; c3.sec = 03;
c4.hr = 21; c4.min = 46; c4.sec = 45;
fin.hr = 19; fin.min = 00; fin.sec = 00;

-- Choix de l'ouverture
-- Si l'ouverture est pilotée par le boitier (téléobjecitf) la valeur doit être 1
-- Si l'ouverture est fixe (téléscope) la valeur doit être 0
setAperture = 1
-- Valeur de l'ouverture
aperture = 5.6


-- Log to stdout and optionally to a file
function log (s, ...)
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
function log_start ()
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
function log_stop ()
	if (logToFile ~= 0)
	then
		print (string.format ("Close log file"))
		loggingFile:close ()
	end
end


function main()
    menu.close()
    console.show()
    console.clear()

    log_start () -- Open log file
    log ("Log begin.")
    
    print ()
	print ()
	print ("------------------------------------------------")
	print (" Eclipse ML OZ")
	print (" Copyright 2020, olivier.zuntini@netcourrier.com")
	print (" Released under the GNU GPL")
	print ("------------------------------------------------")
    print ()
    print "Press any key to exit."

    key.wait()
    console.clear()
    console.hide()
    log ("Normal exit.")
	log_stop () -- close log file
end

keymenu = menu.new
{
    name   = "Eclipse ML OZ",
    help   = "Photographier une Eclipse totale de Soleil",
    select = function(this) task.create(main) end,
}