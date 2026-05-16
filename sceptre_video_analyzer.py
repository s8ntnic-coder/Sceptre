"""
Sceptre Video Analyzer
=====================
A program to interact with Sceptre oscilloscope from 3DB Labs API.
Converts frequency tuning to video emission parameters (HDMI/DVI cables).

Calculates:
- Video resolution
- Pixel rate
- Scanline time
- Frame rate
- Frame duration
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math
from enum import Enum


class VideoStandard(Enum):
    """Common video standards and their pixel clock frequencies"""
    VGA_60 = (640, 480, 25.175)  # width, height, pixel_clock_MHz
    SVGA_60 = (800, 600, 40.0)
    XGA_60 = (1024, 768, 65.0)
    WXGA_60 = (1280, 800, 83.5)
    WXGA_PLUS_60 = (1440, 900, 106.5)
    UXGA_60 = (1600, 1200, 162.0)
    HD_720_60 = (1280, 720, 74.25)
    FULL_HD_60 = (1920, 1080, 148.5)
    FULL_HD_120 = (1920, 1080, 297.0)
    QHD_60 = (2560, 1440, 241.5)
    QHXGA_60 = (2560, 2048, 312.25)
    UHD_4K_30 = (3840, 2160, 297.0)
    UHD_4K_60 = (3840, 2160, 594.0)
    DCI_4K_24 = (4096, 2160, 552.75)
    DCI_4K_48 = (4096, 2160, 1105.5)
    FUHD_8K_30 = (7680, 4320, 1188.0)
    FUHD_8K_60 = (7680, 4320, 2376.0)


@dataclass
class VideoParameters:
    """Calculated video parameters from frequency analysis"""
    frequency_mhz: float
    resolution_width: int
    resolution_height: int
    pixel_clock_mhz: float
    pixel_rate_hz: int
    scanline_time_us: float
    frame_rate_hz: float
    frame_duration_us: float
    standard_name: Optional[str] = None
    is_estimated: bool = False
    estimated_method: Optional[str] = None
    total_pixels_per_frame: int = 0
    horizontal_pixels_total: int = 0
    vertical_lines_total: int = 0


class SceptreVideoAnalyzer:
    """
    Main analyzer for converting Sceptre frequency to video parameters.
    Supports HDMI, DVI, and VGA standards.
    """

    # HDMI/DVI frequency tolerance (MHz)
    FREQUENCY_TOLERANCE = 2.0

    # CVT-R2 (Coordinated Video Timings Revision 2) constants
    CVT_H_SYNC_PERCENT = 0.08
    CVT_V_SYNC_PERCENT = 0.1
    CVT_MIN_V_PORCH = 3

    def __init__(self, debug: bool = False):
        """
        Initialize the analyzer.
        
        Args:
            debug: Enable debug output
        """
        self.debug = debug
        self._build_standard_lookup()

    def _build_standard_lookup(self):
        """Build frequency lookup table for standard video modes"""
        self.standards_by_frequency: Dict[float, Tuple[str, int, int, float]] = {}
        
        for standard in VideoStandard:
            width, height, freq = standard.value
            key = round(freq, 2)
            self.standards_by_frequency[key] = (
                standard.name,
                width,
                height,
                freq
            )

    def analyze_frequency(self, frequency_mhz: float) -> VideoParameters:
        """
        Analyze a frequency and calculate video parameters.
        
        Args:
            frequency_mhz: Sceptre tuned frequency in MHz
            
        Returns:
            VideoParameters object with calculated values
        """
        if self.debug:
            print(f"[DEBUG] Analyzing frequency: {frequency_mhz} MHz")

        # Try to match known standard
        standard = self._match_standard(frequency_mhz)
        if standard:
            return standard

        # Estimate parameters using CVT-R2
        return self._estimate_cvt_r2(frequency_mhz)

    def _match_standard(self, frequency_mhz: float) -> Optional[VideoParameters]:
        """Match frequency to known video standard"""
        for known_freq, (name, width, height, pixel_clock) in self.standards_by_frequency.items():
            if abs(frequency_mhz - known_freq) <= self.FREQUENCY_TOLERANCE:
                if self.debug:
                    print(f"[DEBUG] Matched standard: {name} ({width}x{height})")
                
                return self._calculate_parameters(
                    frequency_mhz=frequency_mhz,
                    width=width,
                    height=height,
                    pixel_clock_mhz=pixel_clock,
                    standard_name=name,
                    is_estimated=False
                )
        return None

    def _estimate_cvt_r2(self, frequency_mhz: float) -> VideoParameters:
        """
        Estimate video parameters using CVT-R2 algorithm.
        
        Assumes:
        - 16:9 aspect ratio (common for modern displays)
        - Reduced blanking v2 (CVT-R2)
        """
        if self.debug:
            print(f"[DEBUG] Estimating parameters using CVT-R2 for {frequency_mhz} MHz")

        # Estimate based on common aspect ratios and refresh rates
        # For a given pixel clock, estimate resolution
        
        # Typical frame rate range for video
        estimated_frame_rate = 60.0  # Hz (common assumption)
        
        # Total pixels per frame ≈ (pixel_clock_MHz * 1e6) / frame_rate_hz
        pixel_clock_hz = frequency_mhz * 1e6
        total_pixels = pixel_clock_hz / estimated_frame_rate
        
        # Assume 16:9 aspect ratio with standard CVT blanking
        # Horizontal blanking ~ 20%, vertical blanking ~ 10%
        active_pixels_percent = 0.80
        active_lines_percent = 0.90
        
        active_pixels = total_pixels * active_pixels_percent
        
        # Estimate width from aspect ratio 16:9
        width = int(math.sqrt(active_pixels * (16 / 9)))
        # Round to nearest 8
        width = (width // 8) * 8
        
        height = int(width * 9 / 16)
        # Round to nearest 2
        height = (height // 2) * 2
        
        return self._calculate_parameters(
            frequency_mhz=frequency_mhz,
            width=width,
            height=height,
            pixel_clock_mhz=frequency_mhz,
            standard_name=None,
            is_estimated=True,
            estimated_method="CVT-R2 16:9"
        )

    def _calculate_parameters(
        self,
        frequency_mhz: float,
        width: int,
        height: int,
        pixel_clock_mhz: float,
        standard_name: Optional[str] = None,
        is_estimated: bool = False,
        estimated_method: Optional[str] = None
    ) -> VideoParameters:
        """Calculate all video parameters from base values"""
        
        pixel_clock_hz = pixel_clock_mhz * 1e6
        pixel_rate_hz = int(pixel_clock_hz)
        
        # Standard timing assumptions
        # Horizontal: Add ~25% for front porch, sync, back porch
        h_total = int(width * 1.25)
        
        # Vertical: Add ~10% for front porch, sync, back porch  
        v_total = int(height * 1.10)
        
        # Scanline time = h_total / pixel_clock_hz (in seconds)
        scanline_time_us = (h_total / pixel_clock_hz) * 1e6
        
        # Frame time = (h_total * v_total) / pixel_clock_hz
        frame_time_us = (h_total * v_total / pixel_clock_hz) * 1e6
        
        # Frame rate = pixel_clock_hz / (h_total * v_total)
        frame_rate_hz = pixel_clock_hz / (h_total * v_total)
        
        total_pixels_per_frame = h_total * v_total
        
        if self.debug:
            print(f"[DEBUG] Parameters calculated:")
            print(f"  Resolution: {width}x{height}")
            print(f"  Pixel clock: {pixel_clock_mhz} MHz")
            print(f"  H-total: {h_total}, V-total: {v_total}")
            print(f"  Frame rate: {frame_rate_hz:.2f} Hz")
            print(f"  Scanline time: {scanline_time_us:.3f} µs")
        
        return VideoParameters(
            frequency_mhz=frequency_mhz,
            resolution_width=width,
            resolution_height=height,
            pixel_clock_mhz=pixel_clock_mhz,
            pixel_rate_hz=pixel_rate_hz,
            scanline_time_us=scanline_time_us,
            frame_rate_hz=frame_rate_hz,
            frame_duration_us=frame_time_us,
            standard_name=standard_name,
            is_estimated=is_estimated,
            estimated_method=estimated_method,
            total_pixels_per_frame=total_pixels_per_frame,
            horizontal_pixels_total=h_total,
            vertical_lines_total=v_total
        )

    def calculate_bandwidth_requirements(self, params: VideoParameters) -> Dict[str, float]:
        """
        Calculate HDMI/DVI bandwidth requirements.
        
        Args:
            params: VideoParameters from analyze_frequency()
            
        Returns:
            Dictionary with bandwidth calculations
        """
        # HDMI/DVI bandwidth = pixel_clock * bits_per_pixel / 8
        # Standard: 24-bit color (8-bit per channel RGB)
        
        bits_per_pixel = 24
        pixel_clock_hz = params.pixel_clock_mhz * 1e6
        
        # Raw bandwidth
        raw_bandwidth_bps = pixel_clock_hz * bits_per_pixel
        raw_bandwidth_gbps = raw_bandwidth_bps / 1e9
        
        # HDMI 1.4 uses TMDS encoding (8b/10b) = 1.25x overhead
        tmds_bandwidth_gbps = raw_bandwidth_gbps * 1.25
        
        return {
            'pixel_clock_mhz': params.pixel_clock_mhz,
            'raw_bandwidth_gbps': raw_bandwidth_gbps,
            'tmds_bandwidth_gbps': tmds_bandwidth_gbps,
            'hdmi_1_4_compatible': tmds_bandwidth_gbps <= 10.2,
            'hdmi_2_0_compatible': tmds_bandwidth_gbps <= 18.0,
            'hdmi_2_1_compatible': tmds_bandwidth_gbps <= 48.0,
        }

    def format_analysis(self, params: VideoParameters) -> str:
        """
        Format analysis results as readable string.
        
        Args:
            params: VideoParameters to format
            
        Returns:
            Formatted analysis string
        """
        output = []
        output.append("=" * 60)
        output.append("SCEPTRE VIDEO ANALYSIS RESULTS")
        output.append("=" * 60)
        output.append(f"Sceptre Frequency: {params.frequency_mhz} MHz")
        output.append("")
        
        if params.standard_name:
            output.append(f"Standard: {params.standard_name}")
        else:
            output.append("Standard: CUSTOM/ESTIMATED")
            if params.estimated_method:
                output.append(f"Estimation Method: {params.estimated_method}")
        output.append("")
        
        output.append("VIDEO PARAMETERS")
        output.append("-" * 60)
        output.append(f"Resolution:          {params.resolution_width}x{params.resolution_height}")
        output.append(f"Pixel Clock:         {params.pixel_clock_mhz} MHz")
        output.append(f"Pixel Rate:          {params.pixel_rate_hz:,} Hz")
        output.append("")
        
        output.append("TIMING")
        output.append("-" * 60)
        output.append(f"H-Total (pixels):    {params.horizontal_pixels_total}")
        output.append(f"V-Total (lines):     {params.vertical_lines_total}")
        output.append(f"Scanline Time:       {params.scanline_time_us:.4f} µs")
        output.append(f"Frame Rate:          {params.frame_rate_hz:.2f} Hz")
        output.append(f"Frame Duration:      {params.frame_duration_us:.2f} µs")
        output.append(f"Total Pixels/Frame:  {params.total_pixels_per_frame:,}")
        output.append("")
        
        bandwidth = self.calculate_bandwidth_requirements(params)
        output.append("BANDWIDTH REQUIREMENTS")
        output.append("-" * 60)
        output.append(f"Raw Bandwidth:       {bandwidth['raw_bandwidth_gbps']:.2f} Gbps")
        output.append(f"TMDS Bandwidth:      {bandwidth['tmds_bandwidth_gbps']:.2f} Gbps")
        output.append("")
        output.append("COMPATIBILITY")
        output.append(f"HDMI 1.4 (10.2 Gbps):  {'✓ YES' if bandwidth['hdmi_1_4_compatible'] else '✗ NO'}")
        output.append(f"HDMI 2.0 (18.0 Gbps):  {'✓ YES' if bandwidth['hdmi_2_0_compatible'] else '✗ NO'}")
        output.append(f"HDMI 2.1 (48.0 Gbps):  {'✓ YES' if bandwidth['hdmi_2_1_compatible'] else '✗ NO'}")
        output.append("")
        
        if params.is_estimated:
            output.append("⚠ NOTE: Parameters are estimated. Accuracy depends on actual signal.")
        
        output.append("=" * 60)
        
        return "\n".join(output)


class SceptreAPIClient:
    """
    Interface to 3DB Labs Sceptre API.
    Placeholder for actual hardware communication.
    """

    def __init__(self, device_path: Optional[str] = None):
        """
        Initialize API client.
        
        Args:
            device_path: Path to Sceptre device (USB/network)
        """
        self.device_path = device_path
        self.connected = False

    def connect(self) -> bool:
        """Connect to Sceptre hardware"""
        try:
            # TODO: Implement actual 3DB Labs API connection
            # This would typically use:
            # - USB communication via pyusb
            # - Network socket to Sceptre server
            # - Serial communication via pyserial
            self.connected = True
            return True
        except Exception as e:
            print(f"Failed to connect to Sceptre: {e}")
            return False

    def disconnect(self):
        """Disconnect from hardware"""
        self.connected = False

    def get_current_frequency(self) -> Optional[float]:
        """
        Get current tuned frequency from Sceptre.
        
        Returns:
            Frequency in MHz, or None if disconnected
        """
        if not self.connected:
            return None
        
        # TODO: Implement actual API call to read frequency
        # Example command structure:
        # response = self.send_command("GET_FREQUENCY")
        # return float(response) / 1e6  # Convert Hz to MHz
        
        return None

    def set_frequency(self, frequency_mhz: float) -> bool:
        """
        Set Sceptre to specific frequency.
        
        Args:
            frequency_mhz: Frequency in MHz
            
        Returns:
            True if successful
        """
        if not self.connected:
            return False
        
        # TODO: Implement actual API call to set frequency
        # Example command structure:
        # frequency_hz = int(frequency_mhz * 1e6)
        # self.send_command(f"SET_FREQUENCY {frequency_hz}")
        
        return False

    def send_command(self, command: str) -> str:
        """
        Send raw command to Sceptre.
        
        Args:
            command: Command string
            
        Returns:
            Response from device
        """
        # TODO: Implement actual communication protocol
        # This depends on 3DB Labs API documentation
        return ""
