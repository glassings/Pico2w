# trackers.py -- recognise Bluetooth item trackers from their advertisements.
#
# Receive-only: this only reads advertisements that are broadcast anyway.
# It never connects to, pings, or rings anything.
#
# Signatures, cross-checked against AirGuard (TU Darmstadt / SEEMOO,
# github.com/seemoo-lab/AirGuard) and the Find Hub (FMDN) spec:
#
#   Apple Find My   manufacturer data, company 0x004C, TLV type 0x12.
#                   TLV length 0x19 (25) = separated from its owner;
#                   short (usually 2) = near its owner.
#                   status byte bits 4-5: 0 Apple device, 1 AirTag,
#                   2 Find My accessory, 3 AirPods.
#   Tile            16-bit service UUID 0xFEED (or 0xFEEC, older units)
#   Samsung         16-bit service UUID 0xFD5A (SmartTag)
#   Google FMDN     service data, UUID 0xFEAA (shared with Eddystone),
#                   frame type 0x40 = normal, 0x41 = unwanted-tracking
#                   mode (separated from its owner for a while).
#                   Other Eddystone frames (0x00-0x30) are plain beacons.

_APPLE = ('apple', 'airtag', 'findmy', 'airpods')

# short labels for the 128px screen
LABEL = {
    'airtag': 'airtag', 'findmy': 'findmy', 'apple': 'apple?',
    'airpods': 'airpods', 'tile': 'tile', 'smarttag': 'smarttag',
    'google': 'google',
}


def _ads(adv):
    """Yield (ad_type, data) from raw advertising bytes."""
    i = 0
    n = len(adv)
    while i < n:
        ln = adv[i]
        if ln == 0 or i + 1 + ln > n:
            return
        yield adv[i + 1], adv[i + 2:i + 1 + ln]
        i += 1 + ln


def classify(adv):
    """-> (kind, state, stable_bytes) or None.

    state: 'away' (separated from its owner, the case that matters),
           'near' (owner close by), or '?' (format doesn't say).
    stable_bytes: payload that stays the same while the address does,
           used to sharpen fingerprints.  May be b''.
    """
    try:
        for t, d in _ads(adv):
            if t == 0xFF and len(d) >= 5 and d[0] == 0x4C and d[1] == 0x00:
                # Apple: a run of [type][len][payload...] after the company id
                k = 2
                while k + 2 < len(d):
                    typ = d[k]
                    ln = d[k + 1]
                    if typ == 0x12:
                        status = d[k + 2]
                        kind = _APPLE[(status >> 4) & 3]
                        state = 'away' if ln == 0x19 else 'near'
                        return kind, state, bytes(d[k + 3:k + 9])
                    k += 2 + ln
            elif t in (0x02, 0x03):
                # complete / incomplete list of 16-bit service UUIDs
                for j in range(0, len(d) - 1, 2):
                    u = d[j] | (d[j + 1] << 8)
                    if u in (0xFEED, 0xFEEC):
                        return 'tile', '?', b''
                    if u == 0xFD5A:
                        return 'smarttag', '?', b''
            elif t == 0x16 and len(d) >= 3:
                # service data: [uuid lo][uuid hi][data...]
                u = d[0] | (d[1] << 8)
                if u in (0xFEED, 0xFEEC):
                    return 'tile', '?', b''
                if u == 0xFD5A:
                    return 'smarttag', '?', bytes(d[3:9])
                if u == 0xFEAA and d[2] in (0x40, 0x41):
                    return 'google', 'away' if d[2] == 0x41 else 'near', bytes(d[3:9])
    except Exception:
        pass
    return None


def hexs(b, n=6):
    return ' '.join('%02x' % x for x in bytes(b)[:n])
