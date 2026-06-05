import sys
import os

# Determine base path - works both in dev and PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    BASE_DIR = os.path.dirname(sys.executable)
    APP_DIR = os.path.join(sys._MEIPASS, 'chat_system')
else:
    # Running as normal Python script
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(APP_DIR)

# ─── Configuration ───────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(APP_DIR, 'config.json')
DB_PATH = os.path.join(BASE_DIR, 'fgo_wiki.db')
PERSONALITIES_PATH = os.path.join(APP_DIR, 'personalities.json')
COLLECTION_MAP_PATH = os.path.join(APP_DIR, 'servant_collection_map.json')
ASSETS_BASE = os.path.join(BASE_DIR, '基本资料')
