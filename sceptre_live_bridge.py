"""
Sceptre Production Live Workspace Bridge
=========================================
Connects to 3dB Labs SCEPTRE by monitoring active runtime database tables
and parsing configuration fallback trees in real-time.
"""

import os
import re
import sqlite3
import shutil
import time
from typing import Optional
from sceptre_video_analyzer import SceptreVideoAnalyzer


class SceptreProductionMonitor:
    """
    Automates real-time parameter syncing from 3dB Labs SCEPTRE session profiles.
    """
    def __init__(self, 
                 session_dir: str = "/home/dingo1/sceptre/session/latest", 
                 cfg_file: str = "/home/dingo1/sceptre/cfg/sceptre.cfg"):
        self.session_dir = session_dir
        self.cfg_file = cfg_file
        self.db_path = None
        self.temp_db_path = "/tmp/sceptre_live_bridge_tmp.db"
        self.last_max_id = 0
        self.last_cfg_mtime = 0.0

    def _find_active_db(self):
        """Scans session workspace for the runtime SQLite database tracking state."""
        if not os.path.exists(self.session_dir):
            return
        for item in os.listdir(self.session_dir):
            full_path = os.path.join(self.session_dir, item)
            if os.path.isfile(full_path):
                try:
                    with open(full_path, "rb") as f:
                        header = f.read(15)
                    if b"SQLite format 3" in header:
                        self.db_path = full_path
                        return
                except IOError:
                    continue

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Extracts active frequencies from the live database or config file parameters.
        """
        # Strategy A: Check active session interception database tables
        if not self.db_path:
            self._find_active_db()
            
        if self.db_path:
            try:
                shutil.copy2(self.db_path, self.temp_db_path)
                conn = sqlite3.connect(self.temp_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id, center_frequency FROM intercepts ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    row_id, center_freq = row
                    if row_id > self.last_max_id:
                        self.last_max_id = row_id
                        return float(center_freq) / 1e6 if center_freq > 1e6 else float(center_freq)
            except Exception:
                pass # Failover dynamically to config tracking

        # Strategy B: Dynamic check on file updates to configuration preferences
        if os.path.exists(self.cfg_file):
            try:
                current_mtime = os.path.getmtime(self.cfg_file)
                if current_mtime > self.last_cfg_mtime:
                    self.last_cfg_mtime = current_mtime
                    with open(self.cfg_file, "r", errors="ignore") as f:
                        content = f.read()
                    
                    # Target input_frequency or tuner_frequency blocks in the active config profile
                    freq_match = re.search(r'(?:tuner_frequency|input_frequency|frequency)\s*=\s*([0-9.]+)', content)
                    if freq_match:
                        val = float(freq_match.group(1))
                        return val / 1e6 if val > 1e6 else val
            except Exception as e:
                print(f"[WARN] Error parsing configuration state file: {e}")

        return None


def main_loop():
    # Attempt parsing configuration across both active system parameters
    monitor = SceptreProductionMonitor(
        session_dir="/home/dingo1/sceptre/session/latest",
        cfg_file="/home/dingo1/sceptre/cfg/sceptre.cfg"  # Update path if saved as sceptre.ini
    )
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (PRODUCTION MONITOR)")
    print("="*75)
    print("Scanning active hardware configurations... Press Ctrl+C to stop.\n")

    last_freq = 0.0
    while True:
        try:
            live_freq = monitor.get_live_frequency_mhz()
            
            if live_freq and abs(live_freq - last_freq) > 0.01:
                print(f"\n[EVENT] Active SCEPTRE Frequency Shift: {live_freq:.3f} MHz")
                
                # Execute timing calculations
                params = analyzer.analyze_frequency(live_freq, blanking_profile='standard')
                print(analyzer.format_analysis(params))
                
                if params.detected_harmonics_from_freq:
                    print("\n--> HARMONIC TRACE COUPLING PAIRS FOUND:")
                    for h in params.detected_harmonics_from_freq:
                        h_type = "Subharmonic" if h.is_subharmonic else "Harmonic"
                        mult = f"1/{h.harmonic_number}" if h.is_subharmonic else f"{h.harmonic_number}x"
                        mode = h.standard_name if h.standard_name else "Custom Mode Frame"
                        print(f"    * [{h_type}] {mult:<5} at {h.frequency_mhz:>8.2f} MHz -> Matches: {mode}")
                        
                last_freq = live_freq
                
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Exiting gracefully.")
            break


if __name__ == "__main__":
    main_loop()
"""
Sceptre Live Session DB Monitor Bridge
=======================================
Connects natively to 3dB Labs SCEPTRE's runtime SQLite session database.
Extracts the latest tracked intercept frequency to feed the video analyzer.
"""

import os
import sqlite3
import shutil
import time
from typing import Optional
from sceptre_video_analyzer import SceptreVideoAnalyzer


class SceptreSessionDbMonitor:
    """
    Safely opens and queries SCEPTRE's active SQLite database files.
    """
    def __init__(self, session_dir: str = "/home/dingo1/sceptre/session/latest"):
        self.session_dir = session_dir
        self.db_path = None
        self.temp_db_path = "/tmp/sceptre_session_monitor_tmp.db"
        self.last_max_id = 0
        
        self._locate_session_db()

    def _locate_session_db(self):
        """Scans the latest folder for the file containing SQLite headers."""
        if not os.path.exists(self.session_dir):
            return

        for item in os.listdir(self.session_dir):
            full_path = os.path.join(self.session_dir, item)
            if os.path.isfile(full_path):
                try:
                    with open(full_path, "rb") as f:
                        header = f.read(15)
                    if b"SQLite format 3" in header:
                        self.db_path = full_path
                        print(f"[DB MONITOR] Locked onto SCEPTRE Runtime DB: {item}")
                        return
                except IOError:
                    continue

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Safely takes a transient snapshot copy of the database to read 
        the latest 'center_frequency' metric from the 'intercepts' table.
        """
        if not self.db_path:
            self._locate_session_db()
            if not self.db_path:
                return None

        try:
            # Copy to tmp directory to bypass active database file write locks
            shutil.copy2(self.db_path, self.temp_db_path)
            
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            
            # Query the newest row sorted by the auto-incrementing ID column
            cursor.execute(
                "SELECT id, center_frequency FROM intercepts ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            
            if row:
                row_id, center_freq = row
                
                # Only report if it's a completely new database log entry row
                if row_id > self.last_max_id:
                    self.last_max_id = row_id
                    
                    # Convert to MHz if SCEPTRE saves the center frequency metric in Hz
                    if center_freq > 1e6:
                        return float(center_freq) / 1e6
                    return float(center_freq)
                    
        except sqlite3.OperationalError:
            pass  # Suppress errors if we try to copy a database mid-write
        except Exception as e:
            print(f"[DB ERROR] Failed reading session tracking state: {e}")
            
        return None


def run_db_bridge_loop(profile: str = 'standard'):
    monitor = SceptreSessionDbMonitor()
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (SQLITE LIVE INTERFACE)")
    print("="*75)
    print("Press Ctrl+C to terminate runtime capturing loops.\n")

    last_freq = 0.0
    try:
        while True:
            live_freq = monitor.get_live_frequency_mhz()
            
            if live_freq and abs(live_freq - last_freq) > 0.01:
                print(f"\n[EVENT] New Intercept Logged in SCEPTRE DB: {live_freq:.3f} MHz")
                
                # Execute emission metrics analysis math
                video_params = analyzer.analyze_frequency(live_freq, blanking_profile=profile)
                print(analyzer.format_analysis(video_params))
                
                if video_params.detected_harmonics_from_freq:
                    print("\n--> RELATED SUB/HARMONICS TRACKED IN RF PROFILE:")
                    for h in video_params.detected_harmonics_from_freq:
                        h_type = "Subharmonic" if h.is_subharmonic else "Harmonic"
                        mult = f"1/{h.harmonic_number}" if h.is_subharmonic else f"{h.harmonic_number}x"
                        mode = h.standard_name if h.standard_name else "Unknown Signal Mode"
                        print(f"    * [{h_type}] {mult:<5} at {h.frequency_mhz:>8.2f} MHz -> Matches: {mode}")
                
                last_freq = live_freq
                
            time.sleep(0.5)  # Quick 500ms sleep loop cadence
            
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by operator loop request.")


if __name__ == "__main__":
    run_db_bridge_loop(profile='standard')
