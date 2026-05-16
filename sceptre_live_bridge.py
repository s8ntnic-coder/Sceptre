"""
Sceptre Live HTTP Bridge
=========================
Connects to 3dB Labs SCEPTRE using its native REST API endpoint.
Polls the active tuner center frequency and feeds it to the video analyzer.
"""

import urllib.request
import urllib.error
import json
import time
import sys
from typing import Optional
from sceptre_video_analyzer import SceptreVideoAnalyzer


class LiveSceptreClient:
    """
    Communicates with a 3dB Labs SCEPTRE instance via its native REST API.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 8080, timeout: float = 2.0):
        # SCEPTRE HTTP interfaces defaults vary, common ports are 8080 or 5000
        self.base_url = f"http://{host}:{port}/api/v1"
        self.timeout = timeout
        self.is_connected = False

    def test_connection(self) -> bool:
        """Verifies the SCEPTRE API endpoint is responsive."""
        try:
            # Poll the system status endpoint
            url = f"{self.base_url}/status"
            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                if response.status == 200:
                    print(f"[LIVE] Successfully verified SCEPTRE REST API at {self.base_url}")
                    self.is_connected = True
                    return True
        except urllib.error.URLError as e:
            print(f"[LIVE ERROR] Cannot connect to SCEPTRE REST API: {e.reason}")
            print("  -> Ensure SCEPTRE is running and the REST API plugin is enabled.")
        except Exception as e:
            print(f"[LIVE ERROR] Connection anomaly: {e}")
        
        self.is_connected = False
        return False

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Queries the current active receiver/tuner center frequency.
        """
        try:
            # Query the active hardware receiver configuration
            url = f"{self.base_url}/receiver/tuner"
            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    
                    # SCEPTRE standard returns frequency values in Hz
                    if "frequency" in data:
                        return float(data["frequency"]) / 1e6
                    elif "center_frequency" in data:
                        return float(data["center_frequency"]) / 1e6
                    
        except urllib.error.URLError:
            # Suppress excessive network log spamming during active tracking
            self.is_connected = False
        except Exception as e:
            print(f"[LIVE WARNING] Parsing configuration failed: {e}")
            
        return None


def run_live_analyzer_loop(sceptre_host: str, sceptre_port: int, blanking: str = 'standard'):
    """Monitors live SCEPTRE signals via HTTP and runs video analysis."""
    client = LiveSceptreClient(host=sceptre_host, port=sceptre_port)
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (REST API)")
    print("="*75)
    print("Press Ctrl+C to terminate live capturing loops.\n")

    # Attempt an initial validation connection check
    if not client.test_connection():
        print("[CRITICAL] Falling back to passive testing loop...")
        print("Continuing execution loop. Listening for target endpoint to wake up...")

    last_freq = 0.0
    try:
        while True:
            live_freq = client.get_live_frequency_mhz()
            
            # Process parameters only when tuner detects significant frequency updates
            if live_freq and abs(live_freq - last_freq) > 0.05:
                print(f"\n[EVENT] Tuner shift detected: {live_freq:.3f} MHz")
                
                # Execute analyzer engine code
                video_params = analyzer.analyze_frequency(live_freq, blanking_profile=blanking)
                print(analyzer.format_analysis(video_params))
                
                # Track accompanying video harmonics
                if video_params.detected_harmonics_from_freq:
                    print("\n--> RELATED SUB/HARMONICS TRACKED IN RF PROFILE:")
                    for h in video_params.detected_harmonics_from_freq:
                        h_type = "Subharmonic" if h.is_subharmonic else "Harmonic"
                        mult = f"1/{h.harmonic_number}" if h.is_subharmonic else f"{h.harmonic_number}x"
                        mode = h.standard_name if h.standard_name else "Unknown Signal Mode"
                        print(f"    * [{h_type}] {mult:<5} at {h.frequency_mhz:>8.2f} MHz -> Matches: {mode}")
                
                last_freq = live_freq
                
            time.sleep(0.5)  # Prevents thread polling exhaustion
            
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by operator loop request.")


if __name__ == "__main__":
    # Adjust target address parameters to match your SCEPTRE installation
    TARGET_IP = "127.0.0.1" 
    TARGET_HTTP_PORT = 8080  # Common ports used by SCEPTRE web control are 8080, 5000, or 8443
    
    run_live_analyzer_loop(sceptre_host=TARGET_IP, sceptre_port=TARGET_HTTP_PORT, blanking='standard')
