"""
Sceptre Manual Frequency Input Tester
=====================================
Bypasses active network sockets to instantly verify video emission 
calculations against user-defined SCEPTRE tuner frequencies.
"""

import sys
from sceptre_video_analyzer import SceptreVideoAnalyzer

def test_static_frequency(freq_mhz: float, profile: str = 'standard'):
    analyzer = SceptreVideoAnalyzer(debug=False)
    
    print("\n" + "="*70)
    print(f" PROCESSING CAPTURED SCEPTRE FREQUENCY: {freq_mhz:.3f} MHz")
    print("="*70)
    
    try:
        params = analyzer.analyze_frequency(freq_mhz, blanking_profile=profile)
        print(analyzer.format_analysis(params))
        
        if params.detected_harmonics_from_freq:
            print("\n--> HARMONIC EMISSION COUPLING TRACE DETECTED:")
            for h in params.detected_harmonics_from_freq:
                h_type = "Subharmonic" if h.is_subharmonic else "Harmonic"
                mult = f"1/{h.harmonic_number}" if h.is_subharmonic else f"{h.harmonic_number}x"
                mode = h.standard_name if h.standard_name else "Custom Mode Frame"
                print(f"    * [{h_type}] {mult:<5} at {h.frequency_mhz:>8.2f} MHz -> Matches: {mode}")
    except Exception as e:
        print(f"[ERROR] Engine processing anomaly: {e}")

if __name__ == "__main__":
    # Fallback to standard 1080p @ 60Hz pixel clock if no argument is supplied
    target_freq = 148.5
    
    if len(sys.argv) > 1:
        try:
            target_freq = float(sys.argv[1])
        except ValueError:
            print("[WARN] Invalid frequency argument. Using default 148.5 MHz.")
            
    test_static_frequency(target_freq, profile='standard')
