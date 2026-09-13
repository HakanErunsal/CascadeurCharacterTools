"""Load in Cascadeur's Python Console, then press Execute."""
import sys
from pathlib import Path
folder=str(Path(__file__).resolve().parent)
if folder not in sys.path:sys.path.insert(0,folder)
import upc_character_tools
upc_character_tools.show()
