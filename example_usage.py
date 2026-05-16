"""
Sceptre Video Analyzer - Example Usage with Harmonics and Blanking
===================================================================
Demonstrates how to use the enhanced analyzer with harmonic detection
and blanking interval analysis.
"""

from sceptre_video_analyzer import SceptreVideoAnalyzer, VideoStandard


def example_1_basic_analysis_with_blanking():
    """Example 1: Basic frequency analysis with blanking details"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Analysis with Blanking Intervals")
    print("="*80)
    
    analyzer = SceptreVideoAnalyzer()
    
    # Analyze Full HD 1080p @60Hz frequency with standard blanking
    params = analyzer.analyze_frequency(148.5, blanking_profile='standard')
    print(analyzer.format_analysis(params))


def example_2_blanking_profiles_comparison():
    """Example 2: Compare different blanking profiles (video card variations)"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Blanking Profile Comparison (Video Card Variations)")
    print("="*80)
    
    analyzer = SceptreVideoAnalyzer()
    frequency = 148.5  # Full HD 1080p @60Hz
    
    profiles = ['minimal', 'standard', 'extended']
    
    print(f"\nAnalyzing {frequency} MHz with different blanking profiles:\n")
    print(f"{'Profile':<12} {'H-Total':<10} {'V-Total':<10} {'H-Blank%':<12} {'V-Blank%':<12}")
    print("-" * 56)
    
    for profile in profiles:
        params = analyzer.analyze_frequency(frequency, blanking_profile=profile)
        print(f"{profile:<12} {params.horizontal_pixels_total:<10} {params.vertical_lines_total:<10} "
              f"{params.blanking.h_blanking_percent:<12.2f} {params.blanking.v_blanking_percent:<12.2f}")
    
    print("\nNote: Different video cards implement varying blanking intervals.")
    print("This affects the exact timing but maintains compatibility with the standard.")


def example_3_harmonic_detection():
    """Example 3: Detect harmonics from a frequency"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Harmonic Detection")
    print("="*80)
    
    analyzer = SceptreVideoAnalyzer(debug=False)
    
    # Analyze a frequency and detect its harmonics
    frequency = 74.25  # HD 720p @60Hz
    print(f"\nDetecting harmonics for {frequency} MHz...\n")
    
    params = analyzer.analyze_frequency(frequency)
    
    if params.detected_harmonics_from_freq:
        print("Detected Harmonics:")
        print(f"{'Type':<12} {'Multiplier':<15} {'Frequency':<15} {'Video Mode':<30}")
        print("-" * 72)
        
        for harmonic in params.detected_harmonics_from_freq:
            h_type = "Subharmonic" if harmonic.is_subharmonic else "Harmonic"
            multiplier = f"1/{harmonic.harmonic_number}" if harmonic.is_subharmonic else f"{harmonic.harmonic_number}x"
            mode = harmonic.estimated_parameters.standard_name if harmonic.estimated_parameters else "Unknown"
            print(f"{h_type:<12} {multiplier:<15} {harmonic.frequency_mhz:<15.2f} {mode:<30}")
    else:
        print("No harmonics detected matching known video standards.")


def example_4_multiple_frequencies_with_harmonics():
    """Example 4: Analyze multiple frequencies and show harmonics"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Multiple Frequencies with Harmonic Analysis")
    print("="*80)
    
    analyzer = SceptreVideoAnalyzer(debug=False)
    
    frequencies = [
        ("VGA 640x480@60Hz", 25.175),
        ("HD 720p@60Hz", 74.25),
        ("Full HD 1080p@60Hz", 148.5),
        ("4K UHD@60Hz", 594.0),
    ]
    
    print(f"\n{'Standard':<30} {'Frequency':<12} {'Harmonics Found':<20}")
    print("-" * 62)
    
    for name, freq in frequencies:
        params = analyzer.analyze_frequency(freq)
        harmonic_count = len(params.detected_harmonics_from_freq)
        print(f"{name:<30} {freq:<12.2f} {harmonic_count:<20}")


def example_5_detailed_blanking_analysis():
    """Example 5: Detailed blanking analysis for a specific mode"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Detailed Blanking Analysis")
    print("="*80)
    
    analyzer = SceptreVideoAnalyzer()
    
    # Full HD 1080p with extended blanking (high-quality setup)
    params = analyzer.analyze_frequency(148.5, blanking_profile='extended')
    
    print(f"\nFull HD 1080p @60Hz with EXTENDED blanking profile:\n")
    
    # Active area
    print("ACTIVE AREA:")
    print(f"  Resolution: {params.resolution_width}x{params.resolution_height}")
    print(f"  Active Pixels/Line: {params.resolution_width}")
    print(f"  Active Lines/Frame: {params.resolution_height}")
    print(f"  Total Active Pixels: {params.resolution_width * params.resolution_height:,}")
    print()
    
    # Horizontal blanking breakdown
    print("HORIZONTAL BLANKING:")
    print(f"  Front Porch:  {params.blanking.h_front_porch_pixels} pixels")
    print(f"  Sync Pulse:   {params.blanking.h_sync_pixels} pixels")
    print(f"  Back Porch:   {params.blanking.h_back_porch_pixels} pixels")
    print(f"  Total Blank:  {params.blanking.h_total_blanking} pixels")
    print(f"  H-Total:      {params.horizontal_pixels_total} pixels")
    print(f"  Blanking %:   {params.blanking.h_blanking_percent:.2f}%")
    print()
    
    # Vertical blanking breakdown
    print("VERTICAL BLANKING:")
    print(f"  Front Porch:  {params.blanking.v_front_porch_lines} lines")
    print(f"  Sync Pulse:   {params.blanking.v_sync_lines} lines")
    print(f"  Back Porch:   {params.blanking.v_back_porch_lines} lines")
    print(f"  Total Blank:  {params.blanking.v_total_blanking} lines")
    print(f"  V-Total:      {params.vertical_lines_total} lines")
    print(f"  Blanking %:   {params.blanking.v_blanking_percent:.2f}%")
    print()
    
    # Timing information
    print("TIMING:")
    print(f"  Scanline Time: {params.scanline_time_us:.4f} µs")
    print(f"  Frame Rate:    {params.frame_rate_hz:.2f} Hz")
    print(f"  Frame Period:  {params.frame_duration_us:.2f} µs")
    print()


def example_6_harmonic_to_video_mapping():
    """Example 6: Map detected harmonics to video modes"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Harmonic-to-Video Mode Mapping")
    print("="*80)
    
    analyzer = SceptreVideoAnalyzer()
    
    # Start with a subharmonic frequency
    base_freq = 25.175  # VGA 640x480@60Hz
    
    print(f"\nStarting frequency: {base_freq} MHz (VGA 640x480@60Hz)\n")
    print("Possible harmonics and corresponding video modes:")
    print(f"{'Harmonic':<15} {'Frequency':<15} {'Expected Resolution':<30}")
    print("-" * 60)
    
    for mult in [1, 2, 3, 4, 6, 8]:
        freq = base_freq * mult
        params = analyzer.analyze_frequency(freq)
        
        if params.standard_name:
            res = f"{params.resolution_width}x{params.resolution_height}"
        else:
            res = f"Estimated: {params.resolution_width}x{params.resolution_height}"
        
        print(f"{mult}x (if exist)    {freq:<15.3f} {res:<30}")


def example_7_all_standards_with_blanking():
    """Example 7: All supported standards with blanking analysis"""
    print("\n" + "="*80)
    print("EXAMPLE 7: All Supported Standards - Blanking Analysis")
    print("="*80)
    
    analyzer = SceptreVideoAnalyzer()
    
    print(f"\n{'Standard':<30} {'H-Blank%':<12} {'V-Blank%':<12} {'H-Total':<10} {'V-Total':<10}")
    print("-" * 74)
    
    for standard in VideoStandard:
        width, height, freq = standard.value
        params = analyzer.analyze_frequency(freq, blanking_profile='standard')
        print(f"{standard.name:<30} {params.blanking.h_blanking_percent:<12.2f} "
              f"{params.blanking.v_blanking_percent:<12.2f} {params.horizontal_pixels_total:<10} "
              f"{params.vertical_lines_total:<10}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("SCEPTRE VIDEO ANALYZER - ENHANCED EXAMPLES")
    print("With Harmonic Detection and Blanking Interval Analysis")
    print("="*80)
    
    # Run all examples
    example_1_basic_analysis_with_blanking()
    example_2_blanking_profiles_comparison()
    example_3_harmonic_detection()
    example_4_multiple_frequencies_with_harmonics()
    example_5_detailed_blanking_analysis()
    example_6_harmonic_to_video_mapping()
    example_7_all_standards_with_blanking()
    
    print("\n" + "="*80)
    print("Enhanced Examples completed!")
    print("="*80)
