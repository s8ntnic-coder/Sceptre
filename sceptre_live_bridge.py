"""
Sceptre Runtime Configuration File Monitor Bridge
==================================================
Bypasses restrictive socket networks by monitoring SCEPTRE's 
runtime user parameters and ini files directly for active tuner settings.
"""

import os
import re
import time
from typing import Optional
from sceptre_video_analyzer import SceptreVideoAnalyzer


class RuntimeSceptreMonitor:
    """
    Scans local SCEPTRE workspaces and system deployment configurations 
    for active frequency parameter shifts.
    """
    def __init__(self, user_home: str = "/home/dingo1"):
        self.user_home = user_home
        self.last_mtime = 0.0
        
        # Array of target locations where 3dB Labs structures configuration logs
        self.target_files = [
            os.path.join(self.user_home, ".config/3db_labs/sceptre.ini"),
            os.path.join(self.user_home, ".sceptre/workspace.xml"),
            os.path.join(self.user_home, "Documents/Sceptre/sceptre.ini"),
            "./sceptre.ini"  # Local fallbacks
        ]
        self.active_config_path: Optional[str] = None
        self._locate_active_config()

    def _locate_active_config(self):
        """Finds which runtime configuration file is actively available."""
        for path in self.target_files:
            if os.path.exists(path):
                self.active_config_path = path
                print(f"[MONITOR] Attached to SCEPTRE configuration track: {path}")
                return
        
        print("[MONITOR WARNING] Active runtime config file not found yet.")
        print("  -> Creating a local fallback './sceptre.ini' for continuous tracking.")
        self.active_config_path = "./sceptre.ini"
        if not os.path.exists(self.active_config_path):
            with open(self.active_config_path, "w") as f:
                f.write("[Tuner]\nfrequency=148.5\n")

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Polls the file system modifications to capture configuration shifts.
        """
        if not self.active_config_path or not os.path.exists(self.active_config_path):
            return None

        try:
            current_mtime = os.path.getmtime(self.active_config_path)
            # Only read the file if it has been updated since our last check
            if current_mtime == self.last_mtime and self.last_mtime != 0.0:
                return None
                
            self.last_mtime = current_mtime
            
            with open(self.active_config_path, "r", errors="ignore") as f:
                content = f.read()

            # Dynamic regular expressions looking for standard frequency attributes
            freq_match = re.search(r'(?:frequency|center_freq|freq|center_frequency)\s*=\s*([0-9.]+)', content, re.IGNORECASE)
            if freq_match:
                val = float(freq_match.group(1))
                # Adjust scales dynamically if SCEPTRE saved the parameters in raw Hz unit values
                return val / 1e6 if val > 50000 else val

            # Fallback block parsing XML layout elements if tracking workspace.xml patterns
            xml_match = re.search(r'<(?:frequency|center_freq)>([0-9.]+)</', content, re.IGNORECASE)
            if xml_match:
                val = float(xml_match.group(1))
                return val / 1e6 if val > 50000 else val

        except Exception as e:
            print(f"[MONITOR ERROR] Problem accessing configuration state: {e}")
            
        return None


def run_file_monitor_loop(profile: str = 'standard'):
    monitor = RuntimeSceptreMonitor()
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (FILE SYSTEM MONITOR)")
    print("="*75)
    print("Press Ctrl+C to terminate runtime capturing loops.\n")

    last_freq = 0.0
    try:
        while True:
            live_freq = monitor.get_live_frequency_mhz()
            
            if live_freq and abs(live_freq - last_freq) > 0.05:
                print(f"\n[EVENT] Tuner parameter modification logged: {live_freq:.3f} MHz")
                
                # Execute fixed standard matching formulas
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
                
            time.sleep(1.0)  # Graceful polling interval cadence to avoid CPU spin locks
            
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by operator loop request.")


if __name__ == "__main__":
    run_file_monitor_loop(profile='standard')
