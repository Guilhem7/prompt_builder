import os
import re
import getpass
import socket
from datetime import datetime
from prompt_builder.models.interpolators.interpolator import InterpolationEngine, BASH_MODE, ZSH_MODE

NOW = datetime.now()
HOST = socket.gethostname()
HOST_SHORT = HOST.split(".")[0]
CWD = os.getcwd()
HOME = os.path.expanduser("~")
CWD_TILDE = CWD.replace(HOME, "~", 1)
USER = getpass.getuser()

PS1_VARS = {
    "u": USER,                 # \u
    "h": HOST_SHORT,           # \h
    "H": HOST,                 # \H

    "w": CWD_TILDE,            # \w
    "W": os.path.basename(CWD),# \W

    "t": NOW.strftime("%H:%M:%S"),    # \t
    "T": NOW.strftime("%I:%M:%S"),    # \T
    "A": NOW.strftime("%H:%M"),       # \A
    "@": NOW.strftime("%I:%M %p"),    # \@
    "d": NOW.strftime("%a %b %d"),    # \d

    "s": os.path.basename(os.environ.get("SHELL", "")),  # \s

    "$": "#" if hasattr(os, "geteuid") and os.geteuid() == 0 else "$",
    "n": "\n",  # \n
}

PROMPT_VARS = {
    "n": USER,                 # %n
    "m": HOST_SHORT,           # %m
    "M": HOST,                 # %M

    "~": CWD_TILDE,            # %~
    "/": CWD,                  # %/
    "c": os.path.basename(CWD),# %c
    "C": CWD.split("/")[-1],   # %C (approx)

    "t": NOW.strftime("%I:%M %p"),    # %t
    "T": NOW.strftime("%H:%M:%S"),    # %T
    "*": NOW.strftime("%H:%M:%S"),    # %*

    "#": "#" if hasattr(os, "geteuid") and os.geteuid() == 0 else "%",
}

class BaseInterpolator:
    def render(self, text: str) -> str:
        return self._pattern.sub(
            lambda m: self.VARS[m.group(0)](),
            text,
        )

class BashInterpolator(BaseInterpolator):
    VARS = {
        r"\\u": lambda: getpass.getuser(),
        r"\\h": lambda: socket.gethostname().split(".")[0],
        r"\\H": lambda: socket.gethostname(),
        r"\\w": lambda: os.getcwd().replace(os.path.expanduser("~"), "~", 1),
        r"\\W": lambda: os.path.basename(os.getcwd()),
        r"\\t": lambda: datetime.now().strftime("%H:%M:%S"),
        r"\\T": lambda: datetime.now().strftime("%I:%M:%S"),
        r"\\A": lambda: datetime.now().strftime("%H:%M"),
        r"\\d": lambda: datetime.now().strftime("%a %b %d"),
        r"\\s": lambda: os.path.basename(os.environ.get("SHELL", "")),
        r"\\$": lambda: "#" if hasattr(os, "geteuid") and os.geteuid() == 0 else "$",
        "$$": lambda: str(os.getpid()),
    }

    _pattern = re.compile(
        "|".join(
            sorted(
                map(re.escape, VARS.keys()),
                key=len,
                reverse=True,
            )
        )
    )

class ZshInterpolator(BaseInterpolator):
    VARS = {
        "%%": lambda: "%",
        "%n": lambda: getpass.getuser(),
        "%m": lambda: socket.gethostname().split(".")[0],
        "%M": lambda: socket.gethostname(),
        "%~": lambda: os.getcwd().replace(os.path.expanduser("~"), "~", 1),
        "%/": lambda: os.getcwd(),
        "%c": lambda: os.path.basename(os.getcwd()),
        "%T": lambda: datetime.now().strftime("%H:%M:%S"),
        "%*": lambda: datetime.now().strftime("%H:%M:%S"),
        "%t": lambda: datetime.now().strftime("%I:%M"),
        "%$": lambda: "#" if hasattr(os, "geteuid") and os.geteuid() == 0 else "$",
    }

    _pattern = re.compile(
        "|".join(
            sorted(
                map(re.escape, VARS.keys()),
                key=len,
                reverse=True,
            )
        )
    )

# BASH_ENGINE = InterpolationEngine(
#     config=BASH_MODE,
#     variables=PS1_VARS,
#     functions={},
# )
BASH_ENGINE = BashInterpolator()

# ZSH_ENGINE = InterpolationEngine(
#     config=ZSH_MODE,
#     variables=PROMPT_VARS,
#     functions={},
# )
ZSH_ENGINE = ZshInterpolator()
