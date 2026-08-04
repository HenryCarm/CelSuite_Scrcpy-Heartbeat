import os
import sys

# Setup kivy headless/dummy testing
os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_WINDOW"] = "mock"
os.environ["KIVY_GL_BACKEND"] = "mock"
os.environ["KIVY_AUDIO"] = "mock"

# Add android folder to sys.path so we can import it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'android')))

try:
    from android.main import HeartbeatApp
except Exception as e:
    print(f"Error importing android/main.py: {e}")
    sys.exit(1)

import kivy
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager

def find_buttons(widget, buttons=None):
    if buttons is None:
        buttons = []
    if isinstance(widget, Button) or type(widget).__name__ == "AnimatedButton" or type(widget).__name__ == "GridCard":
        buttons.append(widget)
    for child in widget.children:
        find_buttons(child, buttons)
    return buttons

def test_buttons():
    app = HeartbeatApp()
    
    # We must call build() to get the root widget (ScreenManager)
    root = app.build()
    
    # We need to manually add the screens that are created on the fly
    from android.main import MainScreen, FileTransferScreen, VaultScreen, SettingsScreen, HelpScreen, LogsScreen
    
    # Ensure all screens are instantiated so we can test their buttons
    screens_to_test = [
        MainScreen(name='main'),
        FileTransferScreen(name='transfer'),
        VaultScreen(name='vault'),
        SettingsScreen(name='settings'),
        HelpScreen(name='help'),
        LogsScreen(name='logs')
    ]
    
    print("Testing Android UI Button Callbacks...")
    errors_found = False
    
    for screen in screens_to_test:
        print(f"--- Scanning Screen: {screen.name} ---")
        buttons = find_buttons(screen)
        for btn in buttons:
            btn_name = getattr(btn, 'text', getattr(btn, 'title_text', type(btn).__name__))
            try:
                # If it's a GridCard, we call its custom callback or on_touch_down
                if type(btn).__name__ == "GridCard" and hasattr(btn, 'on_press_callback') and btn.on_press_callback:
                    # Kivy passes the widget instance
                    btn.on_press_callback(btn)
                    print(f"  [OK] GridCard: {btn_name}")
                elif hasattr(btn, 'dispatch') and 'on_press' in btn.events():
                    btn.dispatch('on_press')
                    print(f"  [OK] Button: {btn_name}")
                else:
                    print(f"  [WARN] No standard on_press mechanism for: {btn_name}")
            except Exception as e:
                print(f"  [ERROR] Exception on button '{btn_name}': {e}")
                errors_found = True
                
    if errors_found:
        sys.exit(2)
    else:
        print("All buttons passed basic callback testing.")

if __name__ == "__main__":
    test_buttons()
