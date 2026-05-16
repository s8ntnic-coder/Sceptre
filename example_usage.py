"""
Sceptre Video Analyzer - Example Usage
======================================
Demonstrates how to use the SceptreVideoAnalyzer to analyze video frequencies.
"""

from sceptre_video_analyzer import SceptreVideoAnalyzer, SceptreAPIClient, VideoStandard


def example_1_basic_analysis():
    """Example 1: Basic frequency analysis"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Frequency Analysis")
    print("="*70)
    
    analyzer = SceptreVideoAnalyzer()
    
    # Analyze Full HD 1080p @60Hz frequency
    params = analyzer.analyze_frequency(148.5)
    print(analyzer.format_analysis(params))


def example_2_multiple_frequencies():
    """Example 2: Analyze multiple standard frequencies"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Multiple Standard Frequencies")
    print("="*70)
    
    analyzer = SceptreVideoAnalyzer()
    
    frequencies = [
        ("VGA 640x480@60Hz", 25.175),
        ("SVGA 800x600@60Hz", 40.0),
        ("XGA 1024x768@60Hz", 65.0),
        ("HD 720p@60Hz", 74.25),
        ("Full HD 1080p@60Hz", 148.5),
        ("Full HD 1080p@120Hz", 297.0),
        ("4K UHD@60Hz", 594.0),
    ]
    
    print("\n{:<30} {:<15} {:<15} {:<15}".format(
        "Standard", "Resolution", "Pixel Clock", "Frame Rate"
    ))
    print("-" * 75)
    
    for name, freq in frequencies:
        params = analyzer.analyze_frequency(freq)
        print("{:<30} {:<15} {:<15} {:<15.2f}Hz".format(
            name,
            f"{params.resolution_width}x{params.resolution_height}",
            f"{params.pixel_clock_mhz} MHz",
            params.frame_rate_hz
        ))


def example_3_custom_frequency():
    """Example 3: Analyze custom/unknown frequency with estimation"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Custom Frequency Estimation (CVT-R2)")
    print("="*70)
    
    analyzer = SceptreVideoAnalyzer()
    
    # Analyze an unknown frequency
    custom_freq = 75.5  # MHz
    params = analyzer.analyze_frequency(custom_freq)
    
    print(f"\nAnalyzing custom frequency: {custom_freq} MHz")
    if params.is_estimated:
        print(f"Method: {params.estimated_method}")
        print(f"Estimated Resolution: {params.resolution_width}x{params.resolution_height}")
        print(f"Estimated Frame Rate: {params.frame_rate_hz:.2f} Hz")
        print("(Note: This is an estimate. Actual values depend on the specific signal.)")


def example_4_bandwidth_check():
    """Example 4: Check HDMI bandwidth compatibility"""
    print("\n" + "="*70)
    print("EXAMPLE 4: HDMI Bandwidth Compatibility Matrix")
    print("="*70)
    
    analyzer = SceptreVideoAnalyzer()
    
    resolutions = [
        ("Full HD 1080p@60Hz", 148.5),
        ("Full HD 1080p@120Hz", 297.0),
        ("4K UHD@30Hz", 297.0),
        ("4K UHD@60Hz", 594.0),
        ("8K FUHD@60Hz", 2376.0),
    ]
    
    print("\n{:<25} {:<15} {:<15} {:<8} {:<8} {:<8}".format(
        "Resolution", "Pixel Clock", "Bandwidth", "HDMI1.4", "HDMI2.0", "HDMI2.1"
    ))
    print("-" * 80)
    
    for name, freq in resolutions:
        params = analyzer.analyze_frequency(freq)
        bw = analyzer.calculate_bandwidth_requirements(params)
        
        hdmi14 = "✓" if bw['hdmi_1_4_compatible'] else "✗"
        hdmi20 = "✓" if bw['hdmi_2_0_compatible'] else "✗"
        hdmi21 = "✓" if bw['hdmi_2_1_compatible'] else "✗"
        
        print("{:<25} {:<15} {:<15.2f} {:<8} {:<8} {:<8}".format(
            name,
            f"{freq} MHz",
            bw['tmds_bandwidth_gbps'],
            hdmi14,
            hdmi20,
            hdmi21
        ))


def example_5_timing_details():
    """Example 5: Detailed timing analysis with debug output"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Detailed Timing Analysis (Debug Mode)")
    print("="*70)
    
    analyzer = SceptreVideoAnalyzer(debug=True)
    
    print("\nAnalyzing 4K UHD@60Hz (594.0 MHz)...\n")
    params = analyzer.analyze_frequency(594.0)
    
    print("\nDetailed Results:")
    print(f"  Resolution: {params.resolution_width}x{params.resolution_height}")
    print(f"  Horizontal Total Pixels: {params.horizontal_pixels_total}")
    print(f"  Vertical Total Lines: {params.vertical_lines_total}")
    print(f"  Scanline Time: {params.scanline_time_us:.4f} µs")
    print(f"  Frame Duration: {params.frame_duration_us:.2f} µs")
    print(f"  Frame Rate: {params.frame_rate_hz:.2f} Hz")
    print(f"  Pixel Rate: {params.pixel_rate_hz:,} Hz")


def example_6_api_client():
    """Example 6: SceptreAPIClient usage (placeholder)"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Sceptre API Client (Placeholder)")
    print("="*70)
    
    # This is a placeholder for actual hardware integration
    client = SceptreAPIClient(device_path="/dev/ttyUSB0")
    
    print("\nAttempting to connect to Sceptre hardware...")
    if client.connect():
        print("✓ Connected to Sceptre")
        
        # Get current frequency (placeholder)
        freq = client.get_current_frequency()
        if freq:
            print(f"Current frequency: {freq} MHz")
            
            # Analyze the frequency
            analyzer = SceptreVideoAnalyzer()
            params = analyzer.analyze_frequency(freq)
            print(analyzer.format_analysis(params))
        else:
            print("Note: get_current_frequency() returns None (placeholder)")
        
        client.disconnect()
        print("✓ Disconnected from Sceptre")
    else:
        print("✗ Failed to connect (this is expected - API client is a placeholder)")
        print("  To enable: Implement actual 3DB Labs API communication in SceptreAPIClient")


def example_7_all_standards():
    """Example 7: Analyze all supported video standards"""
    print("\n" + "="*70)
    print("EXAMPLE 7: All Supported Video Standards")
    print("="*70)
    
    analyzer = SceptreVideoAnalyzer()
    
    print("\n{:<30} {:<15} {:<15} {:<15}".format(
        "Standard", "Resolution", "Pixel Clock", "Frame Rate"
    ))
    print("-" * 75)
    
    for standard in VideoStandard:
        width, height, freq = standard.value
        params = analyzer.analyze_frequency(freq)
        print("{:<30} {:<15} {:<15} {:<15.2f}Hz".format(
            standard.name,
            f"{width}x{height}",
            f"{freq} MHz",
            params.frame_rate_hz
        ))


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SCEPTRE VIDEO ANALYZER - EXAMPLES")
    print("="*70)
    
    # Run all examples
    example_1_basic_analysis()
    example_2_multiple_frequencies()
    example_3_custom_frequency()
    example_4_bandwidth_check()
    example_5_timing_details()
    example_6_api_client()
    example_7_all_standards()
    
    print("\n" + "="*70)
    print("Examples completed!")
    print("="*70)
