"""
Sceptre Real-Time WebSocket Bridge
===================================
Establishes a direct, lockless socket handshake over SCEPTRE's native 
WebSocket port (8080) to intercept live GUI tuner events as they happen.
"""

import socket
import base64
import hashlib
import json
import time
import re
from typing import Optional
from sceptre_video_analyzer import SceptreVideoAnalyzer


class SceptreWebSocketClient:
    """
    Handles standard WebSocket framing protocol handshakes over raw TCP 
    sockets to catch streaming updates from 3dB Labs SCEPTRE.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.connected = False

    def connect(self) -> bool:
        """Performs the mandatory WebSocket connection upgrade handshake sequence."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(2.0)
            self.sock.connect((self.host, self.port))

            # Create a standard compliance key for the handshake
            key = base64.b64encode(b"sceptre_live_bridge_key").decode('utf-8')
            
            # Standard HTTP WebSocket Upgrade request header
            handshake = (
                f"GET / HTTP/1.1\r\n"
                f"Host: {self.host}:{self.port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            )
            
            self.sock.sendall(handshake.encode('utf-8'))
            response = self.sock.recv(1024).decode('utf-8', errors='ignore')
            
            if "101 Switching Protocols" in response:
                self.connected = True
                self.sock.settimeout(0.1) # Drop timeout low for responsive non-blocking loop reads
                print(f"[LIVE] Hooked into SCEPTRE stream channel on port {self.port}!")
                return True
                
            self.sock.close()
        except Exception as e:
            print(f"[CONN WARN] WebSocket channel initialization failed: {e}")
            
        self.connected = False
        return False

    def receive_text_frame(self) -> Optional[str]:
        """Unpacks standard WebSocket data frames received on the wire."""
        if not self.connected or not self.sock:
            return None

        try:
            data = self.sock.recv(4096)
            if not data or len(data) < 2:
                return None

            # Parse standard WebSocket opcode (0x1 = Text frame, 0x8 = Close connection)
            opcode = data[0] & 0x0F
            if opcode == 8:
                print("[LIVE] SCEPTRE closed the streaming channel interface.")
                self.connected = False
                return None

            payload_len = data[1] & 0x7F
            idx = 2
            
            # Handle variable extended payload length formats
            if payload_len == 126:
                if len(data) < 4: return None
                idx = 4
            elif payload_len == 127:
                if len(data) < 10: return None
                idx = 10

            # Unpack payload data bytes safely
            payload = data[idx:]
            return payload.decode('utf-8', errors='ignore').strip()
            
        except socket.timeout:
            return None # Timeouts are normal when user isn't clicking anything
        except Exception:
            self.connected = False
            return None


def run_websocket_bridge():
    client = SceptreWebSocketClient(host="127.0.0.1", port=8080)
    analyzer = SceptreVideoAnalyzer(debug=False)

    print("\n" + "="*75)
    print(" 3DB LABS SCEPTRE TO VIDEO EMISSION ANALYZER (WEB SOCKET LOOP)")
    print("="*75)
    print("Listening for streaming tuner shifts... Scroll/Click inside SCEPTRE GUI now.\n")

    last_freq = 0.0
    
    while True:
        try:
            if not client.connected:
                # Keep attempting to reconnect if connection drops out
                if not client.connect():
                    time.sleep(2.0)
                    continue

            raw_frame = client.receive_text_frame()
            if not raw_frame:
                continue

            # Look for any numeric parameters assigned to tuner keys inside streaming payloads
            freq_match = re.search(r'(?:tuner_frequency|frequency|tuned_freq|cf)\s*["\':=]+\s*([0-9.]+)', raw_frame, re.IGNORECASE)
            if freq_match:
                live_freq = float(freq_match.group(1))
                
                # Auto convert raw Hz or kHz strings down to MHz scale
                if live_freq > 1e6:
                    live_freq /= 1e6
                elif live_freq > 50000:
                    live_freq /= 1e3

                if abs(live_freq - last_freq) > 0.01:
                    print(f"\n[EVENT] Direct WebSocket Tuner Event Intercepted: {live_freq:.3f} MHz")
                    
                    # Call fixed analytical conversion parameters matrix
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

        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Exiting live streaming monitoring environment.")
            if client.sock:
                client.sock.close()
            break


if __name__ == "__main__":
    run_websocket_bridge()
