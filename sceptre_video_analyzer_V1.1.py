"""
Sceptre Video Analyzer - Enhanced Edition (Fixed)
==================================================
A program to interact with Sceptre oscilloscope from 3DB Labs API.
Converts frequency tuning to video emission parameters (HDMI/DVI cables).
"""

from dataclasses import dataclass, field
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
class BlankingParameters:
    """Blanking interval details for video signal"""
    h_front_porch_pixels: int = 0
    h_sync_pixels: int = 0
    h_back_porch_pixels: int = 0
    h_total_blanking: int = 0
    h_blanking_percent: float = 0.0
    
    v_front_porch_lines: int = 0
    v_sync_lines: int = 0
    v_back_porch_lines: int = 0
    v_total_blanking: int = 0
    v_blanking_percent: float = 0.0
    
    profile_name: str = "standard"


@dataclass
class Harmonic:
    """Detected harmonic or subharmonic of a frequency"""
    harmonic_number: float  # 2, 3, 1/2, 1/3, etc.
    frequency_mhz: float
    is_subharmonic: bool
    parent_frequency_mhz: float
    estimated_parameters: Optional['VideoParameters'] = None
    standard_name: Optional[str] = None


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
    blanking: BlankingParameters = field(default_factory=BlankingParameters)
    detected_harmonics_from_freq: List[Harmonic] = field(default_factory=list)


class SceptreVideoAnalyzer:
    """Main analyzer for converting Sceptre frequency to video parameters."""

    FREQUENCY_TOLERANCE = 2.0

    BLANKING_PROFILES = {
        'minimal': {
            'h_front_porch_percent': 0.03, 'h_sync_percent': 0.04, 'h_back_porch_percent': 0.04,
            'v_front_porch_percent': 0.01, 'v_sync_percent': 0.04, 'v_back_porch_percent': 0.02,
        },
        'standard': {
            'h_front_porch_percent': 0.04, 'h_sync_percent': 0.05, 'h_back_porch_percent': 0.08,
            'v_front_porch_percent': 0.01, 'v_sync_percent': 0.05, 'v_back_porch_percent': 0.04,
        },
        'extended': {
            'h_front_porch_percent': 0.05, 'h_sync_percent': 0.06, 'h_back_porch_percent': 0.10,
            'v_front_porch_percent': 0.015, 'v_sync_percent': 0.06, 'v_back_porch_percent': 0.055,
        },
    }

    def __init__(self, debug: bool = False):
        self.debug = debug
        self._build_standard_lookup()

    def _build_standard_lookup(self):
        self.standards_by_frequency: Dict[float, Tuple[str, int, int, float]] = {}
        for standard in VideoStandard:
            width, height, freq = standard.value
            key = round(freq, 2)
            self.standards_by_frequency[key] = (standard.name, width, height, freq)

    def analyze_frequency(self, frequency_mhz: float, blanking_profile: str = 'standard') -> VideoParameters:
        if blanking_profile not in self.BLANKING_PROFILES:
            raise ValueError(f"Invalid blanking profile: {blanking_profile}")
        
        if self.debug:
            print(f"[DEBUG] Analyzing frequency: {frequency_mhz} MHz (blanking: {blanking_profile})")

        # Base user trace calculations can parse tracking harmonics
        standard = self._match_standard(frequency_mhz, blanking_profile, is_harmonic_check=False)
        if standard:
            return standard

        params = self._estimate_cvt_r2(frequency_mhz, blanking_profile)
        params.detected_harmonics_from_freq = self._detect_harmonics(frequency_mhz, blanking_profile)
        return params

    def _match_standard(self, frequency_mhz: float, blanking_profile: str, is_harmonic_check: bool = False) -> Optional[VideoParameters]:
        """Match frequency to known video standard with a recursion guard flag."""
        for known_freq, (name, width, height, pixel_clock) in self.standards_by_frequency.items():
            if abs(frequency_mhz - known_freq) <= self.FREQUENCY_TOLERANCE:
                if self.debug:
                    print(f"[DEBUG] Matched standard: {name} ({width}x{height})")
                
                params = self._calculate_parameters(
                    frequency_mhz=frequency_mhz,
                    width=width,
                    height=height,
                    pixel_clock_mhz=pixel_clock,
                    standard_name=name,
                    is_estimated=False,
                    blanking_profile=blanking_profile
                )
                
                # RECURSION FIX: Block nesting loops if this function instance handles a sub/harmonic lookup
                if not is_harmonic_check:
                    params.detected_harmonics_from_freq = self._detect_harmonics(frequency_mhz, blanking_profile)
                else:
                    params.detected_harmonics_from_freq = []
                
                return params
        return None

    def _estimate_cvt_r2(self, frequency_mhz: float, blanking_profile: str) -> VideoParameters:
        if self.debug:
            print(f"[DEBUG] Estimating parameters using CVT-R2 for {frequency_mhz} MHz")

        estimated_frame_rate = 60.0
        pixel_clock_hz = frequency_mhz * 1e6
        total_pixels = pixel_clock_hz / estimated_frame_rate
        
        active_pixels_percent = 0.80
        active_pixels = total_pixels * active_pixels_percent
        
        width = int(math.sqrt(active_pixels * (16 / 9)))
        width = (width // 8) * 8
        
        height = int(width * 9 / 16)
        height = (height // 2) * 2
        
        return self._calculate_parameters(
            frequency_mhz=frequency_mhz,
            width=width,
            height=height,
            pixel_clock_mhz=frequency_mhz,
            standard_name=None,
            is_estimated=True,
            estimated_method="CVT-R2 Approximation",
            blanking_profile=blanking_profile
        )

    def _calculate_parameters(self, frequency_mhz: float, width: int, height: int, 
                              pixel_clock_mhz: float, standard_name: Optional[str], 
                              is_estimated: bool, blanking_profile: str, 
                              estimated_method: Optional[str] = None) -> VideoParameters:
        """Calculates dynamic sync margins, porch pixel lines, and structural totals."""
        prof = self.BLANKING_PROFILES[blanking_profile]
        
        h_fp = int(width * prof['h_front_porch_percent'])
        h_sync = int(width * prof['h_sync_percent'])
        h_bp = int(width * prof['h_back_porch_percent'])
        h_blank = h_fp + h_sync + h_bp
        h_total = width + h_blank
        h_blank_pct = (h_blank / h_total) * 100 if h_total > 0 else 0.0

        v_fp = int(height * prof['v_front_porch_percent'])
        v_sync = int(height * prof['v_sync_percent'])
        v_bp = int(height * prof['v_back_porch_percent'])
        v_blank = v_fp + v_sync + v_bp
        v_total = height + v_blank
        v_blank_pct = (v_blank / v_total) * 100 if v_total > 0 else 0.0

        blanking_obj = BlankingParameters(
            h_front_porch_pixels=h_fp, h_sync_pixels=h_sync, h_back_porch_pixels=h_bp,
            h_total_blanking=h_blank, h_blanking_percent=h_blank_pct,
            v_front_porch_lines=v_fp, v_sync_lines=v_sync, v_back_porch_lines=v_bp,
            v_total_blanking=v_blank, v_blanking_percent=v_blank_pct,
            profile_name=blanking_profile
        )

        total_pixels = h_total * v_total
        pixel_rate = int(pixel_clock_mhz * 1e6)
        
        scanline_time = (h_total / pixel_clock_mhz) if pixel_clock_mhz > 0 else 0.0
        frame_rate = (pixel_rate / total_pixels) if total_pixels > 0 else 0.0
        frame_duration = (total_pixels / pixel_clock_mhz) if pixel_clock_mhz > 0 else 0.0

        return VideoParameters(
            frequency_mhz=frequency_mhz, resolution_width=width, resolution_height=height,
            pixel_clock_mhz=pixel_clock_mhz, pixel_rate_hz=pixel_rate, scanline_time_us=scanline_time,
            frame_rate_hz=frame_rate, frame_duration_us=frame_duration, standard_name=standard_name,
            is_estimated=is_estimated, estimated_method=estimated_method, total_pixels_per_frame=total_pixels,
            horizontal_pixels_total=h_total, vertical_lines_total=v_total, blanking=blanking_obj
        )

    def _detect_harmonics(self, frequency_mhz: float, blanking_profile: str = 'standard') -> List[Harmonic]:
        """Identifies integer harmonics (2x-10x) and fractional subharmonics safely."""
        harmonics_list = []
        
        # 2x up to 10x Harmonics
        for mult in range(2, 11):
            h_freq = frequency_mhz * mult
            matched = self._match_standard(h_freq, blanking_profile, is_harmonic_check=True)
            if matched:
                harmonics_list.append(Harmonic(
                    harmonic_number=float(mult), frequency_mhz=h_freq, is_subharmonic=False,
                    parent_frequency_mhz=frequency_mhz, estimated_parameters=matched,
                    standard_name=matched.standard_name
                ))

        # 1/2 down to 1/10 Subharmonics
        for div in range(2, 11):
            sub_freq = frequency_mhz / div
            matched = self._match_standard(sub_freq, blanking_profile, is_harmonic_check=True)
            if matched:
                harmonics_list.append(Harmonic(
                    harmonic_number=round(1.0 / div, 3), frequency_mhz=sub_freq, is_subharmonic=True,
                    parent_frequency_mhz=frequency_mhz, estimated_parameters=matched,
                    standard_name=matched.standard_name
                ))

        return harmonics_list

    def calculate_bandwidth_requirements(self, params: VideoParameters) -> Dict:
        """Calculates digital line wire bandwidth and HDMI physical layer limits."""
        raw_bandwidth_gbps = (params.pixel_clock_mhz * 24) / 1000.0
        tmds_bandwidth_gbps = raw_bandwidth_gbps * 1.25
        
        return {
            "raw_bandwidth_gbps": raw_bandwidth_gbps,
            "tmds_bandwidth_gbps": tmds_bandwidth_gbps,
            "hdmi_1_4_compatible": tmds_bandwidth_gbps <= 10.2,
            "hdmi_2_0_compatible": tmds_bandwidth_gbps <= 18.0,
            "hdmi_2_1_compatible": tmds_bandwidth_gbps <= 48.0
        }

    def format_analysis(self, params: VideoParameters) -> str:
        """Formats structural parameter fields into a clean output block."""
        mode_str = params.standard_name if params.standard_name else f"Unknown ({params.estimated_method})"
        
        # Pull bandwidth metrics dynamically
        bw = self.calculate_bandwidth_requirements(params)
        
        return (
            f"{'='*60}\n"
            f"SCEPTRE VIDEO ANALYSIS RESULTS\n"
            f"{'='*60}\n"
            f"Sceptre Frequency: {params.frequency_mhz:.2f} MHz\n"
            f"Standard:          {mode_str}\n\n"
            f"VIDEO PARAMETERS\n"
            f"{'-'*60}\n"
            f"Resolution:        {params.resolution_width}x{params.resolution_height}\n"
            f"Pixel Clock:       {params.pixel_clock_mhz:.2f} MHz\n"
            f"Pixel Rate:        {params.pixel_rate_hz:,} Hz\n\n"
            f"TIMING\n"
            f"{'-'*60}\n"
            f"H-Total (pixels):  {params.horizontal_pixels_total}\n"
            f"V-Total (lines):   {params.vertical_lines_total}\n"
            f"Scanline Time:     {params.scanline_time_us:.4f} µs\n"
            f"Frame Rate:        {params.frame_rate_hz:.2f} Hz\n"
            f"Frame Duration:    {params.frame_duration_us:.2f} µs\n"
            f"Total Pixels/Frame:{params.total_pixels_per_frame:,}\n\n"
            f"BANDWIDTH REQUIREMENTS\n"
            f"{'-'*60}\n"
            f"Raw Bandwidth:     {bw['raw_bandwidth_gbps']:.2f} Gbps\n"
            f"TMDS Bandwidth:    {bw['tmds_bandwidth_gbps']:.2f} Gbps\n\n"
            f"COMPATIBILITY\n"
            f"✓ HDMI 1.4 (10.2 Gbps): {'YES' if bw['hdmi_1_4_compatible'] else 'NO'}\n"
            f"✓ HDMI 2.0 (18.0 Gbps): {'YES' if bw['hdmi_2_0_compatible'] else 'NO'}\n"
            f"✓ HDMI 2.1 (48.0 Gbps): {'YES' if bw['hdmi_2_1_compatible'] else 'NO'}\n"
            f"{'='*60}"
        )


class SceptreAPIClient:
    """Mock interface tracking API endpoints for 3DB Labs Sceptre hardware."""

    def __init__(self, device_path: Optional[str] = None):
        self.device_path = device_path
        self.is_connected = False
        self._current_freq = 148.5

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self):
        self.is_connected = False

    def get_current_frequency(self) -> Optional[float]:
        return self._current_freq if self.is_connected else None

    def set_frequency(self, frequency_mhz: float) -> bool:
        if self.is_connected:
            self._current_freq = frequency_mhz
            return True
        return False

    def send_command(self, command: str) -> str:
        return f"MOCK_ACK: {command}"
