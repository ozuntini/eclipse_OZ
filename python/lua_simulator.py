#!/usr/bin/env python3
"""
Simulateur Lua pour tester les fonctions du script original eclipse_OZ.lua
sans avoir besoin de Magic Lantern. Reproduit les fonctions principales
pour permettre la comparaison avec l'implémentation Python.
"""

import math
import time
import os
from typing import List, Tuple, Dict, Any



class LuaSimulator:
    """Simule l'environnement Lua et les fonctions Magic Lantern"""
    
    def __init__(self, config_file: str, test_mode: bool = True):
        self.config_file = config_file
        self.test_mode = test_mode
        self.log_entries: List[str] = []
        self.current_time_seconds = 0  # Temps simulé en secondes depuis minuit
        self.version = "2.2.1"
        
        # Simulation des variables Magic Lantern
        self.camera = {
            'mode': '3',  # Mode manuel
            'model': 'Canon EOS 6D',
            'iso': {'value': 100},
            'aperture': {'value': 8.0},
            'shutter': {'value': 1.0/125}
        }
        
        self.battery = {'level': 95}
        self.card_free_space = 8000  # Mo
        
        # Configuration de l'éclipse (sera chargée du fichier)
        self.config_table = [0, 0, 0, 0, 0, 0]  # C1, C2, Max, C3, C4, TestMode
        
    def set_current_time(self, hours: int, minutes: int, seconds: int):
        """Définit le temps simulé actuel"""
        self.current_time_seconds = self.convert_second(hours, minutes, seconds)
        
    def log(self, message: str, *args):
        """Simule la fonction log() de Lua"""
        if args:
            message = message % args
        
        current_time_str = self.pretty_time(self.current_time_seconds)
        log_entry = f"{current_time_str} - {message}"
        self.log_entries.append(log_entry)
        print(log_entry)
        
    def get_cur_secs(self) -> int:
        """Simule get_cur_secs() - retourne le temps actuel en secondes"""
        return self.current_time_seconds
        
    def pretty_time(self, time_secs: int) -> str:
        """Convertit des secondes au format HH:MM:SS"""
        hrs = time_secs // 3600
        mins = (time_secs - (hrs * 3600)) // 60
        secs = time_secs - (hrs * 3600) - (mins * 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        
    def convert_second(self, hrs: int, mins: int, secs: int) -> int:
        """Convertit HH:MM:SS en secondes"""
        return hrs * 3600 + mins * 60 + secs
        
    def pretty_shutter(self, shutter_speed: float) -> str:
        """Convertit la vitesse d'obturation en format lisible"""
        if shutter_speed >= 1.0:
            return str(shutter_speed)
        else:
            return f"1/{int(1/shutter_speed)}"
            
    def read_script(self, directory: str, filename: str) -> List[List[str]]:
        """Simule read_script() - lit et parse le fichier de configuration"""
        file_path = os.path.join(directory, filename) if directory else filename
        
        self.log("Script %s loading.", file_path)
        
        tableau = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as fichier:
                row = 0
                for line in fichier:
                    line = line.strip()
                    # Ignore les commentaires et lignes vides
                    if line and not line.startswith('#'):
                        # Parse la ligne avec séparateur virgule
                        parts = [word.strip() for word in line.split(',')]
                        
                        if parts:  # Si la ligne n'est pas vide après parsing
                            # Traitement spécial pour les temps au format HH:MM:SS
                            expanded_parts = []
                            for part in parts:
                                if ':' in part and len(part.split(':')) == 3:
                                    # C'est un temps au format HH:MM:SS, on l'explose
                                    time_parts = part.split(':')
                                    expanded_parts.extend(time_parts)
                                else:
                                    expanded_parts.append(part)
                            
                            tableau.append(expanded_parts)
                            row += 1
                            
        except FileNotFoundError:
            self.log("Erreur: fichier %s non trouvé", file_path)
            return []
            
        self.log("Table of %d lines loaded.", len(tableau))
        return tableau
        
    def convert_time(self, reference: str, operation: str, time_in: int, table_ref: List[int]) -> int:
        """Convertit un temps relatif en temps absolu"""
        time_ref = 0
        
        if reference == "C1":
            time_ref = table_ref[0]
        elif reference == "C2":
            time_ref = table_ref[1]
        elif reference == "Max":
            time_ref = table_ref[2]
        elif reference == "C3":
            time_ref = table_ref[3]
        elif reference == "C4":
            time_ref = table_ref[4]
        else:
            self.log("Erreur dans la déclaration de la ref : %s", reference)
            return 0
            
        if operation == "-":
            time_out = time_ref - time_in
            if time_out < 0:
                time_out = 86400 + time_out
        elif operation == "+":
            time_out = time_ref + time_in
            if time_out > 86400:
                time_out = time_out - 86400
        else:
            self.log("Erreur dans la déclaration de l'opérande : %s", operation)
            return 0
            
        self.log("Conversion : %s soit %s %s %d = %d soit %s",
                reference, time_ref, operation, time_in, time_out, self.pretty_time(time_out))
        return time_out
        
    def take_shoot(self, iso: int, aperture: float, shutter_speed: float, mlu_delay: int):
        """Simule take_shoot() - prend une photo"""
        self.camera['iso']['value'] = iso
        self.camera['aperture']['value'] = aperture
        self.camera['shutter']['value'] = shutter_speed
        
        if mlu_delay > 0:
            self.log("Mirror Up")
            # Simulation du délai mirror lockup
            time.sleep(mlu_delay / 1000.0)  # Convert ms to seconds
            
        if self.test_mode:
            self.log("NO Shoot! ISO: %d Aperture: %.1f shutter: %s Test Mode",
                    iso, aperture, self.pretty_shutter(shutter_speed))
        else:
            self.log("Shoot! ISO: %d Aperture: %.1f shutter: %s",
                    iso, aperture, self.pretty_shutter(shutter_speed))
                    
    def boucle(self, h_fin: int, intervalle: float, iso: int, aperture: float, 
               shutter_speed: float, mlu_delay: int):
        """Simule boucle() - boucle de prises de vue"""
        intervalle = max(1, math.ceil(intervalle - 0.5))
        
        self.log("Boucle: hFin: %s Intervalle: %d s", 
                self.pretty_time(h_fin), intervalle)
        
        shoot_time = self.get_cur_secs()
        
        while (self.get_cur_secs() <= h_fin and 
               (shoot_time + intervalle) <= h_fin):
            
            shoot_time = self.get_cur_secs()
            self.take_shoot(iso, aperture, shutter_speed, mlu_delay)
            
            # Simulation de l'attente
            while ((shoot_time + intervalle - 1) >= self.get_cur_secs() and
                   (shoot_time + intervalle) <= h_fin):
                # Simulation sleep 500ms
                self.current_time_seconds += 1  # Avance le temps simulé
                
        self.log("End of boucle")
        
    def verify_conf(self, line_value: List[str]) -> str:
        """Simule verify_conf() - vérifie la configuration"""
        ref_mode = line_value[1]
        ref_af = line_value[2]  
        ref_bat = line_value[3]
        ref_fs = line_value[4]
        
        # Configuration locale simulée
        local_mode = self.camera['mode']
        local_af = "0"  # AF off
        local_bat = self.battery['level']
        local_fs = self.card_free_space
        
        self.log("Should: Model: %s Mode: %s AF: %s Bat.: %s %% Card: %s Mo",
                self.camera['model'], ref_mode, ref_af, ref_bat, ref_fs)
        self.log("Have  : Model: %s Mode: %s AF: %s Bat.: %d %% Card: %d Mo",
                self.camera['model'], local_mode, local_af, local_bat, local_fs)
        
        # Vérifications
        if ref_mode != "-" and ref_mode != local_mode:
            self.log("Error : Incorrect Mode")
            return "nogo"
        elif ref_af != "-" and local_af != ref_af:
            self.log("Error : AF On")
            return "nogo"
        elif ref_bat != "-" and int(ref_bat) > local_bat:
            self.log("Error : Battery low")
            return "nogo"
        elif ref_fs != "-" and int(ref_fs) > local_fs:
            self.log("Error : Card full")
            return "nogo"
            
        self.log("Configuration accepted.")
        return "go"
        
    def read_config(self, line_value: List[str]) -> Tuple[int, int, int, int, int, int]:
        """Simule read_config() - lit la configuration des temps d'éclipse"""
        action = line_value[0]
        time_c1 = self.convert_second(int(line_value[1]), int(line_value[2]), int(line_value[3]))
        time_c2 = self.convert_second(int(line_value[4]), int(line_value[5]), int(line_value[6]))
        time_max = self.convert_second(int(line_value[7]), int(line_value[8]), int(line_value[9]))
        time_c3 = self.convert_second(int(line_value[10]), int(line_value[11]), int(line_value[12]))
        time_c4 = self.convert_second(int(line_value[13]), int(line_value[14]), int(line_value[15]))
        test_mode = int(line_value[16])
        
        self.log("Action: %s C1: %s:%s:%s/%ds C2: %s:%s:%s/%ds Max: %s:%s:%s/%ds C3: %s:%s:%s/%ds C4: %s:%s:%s/%ds TestMode: %d",
                action, line_value[1], line_value[2], line_value[3], time_c1,
                line_value[4], line_value[5], line_value[6], time_c2,
                line_value[7], line_value[8], line_value[9], time_max,
                line_value[10], line_value[11], line_value[12], time_c3,
                line_value[13], line_value[14], line_value[15], time_c4, test_mode)
                
        return time_c1, time_c2, time_max, time_c3, time_c4, test_mode
        
    def do_action(self, action: str, time_start: int, time_end: int, interval: float,
                 aperture: float, iso: int, shutter_speed: float, mlu_delay: int):
        """Simule do_action() - exécute une action"""
        
        self.log("Mirror lockup setup for delay: %d ms", mlu_delay)
        
        # Attente jusqu'au bon moment
        counter = 0
        while self.get_cur_secs() < (time_start - (mlu_delay/1000)):
            counter += 1
            if counter >= 80:  # Affiche "Waiting" toutes les 20s
                remaining = time_start - self.get_cur_secs()
                self.log("Waiting %d seconds", remaining)
                counter = 0
            # Simulation sleep 250ms
            self.current_time_seconds += 1  # Avance le temps simulé plus rapidement
            
        if action in ["Boucle", "Interval"]:
            if self.get_cur_secs() <= time_end:
                self.boucle(time_end, interval, iso, aperture, shutter_speed, mlu_delay)
            else:
                self.log("Too late! TimeEnd: %ds soit %s", time_end, self.pretty_time(time_end))
        elif action == "Photo":
            self.take_shoot(iso, aperture, shutter_speed, mlu_delay)
            
    def simulate_main(self) -> Dict[str, Any]:
        """Simule la fonction main() du script Lua"""
        self.log_entries.clear()
        self.log("==> eclipse_OZ.lua - Version : %s", self.version)
        self.log("Log begin.")
        
        # Chargement du script
        schedule_table = self.read_script("", self.config_file)
        
        if not schedule_table:
            return {"error": "Failed to load config file", "logs": self.log_entries}
        
        results = {
            "actions_executed": [],
            "logs": [],
            "config": {},
            "error": None
        }
        
        config_table = []
        
        for key, value in enumerate(schedule_table):
            action = value[0]
            
            if action == "Verif":
                ready2go = self.verify_conf(value)
                if ready2go == "nogo":
                    self.log("Configuration not accepted the sequence is stopped!")
                    results["error"] = "Configuration verification failed"
                    break
                else:
                    self.log("Configuration accepted.")
                    
            elif action == "Config":
                config_table = list(self.read_config(value))
                self.test_mode = bool(config_table[5])
                results["config"] = {
                    "C1": config_table[0], "C2": config_table[1], 
                    "Max": config_table[2], "C3": config_table[3], 
                    "C4": config_table[4], "TestMode": config_table[5]
                }
                self.log("Set test mode : %d", self.test_mode)
                
            elif action in ["Boucle", "Interval", "Photo"]:
                ref_time = value[1]
                oper_start = value[2]
                oper_end = value[6] if len(value) > 6 else ""
                
                if ref_time == "-":  # Mode absolu
                    time_start = self.convert_second(int(value[3]), int(value[4]), int(value[5]))
                    if len(value) > 9 and value[7] != "-" and value[8] != "-" and value[9] != "-":
                        time_end = self.convert_second(int(value[7]), int(value[8]), int(value[9]))
                    else:
                        time_end = 0
                else:  # Mode relatif
                    time_start = self.convert_time(ref_time, oper_start, 
                                                 self.convert_second(int(value[3]), int(value[4]), int(value[5])), 
                                                 config_table)
                    if action in ["Boucle", "Interval"] and len(value) > 9:
                        if value[7] != "-" and value[8] != "-" and value[9] != "-":
                            time_end = self.convert_time(ref_time, oper_end,
                                                       self.convert_second(int(value[7]), int(value[8]), int(value[9])),
                                                       config_table)
                        else:
                            time_end = 0
                    else:
                        time_end = 0
                        
                interval = 0
                if action == "Interval" and len(value) > 10 and value[10] != "-":
                    if time_end > 0:
                        interval = (time_end - time_start) / float(value[10])
                    else:
                        interval = 1.0
                elif len(value) > 10 and value[10] != "-":
                    interval = float(value[10])
                else:
                    interval = 1.0
                    
                aperture = float(value[11]) if len(value) > 11 and value[11] != "-" else 8.0
                iso = int(value[12]) if len(value) > 12 and value[12] != "-" else 200
                shutter_speed = float(value[13]) if len(value) > 13 and value[13] != "-" else 1.0/125
                mlu_delay = int(value[14]) if len(value) > 14 and value[14] != "-" else 0
                
                action_result = {
                    "action": action,
                    "time_start": time_start,
                    "time_end": time_end,
                    "interval": interval,
                    "aperture": aperture,
                    "iso": iso,
                    "shutter_speed": shutter_speed,
                    "mlu_delay": mlu_delay
                }
                
                results["actions_executed"].append(action_result)
                
                self.log("Action: %s TimeRef: %s OperStart: %s TimeStart: %ss OperEnd: %s TimeEnd: %ss Interval: %ss Aperture %.1f ISO %d ShutterSpeed: %ss MluDelay: %dms",
                        action, ref_time, oper_start, time_start, oper_end, time_end, 
                        interval, aperture, iso, shutter_speed, mlu_delay)
                
                # Exécution de l'action
                self.do_action(action, time_start, time_end, interval, aperture, iso, shutter_speed, mlu_delay)
                
            self.log("Line %d finish go to the next line.", key)
            
        self.log("Normal exit.")
        results["logs"] = self.log_entries.copy()
        return results


def run_lua_simulation(config_file: str, start_time_hms: Tuple[int, int, int] = (20, 15, 0)) -> Dict[str, Any]:
    """
    Lance une simulation du script Lua avec le fichier de configuration donné
    
    Args:
        config_file: Chemin vers le fichier de configuration
        start_time_hms: Temps de départ de la simulation (heures, minutes, secondes)
    
    Returns:
        Dictionnaire contenant les résultats de la simulation
    """
    simulator = LuaSimulator(config_file, test_mode=True)
    simulator.set_current_time(*start_time_hms)
    
    return simulator.simulate_main()


if __name__ == "__main__":
    # Test de base
    config_file = "../SOLARECL.TXT"
    results = run_lua_simulation(config_file)
    
    print("\n=== Résultats de la simulation Lua ===")
    print(f"Erreur: {results.get('error', 'Aucune')}")
    print(f"Actions exécutées: {len(results['actions_executed'])}")
    print(f"Logs générés: {len(results['logs'])}")