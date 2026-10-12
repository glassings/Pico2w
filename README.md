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
| 3 | timer, stopwatch, dice, notes, status, buzzer | not yet |
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
/main.py  config.py  hw.py  ghost.py  memory.py  render.py
/sprites.py  phrases.py  menu.py
/apps/__init__.py  home.py  wake.py  sleep.py  stub.py  listen.py  familiars.py
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
| Buzzer *(phase 3)* | signal (+) | GP15 (pin 20) |
| | GND (-) | GND |
| NeoPixel *(phase 4)* | DIN | GP22 (pin 29) |

The joystick has to run from 3.3V. At 5V its outputs swing past 3.3V, which
the ADC pins can't take. Keep your hands off the stick while the Pico boots:
the centre position is calibrated at power-up.

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
