"""
Sceptre Native JSON-RPC Live Bridge
====================================
Connects directly to the 3dB Labs SCEPTRE GUI remote command port (8080).
Uses the native JSON-RPC 2.0 protocol to extract live active tuner metrics.
"""

import socket
import json
import time
import sys
from typing import Optional
from sceptre_video_analyzer import SceptreVideoAnalyzer


class NativeSceptreClient:
    """
    Communicates using JSON-RPC 2.0 requests over a raw TCP socket to 
    interface with the 3dB Labs SCEPTRE software platform core.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 8080, timeout: float = 2.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.is_connected = False
        self.request_id = 1

    def connect(self) -> bool:
        """Establishes connection to the active SCEPTRE socket interface."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            print(f"[LIVE] Connected to SCEPTRE JSON-RPC Socket at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[LIVE ERROR] Raw connection to port {self.port} refused: {e}")
            self.is_connected = False
            return False

    def send_rpc_method(self, method_name: str, params: Optional[dict] = None) -> Optional[dict]:
        """Sends a JSON-RPC 2.0 compliant request frame over the active wire thread."""
        if not self.is_connected or not self.socket:
            return None

        # Standard structured request block used by 3dB Labs automation interfaces
        payload = {
            "jsonrpc": "2.0",
            "method": method_name,
            "id": self.request_id
        }
        if params:
            payload["params"] = params

        self.request_id += 1

        try:
            # SCEPTRE's streaming endpoint reads newline-delimited JSON rows
            message = json.dumps(payload) + "\n"
            self.socket.sendall(message.encode('utf-8'))
            
            # Catch the discrete response frame
            response_data = self.socket.recv(4096)
            if not response_data:
                return None
                
            return json.loads(response_data.decode('utf-8').strip())
        except Exception as e:
            print(f"[LIVE WARNING] RPC Transaction failure on method '{method_name}': {e}")
            self.is_connected = False # Mark socket line broken to force reconnect loop
            return None

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Queries common SCEPTRE system methods to extract tuner center frequencies.
        """
        if not self.is_connected:
            self.connect()
            if not self.is_connected:
                return None

        # Fallback sequence scanning common 3dB Labs RPC method maps
        methods_to_try = [
            ("getTunerStatus", None),
            ("getReceiverConfig", None),
            ("getSystemStatus", None)
        ]

        for method, params in methods_to_try:
            response = self.send_rpc_method(method, params)
            if response and "result" in response:
                result = response["result"]
                
                # Dig into common returned dictionary data maps
                freq_val = self._search_dict_for_frequency(result)
                if freq_val:
                    # Convert raw Hz allocations to MHz representation scales instantly
                    return float(freq_val) / 1e6 if float(freq_val) > 50000 else float(freq_val)
                    
        return None

    def _search_dict_for_frequency(self, data: any) -> Optional[float]:
        """Deep parses variable return schemas for targeting tuning properties."""
        target_keys = ["frequency", "center_freq", "center_frequency", "freq", "tuned_frequency", "mhz"]
        
        if isinstance(data, dict):
            for k, v in data.items():
                if k.lower() in target_keys and isinstance(v, (int, float)):
                    return float(v)
                res = self._search_dict_for_frequency(v)
                if res is not None:
                    return res
        elif isinstance(data, list):
            for element in data:
                res = self._search_dict_for_frequency(element)
                if res is not None:
                    return res
        return None

    def close(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
        self.is_connected = False


def run_live_bridge_loop(host: str, port: int, profile: str = 'standard'):
    client = NativeSceptreClient(host=host, port=port)
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (NATIVE RPC CONNECTION)")
    print("="*75)
    print("Press Ctrl+C to terminate live capturing loops.\n")

    last_freq = 0.0
    try:
        while True:
            live_freq = client.get_live_frequency_mhz()
            
            if live_freq and abs(live_freq - last_freq) > 0.05:
                print(f"\n[EVENT] Tuner shift detected: {live_freq:.3f} MHz")
                
                # Execute emission trace analysis formulas
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
                
            time.sleep(1.0) # Consistent poll checking cadences
            
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by operator loop request.")
    finally:
        client.close()


if __name__ == "__main__":
    # Point precisely to the local listening service identified by your lsof log
    run_live_bridge_loop(host="127.0.0.1", port=8080, profile='standard')
