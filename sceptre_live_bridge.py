"""
Sceptre Real-Time Session XML/JSON Watcher
==========================================
Monitors SCEPTRE's volatile text session updates inside /session/latest.
Extracts real-time mouse drag and tuner clicks instantly without DB write locks.
"""

import os
import re
import time
from typing import Optional, Dict
from sceptre_video_analyzer import SceptreVideoAnalyzer


class SceptreSessionTextWatcher:
    """
    Watches and extracts real-time active tuner parameter values out of 
    SCEPTRE's transient session runtime files.
    """
    def __init__(self, session_dir: str = "/home/dingo1/sceptre/session/latest"):
        self.session_dir = session_dir
        self.last_mtimes: Dict[str, float] = {}
        
        print(f"[MONITOR] Initialising real-time session watcher target: {self.session_dir}")

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Scans volatile text parameters files inside the live session folder.
        """
        if not os.path.exists(self.session_dir):
            return None

        try:
            for item in os.listdir(self.session_dir):
                full_path = os.path.join(self.session_dir, item)
                
                # We want text configuration mappings, skip the binary .db databases
                if not os.path.isfile(full_path) or item.endswith(".db"):
                    continue

                try:
                    current_mtime = os.path.getmtime(full_path)
                except OSError:
                    continue

                # Check if SCEPTRE just updated this configuration file
                if full_path not in self.last_mtimes or current_mtime > self.last_mtimes[full_path]:
                    self.last_mtimes[full_path] = current_mtime
                    
                    try:
                        with open(full_path, "r", errors="ignore") as f:
                            content = f.read()
                    except IOError:
                        continue

                    # Look for active tuner configurations (accounts for relative tuning structures)
                    freq_match = re.search(
                        r'(?:tuner_frequency|input_frequency|frequency|tuned_freq|cf)\s*["\':=]+\s*([0-9.]+)', 
                        content, 
                        re.IGNORECASE
                    )
                    
                    if freq_match:
                        val = float(freq_match.group(1))
                        # Normalise raw Hz/kHz allocation variables down to MHz scale
                        if val > 1e6:
                            return val / 1e6
                        elif val > 50000:
                            return val / 1e3
                        return val

                    # Secondary pass looking for structural XML tags (<tuner_frequency>148500000</tuner_frequency>)
                    xml_match = re.search(r'<(?:tuner_frequency|frequency|center_freq)>([0-9.]+)</', content, re.IGNORECASE)
                    if xml_match:
                        val = float(xml_match.group(1))
                        if val > 1e6:
                            return val / 1e6
                        elif val > 50000:
                            return val / 1e3
                        return val
                        
        except Exception as e:
            print(f"[MONITOR ERROR] Session tracking anomaly: {e}")
            
        return None


def run_bridge():
    monitor = SceptreSessionTextWatcher()
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (LIVE VOLATILE WATCH)")
    print("="*75)
    print("Listening for real-time tuner modifications... Press Ctrl+C to stop.\n")

    # Drop an instant initialization log down onto your console screen
    last_freq = 148.50
    print(f"[INITIALISATION] Latching onto baseline emission target: {last_freq:.3f} MHz")
    params = analyzer.analyze_frequency(last_freq, blanking_profile='standard')
    print(analyzer.format_analysis(params))

    print("\n[STATUS] Direct link active. Adjust sliders inside SCEPTRE GUI now...")
    
    while True:
        try:
            live_freq = monitor.get_live_frequency_mhz()
            
            if live_freq and abs(live_freq - last_freq) > 0.01:
                print(f"\n[EVENT] Active Tuner Variation Intercepted: {live_freq:.3f} MHz")
                
                # Execute timing parameter translations
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
                
            time.sleep(0.2)  # Tight 200ms cadence loop ensures hyper-responsive tracking
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Exiting runtime session tracker loop.")
            break


if __name__ == "__main__":
    run_bridge()
