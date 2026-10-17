# Pocket Ghost

A small, glitchy, slightly eerie ghost living in a Raspberry Pi Pico 2 W.
The OLED is its room. It drifts, blinks, mutters, naps when ignored, and sometimes
isn't there. Later it feeds on the radio signals around it.

MicroPython, single cooperative loop, no dependencies beyond `ssd1306.py`.

## Status

| Phase | What | State |
|---|---|---|
| 1 | display, joystick, menu shell, idle ghost, persistence | **built** |
| 2 | listen (WiFi + BLE), familiars, hunger/mood reactions | **built** |
| 3 | timer, stopwatch, dice, notes, status, buzzer | **built** |
| 4 | NeoPixel glow, battery-friendly sleep | not yet |

Menu items that aren't built yet open a placeholder where the ghost says it's
"still forming".

## Firmware

Use the official **Raspberry Pi Pico 2 W** build (`RPI_PICO2_W`) from
<https://micropython.org/download/RPI_PICO2_W/>, v1.24 or newer, the ARM `.uf2`.
It includes `network` (WiFi) and `bluetooth` (BLE), which phase 2 needs.
Do **not** use the plain Pico 2 (`RPI_PICO2`) build, which has no radio.

To check, run this in the REPL:

```python
>>> import network, bluetooth, sys
>>> sys.implementation._machine
'Raspberry Pi Pico 2 W with RP2350'
```

## Files on the Pico

```
/main.py  config.py  hw.py  ghost.py  memory.py  render.py  chrono.py  trackers.py
/sprites.py  phrases.py  menu.py  notes.txt
/apps/__init__.py  home.py  wake.py  sleep.py  stub.py  listen.py  familiars.py  followers.py
      timer.py  alarm.py  stopwatch.py  dice.py  notes.py  status.py
/lib/ssd1306.py          <- already there
/ghost_state.json        <- created by the ghost; delete it to "reset" the ghost
```

With `mpremote`, from this folder:

```sh
mpremote mkdir :apps
mpremote cp *.py :
mpremote cp apps/*.py :apps/
mpremote reset
```

In Thonny, select all the `.py` files and the `apps` folder in the Files pane,
then right-click and choose **Upload to /**.

`main.py` runs on power-up. To stop it, press **Stop** in Thonny or Ctrl-C in the
REPL. The ghost saves before it stops.

## Wiring

All pins are in `config.py`.

| Part | Pin | Pico 2 W |
|---|---|---|
| OLED | VCC | 3V3 (pin 36) |
| | GND | GND |
| | SDA | GP4 (pin 6) |
| | SCL | GP5 (pin 7) |
| Joystick | +5V / VCC | **3V3 (pin 36)**, not VBUS/5V |
| | GND | GND |
| | VRx | GP26 / ADC0 (pin 31) |
| | VRy | GP27 / ADC1 (pin 32) |
| | SW | GP16 (pin 21) |
| Buzzer | signal (+) | GP15 (pin 20) |
| | GND (-) | GND |
| NeoPixel *(phase 4)* | DIN | GP22 (pin 29) |

The joystick has to run from 3.3V. At 5V its outputs swing past 3.3V, which
the ADC pins can't take. Keep your hands off the stick while the Pico boots:
the centre position is calibrated at power-up.

## Controls hardware

Pick any mix in `config.py` (`INPUT_JOYSTICK`, `INPUT_BUTTONS`, `INPUT_ONE_BUTTON`, `INPUT_ENCODER`).
They all send the same events. The default is **one button**.

**One button** (`INPUT_ONE_BUTTON`, the default): GP20 (pin 26) to GND.

| Do this | Means |
|---|---|
| 1 click | down / next |
| 2 clicks | confirm (click) |
| 3 clicks | back |
| 4+ clicks | up |
| long press | left: switch timer field, change die, flip note, reset |

Clicks are counted after a short pause (`MULTI_CLICK_MS`, 400 ms), so every
action lands a moment after you stop clicking. Any press wakes the screen.

**Push buttons.** Each one goes between its GPIO and GND, with no resistors
(the Pico's internal pull-ups are used). Only the first three are required:

| Button | Pico 2 W | Does |
|---|---|---|
| up | GP18 (pin 24) | up / previous |
| down | GP19 (pin 25) | down / next |
| ok | GP20 (pin 26) | click; hold = back |
| left *(optional)* | e.g. GP17 (pin 22) | left |
| right *(optional)* | e.g. GP21 (pin 27) | right |
| back *(optional)* | e.g. GP14 (pin 19) | back |

GND is right there at pin 23 or 28. Without left/right buttons, **hold ok and press
up/down** for left/right.

**Rotary encoder** (KY-040 / EC11): CLK → GP2 (pin 4), DT → GP3 (pin 5),
SW → GP6 (pin 9), + → 3V3, GND → GND. Turn = up/down, press = click, long press =
back, press and turn = left/right. If one click of the knob moves two items, set
`ENC_STEPS_PER_DETENT = 2`. If it scrolls the wrong way, flip `ENC_INVERT`.

## Controls

* **Home (the ghost's room):** click opens the menu. Nudging the stick pushes
  the ghost around, and it sometimes reacts. Holding the button gets an
  unhappy remark.
* **Menu:** up and down move, click chooses, and holding the button goes back.
* **Sleep / screen off:** click to wake.

If the directions are wrong, change `JOY_SWAP_XY`, `JOY_INVERT_X` or
`JOY_INVERT_Y` in `config.py`. Set `JOY_DEBUG = True` to print live
readings (`x=+0.98 y=-0.02 sw=1`) to the REPL. Pushing the stick up should
give a negative `y`.

## How it behaves

* **Needs:** `hunger` rises slowly while it's on. `restless` rises when it's
  ignored and drops when you touch the stick. `content` slowly follows the other
  two. These set how much it glitches and what it says.
* **Ignored:** after 45 s it gets restless. After 2.5 min it naps (eyes closed,
  floating z's), and the first touch only wakes it up. After 5 min the screen
  turns off.
* **Glitches:** tearing, scanline flicker, snow, inverted flashes, letters
  turning into blocks, words that come out wrong and then correct themselves,
  and the sprite stuttering or doubling. All of it is applied in one pass
  after the screen is drawn. Each screen marks a band of rows as protected, and
  tearing and noise never touch it. That's how the timer, dice and notes stay
  correct later on.
* **Waking up:** static, a shape forming, then a remark. The Pico has no
  battery-backed clock, so it usually can't know how long it was off, and it
  says so. When Thonny or `mpremote` has set the clock (they do this when
  connected to a PC), it knows and comments on it.

## Listening and familiars

**listen** scans WiFi first (about 2 s, during which the screen holds still, because
the Pico's WiFi scan blocks), then Bluetooth for 4 s while rings pulse out from
the ghost. Then it reports what it heard:

* `wifi 12 +3`: 12 access points, 3 never heard before
* `near 8 +5`: 8 Bluetooth presences, 5 new this power-on
* `ate 8`: new signals eaten this time

Push down to see the loudest networks with their live name, signal strength in
dBm, and the nickname the ghost gave them (`*` = new, `~` = a familiar). Click to
listen again, hold to go back.

* **WiFi access points become familiars.** Each gets a permanent nickname
  ("pale hum", "sunken whisper") and a count of how often it was heard. The
  **familiars** menu lists them, most-met first. Click one and the ghost tells you
  what it thinks of it.
* **Bluetooth devices are passing presences.** Phones change their addresses
  constantly, so these are only remembered (hashed, in RAM) until the power goes
  off, and are never treated as individuals.
* **Feeding:** a new access point eats 6 hunger, a new presence 1.5, and a
  familiar heard again 0.5. One scan can eat at most 45. Feeding also raises
  contentment.
* **Crowds:** 15 or more strangers at once makes it nervous: restlessness
  goes up even though it ate.

All of this is tunable in the "listening" block of `config.py`. `WIFI_ENABLED`
and `BLE_ENABLED` turn either radio off.

## Trackers (in progress)

Bluetooth item trackers are recognised from their advertisements (receive-only,
nothing is ever connected to). The signatures come from AirGuard's detection code
and the Find Hub (FMDN) spec, and are in `trackers.py`:

| Family | How it's recognised | Separated from owner? |
|---|---|---|
| Apple Find My (AirTag, Find My accessories, AirPods, offline Apple devices) | manufacturer data `4C 00`, type `12`; status byte bits 4-5 give the device kind | yes: payload length `0x19` = away, short = near owner |
| Tile | service UUID `FEED` / `FEEC` | not exposed |
| Samsung SmartTag | service UUID `FD5A` | not decoded yet |
| Google Find Hub tags | service data `FEAA`, frame `40` / `41` (other Eddystone frames ignored) | `41` = unwanted-tracking mode = away |

**followers** (menu) is currently a raw live view: it scans continuously and lists
every tracker it hears with its family, state, signal strength, a few payload bytes
and seconds since last heard. **listen** also lists trackers on its last result
pages. With `TRACKER_DEBUG = True` each detection's full advertisement is printed
to the REPL.

## Useful things

| Menu item | Controls | Notes |
|---|---|---|
| timer | setting: left/right picks minutes or seconds, up/down changes (seconds in 5s steps), click starts. Running: click pauses, hold leaves it running. Paused: click resumes, left resets | Runs in the background. The time left shows in the room's top-right corner and next to "timer" in the menu. When it ends, the alarm takes over the screen (waking it if it's off) and loops for up to 60 s. Any input dismisses it. |
| stopwatch | click start/stop, up = lap (keeps the last 3), left = reset while stopped | Also keeps running if you leave the screen. |
| dice | left/right picks d4, d6, d8, d10, d12 or d20, click rolls | The result is picked the moment you click; the tumbling numbers are just for show. The last 3 results are shown underneath. |
| notes | up/down scrolls, left/right flips between notes | Reads `notes.txt` from the Pico. A line containing only `---` separates notes. Read-only. |
| status | up/down flips the 2 pages | Page 1: time alive, boots, signals eaten, familiars named, presences felt, mood. Page 2: hunger, restlessness, contentment and glitch level as bars with exact numbers. |

Glitches never touch the timer digits, stopwatch time, dice result, notes text or
status values. A one-frame inverted flash is the most they get.

### Buzzer: active or passive?

Touch the buzzer's + leg to 3V3 and - to GND for a second. A continuous beep means
**active**: set `BUZZER_ACTIVE = True`, and you'll get beeps on and off. Just a
click means **passive** (the default): it plays real tones and pitch glides. If
a passive buzzer is too loud, lower `BUZZER_DUTY`. `BUZZER_CLICKS = False`
silences the UI sounds but keeps the alarm, and `BUZZER_ENABLED = False`
silences everything.

## Memory and flash

`ghost_state.json` stores time alive, boot count, totals fed, familiars (from
phase 2) and mood. It's written:

* at most every 5 minutes as a checkpoint,
* after significant events, but never less than 20 s since the last write,
* when the screen goes to sleep, and when the program is stopped.

Each save writes a temporary file and then renames it over the old one, so a
power cut mid-save loses at most a few minutes. Radio identifiers are only
stored as salted SHA-256 hashes, and SSIDs are never written to flash.

## Layout

```
main.py      boot, Ctx (shared state + screen stack), the main loop
config.py    pins, timings, tuning
hw.py        display setup, joystick (deadzone, hysteresis, repeat, click/hold)
ghost.py     needs, mood drift, boot accounting
memory.py    JSON load/save with wear limiting, hash_id()
render.py    Renderer (drawing + glitch pass), Speech (typed, corrupted,
             self-correcting dialogue), Puppet (the ghost's body and moves)
sprites.py   1-bit art drawn as text, packed at import
phrases.py   dialogue pools; "[wrong>right]" says it wrong, then corrects it
menu.py      the menu
apps/        one screen per file
```
