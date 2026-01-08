import sys
import requests
import json
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QComboBox, QMessageBox, QFrame, QScrollArea, QTabWidget)
from PyQt6.QtCore import Qt, QTimer
from collections import deque

HYPIXEL_KEY = "283cd668-95f7-4d83-8929-5e5c8aadfb2b"
RECENT_PLAYERS_FILE = "recent_players.json"

# XP Curves for Skills
SKILL_XP_NORMAL = [0, 50, 175, 375, 675, 1175, 1925, 2925, 4425, 6425, 9925, 14925, 22425, 32425, 47425, 67425, 
                   97425, 147425, 222425, 322425, 522425, 822425, 1222425, 1722425, 2322425, 3022425, 3822425, 
                   4722425, 5722425, 6822425, 8022425, 9322425, 10722425, 12222425, 13822425, 15522425, 17322425, 
                   19222425, 21222425, 23322425, 25522425, 27822425, 30222425, 32722425, 35322425, 38072425, 
                   40972425, 44072425, 47472425, 51172425, 55172425, 59472425, 64072425, 68972425, 74172425, 
                   79672425, 85472425, 91572425, 97972425, 104672425, 111672425]

SKILL_XP_RUNECRAFTING = [0, 50, 150, 275, 435, 635, 885, 1200, 1600, 2100, 2725, 3510, 4510, 5760, 7325, 9325, 
                         11825, 14950, 18950, 23950, 30200, 38050, 47850, 60100, 75400]

SKILL_XP_SOCIAL = [0, 50, 150, 300, 550, 1050, 1800, 2800, 4050, 5550, 7550, 10050, 13050, 16800, 21300, 27300, 
                   35300, 45300, 57800, 72800, 92800, 117800, 147800, 182800, 222800, 272800]

# Slayer XP Curves
SLAYER_XP = {
    'zombie': [0, 5, 15, 200, 1000, 5000, 20000, 100000, 400000, 1000000],
    'spider': [0, 5, 25, 200, 1000, 5000, 20000, 100000, 400000, 1000000],
    'wolf': [0, 10, 30, 250, 1500, 5000, 20000, 100000, 400000, 1000000],
    'enderman': [0, 10, 30, 250, 1500, 5000, 20000, 100000, 400000, 1000000],
    'blaze': [0, 10, 30, 250, 1500, 5000, 20000, 100000, 400000, 1000000],
    'vampire': [0, 20, 75, 240, 840, 2400, 9000, 25000, 100000, 400000, 1000000]
}

recent_players = deque(maxlen=10)
profiles_cache = {}
current_uuid = None

# Correct Dungeoneering XP table from Hypixel (CUMULATIVE - Total XP needed for each level)
# Source: Hypixel Forums research thread
CATACOMBS_XP = [0, 50, 125, 235, 395, 625, 955, 1425, 2095, 3045, 4385, 6275, 8940, 12700, 17960, 25340, 35640,
                50040, 70040, 97640, 135640, 188140, 259640, 356640, 488640, 668640, 911640, 1239640, 1684640, 
                2284640, 3084640, 4149640, 5559640, 7459640, 9959640, 13259640, 17559640, 23159640, 30359640, 
                39559640, 51559640, 66559640, 85559640, 109559640, 139559640, 177559640, 225559640, 285559640, 
                360559640, 453559640, 569809640]
CLASS_XP = [0, 50, 125, 235, 395, 625, 955, 1425, 2095, 3045, 4385, 6275, 8940, 12700, 17960, 25340, 35640,
            50040, 70040, 97640, 135640, 188140, 259640, 356640, 488640, 668640, 911640, 1239640, 1684640, 
            2284640, 3084640, 4149640, 5559640, 7459640, 9959640, 13259640, 17559640, 23159640, 30359640, 
            39559640, 51559640, 66559640, 85559640, 109559640, 139559640, 177559640, 225559640, 285559640, 
            360559640, 453559640, 569809640]

# ---------------- Persistent Storage ----------------

def load_recent_players():
    """Load recent players from file"""
    global recent_players
    try:
        if os.path.exists(RECENT_PLAYERS_FILE):
            with open(RECENT_PLAYERS_FILE, 'r') as f:
                data = json.load(f)
                recent_players = deque(data, maxlen=10)
    except Exception as e:
        print(f"Error loading recent players: {e}")

def save_recent_players():
    """Save recent players to file"""
    try:
        with open(RECENT_PLAYERS_FILE, 'w') as f:
            json.dump(list(recent_players), f)
    except Exception as e:
        print(f"Error saving recent players: {e}")

# ---------------- API ----------------

def get_uuid(username):
    try:
        r = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{username}", timeout=5)
        if r.status_code != 200:
            return None
        return r.json()["id"]
    except Exception as e:
        print(f"Error getting UUID: {e}")
        return None

def hypixel(endpoint, params):
    try:
        r = requests.get(f"https://api.hypixel.net/v2/{endpoint}",
                         headers={"API-Key": HYPIXEL_KEY},
                         params=params,
                         timeout=10)
        data = r.json()
        if not data.get('success', False):
            print(f"API Error: {data}")
            return None
        return data
    except Exception as e:
        print(f"Error calling Hypixel API: {e}")
        return None

# ---------------- Logic ----------------

def level_from_xp(xp, curve):
    if xp <= 0:
        return 0, 0.0, 0.0, curve[1] if len(curve) > 1 else 0
    
    for lvl in range(len(curve)-1):
        if xp < curve[lvl+1]:
            base = curve[lvl]
            nxt = curve[lvl+1]
            frac = (xp-base)/(nxt-base) if nxt > base else 0
            return lvl, lvl+frac, frac*100, nxt-xp
    
    max_lvl = len(curve)-1
    return max_lvl, float(max_lvl), 100.0, 0

def format_time(milliseconds):
    """Convert milliseconds to MM:SS format"""
    if milliseconds <= 0:
        return "--:--"
    seconds = milliseconds / 1000
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

# ---------------- UI ----------------

class SkyBlockTracker(QWidget):
    def __init__(self):
        super().__init__()
        
        # Load recent players at startup
        load_recent_players()
        
        # Initialize UI after loading
        self.init_ui()
        
        # Update recent players UI after everything is set up
        for i, btn in enumerate(self.recent_buttons):
            if i < len(recent_players):
                btn.setText(f"👤 {recent_players[i]}")
                btn.setVisible(True)
                player_name = recent_players[i]
                btn.clicked.connect(lambda checked, n=player_name: QTimer.singleShot(0, lambda: self.load_recent_player(n)))
        
    def init_ui(self):
        self.setWindowTitle("SkyBlock Tracker")
        self.setMinimumSize(1600, 900)
        
        # Modern Dark Theme
        self.setStyleSheet("""
            QWidget {
                background-color: #0f0f1a;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #e0e0e0;
            }
            QScrollBar:vertical {
                background: #1a1a2e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #3d4066;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4a4d6d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QTabWidget::pane {
                border: 2px solid #2d3152;
                border-radius: 8px;
                background: #1a1a2e;
                padding: 5px;
            }
            QTabBar::tab {
                background: #22253f;
                color: #8b9dc3;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background: #5865f2;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background: #2d3152;
            }
        """)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # Sidebar for recent players
        self.create_sidebar()
        
        # Main content area
        self.create_main_content()

    def create_sidebar(self):
        sidebar_container = QFrame()
        sidebar_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16162a);
                border-radius: 15px;
                padding: 15px;
            }
        """)
        sidebar_container.setFixedWidth(240)
        
        self.sidebar = QVBoxLayout(sidebar_container)
        self.sidebar.setSpacing(10)
        
        sidebar_title = QLabel("📜 RECENT PLAYERS")
        sidebar_title.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #8b9dc3;
            padding: 10px;
            letter-spacing: 1px;
        """)
        self.sidebar.addWidget(sidebar_title)
        
        # Scrollable area for recent players
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(8)
        
        self.recent_buttons = []
        for _ in range(10):
            btn = QPushButton("")
            btn.setVisible(False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2a2d4a, stop:1 #22253f);
                    color: #b8c5db;
                    border: 2px solid #33364d;
                    border-radius: 8px;
                    padding: 10px;
                    text-align: left;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #3d4066, stop:1 #32355a);
                    border: 2px solid #4a4d6d;
                }
                QPushButton:pressed {
                    background: #252842;
                }
            """)
            scroll_layout.addWidget(btn)
            self.recent_buttons.append(btn)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        self.sidebar.addWidget(scroll)
        
        self.main_layout.addWidget(sidebar_container)

    def create_main_content(self):
        content_container = QFrame()
        content_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16162a);
                border-radius: 15px;
                padding: 25px;
            }
        """)
        
        self.content_layout = QVBoxLayout(content_container)
        self.content_layout.setSpacing(20)

        # Title (SMALLER)
        title = QLabel("⚔️ SKYBLOCK TRACKER")
        title.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #ffffff;
            padding: 5px;
            letter-spacing: 2px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(title)

        # Search bar (SMALLER)
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background: #22253f;
                border-radius: 10px;
                padding: 10px;
                border: 2px solid #2d3152;
            }
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setSpacing(12)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter Minecraft Username...")
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #2a2d4a;
                color: #ffffff;
                border: 2px solid #3d4066;
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit:focus {
                border: 2px solid #5865f2;
                background-color: #2d3152;
            }
            QLineEdit::placeholder {
                color: #6b7196;
            }
        """)
        self.name_input.returnPressed.connect(self.check_player_ui)
        
        self.check_btn = QPushButton("🔍 SEARCH")
        self.check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_btn.setFixedWidth(140)
        self.check_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5865f2, stop:1 #4752c4);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6a75f5, stop:1 #5461d1);
            }
            QPushButton:pressed {
                background: #4752c4;
            }
            QPushButton:disabled {
                background: #3d4066;
                color: #6b7196;
            }
        """)
        self.check_btn.clicked.connect(self.check_player_ui)
        
        search_layout.addWidget(self.name_input)
        search_layout.addWidget(self.check_btn)
        self.content_layout.addWidget(search_frame)

        # Profile selector & Status in one row (SMALLER)
        profile_frame = QFrame()
        profile_frame.setStyleSheet("""
            QFrame {
                background: #22253f;
                border-radius: 8px;
                padding: 8px;
                border: 2px solid #2d3152;
            }
        """)
        profile_layout = QHBoxLayout(profile_frame)
        profile_layout.setContentsMargins(8, 4, 8, 4)
        
        # Status Label (left side)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #8b9dc3;
        """)
        profile_layout.addWidget(self.status_label)
        
        profile_layout.addStretch()
        
        profile_lbl = QLabel("📊 Profile:")
        profile_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #8b9dc3;")
        
        self.profile_combo = QComboBox()
        self.profile_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.profile_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2d4a;
                color: #ffffff;
                border: 2px solid #3d4066;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 500;
                min-width: 180px;
            }
            QComboBox:hover {
                border: 2px solid #4a4d6d;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #8b9dc3;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2d4a;
                color: #ffffff;
                border: 2px solid #3d4066;
                selection-background-color: #3d4066;
                padding: 5px;
            }
        """)
        self.profile_combo.currentTextChanged.connect(self.load_profile_ui)
        
        profile_layout.addWidget(profile_lbl)
        profile_layout.addWidget(self.profile_combo)
        self.content_layout.addWidget(profile_frame)

        # ============== TAB WIDGET ==============
        self.tabs = QTabWidget()
        self.content_layout.addWidget(self.tabs)

        # Create all tabs
        self.create_dungeon_stats_tab()
        self.create_skills_slayers_tab()
        self.create_general_tab()

        self.main_layout.addWidget(content_container)

    # ============== TAB 1: DUNGEON STATS (ORIGINAL) ==============
    def create_dungeon_stats_tab(self):
        dungeon_tab = QWidget()
        dungeon_layout = QVBoxLayout(dungeon_tab)
        dungeon_layout.setSpacing(20)
        dungeon_layout.setContentsMargins(10, 10, 10, 10)

        # Dungeon Stats - Three Columns (ORIGINAL LAYOUT)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        dungeon_layout.addLayout(stats_layout)

        # Catacombs Card
        self.cata_frame = self.create_stat_card("🏰 CATACOMBS", "#5865f2", stats_layout)
        
        self.cata_info = QLabel("Level: --")
        self.cata_info.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff; line-height: 1.6;")
        self.cata_secrets = QLabel("")
        self.cata_secrets.setStyleSheet("font-size: 14px; color: #d0d5e0; margin-top: 8px;")
        self.cata_magical_power = QLabel("")  # NEW: Magical Power
        self.cata_magical_power.setStyleSheet("font-size: 14px; color: #d0d5e0; margin-top: 8px;")
        
        self.cata_frame.addWidget(self.cata_info)
        self.cata_frame.addWidget(self.cata_secrets)
        self.cata_frame.addWidget(self.cata_magical_power)
        self.cata_frame.addStretch()

        # Classes Card
        self.class_frame = self.create_stat_card("👥 CLASSES", "#eb459e", stats_layout)
        self.class_label = QLabel("No data")
        self.class_label.setStyleSheet("""
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 15px;
            color: #d0d5e0;
            line-height: 1.9;
        """)
        self.class_frame.addWidget(self.class_label)
        self.class_frame.addStretch()

        # Floors Card (with scroll)
        floors_container = QFrame()
        floors_container.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #22253f, stop:1 #1c1e35);
                border-radius: 12px;
                border-top: 3px solid #f2c94c;
                padding: 20px;
            }}
        """)
        
        floors_layout = QVBoxLayout(floors_container)
        
        floors_title = QLabel("🗡️ FLOORS")
        floors_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #f2c94c;
            letter-spacing: 1px;
            padding-bottom: 10px;
        """)
        floors_layout.addWidget(floors_title)
        
        # Scrollable floors area
        floors_scroll = QScrollArea()
        floors_scroll.setWidgetResizable(True)
        floors_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        floors_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        floors_scroll_widget = QWidget()
        floors_scroll_layout = QVBoxLayout(floors_scroll_widget)
        
        self.floors_label = QLabel("No data")
        self.floors_label.setStyleSheet("""
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 15px;
            color: #d0d5e0;
            line-height: 1.8;
        """)
        floors_scroll_layout.addWidget(self.floors_label)
        floors_scroll_layout.addStretch()
        
        floors_scroll.setWidget(floors_scroll_widget)
        floors_layout.addWidget(floors_scroll)
        
        stats_layout.addWidget(floors_container)

        self.tabs.addTab(dungeon_tab, "⚔️ Dungeon Stats")

    # ============== TAB 2: SKILLS & SLAYERS ==============
    def create_skills_slayers_tab(self):
        skills_tab = QWidget()
        skills_main_layout = QVBoxLayout(skills_tab)
        skills_main_layout.setSpacing(15)
        skills_main_layout.setContentsMargins(10, 10, 10, 10)

        # Two columns: Skills | Slayers
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(15)
        skills_main_layout.addLayout(columns_layout)

        # ===== SKILLS COLUMN =====
        skills_container = QWidget()
        skills_container_layout = QVBoxLayout(skills_container)
        skills_container_layout.setSpacing(8)
        skills_container_layout.setContentsMargins(0, 0, 0, 0)
        
        skills_header = QLabel("📚 SKILLS")
        skills_header.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #5865f2;
            letter-spacing: 1px;
            padding: 5px;
            margin-bottom: 5px;
        """)
        skills_container_layout.addWidget(skills_header)
        
        # Skills Grid Layout (3x4 grid for 11 skills)
        skills_grid = QHBoxLayout()
        skills_grid.setSpacing(8)
        
        # Create 3 columns
        col1_layout = QVBoxLayout()
        col1_layout.setSpacing(8)
        col2_layout = QVBoxLayout()
        col2_layout.setSpacing(8)
        col3_layout = QVBoxLayout()
        col3_layout.setSpacing(8)
        col4_layout = QVBoxLayout()
        col4_layout.setSpacing(8)
        
        self.skill_labels = {}
        skill_list = ['farming', 'mining', 'combat', 'foraging', 'fishing', 'enchanting', 
                      'alchemy', 'taming', 'carpentry', 'runecrafting', 'social']
        skill_icons = {
            'farming': '🌾', 'mining': '⛏️', 'combat': '⚔️', 'foraging': '🌲', 
            'fishing': '🎣', 'enchanting': '📖', 'alchemy': '⚗️', 'taming': '🐺', 
            'carpentry': '🪓', 'runecrafting': '🔮', 'social': '👥'
        }
        
        for idx, skill in enumerate(skill_list):
            skill_card = QFrame()
            skill_card.setStyleSheet("""
                QFrame {
                    background: #22253f;
                    border-radius: 6px;
                    padding: 8px;
                    border-left: 3px solid #5865f2;
                }
            """)
            skill_card_layout = QVBoxLayout(skill_card)
            skill_card_layout.setContentsMargins(6, 6, 6, 6)
            
            icon = skill_icons.get(skill, '📊')
            skill_label = QLabel(f"{icon} {skill.capitalize()}\nLvl: --\nProg: --")
            skill_label.setStyleSheet("""
                font-size: 11px;
                font-weight: 500;
                color: #d0d5e0;
                line-height: 1.3;
            """)
            self.skill_labels[skill] = skill_label
            skill_card_layout.addWidget(skill_label)
            
            # Distribute across 4 columns
            if idx < 3:
                col1_layout.addWidget(skill_card)
            elif idx < 6:
                col2_layout.addWidget(skill_card)
            elif idx < 9:
                col3_layout.addWidget(skill_card)
            else:
                col4_layout.addWidget(skill_card)
        
        col1_layout.addStretch()
        col2_layout.addStretch()
        col3_layout.addStretch()
        col4_layout.addStretch()
        
        skills_grid.addLayout(col1_layout)
        skills_grid.addLayout(col2_layout)
        skills_grid.addLayout(col3_layout)
        skills_grid.addLayout(col4_layout)
        
        skills_container_layout.addLayout(skills_grid)
        columns_layout.addWidget(skills_container)

        # ===== SLAYERS COLUMN =====
        slayers_container = QWidget()
        slayers_container_layout = QVBoxLayout(slayers_container)
        slayers_container_layout.setSpacing(8)
        slayers_container_layout.setContentsMargins(0, 0, 0, 0)
        
        slayers_header = QLabel("🗡️ SLAYERS")
        slayers_header.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #eb459e;
            letter-spacing: 1px;
            padding: 5px;
            margin-bottom: 5px;
        """)
        slayers_container_layout.addWidget(slayers_header)
        
        # Slayers Grid (2 columns for 6 slayers)
        slayers_grid = QHBoxLayout()
        slayers_grid.setSpacing(8)
        
        slayer_col1 = QVBoxLayout()
        slayer_col1.setSpacing(8)
        slayer_col2 = QVBoxLayout()
        slayer_col2.setSpacing(8)
        
        self.slayer_labels = {}
        slayer_list = ['zombie', 'spider', 'wolf', 'enderman', 'blaze', 'vampire']
        slayer_icons = {
            'zombie': '🧟', 'spider': '🕷️', 'wolf': '🐺', 
            'enderman': '👾', 'blaze': '🔥', 'vampire': '🧛'
        }
        
        for idx, slayer in enumerate(slayer_list):
            slayer_card = QFrame()
            slayer_card.setStyleSheet("""
                QFrame {
                    background: #22253f;
                    border-radius: 6px;
                    padding: 8px;
                    border-left: 3px solid #eb459e;
                }
            """)
            slayer_card_layout = QVBoxLayout(slayer_card)
            slayer_card_layout.setContentsMargins(6, 6, 6, 6)
            
            icon = slayer_icons.get(slayer, '⚔️')
            slayer_label = QLabel(f"{icon} {slayer.capitalize()}\nLvl: --\nProg: --")
            slayer_label.setStyleSheet("""
                font-size: 11px;
                font-weight: 500;
                color: #d0d5e0;
                line-height: 1.3;
            """)
            self.slayer_labels[slayer] = slayer_label
            slayer_card_layout.addWidget(slayer_label)
            
            # Distribute across 2 columns
            if idx < 3:
                slayer_col1.addWidget(slayer_card)
            else:
                slayer_col2.addWidget(slayer_card)
        
        slayer_col1.addStretch()
        slayer_col2.addStretch()
        
        slayers_grid.addLayout(slayer_col1)
        slayers_grid.addLayout(slayer_col2)
        
        slayers_container_layout.addLayout(slayers_grid)
        columns_layout.addWidget(slayers_container)

        self.tabs.addTab(skills_tab, "📚 Skills & Slayers")

    # ============== TAB 3: GENERAL ==============
    def create_general_tab(self):
        general_tab = QWidget()
        general_main_layout = QVBoxLayout(general_tab)
        general_main_layout.setSpacing(12)
        general_main_layout.setContentsMargins(10, 10, 10, 10)

        # Two columns layout
        columns = QHBoxLayout()
        columns.setSpacing(12)
        
        # LEFT COLUMN
        left_column = QVBoxLayout()
        left_column.setSpacing(12)
        
        # ===== SKYBLOCK LEVEL =====
        sb_level_card = QFrame()
        sb_level_card.setStyleSheet("""
            QFrame {
                background: #22253f;
                border-radius: 8px;
                padding: 12px;
                border-top: 3px solid #5865f2;
            }
        """)
        sb_level_layout = QVBoxLayout(sb_level_card)
        sb_level_layout.setContentsMargins(10, 8, 10, 8)
        
        sb_level_title = QLabel("📊 SKYBLOCK LEVEL")
        sb_level_title.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #5865f2;
            letter-spacing: 1px;
            padding-bottom: 6px;
        """)
        sb_level_layout.addWidget(sb_level_title)
        
        self.sb_level_label = QLabel("Level: --\nProgress: --")
        self.sb_level_label.setStyleSheet("""
            font-size: 12px;
            color: #d0d5e0;
            line-height: 1.5;
        """)
        sb_level_layout.addWidget(self.sb_level_label)
        left_column.addWidget(sb_level_card)
        
        # ===== ACTIVE PET =====
        pet_card = QFrame()
        pet_card.setStyleSheet("""
            QFrame {
                background: #22253f;
                border-radius: 8px;
                padding: 12px;
                border-top: 3px solid #a855f7;
            }
        """)
        pet_layout = QVBoxLayout(pet_card)
        pet_layout.setContentsMargins(10, 8, 10, 8)
        
        pet_title = QLabel("🐾 ACTIVE PET")
        pet_title.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #a855f7;
            letter-spacing: 1px;
            padding-bottom: 6px;
        """)
        pet_layout.addWidget(pet_title)
        
        self.general_pet_label = QLabel("No pet active")
        self.general_pet_label.setStyleSheet("""
            font-size: 12px;
            color: #d0d5e0;
            line-height: 1.5;
        """)
        pet_layout.addWidget(self.general_pet_label)
        left_column.addWidget(pet_card)
        
        left_column.addStretch()
        columns.addLayout(left_column)
        
        # RIGHT COLUMN
        right_column = QVBoxLayout()
        right_column.setSpacing(12)
        
        # ===== PURSE & BANK (Combined in one card) =====
        money_card = QFrame()
        money_card.setStyleSheet("""
            QFrame {
                background: #22253f;
                border-radius: 8px;
                padding: 12px;
                border-top: 3px solid #f2c94c;
            }
        """)
        money_layout = QVBoxLayout(money_card)
        money_layout.setContentsMargins(10, 8, 10, 8)
        
        money_title = QLabel("💰 BANKING")
        money_title.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #f2c94c;
            letter-spacing: 1px;
            padding-bottom: 6px;
        """)
        money_layout.addWidget(money_title)
        
        self.money_combined_label = QLabel("💵 Purse: --\n🏦 Bank: --")
        self.money_combined_label.setStyleSheet("""
            font-size: 12px;
            color: #d0d5e0;
            line-height: 1.5;
        """)
        money_layout.addWidget(self.money_combined_label)
        right_column.addWidget(money_card)
        
        # ===== PROFILE INFO =====
        profile_card = QFrame()
        profile_card.setStyleSheet("""
            QFrame {
                background: #22253f;
                border-radius: 8px;
                padding: 12px;
                border-top: 3px solid #00d4aa;
            }
        """)
        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setContentsMargins(10, 8, 10, 8)
        
        profile_title = QLabel("📋 PROFILE INFO")
        profile_title.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #00d4aa;
            letter-spacing: 1px;
            padding-bottom: 6px;
        """)
        profile_layout.addWidget(profile_title)
        
        self.profile_info_label = QLabel("Profile: --\nGamemode: --")
        self.profile_info_label.setStyleSheet("""
            font-size: 12px;
            color: #d0d5e0;
            line-height: 1.5;
        """)
        profile_layout.addWidget(self.profile_info_label)
        right_column.addWidget(profile_card)
        
        right_column.addStretch()
        columns.addLayout(right_column)
        
        general_main_layout.addLayout(columns)
        
        self.tabs.addTab(general_tab, "📊 General")

    def create_stat_card(self, title, accent_color, parent_layout):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #22253f, stop:1 #1c1e35);
                border-radius: 12px;
                border-top: 3px solid {accent_color};
                padding: 20px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {accent_color};
            letter-spacing: 1px;
            padding-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        parent_layout.addWidget(card)
        return layout

    # ---------------- UI Callbacks ----------------

    def update_recent_ui(self, name):
        if name in recent_players:
            recent_players.remove(name)
        recent_players.appendleft(name)
        
        # Save to file
        save_recent_players()
        
        for i, btn in enumerate(self.recent_buttons):
            if i < len(recent_players):
                btn.setText(f"👤 {recent_players[i]}")
                btn.setVisible(True)
                try:
                    btn.clicked.disconnect()
                except:
                    pass
                player_name = recent_players[i]
                # Use QTimer to prevent hanging - defer the action
                btn.clicked.connect(lambda checked, n=player_name: QTimer.singleShot(0, lambda: self.load_recent_player(n)))
            else:
                btn.setText("")
                btn.setVisible(False)

    def load_recent_player(self, name):
        self.name_input.setText(name)
        self.check_player_ui()
    
    def closeEvent(self, event):
        """Save recent players when closing the app"""
        save_recent_players()
        event.accept()

    def load_profile_ui(self, profile_name):
        if not profile_name or profile_name not in profiles_cache:
            return
        
        profile = profiles_cache[profile_name]
        
        if current_uuid not in profile.get('members', {}):
            self.status_label.setText("❌ Error: Player not found in profile")
            return
        
        member = profile['members'][current_uuid]
        
        # Load all sections
        self.load_dungeon_stats(member)
        self.load_skills_slayers(member)
        self.load_general_data(member, profile)

    # ============== LOAD DUNGEON STATS (ORIGINAL) ==============
    def load_dungeon_stats(self, member):
        dungeon = member.get('dungeons', {})
        
        # Get dungeon types
        dungeon_types = dungeon.get('dungeon_types', {})
        
        # Catacombs (Normal)
        cat = dungeon_types.get('catacombs', {})
        
        # Master Catacombs (separate dungeon type!)
        master_cat = dungeon_types.get('master_catacombs', {})
        
        # Catacombs Level
        cata_xp = cat.get('experience', 0)
        lvl, exact, percent, needed = level_from_xp(cata_xp, CATACOMBS_XP)
        
        # Combine all catacombs info into one text block with better spacing
        bar_length = int(percent / 5)
        progress_bar = "█" * bar_length + "░" * (20 - bar_length)
        
        cata_text = f"Level: {exact:.2f}\n\n"
        cata_text += f"{progress_bar} {percent:.1f}%\n\n"
        cata_text += f"Until next: {int(needed):,} XP"
        
        self.cata_info.setText(cata_text)
        
        # Secrets
        secrets = dungeon.get('secrets', 0)
        self.cata_secrets.setText(f"🔍 Secrets: {secrets:,}")
        
        # Magical Power (NEW)
        magical_power = member.get('accessory_bag_storage', {}).get('highest_magical_power', 0)
        self.cata_magical_power.setText(f"✨ Magical Power: {magical_power}\n")

        # Classes
        classes = dungeon.get('player_classes', {})
        class_icons = {'healer': '❤️', 'tank': '🛡️', 'mage': '🔮', 'berserk': '⚔️', 'archer': '🏹'}
        class_text = ""
        for cls in ['healer', 'tank', 'mage', 'berserk', 'archer']:
            xp = classes.get(cls, {}).get('experience', 0)
            _, ex, _, _ = level_from_xp(xp, CLASS_XP)
            icon = class_icons.get(cls, '•')
            class_text += f"{icon} {cls.capitalize():<10} {int(ex):>3}\n"
        self.class_label.setText(class_text if class_text else "No class data")

        # Floors - Normal and Master Mode (from separate dungeon types)
        floors = cat.get('tier_completions', {})
        fastest_time_s_plus = cat.get('fastest_time_s_plus', {})
        best_score = cat.get('best_score', {})
        
        # Master mode data from master_catacombs
        master_completions = master_cat.get('tier_completions', {})
        master_best_score = master_cat.get('best_score', {})
        master_fastest_s = master_cat.get('fastest_time_s_plus', {})
        
        # Normal Floors Header
        floors_text = f"{'FLOOR':<8} {'RUNS':>8} {'BEST':>8} {'S+ TIME':>10}\n"
        floors_text += "─" * 38 + "\n"
        
        # Normal Floors (E, F1-F7)
        for i in range(8):
            floor_key = str(i)
            n = floors.get(floor_key, 0)
            score = best_score.get(floor_key, 0)
            time_s = fastest_time_s_plus.get(floor_key, 0)
            
            floor_name = "E" if i == 0 else f"F{i}"
            icon = '🔰' if i == 0 else '⚔️'
            
            floors_text += f"{icon} {floor_name:<6} {int(n):>8} {int(score):>8} {format_time(time_s):>10}\n"
        
        # Master Mode Section
        floors_text += "\n" + "─" * 38 + "\n"
        floors_text += f"{'MASTER':<8} {'RUNS':>8} {'BEST':>8} {'S+ TIME':>10}\n"
        floors_text += "─" * 38 + "\n"
        
        # Master Floors (M1-M7, no entrance)
        for i in range(1, 8):
            floor_key = str(i)
            m = master_completions.get(floor_key, 0)
            score_m = master_best_score.get(floor_key, 0)
            time_s_m = master_fastest_s.get(floor_key, 0)
            
            floors_text += f"🔥 M{i:<6} {int(m):>8} {int(score_m):>8} {format_time(time_s_m):>10}\n"
        
        self.floors_label.setText(floors_text if floors_text else "No floor data")

    # ============== LOAD SKILLS & SLAYERS (NEW) ==============
    def load_skills_slayers(self, member):
        # ===== SKILLS =====
        player_data = member.get('player_data', {})
        experience = player_data.get('experience', {})
        
        skill_list = ['farming', 'mining', 'combat', 'foraging', 'fishing', 'enchanting', 
                      'alchemy', 'taming', 'carpentry', 'runecrafting', 'social']
        skill_icons = {
            'farming': '🌾', 'mining': '⛏️', 'combat': '⚔️', 'foraging': '🌲', 
            'fishing': '🎣', 'enchanting': '📖', 'alchemy': '⚗️', 'taming': '🐺', 
            'carpentry': '🪓', 'runecrafting': '🔮', 'social': '👥'
        }
        
        for skill in skill_list:
            xp_key = f'SKILL_{skill.upper()}'
            xp = experience.get(xp_key, 0)
            
            # Determine XP curve
            if skill == 'runecrafting':
                curve = SKILL_XP_RUNECRAFTING
            elif skill == 'social':
                curve = SKILL_XP_SOCIAL
            else:
                curve = SKILL_XP_NORMAL
            
            lvl, exact, percent, needed = level_from_xp(xp, curve)
            
            icon = skill_icons.get(skill, '📊')
            text = f"{icon} {skill.capitalize()}\n"
            text += f"Lvl: {exact:.2f}\n"
            text += f"Prog: {percent:.1f}%\n"
            text += f"Next: {int(needed):,} XP"
            
            if skill in self.skill_labels:
                self.skill_labels[skill].setText(text)
        
        # ===== SLAYERS =====
        slayer_bosses = member.get('slayer', {}).get('slayer_bosses', {})
        slayer_list = ['zombie', 'spider', 'wolf', 'enderman', 'blaze', 'vampire']
        slayer_icons = {
            'zombie': '🧟', 'spider': '🕷️', 'wolf': '🐺', 
            'enderman': '👾', 'blaze': '🔥', 'vampire': '🧛'
        }
        
        for slayer in slayer_list:
            slayer_data = slayer_bosses.get(slayer, {})
            xp = slayer_data.get('xp', 0)
            
            if slayer in SLAYER_XP:
                lvl, exact, percent, needed = level_from_xp(xp, SLAYER_XP[slayer])
                
                icon = slayer_icons.get(slayer, '⚔️')
                text = f"{icon} {slayer.capitalize()}\n"
                text += f"Lvl: {int(lvl)}\n"
                text += f"Prog: {percent:.1f}%\n"
                text += f"Next: {int(needed):,} XP"
                
                if slayer in self.slayer_labels:
                    self.slayer_labels[slayer].setText(text)

    # ============== LOAD GENERAL DATA (NEW) ==============
    def load_general_data(self, member, profile):
        # ===== SKYBLOCK LEVEL =====
        leveling = member.get('leveling', {})
        sb_xp = leveling.get('experience', 0)
        # Simplified SB level calculation (actual formula is complex)
        sb_level = int(sb_xp / 100)  # Placeholder calculation
        
        sb_text = f"Level: {sb_level}\n"
        sb_text += f"Total XP: {int(sb_xp):,}"
        self.sb_level_label.setText(sb_text)
        
        # ===== ACTIVE PET =====
        pets_data = member.get('pets_data', {})
        pets = pets_data.get('pets', [])
        
        active_pet = None
        for pet in pets:
            if pet.get('active', False):
                active_pet = pet
                break
        
        if active_pet:
            pet_type = active_pet.get('type', 'Unknown')
            tier = active_pet.get('tier', 'COMMON')
            exp = active_pet.get('exp', 0)
            
            tier_colors = {
                'COMMON': '⚪',
                'UNCOMMON': '🟢',
                'RARE': '🔵',
                'EPIC': '🟣',
                'LEGENDARY': '🟠',
                'MYTHIC': '🔴'
            }
            tier_icon = tier_colors.get(tier, '⚪')
            
            pet_text = f"{tier_icon} {tier} {pet_type.replace('_', ' ').title()}\n"
            pet_text += f"Experience: {exp:,}"
            self.general_pet_label.setText(pet_text)
        else:
            self.general_pet_label.setText("No pet currently active")
        
        # ===== PURSE & BANK =====
        # Try different possible keys for purse/coins
        purse = member.get('currencies', {}).get('coin_purse', 0)
        if purse == 0:
            purse = member.get('coin_purse', 0)
        if purse == 0:
            purse = member.get('currencies', {}).get('coins', 0)
        
        banking = profile.get('banking', {})
        bank_balance = banking.get('balance', 0)
        
        money_text = f"💵 Purse: {purse:,.0f} coins\n"
        money_text += f"🏦 Bank: {bank_balance:,.0f} coins"
        self.money_combined_label.setText(money_text)
        
        # ===== PROFILE INFO =====
        profile_name = profile.get('cute_name', 'Unknown')
        game_mode = profile.get('game_mode', 'normal')
        game_mode_display = {
            'normal': 'Normal',
            'ironman': '⚔️ Ironman',
            'stranded': '🏝️ Stranded',
            'bingo': '🎯 Bingo'
        }.get(game_mode, game_mode.title())
        
        profile_text = f"Profile: {profile_name}\n"
        profile_text += f"Gamemode: {game_mode_display}"
        self.profile_info_label.setText(profile_text)

    def check_player_ui(self):
        global current_uuid
        
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "⚠️ Error", "Please enter a player name!")
            return
        
        self.status_label.setText("⏳ Loading...")
        self.check_btn.setEnabled(False)
        QApplication.processEvents()
        
        # Get UUID
        uuid = get_uuid(name)
        if not uuid:
            self.status_label.setText("❌ Player not found")
            self.check_btn.setEnabled(True)
            return
        
        current_uuid = uuid
        self.update_recent_ui(name)
        
        # Get online status
        status_data = hypixel('status', {'uuid': uuid})
        if status_data and 'session' in status_data:
            is_online = status_data['session'].get('online', False)
            status_text = "🟢 ONLINE" if is_online else "⚫ OFFLINE"
        else:
            status_text = "❓ Status unknown"
        
        # Get profiles
        profiles_data = hypixel('skyblock/profiles', {'uuid': uuid})
        if not profiles_data or 'profiles' not in profiles_data:
            self.status_label.setText("❌ Could not load profiles")
            self.check_btn.setEnabled(True)
            return
        
        profiles = profiles_data['profiles']
        if not profiles:
            self.status_label.setText("❌ No SkyBlock profiles found")
            self.check_btn.setEnabled(True)
            return
        
        # Clear and populate profiles
        profiles_cache.clear()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        
        selected_profile = None
        for p in profiles:
            if p is None:
                continue
            profile_name = p.get('cute_name', 'Unknown')
            profiles_cache[profile_name] = p
            self.profile_combo.addItem(profile_name)
            
            if p.get('selected', False):
                selected_profile = profile_name
        
        self.profile_combo.blockSignals(False)
        
        if selected_profile and selected_profile in profiles_cache:
            index = self.profile_combo.findText(selected_profile)
            if index >= 0:
                self.profile_combo.setCurrentIndex(index)
        else:
            self.profile_combo.setCurrentIndex(0)
        
        self.load_profile_ui(self.profile_combo.currentText())
        self.status_label.setText(f"{status_text} • Player: {name}")
        self.check_btn.setEnabled(True)

# ---------------- RUN APP ----------------

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SkyBlockTracker()

    # Check if player name was passed as argument
    if len(sys.argv) > 1:
        player_name = sys.argv[1]
        window.name_input.setText(player_name)
        # Auto-search after window shows
        QTimer.singleShot(500, window.check_player_ui)

    window.show()
    sys.exit(app.exec())