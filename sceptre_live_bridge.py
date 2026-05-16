"""
Sceptre Workspace Configuration Target Bridge
==============================================
Directly targets the active 3dB Labs SCEPTRE configuration workspace 
directory path to intercept software tuner adjustments in real-time.
"""

import os
import re
import time
from typing import Optional, List
from sceptre_video_analyzer import SceptreVideoAnalyzer


class SceptreCfgMonitor:
    """
    Monitors targeted config files in the active SCEPTRE deployment path.
    """
    def __init__(self, cfg_dir: str = "/home/dingo1/sceptre/cfg"):
        self.cfg_dir = cfg_dir
        self.tracked_files: List[str] = []
        self.last_mtimes: dict = {}
        
        self._discover_target_files()

    def _discover_target_files(self):
        """Scans the custom config folder layout for parameter maps."""
        if not os.path.exists(self.cfg_dir):
            print(f"[MONITOR ERROR] Directory not found: {self.cfg_dir}")
            return

        # Dynamically map common files inside the user's specific target config folder
        potential_files = ["sceptre.cfg", "tuner.cfg", "receiver.cfg", "sceptre.ini", "default.cfg"]
        
        print(f"[MONITOR] Inspecting SCEPTRE config workspace layout at: {self.cfg_dir}")
        for filename in potential_files:
            full_path = os.path.join(self.cfg_dir, filename)
            if os.path.exists(full_path):
                self.tracked_files.append(full_path)
                self.last_mtimes[full_path] = 0.0
                print(f"  -> Successfully attached track targeting: {filename}")

        # Dynamic fallback: track all .cfg files in the folder if defaults aren't there
        if not self.tracked_files:
            for item in os.listdir(self.cfg_dir):
                if item.endswith(".cfg") or item.endswith(".ini"):
                    full_path = os.path.join(self.cfg_dir, item)
                    self.tracked_files.append(full_path)
                    self.last_mtimes[full_path] = 0.0
                    print(f"  -> Dynamic track attached targeting: {item}")

        if not self.tracked_files:
            print("[MONITOR WARNING] No configuration structures discovered yet inside path folder.")

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Scans tracked system files for internal modification state updates.
        """
        for path in self.tracked_files:
            if not os.path.exists(path):
                continue
                
            try:
                current_mtime = os.path.getmtime(path)
                # Skip reading if the file has not been saved or rewritten
                if current_mtime == self.last_mtimes[path] and self.last_mtimes[path] != 0.0:
                    continue
                    
                self.last_mtimes[path] = current_mtime
                
                with open(path, "r", errors="ignore") as f:
                    content = f.read()

                # Dynamic regex scanning for standard frequency allocation items
                freq_match = re.search(r'(?:frequency|center_freq|freq|center_frequency|tuned_freq)\s*[:=]\s*([0-9.]+)', content, re.IGNORECASE)
                if freq_match:
                    val = float(freq_match.group(1))
                    # Handle raw Hz to MHz scale conversions automatically
                    return val / 1e6 if val > 50000 else val
                    
            except Exception as e:
                print(f"[MONITOR ERROR] Problem accessing configuration state: {e}")
                
        return None


def run_targeted_monitor_loop(profile: str = 'standard'):
    # Targets the exact local user home path verified by your terminal session
    monitor = SceptreCfgMonitor(cfg_dir="/home/dingo1/sceptre/cfg")
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (CFG TARGET INTERFACE)")
    print("="*75)
    print("Press Ctrl+C to terminate runtime capturing loops.\n")

    last_freq = 0.0
    try:
        while True:
            live_freq = monitor.get_live_frequency_mhz()
            
            if live_freq and abs(live_freq - last_freq) > 0.05:
                print(f"\n[EVENT] SCEPTRE configuration layout update detected: {live_freq:.3f} MHz")
                
                # Run analyzer math calculation blocks
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
                
            time.sleep(1.0) # 1-second cadence polling protects file handles
            
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by operator loop request.")


if __name__ == "__main__":
    run_targeted_monitor_loop(profile='standard')
