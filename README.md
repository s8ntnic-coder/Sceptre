# Sceptre Video Analyzer

A Python program to interact with the **Sceptre oscilloscope** from **3DB Labs** API. This tool converts RF frequency tuning data into video emission parameters for HDMI and display cables.

## Features

✅ **Frequency-to-Video Parameter Conversion**
- Analyzes RF frequency from Sceptre oscilloscope
- Calculates video resolution, refresh rate, and timing parameters
- Supports 17 standard video modes (VGA through 8K)
- CVT-R2 estimation for custom frequencies

✅ **Complete Timing Analysis**
- Pixel clock frequency
- Pixel rate (Hz)
- Scanline time (microseconds)
- Frame rate (Hz)
- Frame duration (microseconds)
- Total pixels per frame

✅ **HDMI/DVI Compatibility**
- Calculates bandwidth requirements
- Checks HDMI 1.4/2.0/2.1 compatibility
- Supports data rates up to 48 Gbps

✅ **Easy Integration**
- Zero external dependencies
- Simple API client interface
- Debug mode for troubleshooting

## Installation

```bash
# Clone the repository
git clone https://github.com/s8ntnic-coder/Sceptre.git
cd Sceptre

# No dependencies needed! Uses Python standard library only
python3 example_usage.py
```

## Quick Start

```python
from sceptre_video_analyzer import SceptreVideoAnalyzer

# Create analyzer
analyzer = SceptreVideoAnalyzer()

# Analyze a frequency (Full HD 1080p @60Hz = 148.5 MHz)
params = analyzer.analyze_frequency(148.5)

# Print results
print(analyzer.format_analysis(params))
```

Output:
```
============================================================
SCEPTRE VIDEO ANALYSIS RESULTS
============================================================
Sceptre Frequency: 148.5 MHz

Standard: FULL_HD_60

VIDEO PARAMETERS
------------------------------------------------------------
Resolution:          1920x1080
Pixel Clock:         148.5 MHz
Pixel Rate:          148,500,000 Hz

TIMING
------------------------------------------------------------
H-Total (pixels):    2200
V-Total (lines):     1125
Scanline Time:       14.8148 µs
Frame Rate:          60.00 Hz
Frame Duration:      16666.67 µs
Total Pixels/Frame:  2,475,000

BANDWIDTH REQUIREMENTS
------------------------------------------------------------
Raw Bandwidth:       3.56 Gbps
TMDS Bandwidth:      4.45 Gbps

COMPATIBILITY
✓ HDMI 1.4 (10.2 Gbps):   YES
✓ HDMI 2.0 (18.0 Gbps):   YES
✓ HDMI 2.1 (48.0 Gbps):   YES
============================================================
```

## Supported Video Standards

| Resolution | Refresh Rate | Pixel Clock | HDMI Version |
|------------|-------------|-------------|-------------|
| 640×480    | 60 Hz      | 25.175 MHz  | 1.0         |
| 800×600    | 60 Hz      | 40.0 MHz    | 1.0         |
| 1024×768   | 60 Hz      | 65.0 MHz    | 1.0         |
| 1280×720   | 60 Hz      | 74.25 MHz   | 1.3         |
| 1280×800   | 60 Hz      | 83.5 MHz    | 1.3         |
| 1440×900   | 60 Hz      | 106.5 MHz   | 1.3         |
| 1600×1200  | 60 Hz      | 162.0 MHz   | 1.3         |
| 1920×1080  | 60 Hz      | 148.5 MHz   | 1.4         |
| 1920×1080  | 120 Hz     | 297.0 MHz   | 2.0         |
| 2560×1440  | 60 Hz      | 241.5 MHz   | 1.4         |
| 2560×2048  | 60 Hz      | 312.25 MHz  | 2.0         |
| 3840×2160  | 30 Hz      | 297.0 MHz   | 2.0         |
| 3840×2160  | 60 Hz      | 594.0 MHz   | 2.0         |
| 4096×2160  | 24 Hz      | 552.75 MHz  | 2.0         |
| 4096×2160  | 48 Hz      | 1105.5 MHz  | 2.1         |
| 7680×4320  | 30 Hz      | 1188.0 MHz  | 2.1         |
| 7680×4320  | 60 Hz      | 2376.0 MHz  | 2.1         |

## API Reference

### SceptreVideoAnalyzer

Main analyzer class for frequency conversion.

#### Methods

**`__init__(debug: bool = False)`**
- Initialize the analyzer
- `debug`: Enable debug output

**`analyze_frequency(frequency_mhz: float) -> VideoParameters`**
- Analyze a frequency and calculate video parameters
- Returns: `VideoParameters` object
- Automatically detects standard or estimates parameters

**`calculate_bandwidth_requirements(params: VideoParameters) -> Dict`**
- Calculate HDMI/DVI bandwidth
- Returns: Dictionary with bandwidth metrics and HDMI compatibility

**`format_analysis(params: VideoParameters) -> str`**
- Format results as human-readable string
- Returns: Formatted analysis output

### VideoParameters (Dataclass)

Result object containing calculated parameters.

#### Attributes
- `frequency_mhz` (float) - Input frequency in MHz
- `resolution_width` (int) - Horizontal resolution in pixels
- `resolution_height` (int) - Vertical resolution in pixels
- `pixel_clock_mhz` (float) - Pixel clock frequency
- `pixel_rate_hz` (int) - Pixel rate in Hz
- `scanline_time_us` (float) - Time per scanline in microseconds
- `frame_rate_hz` (float) - Refresh rate in Hz
- `frame_duration_us` (float) - Time per frame in microseconds
- `standard_name` (str, optional) - Matched video standard name
- `is_estimated` (bool) - Whether parameters were estimated
- `estimated_method` (str, optional) - Estimation method used
- `total_pixels_per_frame` (int) - Total pixels per frame
- `horizontal_pixels_total` (int) - Total horizontal pixels (incl. blanking)
- `vertical_lines_total` (int) - Total vertical lines (incl. blanking)

### SceptreAPIClient

Interface to 3DB Labs Sceptre hardware (placeholder for integration).

#### Methods

**`__init__(device_path: Optional[str] = None)`**
- Initialize API client
- `device_path`: Path to USB/serial device or network address

**`connect() -> bool`**
- Connect to Sceptre hardware
- Returns: Connection status

**`disconnect()`**
- Disconnect from hardware

**`get_current_frequency() -> Optional[float]`**
- Get current tuned frequency from Sceptre
- Returns: Frequency in MHz (or None if disconnected)

**`set_frequency(frequency_mhz: float) -> bool`**
- Set Sceptre to specific frequency
- Returns: Success status

**`send_command(command: str) -> str`**
- Send raw command to device
- Returns: Device response

## Examples

### Example 1: Basic Analysis

```python
analyzer = SceptreVideoAnalyzer()
params = analyzer.analyze_frequency(148.5)
print(analyzer.format_analysis(params))
```

### Example 2: Batch Analysis

```python
analyzer = SceptreVideoAnalyzer()

frequencies = [25.175, 40.0, 65.0, 148.5, 297.0]

for freq in frequencies:
    params = analyzer.analyze_frequency(freq)
    print(f"{freq} MHz -> {params.resolution_width}x{params.resolution_height} @ {params.frame_rate_hz:.0f}Hz")
```

### Example 3: Bandwidth Checking

```python
analyzer = SceptreVideoAnalyzer()
params = analyzer.analyze_frequency(594.0)  # 4K @60Hz

bandwidth = analyzer.calculate_bandwidth_requirements(params)

if bandwidth['hdmi_2_0_compatible']:
    print("✓ Compatible with HDMI 2.0")
else:
    print("✗ Requires HDMI 2.1")
```

### Example 4: Custom Frequency Estimation

```python
analyzer = SceptreVideoAnalyzer()

# Unknown/custom frequency - will use CVT-R2 estimation
params = analyzer.analyze_frequency(75.5)

if params.is_estimated:
    print(f"Estimated using: {params.estimated_method}")
    print(f"Estimated resolution: {params.resolution_width}x{params.resolution_height}")
```

### Example 5: Real-time Monitoring (with Sceptre API)

```python
from sceptre_video_analyzer import SceptreVideoAnalyzer, SceptreAPIClient

analyzer = SceptreVideoAnalyzer()
client = SceptreAPIClient(device_path="/dev/ttyUSB0")

if client.connect():
    freq = client.get_current_frequency()
    if freq:
        params = analyzer.analyze_frequency(freq)
        print(analyzer.format_analysis(params))
    client.disconnect()
```

## Technical Details

### CVT-R2 Algorithm

For frequencies that don't match standard video modes, the analyzer uses **CVT-R2 (Coordinated Video Timings Revision 2)** estimation:

1. Assumes 16:9 aspect ratio (common for modern displays)
2. Estimates 60 Hz refresh rate as baseline
3. Calculates total pixels from pixel clock
4. Applies standard blanking percentages:
   - Horizontal blanking: ~20%
   - Vertical blanking: ~10%
5. Derives resolution from aspect ratio

### Timing Calculations

**Scanline Time:**
```
scanline_time_us = (H_total / pixel_clock_hz) * 1e6
```

**Frame Duration:**
```
frame_duration_us = (H_total * V_total / pixel_clock_hz) * 1e6
```

**Frame Rate:**
```
frame_rate_hz = pixel_clock_hz / (H_total * V_total)
```

### Bandwidth Calculation

**Raw Bandwidth (24-bit color):**
```
bandwidth = pixel_clock_mhz * 24 bits / 8 (Gbps)
```

**HDMI TMDS Bandwidth (with encoding overhead):**
```
tmds_bandwidth = raw_bandwidth * 1.25 (Gbps)
```

**HDMI Compatibility:**
- HDMI 1.4: ≤ 10.2 Gbps
- HDMI 2.0: ≤ 18.0 Gbps
- HDMI 2.1: ≤ 48.0 Gbps

## Integration with 3DB Labs Sceptre

To integrate with your Sceptre hardware:

1. **Implement `SceptreAPIClient` methods** with actual 3DB Labs API calls:
   - Update `connect()` for USB/serial/network initialization
   - Implement `get_current_frequency()` to read from hardware
   - Implement `set_frequency()` to tune the oscilloscope

2. **Communication Protocols** (check 3DB Labs documentation):
   - USB: PyUSB or serial library
   - Serial: PySerial
   - Network: Socket or dedicated client library

3. **Example Integration:**

```python
import serial
from sceptre_video_analyzer import SceptreVideoAnalyzer, SceptreAPIClient

class SceptreHardwareClient(SceptreAPIClient):
    def connect(self):
        try:
            self.serial = serial.Serial(self.device_path, 115200)
            self.connected = True
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def get_current_frequency(self):
        if self.connected:
            self.serial.write(b"*IDN?\n")
            response = self.serial.readline().decode().strip()
            # Parse response to extract frequency
            return float(response)
        return None
```

## Troubleshooting

**"Frequency not recognized"**
- Check if frequency is within ±2 MHz of a standard mode
- Use the CVT-R2 estimation by providing the exact frequency

**"Parameters seem incorrect"**
- Enable debug mode: `SceptreVideoAnalyzer(debug=True)`
- Check if the signal is interlaced (currently assumes progressive)
- Verify Sceptre frequency reading

**"HDMI compatibility issue"**
- Check calculated TMDS bandwidth
- Ensure cable quality for high-frequency signals
- Verify HDMI version support on both ends

## License

[Add your license here]

## Contributing

Contributions welcome! Areas for enhancement:

- [ ] Interlaced video support
- [ ] Custom blanking calculations
- [ ] Real-time oscilloscope integration
- [ ] Additional video standards
- [ ] GUI interface
- [ ] Data logging and analysis

## Contact

Repository: https://github.com/s8ntnic-coder/Sceptre

---

**Built for analyzing HDMI/DVI video emissions using Sceptre oscilloscope and 3DB Labs API**
