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
        return f"MOCK_ACK: {command}""""
Sceptre Video Analyzer - Enhanced Edition
==========================================
A program to interact with Sceptre oscilloscope from 3DB Labs API.
Converts frequency tuning to video emission parameters (HDMI/DVI cables).

Now includes:
- Detailed blanking interval analysis (accounts for video card variations)
- Harmonic detection (2x-10x harmonics and subharmonics)
- Multiple blanking profiles (minimal, standard, extended)

Calculates:
- Video resolution
- Pixel rate
- Scanline time
- Frame rate
- Frame duration
- Blanking intervals (horizontal and vertical)
- Detected harmonics and subharmonics
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
    # Horizontal blanking (in pixels)
    h_front_porch_pixels: int = 0
    h_sync_pixels: int = 0
    h_back_porch_pixels: int = 0
    h_total_blanking: int = 0
    h_blanking_percent: float = 0.0
    
    # Vertical blanking (in lines)
    v_front_porch_lines: int = 0
    v_sync_lines: int = 0
    v_back_porch_lines: int = 0
    v_total_blanking: int = 0
    v_blanking_percent: float = 0.0
    
    # Profile used for calculation
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
    """
    Main analyzer for converting Sceptre frequency to video parameters.
    Supports HDMI, DVI, and VGA standards.
    Includes harmonic detection and blanking interval analysis.
    """

    # HDMI/DVI frequency tolerance (MHz)
    FREQUENCY_TOLERANCE = 2.0

    # Blanking profiles for different video card implementations
    BLANKING_PROFILES = {
        'minimal': {
            'h_front_porch_percent': 0.03,
            'h_sync_percent': 0.04,
            'h_back_porch_percent': 0.04,
            'v_front_porch_percent': 0.01,
            'v_sync_percent': 0.04,
            'v_back_porch_percent': 0.02,
        },
        'standard': {
            'h_front_porch_percent': 0.04,
            'h_sync_percent': 0.05,
            'h_back_porch_percent': 0.08,
            'v_front_porch_percent': 0.01,
            'v_sync_percent': 0.05,
            'v_back_porch_percent': 0.04,
        },
        'extended': {
            'h_front_porch_percent': 0.05,
            'h_sync_percent': 0.06,
            'h_back_porch_percent': 0.10,
            'v_front_porch_percent': 0.015,
            'v_sync_percent': 0.06,
            'v_back_porch_percent': 0.055,
        },
    }

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

    def analyze_frequency(self, frequency_mhz: float, blanking_profile: str = 'standard') -> VideoParameters:
        """
        Analyze a frequency and calculate video parameters.
        
        Args:
            frequency_mhz: Sceptre tuned frequency in MHz
            blanking_profile: Blanking profile ('minimal', 'standard', 'extended')
            
        Returns:
            VideoParameters object with calculated values
        """
        if blanking_profile not in self.BLANKING_PROFILES:
            raise ValueError(f"Invalid blanking profile: {blanking_profile}")
        
        if self.debug:
            print(f"[DEBUG] Analyzing frequency: {frequency_mhz} MHz (blanking: {blanking_profile})")

        # Try to match known standard
        standard = self._match_standard(frequency_mhz, blanking_profile)
        if standard:
            return standard

        # Estimate parameters using CVT-R2
        params = self._estimate_cvt_r2(frequency_mhz, blanking_profile)
        
        # Detect harmonics
        params.detected_harmonics_from_freq = self._detect_harmonics(frequency_mhz)
        
        return params

    def _match_standard(self, frequency_mhz: float, blanking_profile: str) -> Optional[VideoParameters]:
        """Match frequency to known video standard"""
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
                
                # Detect harmonics
                params.detected_harmonics_from_freq = self._detect_harmonics(frequency_mhz)
                
                return params
        return None

    def _estimate_cvt_r2(self, frequency_mhz: float, blanking_profile: str) -> VideoParameters:
        """
        Estimate video parameters using CVT-R2 algorithm.
        
        Assumes:
        - 16:9 aspect ratio (common for modern displays)
        - Reduced blanking v2 (CVT-R2)
        """
        if self.debug:
            print(f"[DEBUG] Estimating parameters using CVT-R2 for {frequency_mhz} MHz")

        estimated_frame_rate = 60.0  # Hz (common assumption)
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
            estimated_method="CVT-R2 16:9",
            blanking_profile=blanking_profile
        )

    def _calculate_parameters(
        self,
        frequency_mhz: float,
        width: int,
        height: int,
        pixel_clock_mhz: float,
        standard_name: Optional[str] = None,
        is_estimated: bool = False,
        estimated_method: Optional[str] = None,
        blanking_profile: str = 'standard'
    ) -> VideoParameters:
        """Calculate all video parameters from base values"""
        
        pixel_clock_hz = pixel_clock_mhz * 1e6
        pixel_rate_hz = int(pixel_clock_hz)
        
        # Calculate blanking parameters based on profile
        profile = self.BLANKING_PROFILES[blanking_profile]
        
        # Horizontal blanking
        h_front_porch = int(width * profile['h_front_porch_percent'])
        h_sync = int(width * profile['h_sync_percent'])
        h_back_porch = int(width * profile['h_back_porch_percent'])
        h_total_blanking = h_front_porch + h_sync + h_back_porch
        h_total = width + h_total_blanking
        h_blanking_percent = (h_total_blanking / h_total) * 100
        
        # Vertical blanking
        v_front_porch = max(1, int(height * profile['v_front_porch_percent']))
        v_sync = max(1, int(height * profile['v_sync_percent']))
        v_back_porch = max(1, int(height * profile['v_back_porch_percent']))
        v_total_blanking = v_front_porch + v_sync + v_back_porch
        v_total = height + v_total_blanking
        v_blanking_percent = (v_total_blanking / v_total) * 100
        
        # Timing calculations
        scanline_time_us = (h_total / pixel_clock_hz) * 1e6
        frame_time_us = (h_total * v_total / pixel_clock_hz) * 1e6
        frame_rate_hz = pixel_clock_hz / (h_total * v_total)
        total_pixels_per_frame = h_total * v_total
        
        # Create blanking parameters object
        blanking = BlankingParameters(
            h_front_porch_pixels=h_front_porch,
            h_sync_pixels=h_sync,
            h_back_porch_pixels=h_back_porch,
            h_total_blanking=h_total_blanking,
            h_blanking_percent=h_blanking_percent,
            v_front_porch_lines=v_front_porch,
            v_sync_lines=v_sync,
            v_back_porch_lines=v_back_porch,
            v_total_blanking=v_total_blanking,
            v_blanking_percent=v_blanking_percent,
            profile_name=blanking_profile
        )
        
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
            vertical_lines_total=v_total,
            blanking=blanking
        )

    def _detect_harmonics(self, frequency_mhz: float, max_harmonic: int = 10) -> List[Harmonic]:
        """
        Detect harmonics and subharmonics of a frequency.
        
        Args:
            frequency_mhz: Base frequency in MHz
            max_harmonic: Maximum harmonic order to check
            
        Returns:
            List of detected harmonics matching known video standards
        """
        harmonics = []
        
        # Check harmonics (2x, 3x, etc.)
        for n in range(2, max_harmonic + 1):
            harmonic_freq = frequency_mhz * n
            matched = self._match_standard(harmonic_freq, 'standard')
            if matched:
                harmonics.append(Harmonic(
                    harmonic_number=float(n),
                    frequency_mhz=harmonic_freq,
                    is_subharmonic=False,
                    parent_frequency_mhz=frequency_mhz,
                    estimated_parameters=matched,
                    standard_name=matched.standard_name
                ))
        
        # Check subharmonics (1/2, 1/3, etc.)
        for n in range(2, max_harmonic + 1):
            subharmonic_freq = frequency_mhz / n
            matched = self._match_standard(subharmonic_freq, 'standard')
            if matched:
                harmonics.append(Harmonic(
                    harmonic_number=float(n),
                    frequency_mhz=subharmonic_freq,
                    is_subharmonic=True,
                    parent_frequency_mhz=frequency_mhz,
                    estimated_parameters=matched,
                    standard_name=matched.standard_name
                ))
        
        return harmonics

    def calculate_bandwidth_requirements(self, params: VideoParameters) -> Dict[str, float]:
        """
        Calculate HDMI/DVI bandwidth requirements.
        
        Args:
            params: VideoParameters from analyze_frequency()
            
        Returns:
            Dictionary with bandwidth calculations
        """
        bits_per_pixel = 24
        pixel_clock_hz = params.pixel_clock_mhz * 1e6
        
        raw_bandwidth_bps = pixel_clock_hz * bits_per_pixel
        raw_bandwidth_gbps = raw_bandwidth_bps / 1e9
        
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
        output.append("=" * 70)
        output.append("SCEPTRE VIDEO ANALYSIS RESULTS")
        output.append("=" * 70)
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
        output.append("-" * 70)
        output.append(f"Resolution:          {params.resolution_width}x{params.resolution_height}")
        output.append(f"Pixel Clock:         {params.pixel_clock_mhz} MHz")
        output.append(f"Pixel Rate:          {params.pixel_rate_hz:,} Hz")
        output.append("")
        
        output.append("TIMING")
        output.append("-" * 70)
        output.append(f"H-Total (pixels):    {params.horizontal_pixels_total}")
        output.append(f"V-Total (lines):     {params.vertical_lines_total}")
        output.append(f"Scanline Time:       {params.scanline_time_us:.4f} µs")
        output.append(f"Frame Rate:          {params.frame_rate_hz:.2f} Hz")
        output.append(f"Frame Duration:      {params.frame_duration_us:.2f} µs")
        output.append(f"Total Pixels/Frame:  {params.total_pixels_per_frame:,}")
        output.append("")
        
        output.append("BLANKING INTERVALS")
        output.append("-" * 70)
        output.append(f"Profile: {params.blanking.profile_name.upper()}")
        output.append(f"Horizontal Blanking: {params.blanking.h_total_blanking} pixels ({params.blanking.h_blanking_percent:.2f}%)")
        output.append(f"  Front Porch: {params.blanking.h_front_porch_pixels}px | "
                      f"Sync: {params.blanking.h_sync_pixels}px | "
                      f"Back Porch: {params.blanking.h_back_porch_pixels}px")
        output.append(f"Vertical Blanking:   {params.blanking.v_total_blanking} lines ({params.blanking.v_blanking_percent:.2f}%)")
        output.append(f"  Front Porch: {params.blanking.v_front_porch_lines}ln | "
                      f"Sync: {params.blanking.v_sync_lines}ln | "
                      f"Back Porch: {params.blanking.v_back_porch_lines}ln")
        output.append("")
        
        bandwidth = self.calculate_bandwidth_requirements(params)
        output.append("BANDWIDTH REQUIREMENTS")
        output.append("-" * 70)
        output.append(f"Raw Bandwidth:       {bandwidth['raw_bandwidth_gbps']:.2f} Gbps")
        output.append(f"TMDS Bandwidth:      {bandwidth['tmds_bandwidth_gbps']:.2f} Gbps")
        output.append("")
        output.append("COMPATIBILITY")
        output.append(f"HDMI 1.4 (10.2 Gbps):  {'✓ YES' if bandwidth['hdmi_1_4_compatible'] else '✗ NO'}")
        output.append(f"HDMI 2.0 (18.0 Gbps):  {'✓ YES' if bandwidth['hdmi_2_0_compatible'] else '✗ NO'}")
        output.append(f"HDMI 2.1 (48.0 Gbps):  {'✓ YES' if bandwidth['hdmi_2_1_compatible'] else '✗ NO'}")
        output.append("")
        
        if params.detected_harmonics_from_freq:
            output.append("DETECTED HARMONICS")
            output.append("-" * 70)
            for harmonic in params.detected_harmonics_from_freq:
                h_type = "Subharmonic" if harmonic.is_subharmonic else "Harmonic"
                multiplier = f"1/{int(harmonic.harmonic_number)}" if harmonic.is_subharmonic else f"{int(harmonic.harmonic_number)}x"
                mode = harmonic.standard_name if harmonic.standard_name else "Unknown"
                output.append(f"{h_type:12} {multiplier:8} → {harmonic.frequency_mhz:10.2f} MHz → {mode}")
            output.append("")
        
        if params.is_estimated:
            output.append("⚠ NOTE: Parameters are estimated. Accuracy depends on actual signal.")
        
        output.append("=" * 70)
        
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
        
        return False

    def send_command(self, command: str) -> str:
        """
        Send raw command to Sceptre.
        
        Args:
            command: Command string
            
        Returns:
            Response from device
        """
        return ""
