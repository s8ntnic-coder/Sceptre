"""
Sceptre Native REST API Live Bridge
====================================
Establishes a direct HTTP loop with 3dB Labs SCEPTRE's integrated REST engine.
Queries live memory variables to intercept slider frequency adjustments instantly.
"""

import urllib.request
import urllib.error
import json
import time
from typing import Optional
from sceptre_video_analyzer import SceptreVideoAnalyzer


class SceptreLiveRestAPIClient:
    """
    Interfaces natively with SCEPTRE's automated REST routing endpoints.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 8080, timeout: float = 1.0):
        self.base_url = f"http://{host}:{port}/api/v1"
        self.timeout = timeout
        self.connected_route = None

    def discover_active_endpoint(self) -> bool:
        """Probes SCEPTRE's interface architecture to resolve the live tuner route."""
        # Common structural API paths used across standard SCEPTRE version deployments
        test_routes = ["/tuner", "/receiver/tuner", "/receiver", "/status"]
        
        for route in test_routes:
            url = f"{self.base_url}{route}"
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    if response.status == 200:
                        self.connected_route = url
                        print(f"[REST ENGINE] Linked successfully to active SCEPTRE API: {url}")
                        return True
            except Exception:
                continue
        return False

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Polls the validated REST route to parse running tuner frequencies.
        """
        if not self.connected_route:
            if not self.discover_active_endpoint():
                return None

        try:
            req = urllib.request.Request(self.connected_route, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    raw_payload = response.read().decode('utf-8')
                    data = json.loads(raw_payload)
                    return self._extract_field_recursive(data)
        except urllib.error.URLError:
            self.connected_route = None  # Reset route to trigger rediscovery if link drops
        except Exception as e:
            print(f"[REST WARNING] Failed extracting data frame variables: {e}")
            
        return None

    def _extract_field_recursive(self, data: any) -> Optional[float]:
        """Deep parses variable json configurations for running frequencies."""
        keys = ["tuner_frequency", "frequency", "center_frequency", "center_freq", "freq", "input_frequency"]
        
        if isinstance(data, dict):
            for k, v in data.items():
                if k.lower() in keys and isinstance(v, (int, float)):
                    val = float(v)
                    return val / 1e6 if val > 1e6 else val
                res = self._extract_field_recursive(v)
                if res is not None:
                    return res
        elif isinstance(data, list):
            for item in data:
                res = self._extract_field_recursive(item)
                if res is not None:
                    return res
        return None


def run_rest_bridge_loop():
    client = SceptreLiveRestAPIClient(host="127.0.0.1", port=8080)
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (REST LIVE BRIDGE)")
    print("="*75)
    print("Connecting to live application memory... Press Ctrl+C to stop.\n")

    last_freq = 148.50
    print(f"[INITIALISATION] Latching onto baseline emission target: {last_freq:.3f} MHz")
    params = analyzer.analyze_frequency(last_freq, blanking_profile='standard')
    print(analyzer.format_analysis(params))

    print("\n[STATUS] Active connection loop polling. Adjust sliders inside SCEPTRE now...")
    
    while True:
        try:
            live_freq = client.get_live_frequency_mhz()
            
            if live_freq and abs(live_freq - last_freq) > 0.01:
                print(f"\n[EVENT] Live Software Tuner Adjust Intercepted: {live_freq:.3f} MHz")
                
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
                
            time.sleep(0.2)  # Tight 200ms sleep prevents lag during active tuning
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Terminating API integration link loops.")
            break


if __name__ == "__main__":
    run_rest_bridge_loop()
