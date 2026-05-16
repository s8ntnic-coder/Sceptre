"""
Sceptre Adaptive Live HTTP Bridge
==================================
Queries 3dB Labs SCEPTRE REST API structures adaptively.
Extracts receiver tuner metrics dynamically and forwards to video analyzer.
"""

import urllib.request
import urllib.error
import json
import time
from typing import Optional, List, Dict
from sceptre_video_analyzer import SceptreVideoAnalyzer


class AdaptiveSceptreClient:
    """
    Connects to 3dB Labs SCEPTRE software across varied REST API layout designs.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 8080, timeout: float = 2.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        self.validated_endpoint: Optional[str] = None
        
        # Matrix of known 3dB Labs API endpoint layout variants
        self.candidate_paths = [
            "/api/v1/receiver/tuner",
            "/api/v1/tuner",
            "/api/receiver",
            "/api/status",
            "/sceptre/api/v1/status",
            "/"  # Inspect root index directly
        ]

    def discover_endpoint(self) -> bool:
        """Probes the SCEPTRE interface to find an operational target endpoint path."""
        print(f"[DISCOVERY] Probing SCEPTRE instance endpoints on {self.base_url}...")
        
        for path in self.candidate_paths:
            target_url = f"{self.base_url}{path}"
            try:
                with urllib.request.urlopen(target_url, timeout=self.timeout) as response:
                    status = response.status
                    if status == 200:
                        raw_data = response.read().decode('utf-8', errors='ignore')
                        # If it's a structural success, save it
                        self.validated_endpoint = target_url
                        print(f"[DISCOVERY] Success! Found responsive route: {target_url}")
                        return True
            except urllib.error.HTTPError as e:
                # Catch 404/500 specifically to explore deeper structure if possible
                if e.code == 404 and path == "/":
                    pass 
            except urllib.error.URLError:
                # Port closed or interface offline entirely
                break
            except Exception:
                pass

        # Deeper introspection patch if everything fails but port is listening
        self._try_dump_root_json()
        return False

    def _try_dump_root_json(self):
        """Attempts to print out root JSON maps to diagnose 404 pathing layout blocks."""
        try:
            with urllib.request.urlopen(f"{self.base_url}/", timeout=self.timeout) as r:
                content = r.read().decode('utf-8', errors='ignore')
                print("\n[DIAGNOSTIC] Root index server content detected:")
                print(content[:300]) # Print structural fragment to terminal screen
        except Exception:
            pass

    def get_live_frequency_mhz(self) -> Optional[float]:
        """Reads tuning telemetry out of the validated functional API endpoint."""
        if not self.validated_endpoint:
            # Try to recover dynamically if connection was dropped
            if not self.discover_endpoint():
                return None

        try:
            with urllib.request.urlopen(self.validated_endpoint, timeout=self.timeout) as response:
                if response.status == 200:
                    raw_body = response.read().decode('utf-8')
                    data = json.loads(raw_body)
                    
                    # Call nested scanner to locate any numeric frequency tokens inside the JSON response
                    freq_hz = self._extract_field_recursive(data, ["frequency", "center_freq", "center_frequency", "freq", "tuned_frequency"])
                    if freq_hz:
                        # Auto-convert Hz values to MHz scale safely if value scale is huge
                        return float(freq_hz) / 1e6 if float(freq_hz) > 50000 else float(freq_hz)
        except Exception:
            self.validated_endpoint = None # Force rediscover on error break
        return None

    def _extract_field_recursive(self, data: any, targeted_keys: List[str]) -> Optional[float]:
        """Deep searches complex JSON nested structures for tuning frequency metrics."""
        if isinstance(data, dict):
            for k, v in data.items():
                if k.lower() in targeted_keys and isinstance(v, (int, float)):
                    return float(v)
                res = self._extract_field_recursive(v, targeted_keys)
                if res is not None:
                    return res
        elif isinstance(data, list):
            for item in data:
                res = self._extract_field_recursive(item, targeted_keys)
                if res is not None:
                    return res
        return None


def run_live_analyzer_loop(sceptre_host: str, sceptre_port: int, blanking: str = 'standard'):
    """Active event tracking engine reading from 3dB Labs SCEPTRE platform hooks."""
    client = AdaptiveSceptreClient(host=sceptre_host, port=sceptre_port)
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (ADAPTIVE API BRIDGE)")
    print("="*75)
    print("Press Ctrl+C to terminate live capturing loops.\n")

    last_freq = 0.0
    try:
        while True:
            live_freq = client.get_live_frequency_mhz()
            
            if live_freq and abs(live_freq - last_freq) > 0.05:
                print(f"\n[EVENT] Tuner shift detected: {live_freq:.3f} MHz")
                
                # Forward to fixed structural calculation blocks
                video_params = analyzer.analyze_frequency(live_freq, blanking_profile=blanking)
                print(analyzer.format_analysis(video_params))
                
                if video_params.detected_harmonics_from_freq:
                    print("\n--> RELATED SUB/HARMONICS TRACKED IN RF PROFILE:")
                    for h in video_params.detected_harmonics_from_freq:
                        h_type = "Subharmonic" if h.is_subharmonic else "Harmonic"
                        mult = f"1/{h.harmonic_number}" if h.is_subharmonic else f"{h.harmonic_number}x"
                        mode = h.standard_name if h.standard_name else "Unknown Signal Mode"
                        print(f"    * [{h_type}] {mult:<5} at {h.frequency_mhz:>8.2f} MHz -> Matches: {mode}")
                
                last_freq = live_freq
                
            time.sleep(1.0) # Graceful polling cadence to protect network sockets
            
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by operator loop request.")


if __name__ == "__main__":
    TARGET_IP = "127.0.0.1" 
    TARGET_HTTP_PORT = 8080 # Update this parameter if SCEPTRE runs on a specialized local port layout
    
    run_live_analyzer_loop(sceptre_host=TARGET_IP, sceptre_port=TARGET_HTTP_PORT, blanking='standard')
