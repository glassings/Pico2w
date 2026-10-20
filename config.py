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

# --------------------------------------------------------------- controls
# Any mix can be on at once; they all send the same events.
INPUT_JOYSTICK = False      # True only if the joystick is plugged in
INPUT_BUTTONS = False       # 3-6 buttons (below)
INPUT_ONE_BUTTON = True     # everything on one button (below)
INPUT_ENCODER = False

# One button: between its GPIO and GND.
#   1 click = down   2 clicks = confirm   3 clicks = back   4+ clicks = up
#   long press = left (switch timer field, change die, flip note, reset)
PIN_ONE_BTN = 20            # physical pin 26
MULTI_CLICK_MS = 400        # pause this long and the clicks are counted

# Push buttons: each one between its GPIO and GND (no resistors needed).
# up, down and ok are required; set the others to None if not fitted.
#   no left/right buttons -> hold ok + press up/down = left/right
#   no back button        -> hold ok = back
PIN_BTN_UP = 18             # physical pin 24
PIN_BTN_DOWN = 19           # physical pin 25
PIN_BTN_OK = 20             # physical pin 26
PIN_BTN_LEFT = None         # e.g. 17 (pin 22)
PIN_BTN_RIGHT = None        # e.g. 21 (pin 27)
PIN_BTN_BACK = None         # e.g. 14 (pin 19)

# Rotary encoder (KY-040 / EC11): turn = up/down, press = click,
# long press = back, press + turn = left/right.
PIN_ENC_CLK = 2             # physical pin 4  (also called A)
PIN_ENC_DT = 3              # physical pin 5  (also called B)
PIN_ENC_SW = 6              # physical pin 9
ENC_STEPS_PER_DETENT = 4    # try 2 if one click of the knob moves two items
ENC_INVERT = False          # True if turning right moves up

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
# signal -> GP15, - -> GND.  ACTIVE buzzers beep on their own when powered;
# PASSIVE buzzers need a tone (PWM).  Set BUZZER_ACTIVE to match yours.
PIN_BUZZER = 15
BUZZER_ENABLED = True
BUZZER_ACTIVE = False       # False = passive (tones, glides); True = active (beeps)
BUZZER_DUTY = 0.5           # passive only: 0.5 = loudest, lower = thinner/quieter
BUZZER_BOOT_CHIME = True    # little sound while it wakes up
BUZZER_CLICKS = True        # dice rattle, start/stop blips, the odd whisper
ALARM_MAX_S = 60            # timer alarm gives up sounding after this

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

# ------------------------------------------------------------- trackers
TRACKER_DEBUG = True        # print every tracker detection to the REPL

# ---------------------------------------------------------------- clock
# Needs secrets.py (copy secrets.example.py) with your home WiFi.
CLOCK_ENABLED = True
TZ = "US_CENTRAL"           # US_EASTERN / US_CENTRAL / US_MOUNTAIN / US_PACIFIC / US_ARIZONA / UTC
CLOCK_24H = False
NTP_HOST = "pool.ntp.org"
CLOCK_SYNC_BUDGET_MS = 8000 # give up on one sync attempt after this
CLOCK_RESYNC_H = 6
CLOCK_RETRY_MIN = 30        # after a failed sync
QUIET_START = 23            # quiet hours (local): naps, dim screen
QUIET_END = 7
QUIET_NAP_S = 20            # in quiet hours it dozes off after this idle
QUIET_CONTRAST = 8          # screen brightness during quiet hours
WITCHING = (3, 7)           # its hour and minute

# ------------------------------------------------------------ halloween
# The auto/on/off switch lives in the device's settings menu.
HALLOWEEN_PRETEND_OCT31 = False # testing: act as if it's Oct 31, knocks soon
KNOCK_FROM = 17             # trick-or-treat hours on Oct 31 (local)
KNOCK_UNTIL = 23
KNOCK_GAP_MIN = (8, 20)     # minutes between knocks (random)
KNOCK_MAX = 6               # knocks per night
HALLOWEEN_SSIDS = ("trick or treat", "the veil is thin", "do not open the door")

# ------------------------------------------------------------ telegraph
TELEGRAPH_PIN = 20          # the key: the one button (GP20, physical pin 26)
TELEGRAPH_SIDETONE = True
TELEGRAPH_TONE_HZ = 600
TELEGRAPH_WPM = 8           # 5..20 (or 'auto' inside the app)
TELEGRAPH_EXIT_MS = 1500    # holding the key this long leaves the app
TELEGRAPH_DEBOUNCE_MS = 10
TELEGRAPH_DEBUG = False     # show raw press/gap timings instead of the ghost's lines

# ---------------------------------------------------------------- storage
STATE_FILE = "ghost_state.json"
NOTES_FILE = "notes.txt"
SAVE_INTERVAL_S = 300       # routine save at most this often
SAVE_MIN_GAP_S = 20         # even "important" saves wait this long
