"""
Sceptre Live Dynamic Workspace Monitor
=======================================
Directly captures real-time dynamic tuner frequencies from SCEPTRE session profiles,
accounting for relative_tune setups by targeting active UI context blocks.
"""

import os
import re
import sqlite3
import shutil
import time
from typing import Optional
from sceptre_video_analyzer import SceptreVideoAnalyzer


class SceptreTunerMonitor:
    """
    Tracks precise active live-tuned frequencies from 3dB Labs SCEPTRE configuration states.
    """
    def __init__(self, 
                 session_dir: str = "/home/dingo1/sceptre/session/latest", 
                 cfg_file: str = "/home/dingo1/sceptre/cfg/sceptre.cfg"):
        self.session_dir = session_dir
        self.cfg_file = cfg_file
        self.db_path = None
        self.temp_db_path = "/tmp/sceptre_tuner_bridge_tmp.db"
        self.last_cfg_mtime = 0.0

    def _find_active_db(self):
        """Scans the active directory layout to isolate the running database file."""
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
        Extracts active frequencies by isolating true live dynamic software tuners.
        """
        # Strategy A: Check active configuration snapshot file updates (Most reliable for live scrolling)
        if os.path.exists(self.cfg_file):
            try:
                current_mtime = os.path.getmtime(self.cfg_file)
                if current_mtime > self.last_cfg_mtime:
                    self.last_cfg_mtime = current_mtime
                    with open(self.cfg_file, "r", errors="ignore") as f:
                        content = f.read()
                    
                    # Target the live software tuner blocks specifically (e.g., tuner_frequency = 148500000)
                    # This intentionally bypasses the fixed hardware input block frequencies (1097.5 MHz)
                    tuner_match = re.findall(r'tuner_frequency\s*=\s*([0-9.]+)', content)
                    if tuner_match:
                        val = float(tuner_match[-1])
                        return val / 1e6 if val > 1e6 else val

                    # Fallback context match for standalone software input tracking values
                    input_freq_match = re.findall(r'input_frequency\s*=\s*([0-9.]+)', content)
                    if input_freq_match:
                        val = float(input_freq_match[-1])
                        return val / 1e6 if val > 1e6 else val
            except Exception as e:
                print(f"[WARN] Error reading config: {e}")

        # Strategy B: Extract frequency values by checking temporary table logs
        if not self.db_path:
            self._find_active_db()
            
        if self.db_path:
            try:
                shutil.copy2(self.db_path, self.temp_db_path)
                conn = sqlite3.connect(self.temp_db_path)
                cursor = conn.cursor()
                
                # Pull raw stream details from your collectors table layout map
                cursor.execute("SELECT stream_path FROM collectors ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                conn.close()
                
                if row and row[0]:
                    # Extract numeric components directly out of strings like "/Input 1/148500000"
                    nums = re.findall(r'\d+', row[0])
                    if nums:
                        val = float(nums[-1])
                        if val > 1e6:
                            return val / 1e6
            except Exception:
                pass

        return None


def run_bridge():
    monitor = SceptreTunerMonitor(
        session_dir="/home/dingo1/sceptre/session/latest",
        cfg_file="/home/dingo1/sceptre/cfg/sceptre.cfg"
    )
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (LIVE TUNER BRIDGE)")
    print("="*75)
    print("Monitoring software tuner shifts... Press Ctrl+C to terminate loops.\n")

    last_freq = 0.0
    while True:
        try:
            live_freq = monitor.get_live_frequency_mhz()
            
            if live_freq and abs(live_freq - last_freq) > 0.01:
                print(f"\n[EVENT] Live Software Tuner Adjust detected: {live_freq:.3f} MHz")
                
                # Process video timing conversion mathematics
                params = analyzer.analyze_frequency(live_freq, blanking_profile='standard')
                print(analyzer.format_analysis(params))
                
                if params.detected_harmonics_from_freq:
                    print("\n--> RELATED EMISSION HARMONICS IDENTIFIED:")
                    for h in params.detected_harmonics_from_freq:
                        h_type = "Subharmonic" if h.is_subharmonic else "Harmonic"
                        mult = f"1/{h.harmonic_number}" if h.is_subharmonic else f"{h.harmonic_number}x"
                        mode = h.standard_name if h.standard_name else "Custom Mode Layout"
                        print(f"    * [{h_type}] {mult:<5} at {h.frequency_mhz:>8.2f} MHz -> Matches: {mode}")
                        
                last_freq = live_freq
                
            time.sleep(0.3)  # Faster 300ms polling cadence to capture fast user clicks instantly
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Exiting bridge connection layer.")
            break


if __name__ == "__main__":
    run_bridge()
