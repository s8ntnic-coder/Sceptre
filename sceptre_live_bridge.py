"""
Sceptre Web Interface Extraction Bridge
=======================================
Directly captures real-time tuner frequencies from SCEPTRE's active 
integrated web UI control panel stream running on port 8080.
"""

import urllib.request
import urllib.error
import re
import time
from sceptre_video_analyzer import SceptreVideoAnalyzer


class SceptreWebInterfaceClient:
    """
    Scrapes or reads real-time tuner values from the SCEPTRE web workspace front-end.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 8080, timeout: float = 1.0):
        self.target_url = f"http://{host}:{port}/"
        self.timeout = timeout
        self.is_server_alive = False

    def test_web_presence(self) -> bool:
        """Verifies if the SCEPTRE integrated web server framework is responding."""
        try:
            req = urllib.request.Request(self.target_url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    self.is_server_alive = True
                    return True
        except Exception:
            pass
        return False

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Pulls down the active web view state and extracts active slider or 
        tuner frequencies instantly via regular expressions.
        """
        try:
            req = urllib.request.Request(self.target_url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
                
            # Scan the web dashboard state block for active tuner frequency numeric parameters
            # Matches entries like "tuner_frequency": 148500000, frequency = 148.5, or data-freq="148500000"
            freq_match = re.search(
                r'(?:tuner_frequency|frequency|tuned_freq|center_freq|cf)\b["\':\s=]+([0-9.]+)', 
                html_content, 
                re.IGNORECASE
            )
            
            if freq_match:
                val = float(freq_match.group(1))
                # Normalise Hz and kHz readings down to standard MHz scales instantly
                if val > 1e6:
                    return val / 1e6
                elif val > 50000:
                    return val / 1e3
                return val
                
        except Exception:
            pass
            
        return None


def run_bridge_loop():
    client = SceptreWebInterfaceClient(host="127.0.0.1", port=8080)
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (WEB VIEW INTERFACE)")
    print("="*75)
    print("Connecting to live server viewport... Press Ctrl+C to terminate loops.\n")

    # Confirm network presence immediately
    if client.test_web_presence():
        print(f"[SUCCESS] Linked natively to SCEPTRE Web Server interface on port 8080!")
    else:
        print(f"[NOTE] Web port 8080 is quiet. Ensure SCEPTRE's interface is completely loaded.")

    # Drop our initial baseline parameter analysis out on launch
    last_freq = 148.50
    print(f"\n[INITIALISATION] Latching onto baseline emission target: {last_freq:.3f} MHz")
    params = analyzer.analyze_frequency(last_freq, blanking_profile='standard')
    print(analyzer.format_analysis(params))

    print("\n[STATUS] Active connection loop polling. Adjust sliders inside SCEPTRE now...")
    
    while True:
        try:
            live_freq = client.get_live_frequency_mhz()
            
            if live_freq and abs(live_freq - last_freq) > 0.01:
                print(f"\n[EVENT] Live Web Tuner Mutation Intercepted: {live_freq:.3f} MHz")
                
                # Forward to timing generation conversion structures
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
                
            time.sleep(0.3)  # Rapid 300ms checks handle snappy real-time responsiveness
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Safely exiting live web monitoring environment loops.")
            break


if __name__ == "__main__":
    run_bridge_loop()
