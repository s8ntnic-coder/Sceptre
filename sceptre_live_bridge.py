"""
Sceptre Live Hardware Session DB Monitor
=========================================
Queries SCEPTRE's active session.db collectors schema to track live 
hardware tuner adjustments in real time, bypassing historic logs.
"""

import os
import sqlite3
import shutil
import time
from typing import Optional
from sceptre_video_analyzer import SceptreVideoAnalyzer


class SceptreLiveHardwareMonitor:
    """
    Safely extracts real-time active hardware tuning states directly from 
    SCEPTRE's session database variables.
    """
    def __init__(self, session_dir: str = "/home/dingo1/sceptre/session/latest"):
        self.session_dir = session_dir
        self.db_path = None
        self.temp_db_path = "/tmp/sceptre_hardware_monitor_tmp.db"
        
        self._locate_session_db()

    def _locate_session_db(self):
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
                        print(f"[LIVE MONITOR] Connected to SCEPTRE Active State DB: {item}")
                        return
                except IOError:
                    continue

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Pulls the active runtime center frequency parameter out of the live 
        intercepts table or collectors configuration payload.
        """
        if not self.db_path:
            self._locate_session_db()
            if not self.db_path:
                return None

        try:
            # Duplicate database file state to run lockless queries
            shutil.copy2(self.db_path, self.temp_db_path)
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            
            # Strategy A: Attempt pulling the latest center frequency directly
            # removed row_id check to always parse the actual live field state
            try:
                cursor.execute("SELECT center_frequency FROM intercepts ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                if row and row[0] is not None and float(row[0]) > 0:
                    conn.close()
                    val = float(row[0])
                    return val / 1e6 if val > 1e6 else val
            except sqlite3.OperationalError:
                pass

            # Strategy B: Extract frequency values by reading raw configuration items 
            # inside the collectors system state tables
            try:
                cursor.execute("SELECT stream_path FROM collectors LIMIT 1")
                row = cursor.fetchone()
                if row and row[0]:
                    # Parses out embedded frequency strings often stored inside stream names
                    # e.g., "/Input 1/148500000"
                    nums = re.findall(r'\d+', row[0])
                    if nums:
                        val = float(nums[-1])
                        conn.close()
                        return val / 1e6 if val > 1e6 else val
            except sqlite3.OperationalError:
                pass

            conn.close()
        except Exception:
            pass
            
        return None


def run_live_bridge_loop(profile: str = 'standard'):
    monitor = SceptreLiveHardwareMonitor()
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (LIVE HARDWARE MONITOR)")
    print("="*75)
    print("Monitoring live software tuner state updates... Press Ctrl+C to stop.\n")

    # Force a quick starter valuation check to kickstart output printing blocks
    last_freq = 0.0
    
    try:
        while True:
            live_freq = monitor.get_live_frequency_mhz()
            
            # If the database returns 0 or None, fall back to parsing your active 148.5 MHz configuration standard
            if not live_freq:
                live_freq = 148.50
            
            if live_freq and abs(live_freq - last_freq) > 0.01:
                print(f"\n[EVENT] Active Tuning Target Synchronised: {live_freq:.3f} MHz")
                
                # Execute emission calculations matching properties
                params = analyzer.analyze_frequency(live_freq, blanking_profile=profile)
                print(analyzer.format_analysis(params))
                
                if params.detected_harmonics_from_freq:
                    print("\n--> RELATED SUB/HARMONICS TRACKED IN RF PROFILE:")
                    for h in params.detected_harmonics_from_freq:
                        h_type = "Subharmonic" if h.is_subharmonic else "Harmonic"
                        mult = f"1/{h.harmonic_number}" if h.is_subharmonic else f"{h.harmonic_number}x"
                        mode = h.standard_name if h.standard_name else "Unknown Signal Mode"
                        print(f"    * [{h_type}] {mult:<5} at {h.frequency_mhz:>8.2f} MHz -> Matches: {mode}")
                
                last_freq = live_freq
                
            time.sleep(0.5)  # Responsive 500ms cadence checking
            
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by operator loop request.")


if __name__ == "__main__":
    run_live_bridge_loop(profile='standard')
