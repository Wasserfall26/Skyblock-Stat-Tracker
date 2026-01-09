# SkyBlock Dungeon Tracker Premium UI (PyQt6)
# Dark theme with all dungeon stats
# Updated: Simplified - removed overlay mode

import sys
import requests
import json
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QComboBox, QMessageBox, QFrame, QScrollArea)
from PyQt6.QtCore import Qt, QTimer
from collections import deque

HYPIXEL_KEY = "283cd668-95f7-4d83-8929-5e5c8aadfb2b"
RECENT_PLAYERS_FILE = "recent_players.json"

recent_players = deque(maxlen=10)
profiles_cache = {}
current_uuid = None

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

CATACOMBS_XP = [0, 50, 125, 235, 395, 625, 955, 1425, 2095, 3045, 4385, 6275, 8945, 12745, 18045, 25345, 35645,
                50045, 70045, 97645, 135645, 188645, 262645, 365645, 508645, 708645, 988645, 1378645, 1928645,
                2688645, 3768645, 5268645, 7368645, 10328645, 14448645, 20248645, 28348645, 39648645, 55548645,
                77848645, 108948645, 152448645, 213448645, 298448645, 418448645, 586448645, 820448645, 1149448645,
                1609448645]
CLASS_XP = [0, 50, 125, 235, 395, 625, 955, 1425, 2095, 3045, 4385, 6275, 8945, 12745, 18045, 25345, 35645,
            50045, 70045, 97645, 135645, 188645, 262645, 365645, 508645, 708645, 988645, 1378645, 1928645,
            2688645, 3768645, 5268645, 7368645, 10328645, 14448645, 20248645, 28348645, 39648645, 55548645]

# ---------------- UI ----------------

class SkyBlockTracker(QWidget):
    def __init__(self):
        super().__init__()
        
        # Load recent players at startup
        load_recent_players()
        
        # Initialize UI
        self.init_ui()
        
        # Update recent players UI after everything is set up
        for i, btn in enumerate(self.recent_buttons):
            if i < len(recent_players):
                btn.setText(f"👤 {recent_players[i]}")
                btn.setVisible(True)
                player_name = recent_players[i]
                btn.clicked.connect(lambda checked, n=player_name: QTimer.singleShot(0, lambda: self.load_recent_player(n)))
    
    def init_ui(self):
        self.setWindowTitle("SkyBlock Dungeon Tracker Premium")
        self.setMinimumSize(1600, 900)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        
        # Main container
        self.container = QFrame(self)
        self.container.setStyleSheet("""
            QFrame {
                background: #0f0f1a;
                border-radius: 15px;
                border: 2px solid #5865f2;
            }
        """)
        
        container_layout = QVBoxLayout(self)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.container)
        
        # Content inside container
        self.setup_content()
    
    def setup_content(self):
        main_layout = QHBoxLayout(self.container)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Global stylesheet
        self.setStyleSheet("""
            QWidget {
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
        """)

        # Sidebar
        self.create_sidebar(main_layout)
        
        # Main content area
        self.create_main_content(main_layout)

    def create_sidebar(self, parent_layout):
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
                        stop:0 rgba(42, 45, 74, 0.8), stop:1 rgba(34, 37, 63, 0.8));
                    color: #b8c5db;
                    border: 2px solid rgba(51, 54, 77, 0.5);
                    border-radius: 8px;
                    padding: 10px;
                    text-align: left;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(61, 64, 102, 0.9), stop:1 rgba(50, 53, 90, 0.9));
                    border: 2px solid rgba(74, 77, 109, 0.7);
                }
                QPushButton:pressed {
                    background: rgba(37, 40, 66, 0.9);
                }
            """)
            scroll_layout.addWidget(btn)
            self.recent_buttons.append(btn)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        self.sidebar.addWidget(scroll)
        
        parent_layout.addWidget(sidebar_container)

    def create_main_content(self, parent_layout):
        content_container = QFrame()
        
        if self.overlay_mode:
            content_container.setStyleSheet("""
                QFrame {
                    background: rgba(26, 26, 46, 0.75);
                    border-radius: 15px;
                    padding: 20px;
                    border: 1px solid rgba(88, 101, 242, 0.3);
                }
            """)
        else:
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

        # Title
        title = QLabel("⚔️ SKYBLOCK DUNGEON TRACKER")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #ffffff;
            padding: 10px;
            letter-spacing: 2px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(title)

        # Search bar
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background: rgba(34, 37, 63, 0.8);
                border-radius: 12px;
                padding: 15px;
                border: 2px solid rgba(45, 49, 82, 0.6);
            }
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setSpacing(15)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter Minecraft Username...")
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(42, 45, 74, 0.8);
                color: #ffffff;
                border: 2px solid rgba(61, 64, 102, 0.6);
                border-radius: 8px;
                padding: 14px 18px;
                font-size: 15px;
                font-weight: 500;
            }
            QLineEdit:focus {
                border: 2px solid rgba(88, 101, 242, 0.8);
                background-color: rgba(45, 49, 82, 0.9);
            }
            QLineEdit::placeholder {
                color: #6b7196;
            }
        """)
        self.name_input.returnPressed.connect(self.check_player_ui)
        
        self.check_btn = QPushButton("🔍 SEARCH")
        self.check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_btn.setFixedWidth(160)
        self.check_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(88, 101, 242, 0.9), stop:1 rgba(71, 82, 196, 0.9));
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 14px 24px;
                font-size: 15px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(106, 117, 245, 1), stop:1 rgba(84, 97, 209, 1));
            }
            QPushButton:pressed {
                background: rgba(71, 82, 196, 1);
            }
            QPushButton:disabled {
                background: rgba(61, 64, 102, 0.6);
                color: #6b7196;
            }
        """)
        self.check_btn.clicked.connect(self.check_player_ui)
        
        search_layout.addWidget(self.name_input)
        search_layout.addWidget(self.check_btn)
        self.content_layout.addWidget(search_frame)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            padding: 12px;
            color: #8b9dc3;
        """)
        self.content_layout.addWidget(self.status_label)

        # Profile selector
        profile_frame = QFrame()
        profile_frame.setStyleSheet("""
            QFrame {
                background: rgba(34, 37, 63, 0.8);
                border-radius: 10px;
                padding: 12px;
                border: 2px solid rgba(45, 49, 82, 0.6);
            }
        """)
        profile_layout = QHBoxLayout(profile_frame)
        
        profile_lbl = QLabel("📊 Profile:")
        profile_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #8b9dc3;")
        
        self.profile_combo = QComboBox()
        self.profile_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.profile_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(42, 45, 74, 0.8);
                color: #ffffff;
                border: 2px solid rgba(61, 64, 102, 0.6);
                border-radius: 6px;
                padding: 10px 15px;
                font-size: 14px;
                font-weight: 500;
                min-width: 200px;
            }
            QComboBox:hover {
                border: 2px solid rgba(74, 77, 109, 0.8);
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
                background-color: rgba(42, 45, 74, 0.95);
                color: #ffffff;
                border: 2px solid rgba(61, 64, 102, 0.8);
                selection-background-color: rgba(61, 64, 102, 0.9);
                padding: 5px;
            }
        """)
        self.profile_combo.currentTextChanged.connect(self.load_profile_ui)
        
        profile_layout.addWidget(profile_lbl)
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addStretch()
        self.content_layout.addWidget(profile_frame)

        # Dungeon Stats - Three Columns
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        self.content_layout.addLayout(stats_layout)

        # Catacombs Card
        self.cata_frame = self.create_stat_card("🏰 CATACOMBS", "#5865f2", stats_layout)
        
        self.cata_info = QLabel("Level: --")
        self.cata_info.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff; line-height: 1.6;")
        self.cata_secrets = QLabel("")
        self.cata_secrets.setStyleSheet("font-size: 14px; color: #d0d5e0; margin-top: 8px;")
        
        self.cata_frame.addWidget(self.cata_info)
        self.cata_frame.addWidget(self.cata_secrets)
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
                    stop:0 rgba(34, 37, 63, 0.9), stop:1 rgba(28, 30, 53, 0.9));
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

        parent_layout.addWidget(content_container)

    def create_stat_card(self, title, accent_color, parent_layout):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(34, 37, 63, 0.9), stop:1 rgba(28, 30, 53, 0.9));
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

    def showEvent(self, event):
        """Called when window is shown - force frameless again"""
        super().showEvent(event)
        
        if self.overlay_mode:
            # Try again when shown
            QTimer.singleShot(50, self.force_frameless)
            QTimer.singleShot(200, self.force_frameless)
    
    # ---------------- Drag Window ----------------
    
    def mouse_press_event(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouse_move_event(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_Escape:
            if self.overlay_mode:
                # Close on ESC in overlay mode
                self.close()
            else:
                # Optional: also close in normal mode, or do nothing
                pass
        else:
            super().keyPressEvent(event)

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
        
        # Combine all catacombs info into one text block
        bar_length = int(percent / 5)
        progress_bar = "█" * bar_length + "░" * (20 - bar_length)
        
        cata_text = f"Level: {exact:.2f}\n"
        cata_text += f"{progress_bar} {percent:.1f}%\n"
        cata_text += f"Until next: {int(needed):,} XP"
        
        self.cata_info.setText(cata_text)
        
        # Secrets
        secrets = dungeon.get('secrets', 0)
        self.cata_secrets.setText(f"🔍 Secrets: {secrets:,}")

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
        
        self.floors_label.setText(floors_text if floors_text else "No floor data")# SkyBlock Dungeon Tracker Premium UI (PyQt6)
# Fixed: Master Mode data, Save recent players, Remove decimals from classes
# Updated: Persistent storage for recent players

import sys
import requests
import json
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QComboBox, QMessageBox, QFrame, QScrollArea)
from PyQt6.QtCore import Qt, QTimer
from collections import deque

HYPIXEL_KEY = "283cd668-95f7-4d83-8929-5e5c8aadfb2b"
RECENT_PLAYERS_FILE = "recent_players.json"

CATACOMBS_XP = [0, 50, 125, 235, 395, 625, 955, 1425, 2095, 3045, 4385, 6275, 8945, 12745, 18045, 25345, 35645,
                50045, 70045, 97645, 135645, 188645, 262645, 365645, 508645, 708645, 988645, 1378645, 1928645,
                2688645, 3768645, 5268645, 7368645, 10328645, 14448645, 20248645, 28348645, 39648645, 55548645,
                77848645, 108948645, 152448645, 213448645, 298448645, 418448645, 586448645, 820448645, 1149448645,
                1609448645]
CLASS_XP = [0, 50, 125, 235, 395, 625, 955, 1425, 2095, 3045, 4385, 6275, 8945, 12745, 18045, 25345, 35645,
            50045, 70045, 97645, 135645, 188645, 262645, 365645, 508645, 708645, 988645, 1378645, 1928645,
            2688645, 3768645, 5268645, 7368645, 10328645, 14448645, 20248645, 28348645, 39648645, 55548645]

recent_players = deque(maxlen=10)
profiles_cache = {}
current_uuid = None

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
        self.setWindowTitle("SkyBlock Dungeon Tracker Premium")
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
        for _ in range(10):  # Changed to 10
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

        # Title
        title = QLabel("⚔️ SKYBLOCK DUNGEON TRACKER")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #ffffff;
            padding: 10px;
            letter-spacing: 2px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(title)

        # Search bar
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background: #22253f;
                border-radius: 12px;
                padding: 15px;
                border: 2px solid #2d3152;
            }
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setSpacing(15)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter Minecraft Username...")
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #2a2d4a;
                color: #ffffff;
                border: 2px solid #3d4066;
                border-radius: 8px;
                padding: 14px 18px;
                font-size: 15px;
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
        self.check_btn.setFixedWidth(160)
        self.check_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5865f2, stop:1 #4752c4);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 14px 24px;
                font-size: 15px;
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

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            padding: 12px;
            color: #8b9dc3;
        """)
        self.content_layout.addWidget(self.status_label)

        # Profile selector
        profile_frame = QFrame()
        profile_frame.setStyleSheet("""
            QFrame {
                background: #22253f;
                border-radius: 10px;
                padding: 12px;
                border: 2px solid #2d3152;
            }
        """)
        profile_layout = QHBoxLayout(profile_frame)
        
        profile_lbl = QLabel("📊 Profile:")
        profile_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #8b9dc3;")
        
        self.profile_combo = QComboBox()
        self.profile_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.profile_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2d4a;
                color: #ffffff;
                border: 2px solid #3d4066;
                border-radius: 6px;
                padding: 10px 15px;
                font-size: 14px;
                font-weight: 500;
                min-width: 200px;
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
        profile_layout.addStretch()
        self.content_layout.addWidget(profile_frame)

        # Dungeon Stats - Three Columns
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        self.content_layout.addLayout(stats_layout)

        # Catacombs Card
        self.cata_frame = self.create_stat_card("🏰 CATACOMBS", "#5865f2", stats_layout)
        
        self.cata_info = QLabel("Level: --")
        self.cata_info.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff; line-height: 1.6;")
        self.cata_secrets = QLabel("")
        self.cata_secrets.setStyleSheet("font-size: 14px; color: #d0d5e0; margin-top: 8px;")
        
        self.cata_frame.addWidget(self.cata_info)
        self.cata_frame.addWidget(self.cata_secrets)
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

        self.main_layout.addWidget(content_container)

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
        
        # Combine all catacombs info into one text block
        bar_length = int(percent / 5)
        progress_bar = "█" * bar_length + "░" * (20 - bar_length)
        
        cata_text = f"Level: {exact:.2f}\n"
        cata_text += f"{progress_bar} {percent:.1f}%\n"
        cata_text += f"Until next: {int(needed):,} XP"
        
        self.cata_info.setText(cata_text)
        
        # Secrets
        secrets = dungeon.get('secrets', 0)
        self.cata_secrets.setText(f"🔍 Secrets: {secrets:,}")

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