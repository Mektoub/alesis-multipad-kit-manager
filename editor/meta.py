"""Description des paramètres pour l'interface : noms, plages, libellés."""
import strike_kits as sk

COLORS = [
    ("Red", "#ff2020"), ("Coral", "#ff7f50"), ("Deep Pink", "#ff1493"), ("Light Pink", "#ffb6c1"),
    ("Magenta", "#ff00ff"), ("Purple", "#8a2be2"), ("Plum", "#dda0dd"), ("Blue", "#1e50ff"),
    ("Sky Blue", "#87ceeb"), ("Cyan", "#00e5ff"), ("Aquamarine", "#7fffd4"), ("Lime", "#a0ff20"),
    ("Green", "#20c040"), ("Yellow", "#ffe020"), ("Orange", "#ff9900"), ("Orange Red", "#ff4500"),
    ("White", "#ffffff"),
]
PLAY_MODES = ["Off", "Trigger", "Audio Meter", "Audio Breath", "Fill", "BPM Pulse", "BPM Pong"]
STOP_MODES = ["Off", "Solid Dim", "Solid Medium", "Solid Bright", "BPM Pulse", "BPM Pong"]

# Libellés des valeurs, dans l'ordre du manuel. `verified` : confirmé sur l'appareil.
LABELS = {
    "control": (["Off", "Next Kit", "Previous Kit", "Click On/Off", "Tap Tempo", "Panic",
                 "Looper Rec", "Looper Play/Stop", "Kit FX1 On/Off", "Kit FX2 On/Off",
                 "Kit FX3 On/Off", "MST FX On/Off"], True),
    "audio_output": (["Main+Phone", "FX1", "FX2", "FX3", "Aux+Phone", "Phone Only"], True),
    "priority": (["Low", "Medium", "High"], False),
}
TITLES = {
    "volume": "Volume", "pan": "Pan", "midi_note": "Note MIDI", "sync_group": "Sync Group",
    "audio_output": "Audio Output", "fixed_level": "Fixed Level", "sensitivity": "Sensitivity",
    "threshold": "Threshold", "control": "Control", "sound": "Sound", "fade_in": "Fade In",
    "fade_out": "Fade Out", "priority": "Priority",
}


def params(layout, table):
    out = []
    for rid, lo, hi in layout:
        name = sk.param_name(table, rid)
        labels, verified = LABELS.get(name, (None, False))
        out.append({"name": name, "title": TITLES.get(name, name), "min": lo, "max": hi,
                    "known": rid in table, "labels": labels, "verified": verified})
    return out


def meta():
    return {
        "pad_params": params(sk.PAD_LAYOUT, sk.PAD_PARAMS),
        "wave_params": params(sk.WAVE_LAYOUT, sk.WAVE_PARAMS),
        "colors": [{"name": n, "css": c} for n, c in COLORS],
        "play_modes": PLAY_MODES,
        "stop_modes": STOP_MODES,
        "slots": [{"slot": i + 1, "label": sk.slot_label(i)} for i in range(sk.SLOT_COUNT)],
        "kit_name_max": sk.NAME_LEN,
    }
