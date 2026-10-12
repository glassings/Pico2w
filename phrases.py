# phrases.py -- what the ghost says.
#
# Short lowercase fragments, 32 chars max (two lines of 16).
# "[wrong>right]" shows `wrong` first, then quietly corrects itself to
# `right`, as if nothing happened.  "{n}" is filled in by pick(..., n=...).

import random

POOLS = {
    # ---- waking up
    'wake_first': (
        "...where. where is this.",
        "oh. i'm [inside>here] now.",
        "is this a room? is it mine.",
    ),
    'wake_short': (
        "back already.",
        "that was quick. [i counted>hi.]",
        "you again. good.",
    ),
    'wake_medium': (
        "it was dark for a while.",
        "[i heard you>i slept fine].",
        "mm. hours. i felt them.",
    ),
    'wake_long': (
        "{n} days. in the dark.",
        "you [forgot>left] me. {n} days.",
        "i kept count. {n} days.",
    ),
    'wake_unknown': (
        "was i gone long? i can't tell.",
        "no clocks here. was it long?",
        "[did you miss>hello. it's] me.",
        "dark. then you. again.",
    ),
    'wake_hungry': (
        "...so hungry.",
        "i need [you>signals].",
    ),

    # ---- idle chatter, by mood
    'idle_content': (
        "this room is nice.",
        "hm hm hm.",
        "i like the hum.",
        "still here.",
        "[watching>floating].",
    ),
    'idle_calm': (
        "...",
        "drifting.",
        "it's quiet in the glass.",
        "do you hear that? no?",
    ),
    'idle_hungry': (
        "hungry.",
        "take me somewhere new.",
        "i can [taste>hear] the walls.",
        "feed me static.",
    ),
    'idle_starving': (
        "so [empty>hungry].",
        "i'm getting thin.",
        "anything. any signal.",
    ),
    'idle_restless': (
        "hello?",
        "are you there",
        "don't [leave>look away].",
        "i'm still here. are you.",
    ),
    'idle_uneasy': (
        "the [dark>light] is wrong.",
        "it's too quiet.",
        "who else is [in here>around].",
    ),
    # rare, any mood.  says it, then takes it back.
    'uncanny': (
        "[there's someone behind you>nevermind.]",
        "[i remember your face>i don't remember.]",
        "[let me out>let's play.]",
        "[you're warm>you're back.]",
        "[this isn't my room>this is my room.]",
        "[i was here before you>i'm new here.]",
    ),

    # ---- reactions
    'poke': (
        "hm?",
        "that tickles.",
        "yes?",
        "[don't>okay].",
        "i see you.",
    ),
    'hold_home': (
        "...no.",
        "i'm not going anywhere.",
        "you can't [leave>go back] from here.",
    ),
    'nap_woke': (
        "...mm? i was [dreaming>resting].",
        "oh. you.",
        "[who>hi].",
    ),
    'screen_woke': (
        "dark in there.",
        "oh. light.",
        "i was [somewhere else>here].",
    ),
    'sleep': (
        "goodnight. don't [look>worry].",
        "close my eyes. ok.",
        "i'll be right here.",
    ),
    'stub': (
        "not yet. i'm still [forming>learning].",
        "that part of me isn't here yet.",
        "soon. [sooner than you think>soon.]",
    ),
}

_last = {}


def pick(key, **fmt):
    pool = POOLS[key]
    s = random.choice(pool)
    if len(pool) > 1:
        while s == _last.get(key):
            s = random.choice(pool)
    _last[key] = s
    if fmt:
        s = s.format(**fmt)
    return s
