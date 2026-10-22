"""90 s cut: hook (existing plates 0–11 s) → principle act (scene2.py, 58 s) → tunnel application + logo
(existing plates, shifted) → white end card.  All times in seconds; FPS = 30."""
from timeline import FPS, f
DURATION = 90.0

# --- segment A: existing plates, old 0–11 s
A_START, A_END = 0.0, 11.0
# --- segment P: principle act, local time 0–58 (scene2.py), placed at 11 s
P_START = 11.0
P_LEN = 58.0
P_SHOWER   = 0.0    # cosmic-ray shower, muons reach the ground
P_ATTEN    = 12.0   # thin rock / thick rock / rock with a cavity
P_TELE     = 26.0   # telescope under a hill: direction → thickness
P_TOMO     = 40.0   # three viewpoints → 3-D density (tomography)
P_OUTRO    = 54.0   # pull back, title "muon transmission tomography"
P_END      = 58.0
# --- segment B: existing plates, old 11–27 s → new 69–85 s
B_START = P_START + P_LEN            # 69
B_OLD_START, B_OLD_END = 11.0, 27.0
SHIFT = B_START - B_OLD_START        # +58
T_LOGO_IN = 24.0 + SHIFT             # 82
T_WHITE = 27.0 + SHIFT               # 85
T_END = DURATION

def p(t_local):  # principle local time → global
    return P_START + t_local
