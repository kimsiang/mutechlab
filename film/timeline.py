"""Single source of truth for timing (plain Python, no bpy)."""
FPS = 30
DURATION = 30.0
N_FRAMES = int(DURATION * FPS)          # 900

# Shots (seconds)
T_STREET      = 0.0    # street level, city skyline, cars rolling
T_CUT         = 3.5    # camera cranes down: cutaway earth, pipes, tunnel reveal
T_TUNNEL      = 11.0   # close on the metro tunnel + muon telescope
T_MUONS       = 13.0   # muon rain starts
T_IMAGE       = 17.0   # muography image (cyan void + pipes) fades in
T_WIDE        = 20.0   # pull back wide, whole cutaway lit by muon rain
T_LOGO_IN     = 24.0   # wordmark floats in front of the scene (like GSCAN)
T_WHITE       = 27.0   # cut to clean white end card
T_END         = 30.0

PLATE_END = T_WHITE    # 3D plates needed only up to the white card

def f(t):
    return int(round(t * FPS))
