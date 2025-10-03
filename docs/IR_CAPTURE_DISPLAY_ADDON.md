# SSD1306 OLED Display Add-on for IR Capture Device

## Overview

Adding an SSD1306 OLED display to your IR capture device provides real-time visual feedback without needing to check logs or open the web interface. The display shows WiFi status, IP address, signal strength, and captured IR codes in real-time.

## Display Features

### What's Shown on the Display:

```
┌────────────────────────────┐
│     IR CAPTURE            │  ← Header
├────────────────────────────┤
│ WiFi: 192.168.101.126     │  ← IP Address
│ Signal: -52 dBm           │  ← WiFi Signal
│                           │
│ Last Code:                │  ← Status
│ [4500, 4500, 560...       │  ← First 20 chars
└────────────────────────────┘
```

### Real-time Updates:
- ✅ WiFi connection status
- ✅ IP address (for easy access)
- ✅ WiFi signal strength
- ✅ Last captured IR code preview
- ✅ "Ready to capture" status
- ✅ LED flash on code capture

## Hardware Requirements

### Display Options

You can use either size (128x64 recommended):

| Display | Resolution | Size | I2C Address | Notes |
|---------|-----------|------|-------------|-------|
| SSD1306 128x64 | 128x64 pixels | 0.96" | 0x3C or 0x3D | **Recommended** - More info fits |
| SSD1306 128x32 | 128x32 pixels | 0.91" | 0x3C or 0x3D | Smaller, less text |

### Where to Buy

**Common Sources:**
- Amazon: "SSD1306 OLED 128x64 I2C"
- AliExpress: ~$2-4 USD
- Adafruit: Product #326 (0.96" OLED)
- SparkFun: Part #LCD-14532

**What to Look For:**
- I2C interface (4 pins: VCC, GND, SCL, SDA)
- 3.3V or 5V compatible
- Address jumpers (to change 0x3C ↔ 0x3D if needed)

### Complete Parts List

| Component | Quantity | Purpose |
|-----------|----------|---------|
| SSD1306 OLED (128x64) | 1 | Display module |
| Jumper wires (Female-Female) | 4 | I2C connections |
| *(All other parts same as base IR capture device)* | | |

## Wiring Diagram

### SSD1306 to ESP32 Connections

```
SSD1306 OLED Display               ESP32-WROOM-32
┌─────────────────┐                ┌──────────────┐
│                 │                │              │
│  ┌───────────┐  │                │              │
│  │  SCREEN   │  │                │              │
│  │           │  │                │              │
│  │  128x64   │  │                │              │
│  │           │  │                │              │
│  └───────────┘  │                │              │
│                 │                │              │
│  [Pin Header]   │                │              │
│   │ │ │ │       │                │              │
└───┼─┼─┼─┼───────┘                │              │
    │ │ │ │                        │              │
    │ │ │ └─ VCC ────────────────→ 3.3V or 5V    │
    │ │ └─── GND ──────────────────→ GND         │
    │ └───── SCL ───────────────────→ GPIO22     │
    └─────── SDA ───────────────────→ GPIO21     │
                                     │              │
                                     └──────────────┘
```

### Pin Connections Table

| SSD1306 Pin | ESP32 Pin | Wire Color (Suggested) |
|-------------|-----------|------------------------|
| **VCC** | 3.3V or 5V | Red |
| **GND** | GND | Black |
| **SCL** | GPIO22 | Yellow |
| **SDA** | GPIO21 | Blue |

**Note:** Most SSD1306 displays work with both 3.3V and 5V. Check your module specs.

### I2C Pull-up Resistors

Most SSD1306 modules have **built-in pull-up resistors**, so you don't need external ones. If you have issues:

```
Optional External Pull-ups:
   3.3V ──┬─[4.7kΩ]─┬─ SCL (GPIO22)
          └─[4.7kΩ]─┘─ SDA (GPIO21)
```

### Complete System Schematic

```
┌─────────────────────────────────────────────────────────┐
│              ESP32-WROOM-32 with OLED Display           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌───────────────────────────────┐                    │
│   │      ESP32 Board              │                    │
│   │                               │                    │
│   │  3.3V ─────┬──────────────────┼─→ OLED VCC        │
│   │            │                  │                    │
│   │  GND ──────┼─────┬────────────┼─→ OLED GND        │
│   │            │     │            │                    │
│   │  GPIO21 ───┼─────┼────────────┼─→ OLED SDA        │
│   │  GPIO22 ───┼─────┼────────────┼─→ OLED SCL        │
│   │            │     │            │                    │
│   │  GPIO14 ───┼─────┼────────────┼─→ TSOP38238 OUT   │
│   │            │     │            │                    │
│   │  GPIO12 ───┼─────┼────────────┼─→ IR LED Circuit  │
│   │            │     │            │                    │
│   │  GPIO2 ────┘     └────────────┼─→ Status LED      │
│   │                               │                    │
│   └───────────────────────────────┘                    │
│                                                         │
└─────────────────────────────────────────────────────────┘

         ┌─────────────┐
         │ SSD1306     │
         │  ┌───────┐  │
         │  │ OLED  │  │
         │  │128x64 │  │
         │  └───────┘  │
         └─────────────┘
```

## Software Configuration

### YAML File

The enhanced configuration is in: `esphome/ir_capture_device_with_display.yaml`

### Key Configuration Sections

#### 1. I2C Bus Setup
```yaml
i2c:
  sda: GPIO21  # Default SDA on ESP32
  scl: GPIO22  # Default SCL on ESP32
  scan: true   # Auto-detect I2C devices
```

#### 2. Display Fonts
```yaml
font:
  - file: "gfonts://Roboto"
    id: font_small
    size: 10
  - file: "gfonts://Roboto"
    id: font_medium
    size: 14
  - file: "gfonts://Roboto@700"
    id: font_large
    size: 20
```

Fonts are downloaded from Google Fonts during compilation.

#### 3. Display Component
```yaml
display:
  - platform: ssd1306_i2c
    model: "SSD1306 128x64"  # or "SSD1306 128x32"
    address: 0x3C            # or 0x3D
    id: oled_display
    update_interval: 200ms
```

#### 4. Display Lambda (What Shows)
```yaml
lambda: |-
  // Header with border
  it.rectangle(0, 0, it.get_width(), 16);
  it.print(64, 2, id(font_medium), TextAlign::TOP_CENTER, "IR CAPTURE");

  // WiFi status
  if (id(wifi_component).is_connected()) {
    it.printf(2, 20, id(font_small), "WiFi: %s", id(wifi_ip).state.c_str());
    it.printf(2, 32, id(font_small), "Signal: %.0f dBm", id(wifi_signal_sensor).state);
  } else {
    it.print(2, 20, id(font_small), "WiFi: Disconnected");
  }

  // IR code preview
  if (id(last_ir_code).state.length() > 10) {
    it.print(2, 44, id(font_small), "Last Code:");
    std::string code = id(last_ir_code).state.substr(0, 20);
    it.printf(2, 54, id(font_small), "%s...", code.c_str());
  } else {
    it.print(2, 44, id(font_small), "Ready to capture");
    it.print(2, 54, id(font_small), "Point remote & press");
  }
```

## Installation Steps

### Step 1: Physical Assembly

1. **Prepare the Display**
   - Check which pins are labeled on your module
   - Some modules have pins: GND, VCC, SCL, SDA
   - Others have: VCC, GND, SCL, SDA (different order!)

2. **Connect Wires**
   ```
   Display → ESP32
   ─────────────────
   VCC → 3.3V (or 5V if specified)
   GND → GND
   SCL → GPIO22
   SDA → GPIO21
   ```

3. **Secure the Display**
   - Use double-sided tape or mount
   - Position for easy viewing
   - Keep wires organized

### Step 2: Compile and Flash

#### Option A: First-Time Flash (USB)
```bash
# Compile the new YAML
source venv/bin/activate
esphome compile esphome/ir_capture_device_with_display.yaml

# Flash via USB
esphome upload esphome/ir_capture_device_with_display.yaml --device /dev/ttyUSB0
```

#### Option B: OTA Update (If Already Flashed)
```bash
# Change device name in YAML first, or flash to new device
esphome upload esphome/ir_capture_device_with_display.yaml --device 192.168.101.126
```

#### Option C: Create New Device
```bash
# For a separate device with display
# The YAML is already configured for device_name: ir-capture-display
esphome run esphome/ir_capture_device_with_display.yaml
```

### Step 3: Verify Display Works

After flashing, you should immediately see:

1. **Boot Screen** (brief)
   - Display initializes

2. **WiFi Connecting** (2-5 seconds)
   - "WiFi: Disconnected" shown

3. **Connected Screen**
   ```
   ┌──────────────────────┐
   │   IR CAPTURE        │
   ├──────────────────────┤
   │ WiFi: 192.168.101.X │
   │ Signal: -XX dBm     │
   │                     │
   │ Ready to capture    │
   │ Point remote & press│
   └──────────────────────┘
   ```

## Troubleshooting

### Display Doesn't Turn On

**Check Power:**
```bash
# Measure voltage at display VCC pin
# Should be 3.3V or 5V

# Check ESP32 serial logs
esphome logs esphome/ir_capture_device_with_display.yaml
```

**Common Issues:**
- Loose wire connection → Re-seat all connections
- Wrong VCC voltage → Check module specs (3.3V vs 5V)
- Bad display module → Try different display

### Display Shows Random Pixels/Garbage

**I2C Address Wrong:**
```yaml
# Try changing address in YAML:
display:
  - platform: ssd1306_i2c
    address: 0x3D  # Change from 0x3C to 0x3D
```

**Check I2C Scan Results:**
```bash
# Look in logs for:
# [I][i2c:068]: Scan Results:
# [I][i2c:074]: 0x3C

# Update YAML with detected address
```

**Some displays have address jumper:**
- Small solder pads on back
- Bridge to change 0x3C ↔ 0x3D

### Display Works But Shows Wrong Content

**Check Lambda Code:**
- Verify font IDs match
- Check sensor IDs are correct
- Ensure WiFi component ID is set

**Font Download Failed:**
```bash
# Check internet connection during compile
# Fonts downloaded from Google Fonts

# Manual font file alternative:
font:
  - file: "/path/to/font.ttf"
    id: font_small
    size: 10
```

### Display Flickers or Updates Slowly

**Adjust Update Interval:**
```yaml
display:
  update_interval: 500ms  # Slower = less flicker (was 200ms)
```

**I2C Speed Issues:**
```yaml
i2c:
  sda: GPIO21
  scl: GPIO22
  frequency: 100kHz  # Slower, more reliable (default 400kHz)
```

### Wrong Display Size

**128x32 Instead of 128x64:**
```yaml
display:
  - platform: ssd1306_i2c
    model: "SSD1306 128x32"  # Change this
```

**Adjust Lambda for 128x32:**
```yaml
lambda: |-
  // Simplified layout for smaller display
  it.print(64, 0, id(font_medium), TextAlign::TOP_CENTER, "IR CAPTURE");

  if (id(wifi_component).is_connected()) {
    it.printf(0, 12, id(font_small), "%s", id(wifi_ip).state.c_str());
  }

  if (id(last_ir_code).state.length() > 10) {
    it.print(0, 22, id(font_small), "Code captured!");
  } else {
    it.print(0, 22, id(font_small), "Ready...");
  }
```

## Display Customization

### Change Text/Layout

Edit the `lambda:` section in the YAML:

```yaml
lambda: |-
  // Your custom layout here
  it.print(0, 0, id(font_large), "My Custom Text");
  it.printf(0, 25, id(font_small), "IP: %s", id(wifi_ip).state.c_str());
```

### Add Graphics

```yaml
lambda: |-
  // Draw shapes
  it.rectangle(0, 0, 128, 64);  // Border
  it.line(0, 16, 128, 16);      // Horizontal line
  it.circle(100, 50, 10);        // Circle at x=100, y=50, r=10
  it.filled_rectangle(10, 10, 20, 20);  // Filled square
```

### Show Code Count

```yaml
lambda: |-
  // Add counter
  int code_count = /* your logic to count codes */;
  it.printf(0, 54, id(font_small), "Codes: %d", code_count);
```

### Add Icons

Use pre-made fonts with icons:

```yaml
font:
  - file: "gfonts://Material+Symbols+Outlined"
    id: icon_font
    size: 20
    glyphs: ["\U0000e1b6", "\U0000f09c"]  # WiFi, Remote icons

lambda: |-
  it.print(0, 0, id(icon_font), "\U0000e1b6");  # WiFi icon
```

## Benefits of Adding Display

### User Experience Improvements

✅ **Instant Feedback**
- See IP address without computer
- Know when code captured (visual + LED)
- Check WiFi status at a glance

✅ **Standalone Operation**
- No need to open web interface
- No computer required to verify
- Perfect for field/production use

✅ **Debugging Made Easy**
- See exact IP for browser access
- WiFi signal strength visible
- Connection status clear

✅ **Professional Look**
- Clean, finished appearance
- Looks like commercial product
- Great for demos/presentations

### Development Benefits

✅ **Faster Testing**
- Immediate visual confirmation
- No need to check serial logs
- See codes being captured live

✅ **Remote Deployment**
- Install in other rooms
- No serial connection needed
- Just glance at display

✅ **Error Detection**
- WiFi disconnection obvious
- Can see when codes captured
- Status always visible

## Cost Analysis

### Price Breakdown

| Component | Cost (USD) |
|-----------|-----------|
| SSD1306 128x64 OLED | $3-8 |
| 4x Jumper Wires | $0.50 |
| **Total Add-on Cost** | **~$4-9** |

### Value Proposition

For ~$4-9 USD, you get:
- Real-time status display
- No need for computer/phone to check status
- Professional appearance
- Easier debugging
- Better user experience

**ROI:** Worth it if you value standalone operation or professional appearance.

## Alternative Display Options

### Other Compatible Displays

| Display | Resolution | Interface | Notes |
|---------|-----------|-----------|-------|
| SSD1306 | 128x64 | I2C | **Recommended** - Best value |
| SSD1306 | 128x32 | I2C | Cheaper, less space |
| SH1106 | 128x64 | I2C | Similar to SSD1306 |
| ST7735 | 128x160 | SPI | Color TFT, more complex |
| ILI9341 | 240x320 | SPI | Large color display |

### Why SSD1306 is Recommended

✅ Cheap (~$3-5 USD)
✅ Easy to wire (only 4 wires)
✅ Low power consumption
✅ Good library support in ESPHome
✅ Perfect size for status info
✅ Works with 3.3V or 5V

## Advanced Features

### Add Button Input

```yaml
# Add a button to cycle display modes
binary_sensor:
  - platform: gpio
    pin:
      number: GPIO13
      mode: INPUT_PULLUP
    name: "Display Mode Button"
    on_press:
      - lambda: |-
          // Cycle display mode
          static int mode = 0;
          mode = (mode + 1) % 3;
          // Update display based on mode
```

### Show More Info

```yaml
lambda: |-
  // Multi-page display
  static unsigned long last_change = 0;
  static int page = 0;

  if (millis() - last_change > 3000) {
    page = (page + 1) % 3;
    last_change = millis();
  }

  switch(page) {
    case 0: // WiFi Info
      it.print(0, 0, id(font_medium), "WiFi Status");
      // ...
      break;
    case 1: // IR Status
      it.print(0, 0, id(font_medium), "IR Capture");
      // ...
      break;
    case 2: // System Info
      it.print(0, 0, id(font_medium), "System");
      // ...
      break;
  }
```

### Add Animations

```yaml
lambda: |-
  // Scrolling text
  static int scroll_pos = 0;
  scroll_pos = (scroll_pos + 1) % 200;

  it.printf(scroll_pos - 100, 30, id(font_small), "Scrolling text...");
```

## Conclusion

Adding an SSD1306 OLED display to your IR capture device is:

- ✅ **Easy** - Just 4 wires
- ✅ **Cheap** - ~$4-9 USD
- ✅ **Useful** - Instant visual feedback
- ✅ **Professional** - Looks complete
- ✅ **Fun** - Customize however you want!

**Recommendation:** Definitely worth adding for production use or if deploying remotely!

---

## Quick Reference

```
┌─────────────────────────────────────────────┐
│      SSD1306 DISPLAY QUICK REFERENCE       │
├─────────────────────────────────────────────┤
│ Wiring:                                     │
│   VCC → 3.3V or 5V                         │
│   GND → GND                                 │
│   SCL → GPIO22                              │
│   SDA → GPIO21                              │
├─────────────────────────────────────────────┤
│ I2C Address: 0x3C (or 0x3D)                │
│ Update Rate: 200ms (adjustable)            │
│ Resolution:  128x64 (or 128x32)            │
├─────────────────────────────────────────────┤
│ YAML File:                                  │
│   esphome/ir_capture_device_with_display.yaml│
├─────────────────────────────────────────────┤
│ Flash Command:                              │
│   esphome run ir_capture_device_with_display.yaml│
└─────────────────────────────────────────────┘
```

---

**Document Version:** 1.0
**Last Updated:** 2025-10-03
**Compatible With:** ESPHome 2025.9.0+
