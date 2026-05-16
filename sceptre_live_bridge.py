"""
Sceptre Live Bridge
====================
Connects directly to a 3dB Labs SCEPTRE software instance network stream port,
extracts real-time RF tuning metrics, and parses video emission metrics.
"""

import socket
import struct
import sys
import time
from typing import Optional
from sceptre_video_analyzer import SceptreVideoAnalyzer


class LiveSceptreClient:
    """
    Communicates with a 3dB Labs SCEPTRE receiver system via network streaming sockets.
    Captures active software tuner adjustments and peak signal profiles.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 5005, timeout: float = 3.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.is_connected = False

    def connect(self) -> bool:
        """Establishes connection to SCEPTRE's command or streaming export interface."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            print(f"[LIVE] Successfully connected to 3dB Labs SCEPTRE at {self.host}:{self.port}")
            return True
        except (socket.timeout, ConnectionRefusedError) as e:
            print(f"[LIVE ERROR] Connection failed to SCEPTRE platform: {e}")
            self.is_connected = False
            return False

    def get_live_frequency_mhz(self) -> Optional[float]:
        """
        Polls or reads the current frequency marker from the SCEPTRE interface.
        Handles both basic text-based protocols and structured binary packets.
        """
        if not self.is_connected or not self.socket:
            return None

        try:
            # Send standard query if using an interactive control command loop
            # SCEPTRE control endpoints typically accept SCPI-like or JSON string inputs
            self.socket.sendall(b"GET_FREQ\n")
            response = self.socket.recv(1024)
            
            if not response:
                return None

            # Attempt Binary/Structured payload parsing first
            try:
                # Assuming standard 3dB Labs payload sync: Magic short + float (Freq in Hz)
                if len(response) >= 6 and response[:2] == b'\xAA\x55':
                    freq_hz = struct.unpack("<f", response[2:6])[0]
                    return freq_hz / 1e6
            except struct.error:
                pass

            # Fallback to Text/ASCII reading if the channel outputs raw strings
            clean_text = response.decode('utf-8', errors='ignore').strip()
            # Expecting raw numeric data or "FREQUENCY=XXXX" formatting
            if "FREQ" in clean_text or "=" in clean_text:
                parts = clean_text.split("=")
                value_str = parts[-1].strip().replace("MHz", "").replace("Hz", "")
                return float(value_str)
            
            return float(clean_text)

        except (socket.timeout, socket.error) as e:
            print(f"[LIVE WARNING] Failed parsing data frame: {e}")
            return None

    def close(self):
        """Safely tears down the socket layer connection."""
        if self.socket:
            self.socket.close()
        self.is_connected = False
        print("[LIVE] Disconnected from SCEPTRE instance interface loop.")


def run_live_analyzer_loop(sceptre_host: str, sceptre_port: int, blanking: str = 'standard'):
    """Monitors live SCEPTRE signals and continuously reports video standard metrics."""
    client = LiveSceptreClient(host=sceptre_host, port=sceptre_port)
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*70)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER BRIDGE")
    print("="*70)
    print("Press Ctrl+C to terminate live capturing loops.\n")

    if not client.connect():
        print("[CRITICAL] Could not attach to live data stream. Exiting hook script.")
        return

    last_freq = 0.0
    try:
        while True:
            live_freq = client.get_live_frequency_mhz()
            
            # Process parameters only when tuner detects significant frequency transitions
            if live_freq and abs(live_freq - last_freq) > 0.05:
                print(f"\n[EVENT] Tuner shift detected: {live_freq:.3f} MHz")
                
                # Fire analytical conversion models
                video_params = analyzer.analyze_frequency(live_freq, blanking_profile=blanking)
                print(analyzer.format_analysis(video_params))
                
                # Check for linked harmonic detections
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
    finally:
        client.close()


if __name__ == "__main__":
    # Adjust target address to point to your physical SCEPTRE controller device workstation ip
    TARGET_IP = "127.0.0.1" 
    TARGET_PORT = 5005
    
    run_live_analyzer_loop(sceptre_host=TARGET_IP, sceptre_port=TARGET_PORT, blanking='standard')
