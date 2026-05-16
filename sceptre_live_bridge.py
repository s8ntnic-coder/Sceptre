"""
Sceptre Production Session Data Bridge
=======================================
Directly targets 3dB Labs SCEPTRE's runtime session database file.
Extracts live software tuner center frequencies to drive video emission math.
"""

import os
import sqlite3
import shutil
import time
from typing import Optional
from sceptre_video_analyzer import SceptreVideoAnalyzer


class SceptreSessionDbWatcher:
    """
    Safely captures live software tuner attributes out of SCEPTRE's active session DB.
    """
    def __init__(self, session_dir: str = "/home/dingo1/sceptre/session/latest"):
        self.session_dir = session_dir
        self.db_path = None
        self.temp_db_path = "/tmp/sceptre_production_bridge_tmp.db"
        
        self._locate_database()

    def _locate_database(self):
        """Locates the active SQLite binary workspace file inside the session folder."""
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
                        print(f"[DB WATCHER] Connected to SCEPTRE Live Database: {item}")
                        return
                except IOError:
                    continue

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Takes a transient copy of the active session database file, then queries 
        the latest 'center_frequency' metric from the intercepts telemetry loop.
        """
        if not self.db_path:
            self._locate_database()
            if not self.db_path:
                return None

        try:
            # Create a localized clone block to avoid locking errors while SCEPTRE writes
            shutil.copy2(self.db_path, self.temp_db_path)
            
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            
            # Query the newest row sorted by the internal auto-increment tracking column
            cursor.execute(
                "SELECT center_frequency FROM intercepts ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] is not None:
                center_freq = float(row[0])
                # Automatically normalize values down to MHz if saved in raw Hz notation scale
                return center_freq / 1e6 if center_freq > 1e6 else center_freq
                
        except sqlite3.OperationalError:
            pass  # Suppress lock contentions during active write executions
        except Exception as e:
            print(f"[DB WATCHER ERROR] Problem parsing session variables: {e}")
            
        return None


def run_bridge_loop():
    monitor = SceptreSessionDbWatcher()
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (SQLITE SESSION WATCH)")
    print("="*75)
    print("Monitoring active hardware data tables... Press Ctrl+C to terminate loops.\n")

    # Seed the console output immediately on launch with your verified 148.50 MHz baseline
    last_freq = 148.50
    print(f"[INITIALISATION] Latching onto baseline emission target: {last_freq:.3f} MHz")
    params = analyzer.analyze_frequency(last_freq, blanking_profile='standard')
    print(analyzer.format_analysis(params))
    
    if params.detected_harmonics_from_freq:
        print("\n--> COMPATIBLE HARMONIC EMISSION PROFILE DETECTED:")
        for h in params.detected_harmonics_from_freq:
            h_type = "Subharmonic" if h.is_subharmonic else "Harmonic"
            mult = f"1/{h.harmonic_number}" if h.is_subharmonic else f"{h.harmonic_number}x"
            mode = h.standard_name if h.standard_name else "Custom Raster Frame"
            print(f"    * [{h_type}] {mult:<5} at {h.frequency_mhz:>8.2f} MHz -> Matches: {mode}")

    print("\n[STATUS] Listening for active software tuner updates...")
    
    while True:
        try:
            live_freq = monitor.get_live_frequency_mhz()
            
            # Print update statements if the user implements a distinct tune adjustment
            if live_freq and abs(live_freq - last_freq) > 0.01:
                print(f"\n[EVENT] Active Tuner Variation Intercepted: {live_freq:.3f} MHz")
                
                # Forward to timing generation math parameters
                params = analyzer.analyze_frequency(live_freq, blanking_profile='standard')
                print(analyzer.format_analysis(params))
                
                if params.detected_harmonics_from_freq:
                    print("\n--> RELATED SUB/HARMONICS TRACKED IN RF PROFILE:")
                    for h in params.detected_harmonics_from_freq:
                        h_type = "Subharmonic" if h.is_subharmonic else "Harmonic"
                        mult = f"1/{h.harmonic_number}" if h.is_subharmonic else f"{h.harmonic_number}x"
                        mode = h.standard_name if h.standard_name else "Unknown Signal Mode"
                        print(f"    * [{h_type}] {mult:<5} at {h.frequency_mhz:>8.2f} MHz -> Matches: {mode}")
                        
                last_freq = live_freq
                
            time.sleep(0.4)  # 400ms polling cadences minimize system load
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Exiting runtime session tracker loop.")
            break


if __name__ == "__main__":
    run_bridge_loop()
