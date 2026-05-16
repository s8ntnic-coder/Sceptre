"""
Sceptre Live Session Monitor Bridge
====================================
Directly tracks the live 3dB Labs SCEPTRE active workspace session directory.
Parses runtime updates automatically to drive real-time video emission math.
"""

import os
import re
import time
from typing import Optional, Dict
from sceptre_video_analyzer import SceptreVideoAnalyzer


class SceptreSessionMonitor:
    """
    Watches file state changes inside SCEPTRE's active session tracking directory.
    """
    def __init__(self, session_dir: str = "/home/dingo1/sceptre/session/latest"):
        self.session_dir = session_dir
        self.last_mtimes: Dict[str, float] = {}
        
        print(f"[MONITOR] Initialising SCEPTRE session monitor target: {self.session_dir}")
        if not os.path.exists(self.session_dir):
            print(f"[MONITOR WARNING] Target directory path does not exist yet: {self.session_dir}")
            print("  -> The script will continuously check for this folder to spin up...")

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Scans all files inside the session directory for real-time frequency edits.
        """
        if not os.path.exists(self.session_dir):
            return None

        try:
            # Check all items in the session snapshot folder
            for item in os.listdir(self.session_dir):
                full_path = os.path.join(self.session_dir, item)
                
                # Skip subdirectories or structural socket descriptors
                if not os.path.isfile(full_path):
                    continue

                try:
                    current_mtime = os.path.getmtime(full_path)
                except OSError:
                    continue  # Handle temporary lock transitions gracefully

                # Check if this file was created or modified since our last parsing run
                if full_path not in self.last_mtimes or current_mtime > self.last_mtimes[full_path]:
                    self.last_mtimes[full_path] = current_mtime
                    
                    # Read and analyze the updated file contents
                    try:
                        with open(full_path, "r", errors="ignore") as f:
                            content = f.read()
                    except IOError:
                        continue

                    # Regex captures standard tuning fields (e.g., "frequency: 148500000", "center_freq = 148.5")
                    freq_match = re.search(
                        r'(?:frequency|center_freq|freq|center_frequency|tuned_freq|cf)\s*[:=]\s*([0-9.]+)', 
                        content, 
                        re.IGNORECASE
                    )
                    
                    if freq_match:
                        val = float(freq_match.group(1))
                        # Automatically convert raw Hz or kHz units down to the expected MHz scale
                        if val > 1e6:      # Looks like raw Hz (e.g., 148500000)
                            return val / 1e6
                        elif val > 50000:  # Looks like kHz (e.g., 148500)
                            return val / 1e3
                        return val

                    # Backup tracker looking for structured XML configuration syntax blocks
                    xml_match = re.search(r'<(?:frequency|center_freq|freq)>([0-9.]+)</', content, re.IGNORECASE)
                    if xml_match:
                        val = float(xml_match.group(1))
                        if val > 1e6:
                            return val / 1e6
                        elif val > 50000:
                            return val / 1e3
                        return val

        except Exception as e:
            print(f"[MONITOR ERROR] Session tracking processing exception: {e}")
            
        return None


def run_session_bridge_loop(profile: str = 'standard'):
    monitor = SceptreSessionMonitor(session_dir="/home/dingo1/sceptre/session/latest")
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (LIVE SESSION BRIDGE)")
    print("="*75)
    print("Press Ctrl+C to terminate runtime capturing loops.\n")

    last_freq = 0.0
    try:
        while True:
            live_freq = monitor.get_live_frequency_mhz()
            
            # Trigger updates when a verifiable tuning shift occurs
            if live_freq and abs(live_freq - last_freq) > 0.05:
                print(f"\n[EVENT] Active SCEPTRE Session Tuner Shift: {live_freq:.3f} MHz")
                
                # Run the analyzer metrics calculations
                video_params = analyzer.analyze_frequency(live_freq, blanking_profile=profile)
                print(analyzer.format_analysis(video_params))
                
                # Check for linked emissions harmonics
                if video_params.detected_harmonics_from_freq:
                    print("\n--> RELATED SUB/HARMONICS TRACKED IN RF PROFILE:")
                    for h in video_params.detected_harmonics_from_freq:
                        h_type = "Subharmonic" if h.is_subharmonic else "Harmonic"
                        mult = f"1/{h.harmonic_number}" if h.is_subharmonic else f"{h.harmonic_number}x"
                        mode = h.standard_name if h.standard_name else "Unknown Signal Mode"
                        print(f"    * [{h_type}] {mult:<5} at {h.frequency_mhz:>8.2f} MHz -> Matches: {mode}")
                
                last_freq = live_freq
                
            time.sleep(0.5)  # Responsive 500ms cadence window to catch live clicks quickly
            
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by operator loop request.")


if __name__ == "__main__":
    run_session_bridge_loop(profile='standard')
