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


# Infobulles, d'après le manuel (menus Pad et Sound). Les paramètres non
# identifiés reçoivent une description générique, avec une piste quand leur
# plage concorde avec un réglage du manuel.
PAD_DESCRIPTIONS = {
    "volume": "Volume du pad (0 à 100).",
    "pan": "Position du son dans le champ stéréo : L15 (gauche) … C (centre) … R15 (droite).",
    "midi_note": "Note MIDI envoyée quand on frappe le pad (0 à 127).",
    "sync_group": "Groupe de jeu simultané (Off, 1 à 16) : les pads d'un même groupe réagissent "
                  "ensemble selon le Sync Mode (s'excluent, alternent, jouent ensemble…).",
    "audio_output": "Sortie audio du pad : Main+Phone, effets FX1 à FX3, Aux+Phone ou casque seul (Phone Only).",
    "fixed_level": "Dynamique fixe (1 à 127) appliquée quelle que soit la force de frappe. "
                   "Off : le pad suit la dynamique de jeu.",
    "sensitivity": "Gain du pad (1 à 32) : plus la valeur est élevée, plus un coup léger produit un son fort. "
                   "Baisser si le pad sonne trop fort au moindre effleurement.",
    "threshold": "Seuil de déclenchement (0 à 32, 4 par défaut) : force minimale en dessous de laquelle "
                 "la frappe est ignorée. Monter pour éviter les déclenchements parasites "
                 "(vibrations, basses d'une enceinte proche).",
    "control": "Fonction de commande déclenchée par la frappe : kit suivant ou précédent, "
               "Click On/Off, Tap Tempo, Panic, Looper, activation des effets… Off : aucune.",
    "sound": "Indique si la frappe joue le son du pad (On/Off ; correspondance des valeurs non vérifiée).",
    "p09": "Paramètre non identifié (plage 0 à 4). Piste : Sync Mode (Mute, Cycle, Random, Together, Hihat).",
    "p16": "Paramètre non identifié (plage 0 à 127). Piste : Kit FX Level.",
}
WAVE_DESCRIPTIONS = {
    "volume": "Volume de la couche (0 à 100).",
    "pan": "Position de la couche dans le champ stéréo.",
    "fade_in": "Fondu d'entrée appliqué au son (Off, 1 à 100 %).",
    "fade_out": "Fondu de sortie appliqué au son (Off, 1 à 100 %).",
    "priority": "Priorité dans la polyphonie (32 voix mono / 16 stéréo) : une voix Low est coupée en "
                "premier quand la limite est atteinte, une voix High en dernier.",
    "p09": "Paramètre non identifié (plage 0 à 5). Piste : Playback Mode (OneShot, Alter, Loop, RoundRobin…).",
    "p19": "Paramètre non identifié (plage 0 à 1). Piste : Poly/Mono.",
}
HELP = {
    "name": "Nom du kit (16 caractères au plus).",
    "level": "Volume global du kit (0 à 100, 90 par défaut).",
    "tempo": "Tempo du kit en BPM (30 à 280) ; remplace le tempo global quand le kit est chargé.",
    "play_color": "Couleur des LED du pad quand un son est joué.",
    "play_mode": "Comportement des LED quand un son est joué : Off, Trigger (faible à fort), "
                 "Audio Meter, Audio Breath, Fill, BPM Pulse, BPM Pong.",
    "stop_color": "Couleur des LED du pad au repos.",
    "stop_mode": "Comportement des LED au repos : éteintes, couleur fixe (pâle, moyenne, vive), "
                 "BPM Pulse ou BPM Pong.",
    "sample": "Sample joué par cette couche (Wave A ou Wave B).",
    "velocity_low": "Velocity Low (0 à 126) : une frappe plus faible ne déclenche pas cette couche.",
    "velocity_high": "Velocity High (1 à 127) : une frappe plus forte ne déclenche pas cette couche. "
                     "En répartissant les plages entre Wave A et Wave B, on superpose deux sons selon la force.",
}


def describe(name, lo, hi, descriptions):
    if name in descriptions:
        return descriptions[name]
    return "Paramètre non identifié (plage %d à %d)." % (lo, hi)


def params(layout, table, descriptions):
    out = []
    for rid, lo, hi in layout:
        name = sk.param_name(table, rid)
        labels, verified = LABELS.get(name, (None, False))
        out.append({"name": name, "title": TITLES.get(name, name), "min": lo, "max": hi,
                    "known": rid in table, "labels": labels, "verified": verified,
                    "description": describe(name, lo, hi, descriptions)})
    return out


def meta():
    return {
        "pad_params": params(sk.PAD_LAYOUT, sk.PAD_PARAMS, PAD_DESCRIPTIONS),
        "wave_params": params(sk.WAVE_LAYOUT, sk.WAVE_PARAMS, WAVE_DESCRIPTIONS),
        "help": HELP,
        "colors": [{"name": n, "css": c} for n, c in COLORS],
        "play_modes": PLAY_MODES,
        "stop_modes": STOP_MODES,
        "slots": [{"slot": i + 1, "label": sk.slot_label(i)} for i in range(sk.SLOT_COUNT)],
        "kit_name_max": sk.NAME_LEN,
    }
