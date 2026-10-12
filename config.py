# config.py -- every pin, timing and feature switch lives here.
# Rewire the breadboard? Change it here and nowhere else.

# ---------------------------------------------------------------- display
# SSD1306 0.96" 128x64 on I2C0.  GP4/GP5 are an I2C0 pin pair.
I2C_ID = 0
PIN_SDA = 4
PIN_SCL = 5
I2C_FREQ = 400_000      # most SSD1306 boards also tolerate 1_000_000
OLED_ADDR = 0x3C        # 0x3D is tried automatically if 0x3C isn't found
OLED_W = 128
OLED_H = 64
OLED_CONTRAST = 180     # 0..255; lower = dimmer = less power

# --------------------------------------------------------------- joystick
# Power the module from 3.3V, NOT 5V: the Pico ADC tops out at 3.3V.
PIN_JOY_X = 26          # ADC0
PIN_JOY_Y = 27          # ADC1
PIN_JOY_SW = 16         # internal pull-up, pressed = low

# Joystick modules get mounted every which way on a breadboard.  If "up"
# moves the cursor down (etc), flip these until it feels right.
JOY_SWAP_XY = False
JOY_INVERT_X = False
JOY_INVERT_Y = False

JOY_DEADZONE = 0.45         # fraction of full travel before a push counts
JOY_REPEAT_DELAY_MS = 450   # hold a direction this long to auto-repeat...
JOY_REPEAT_MS = 140         # ...then repeat this often
BTN_DEBOUNCE_MS = 25
BTN_HOLD_MS = 650           # press longer than this = "hold" (go back)
JOY_DEBUG = False           # True: print raw joystick readings to the REPL

# ----------------------------------------------------------------- buzzer
# (phase 3) signal -> GP15.  ACTIVE buzzers beep on their own when powered;
# PASSIVE buzzers need a tone (PWM).  Set BUZZER_ACTIVE to match yours.
PIN_BUZZER = 15
BUZZER_ENABLED = False
BUZZER_ACTIVE = False

# --------------------------------------------------------------- neopixel
# (phase 4) one WS2812 "glow" on GP22.
PIN_NEOPIXEL = 22
NEOPIXEL_ENABLED = False

# ------------------------------------------------------------------ timing
FRAME_MS = 50               # ~20 fps
SLEEP_POLL_MS = 60          # loop rate while the screen is off
NAP_AFTER_S = 150           # ignored this long -> the ghost naps
SCREEN_OFF_AFTER_S = 300    # ignored this long -> screen turns off

# --------------------------------------------------------------- the ghost
HUNGER_PER_HOUR = 4.0       # rises while powered on (0..100)
HUNGER_OFF_PER_HOUR = 1.0   # rises while off, only if the clock is known
RESTLESS_AFTER_S = 45       # ignored this long -> restlessness starts rising
RESTLESS_PER_MIN = 8.0
RESTLESS_NAP_DECAY_PER_MIN = 4.0
RESTLESS_PER_INPUT = 10.0   # each joystick event calms it this much
CONTENT_TAU_S = 600         # how slowly contentment follows the other needs

CHATTER_MIN_S = 14         # idle remarks happen between these gaps
CHATTER_MAX_S = 40

# ------------------------------------------------------------ listening
WIFI_ENABLED = True
BLE_ENABLED = True
BLE_SCAN_MS = 4000          # how long it listens for Bluetooth
BLE_MAX = 200               # ignore anything past this many presences per scan

FEED_NEW_WIFI = 6.0         # hunger eaten per never-seen access point
FEED_NEW_BLE = 1.5          # ...per new Bluetooth presence
FEED_FAMILIAR = 0.5         # ...per familiar heard again (counts up to 10)
FEED_MAX = 45.0             # most hunger one scan can satisfy
CROWD_SIZE = 15             # this many strangers at once makes it nervous
CROWD_RESTLESS = 15.0
MAX_FAMILIARS = 200         # least-seen ones are forgotten past this

# ---------------------------------------------------------------- storage
STATE_FILE = "ghost_state.json"
NOTES_FILE = "notes.txt"
SAVE_INTERVAL_S = 300       # routine save at most this often
SAVE_MIN_GAP_S = 20         # even "important" saves wait this long
