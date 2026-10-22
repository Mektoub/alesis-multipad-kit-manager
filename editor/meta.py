"""Description des paramètres pour l'interface : noms, plages, libellés."""

import strike_kits as sk

COLORS = [
    ("Red", "#ff2020"),
    ("Coral", "#ff7f50"),
    ("Deep Pink", "#ff1493"),
    ("Light Pink", "#ffb6c1"),
    ("Magenta", "#ff00ff"),
    ("Purple", "#8a2be2"),
    ("Plum", "#dda0dd"),
    ("Blue", "#1e50ff"),
    ("Sky Blue", "#87ceeb"),
    ("Cyan", "#00e5ff"),
    ("Aquamarine", "#7fffd4"),
    ("Lime", "#a0ff20"),
    ("Green", "#20c040"),
    ("Yellow", "#ffe020"),
    ("Orange", "#ff9900"),
    ("Orange Red", "#ff4500"),
    ("White", "#ffffff"),
]
PLAY_MODES = ["Off", "Trigger", "Audio Meter", "Audio Breath", "Fill", "BPM Pulse", "BPM Pong"]
STOP_MODES = ["Off", "Solid Dim", "Solid Medium", "Solid Bright", "BPM Pulse", "BPM Pong"]
BEATS = ["1/2", "1/4", "1/8", "1/16"]

# Libellés des valeurs, dans l'ordre du manuel. `verified` : confirmé sur l'appareil.
LABELS = {
    "control": (
        [
            "Off",
            "Next Kit",
            "Previous Kit",
            "Click On/Off",
            "Tap Tempo",
            "Panic",
            "Looper Rec",
            "Looper Play/Stop",
            "Kit FX1 On/Off",
            "Kit FX2 On/Off",
            "Kit FX3 On/Off",
            "MST FX On/Off",
        ],
        True,
    ),
    "audio_output": (["Main+Phone", "FX1", "FX2", "FX3", "Aux+Phone", "Phone Only"], True),
    "curve": (["Normal", "Exp1", "Exp2", "Log1", "Log2", "Loud"], True),
    "sync_mode": (["Mute", "Cycle", "Random", "Together", "HiHat"], False),
    "priority": (["Low", "Medium", "High"], False),
    # FS4 = 9 vérifié ; FS1–FS3 supposés juste avant, la valeur 5 reste inconnue
    "playback_mode": (["Oneshot", "Alter", "Loop", "RoundRobin", "Hi-hat", None, "FS1", "FS2", "FS3", "FS4"], False),
    "poly_mono": (["Mono", "Poly"], True),
}
LIGHT_LABELS = {
    "play_color": [n for n, _ in COLORS],
    "play_mode": PLAY_MODES,
    "play_beat": BEATS,
    "stop_color": [n for n, _ in COLORS],
    "stop_mode": STOP_MODES,
    "stop_beat": BEATS,
}
TITLES = {
    "volume": "Volume",
    "pan": "Pan",
    "midi_note": "MIDI Note Output",
    "sync_group": "Sync Group",
    "sync_mode": "Sync Mode",
    "audio_output": "Audio Output",
    "kit_fx_level": "Kit FX Level",
    "fixed_level": "Fixed Level",
    "sensitivity": "Sensitivity",
    "curve": "Curve",
    "threshold": "Threshold",
    "control": "Mode",
    "sound": "Sound",
    "playback_mode": "Playback Mode",
    "poly_mono": "Poly/Mono",
    "play_color": "Play Color",
    "play_mode": "Play Mode",
    "play_beat": "Play Beat",
    "stop_color": "Stop Color",
    "stop_mode": "Stop Mode",
    "stop_beat": "Stop Beat",
    "velocity_low": "Velocity Low",
    "velocity_high": "Velocity High",
    "fade_in": "Fade In",
    "fade_out": "Fade Out",
    "priority": "Priority",
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
    "threshold": "Seuil de déclenchement (0 à 32) : force minimale en dessous de laquelle "
    "la frappe est ignorée. Monter pour éviter les déclenchements parasites "
    "(vibrations, basses d'une enceinte proche).",
    "control": "Fonction de commande déclenchée par la frappe : kit suivant ou précédent, "
    "Click On/Off, Tap Tempo, Panic, Looper, activation des effets… Off : aucune.",
    "sound": "Indique si la frappe joue le son du pad (On/Off ; correspondance des valeurs non vérifiée).",
    "curve": "Courbe de réponse à la force de frappe : Normal, Exp1, Exp2, Log1, Log2, Loud.",
    "kit_fx_level": "Niveau envoyé aux effets du kit (0 à 127).",
    "sync_mode": "Comportement des pads du même Sync Group : Mute (le dernier frappé coupe les autres), "
    "Cycle, Random, Together (jouent ensemble) ou HiHat.",
}
WAVE_DESCRIPTIONS = {
    "volume": "Volume de la couche (0 à 100).",
    "pan": "Position de la couche dans le champ stéréo.",
    "fade_in": "Fondu d'entrée appliqué au son (Off, 1 à 100 %).",
    "fade_out": "Fondu de sortie appliqué au son (Off, 1 à 100 %).",
    "priority": "Priorité dans la polyphonie (32 voix mono / 16 stéréo) : une voix Low est coupée en "
    "premier quand la limite est atteinte, une voix High en dernier.",
    "playback_mode": "Mode de lecture : Oneshot, Alter, Loop, RoundRobin, Hi-hat, ou pilotage par "
    "une pédale FS1 à FS4 (valeurs de FS1 à FS3 supposées).",
    "poly_mono": "Poly : une nouvelle frappe laisse sonner la précédente ; Mono : elle la coupe.",
}
HELP = {
    "name": "Nom du kit (16 caractères au plus).",
    "level": "Volume global du kit (0 à 100).",
    "tempo": "Tempo du kit en BPM (30 à 280) ; remplace le tempo global quand le kit est chargé.",
    "play_color": "Couleur des LED du pad quand un son est joué.",
    "play_mode": "Comportement des LED quand un son est joué : Off, Trigger (faible à fort), "
    "Audio Meter, Audio Breath, Fill, BPM Pulse, BPM Pong.",
    "stop_color": "Couleur des LED du pad au repos.",
    "stop_mode": "Comportement des LED au repos : éteintes, couleur fixe (pâle, moyenne, vive), BPM Pulse ou BPM Pong.",
    "play_beat": "Rythme des LED quand un son est joué, en modes BPM : 1/2 à 1/16 de temps.",
    "stop_beat": "Rythme des LED au repos, en modes BPM : 1/2 à 1/16 de temps.",
    "sample": "Sample joué par cette couche (Wave A ou Wave B).",
    "velocity_low": "Velocity Low (0 à 126) : une frappe plus faible ne déclenche pas cette couche.",
    "velocity_high": "Velocity High (1 à 127) : une frappe plus forte ne déclenche pas cette couche. "
    "En répartissant les plages entre Wave A et Wave B, on superpose deux sons selon la force.",
}


# Valeurs par défaut : celles d'un kit vide écrit par l'appareil (le manuel
# annonce 90 pour le volume du kit, l'appareil écrit 100). Elles varient d'un
# emplacement à l'autre pour la note MIDI, la sensibilité et l'éclairage Play.
DEFAULT_KIT = {"level": 100, "tempo": 120.0}
DEFAULT_MIDI_NOTES = [
    36,
    37,
    38,
    40,
    41,
    42,
    44,
    45,
    46,
    43,
    42,
    39,
    48,
    49,
    50,
    51,
    43,
    124,
    125,
    126,
    127,
    53,
    57,
    53,
]
DEFAULT_SENSITIVITY = [16] * 6 + [24] * 3 + [16] * 8 + [8] * 7  # P7–P9, petits pads : 24
DEFAULT_PAD = {
    "volume": 90,
    "pan": 15,
    "p09": 0,
    "sync_group": 0,
    "sync_mode": 0,
    "p0e": 40,
    "audio_output": 0,
    "fixed_level": 0,
    "threshold": 4,
    "curve": 0,
    "control": 0,
    "sound": 0,
    "kit_fx_level": 40,
    "p17": 40,
}
DEFAULT_WAVE = {
    "velocity_low": 0,
    "velocity_high": 127,
    "params": {
        "volume": 90,
        "pan": 15,
        "playback_mode": 0,
        "p10": 0,
        "p18": 0,
        "poly_mono": 1,
        "fade_in": 0,
        "fade_out": 0,
        "priority": 0,
    },
}


def default_slot(index):
    pad = dict(DEFAULT_PAD, midi_note=DEFAULT_MIDI_NOTES[index], sensitivity=DEFAULT_SENSITIVITY[index])
    names = [sk.param_name(sk.PAD_PARAMS, rid) for rid, _, _ in sk.PAD_LAYOUT] + list(sk.PAD_FIELDS)
    params = {name: pad[name] for name in names}
    # White / Audio Breath au 1/4, sinon Sky Blue / Trigger au 1/2
    play, beat = ((16, 3), 1) if index < 11 else ((8, 1), 0)
    wave = {
        "velocity_low": DEFAULT_WAVE["velocity_low"],
        "velocity_high": DEFAULT_WAVE["velocity_high"],
        "params": dict(DEFAULT_WAVE["params"]),
    }
    return {
        "params": params,
        "light": {
            "play_color": play[0],
            "play_mode": play[1],
            "play_beat": beat,
            "stop_color": 8,
            "stop_mode": 1,
            "stop_beat": beat,
        },
        "wave_a": wave,
        "wave_b": {**wave, "params": dict(wave["params"])},
    }


def defaults():
    return {"kit": DEFAULT_KIT, "slots": [default_slot(i) for i in range(sk.SLOT_COUNT)]}


def describe(name, lo, hi, descriptions):
    if name in descriptions:
        return descriptions[name]
    return "Paramètre non identifié (plage %d à %d)." % (lo, hi)


def param(name, lo, hi, known, descriptions, labels=None, verified=False):
    if labels is None:
        labels, verified = LABELS.get(name, (None, False))
    return {
        "name": name,
        "title": TITLES.get(name, name),
        "min": lo,
        "max": sk.VALUE_MAX.get(name, hi),
        "known": known,
        "labels": labels,
        "verified": verified,
        "description": describe(name, lo, hi, descriptions),
    }


def params(layout, table, descriptions, fixed=None):
    out = [param(sk.param_name(table, rid), lo, hi, rid in table, descriptions) for rid, lo, hi in layout]
    return out + [param(name, 0, hi, True, descriptions) for name, (_, hi) in (fixed or {}).items()]


# Sections de l'éditeur, comme dans les menus de l'appareil : champs au format
# « section.clé » du JSON d'un emplacement (pad) ou d'une wave. Les paramètres non
# identifiés n'y figurent pas.
PAD_SECTIONS = [
    ("Feel", ["params.sensitivity", "params.curve", "params.threshold", "params.fixed_level"]),
    ("Control", ["params.control", "params.sound"]),
    ("Output", ["params.audio_output", "params.kit_fx_level", "params.midi_note", "params.volume", "params.pan"]),
    ("Light", ["light." + k for k in ("play_color", "play_mode", "play_beat", "stop_color", "stop_mode", "stop_beat")]),
    ("Group", ["params.sync_group", "params.sync_mode"]),
]
WAVE_SECTIONS = [
    ("Mode", ["params.playback_mode", "params.poly_mono"]),
    (
        "Mix",
        [
            "params.volume",
            "params.pan",
            "params.fade_in",
            "params.fade_out",
            "velocity_high",
            "velocity_low",
            "params.priority",
        ],
    ),
]


def sections(table):
    return [{"title": title, "fields": fields} for title, fields in table]


def meta():
    return {
        "pad_params": params(sk.PAD_LAYOUT, sk.PAD_PARAMS, PAD_DESCRIPTIONS, sk.PAD_FIELDS),
        "wave_params": params(sk.WAVE_LAYOUT, sk.WAVE_PARAMS, WAVE_DESCRIPTIONS),
        "light_params": [param(k, 0, hi, True, HELP, LIGHT_LABELS[k], True) for k, (_, hi) in sk.LIGHT_FIELDS.items()],
        "velocity_params": [
            param("velocity_low", 0, 126, True, HELP),
            param("velocity_high", 1, 127, True, HELP),
        ],
        "pad_sections": sections(PAD_SECTIONS),
        "wave_sections": sections(WAVE_SECTIONS),
        "help": HELP,
        "defaults": defaults(),
        "colors": [{"name": n, "css": c} for n, c in COLORS],
        "slots": [{"slot": i + 1, "label": sk.slot_label(i)} for i in range(sk.SLOT_COUNT)],
        "kit_name_max": sk.NAME_LEN,
    }
