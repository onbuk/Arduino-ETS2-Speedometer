import sys
import time
import requests
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QComboBox, QPushButton, 
                            QFileDialog, QCheckBox, QSystemTrayIcon, QMenu, QErrorMessage)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QIcon, QAction
import subprocess
import json
import os
import winreg
import ctypes

class SpeedWorker(QThread):
    speed_update = pyqtSignal(int)
    rpm_update = pyqtSignal(int)
    error_signal = pyqtSignal(str)
    connection_status = pyqtSignal(bool)

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.running = True
        self.arduino = None
        self.connected = False
        self.reconnect_interval = 5  # seconds
        self.last_speed = -1
        self.last_rpm = -1
        self.update_interval = 0.02  # 20ms minimum interval between updates
        self.last_update_time = 0

    def connect_arduino(self):
        try:
            if self.arduino:
                self.arduino.close()
            self.arduino = serial.Serial(port=self.port, 
                                      baudrate=115200, 
                                      timeout=0.1,
                                      write_timeout=0.1)
            self.arduino.reset_input_buffer()
            self.arduino.reset_output_buffer()
            self.connected = True
            self.connection_status.emit(True)
            return True
        except serial.SerialException as e:
            self.error_signal.emit(f"Arduino connection error: {str(e)}")
            self.connected = False
            self.connection_status.emit(False)
            return False

    def run(self):
        last_reconnect_attempt = 0
        session = requests.Session()  # Create a persistent session

        while self.running:
            current_time = time.time()

            # Handle reconnection if needed
            if not self.connected and current_time - last_reconnect_attempt > self.reconnect_interval:
                self.connect_arduino()
                last_reconnect_attempt = current_time

            # Check if enough time has passed since last update
            if current_time - self.last_update_time < self.update_interval:
                time.sleep(0.001)  # Short sleep to prevent CPU hogging
                continue

            if self.connected:
                try:
                    # Use session for better performance
                    response = session.get("http://localhost:25555/api/ets2/telemetry", 
                                        timeout=0.1)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Process speed and RPM...
                        # (the rest of your processing code)
                        
                    self.last_update_time = current_time

                except requests.Timeout:
                    # Timeout occurred, but don't report as an error
                    # You may optionally log or handle retries here
                    continue
                except requests.RequestException as e:
                    # For other request-related errors, emit the error signal
                    self.error_signal.emit(f"Telemetry error: {str(e)}")
                except serial.SerialException as e:
                    self.error_signal.emit(f"Arduino error: {str(e)}")
                    self.connected = False
                    self.connection_status.emit(False)
                except Exception as e:
                    self.error_signal.emit(f"Unexpected error: {str(e)}")

        if self.arduino:
            self.arduino.close()

    def update_port(self, new_port):
        self.port = new_port
        return self.connect_arduino()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.error_dialog = None  # Track the current error dialog
        self.setWindowTitle("Speed & RPM Telemetry")
        self.setFixedSize(400, 400)

        # Initialize system tray
        self.setup_system_tray()

        # Load settings
        self.settings_file = "telemetry_settings.json"
        self.settings = self.load_settings()

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Connection status indicator
        self.connection_status = QLabel("Disconnected")
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_status.setStyleSheet("color: red;")
        layout.addWidget(self.connection_status)

        # Speed display
        self.speed_label = QLabel("0 km/h")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speed_label.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        self.speed_label.setStyleSheet(""" 
            QLabel {
                background-color: #2c3e50;
                color: #ecf0f1;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        layout.addWidget(self.speed_label)

        # RPM display
        self.rpm_label = QLabel("0 RPM")
        self.rpm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rpm_label.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self.rpm_label.setStyleSheet(""" 
            QLabel {
                background-color: #34495e;
                color: #ecf0f1;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        layout.addWidget(self.rpm_label)

        # COM Port selection
        port_layout = QHBoxLayout()
        port_label = QLabel("COM Port:")
        self.port_combo = QComboBox()
        self.refresh_ports()
        self.port_combo.currentTextChanged.connect(self.port_changed)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_ports)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_combo)
        port_layout.addWidget(refresh_button)
        layout.addLayout(port_layout)

        # Add remaining UI elements (telemetry launcher, startup options, etc.)
        self.setup_additional_ui(layout)

        # Start the worker thread
        self.worker = SpeedWorker(self.port_combo.currentText())
        self.worker.speed_update.connect(self.update_speed)
        self.worker.rpm_update.connect(self.update_rpm)
        self.worker.error_signal.connect(self.show_error)
        self.worker.connection_status.connect(self.update_connection_status)
        self.worker.start()

        # Auto-launch telemetry if enabled
        if self.settings.get("auto_launch_telemetry", False):
            self.launch_telemetry()

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))  # You'll need to provide an icon file
        
        # Create tray menu
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quit_application)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # Connect double-click to show window
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def setup_additional_ui(self, layout):
        # Telemetry app launcher
        launcher_layout = QHBoxLayout()
        self.telemetry_path_label = QLabel(self.settings.get("telemetry_path", "No path selected"))
        self.telemetry_path_label.setWordWrap(True)
        browse_button = QPushButton("Browse Telemetry App")
        browse_button.clicked.connect(self.browse_telemetry)
        launch_button = QPushButton("Launch Telemetry")
        launch_button.clicked.connect(self.launch_telemetry)
        launcher_layout.addWidget(self.telemetry_path_label)
        launcher_layout.addWidget(browse_button)
        launcher_layout.addWidget(launch_button)
        layout.addLayout(launcher_layout)

        # Startup options
        startup_layout = QVBoxLayout()
        self.startup_checkbox = QCheckBox("Run at Windows startup")
        self.startup_checkbox.setChecked(self.is_in_startup())
        self.startup_checkbox.stateChanged.connect(self.toggle_startup)
        startup_layout.addWidget(self.startup_checkbox)

        self.auto_launch_checkbox = QCheckBox("Auto-launch telemetry app on startup")
        self.auto_launch_checkbox.setChecked(self.settings.get("auto_launch_telemetry", False))
        self.auto_launch_checkbox.stateChanged.connect(self.toggle_auto_launch)
        startup_layout.addWidget(self.auto_launch_checkbox)

        # Minimize to tray option
        self.minimize_to_tray_checkbox = QCheckBox("Minimize to system tray")
        self.minimize_to_tray_checkbox.setChecked(self.settings.get("minimize_to_tray", True))
        self.minimize_to_tray_checkbox.stateChanged.connect(self.toggle_minimize_to_tray)
        startup_layout.addWidget(self.minimize_to_tray_checkbox)

        layout.addLayout(startup_layout)

    def toggle_auto_launch(self, state):
        self.settings["auto_launch_telemetry"] = bool(state)
        self.save_settings()

    def update_connection_status(self, connected):
        if connected:
            self.connection_status.setText("Connected")
            self.connection_status.setStyleSheet("color: green;")
        else:
            self.connection_status.setText("Disconnected")
            self.connection_status.setStyleSheet("color: red;")

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def toggle_minimize_to_tray(self, state):
        self.settings["minimize_to_tray"] = bool(state)
        self.save_settings()

    def closeEvent(self, event):
        if self.settings.get("minimize_to_tray", True) and self.tray_icon.isVisible():
            event.ignore()
            self.hide()
        else:
            event.accept()

    def port_changed(self):
        new_port = self.port_combo.currentText()
        if self.worker.update_port(new_port):
            self.worker.start()

    def refresh_ports(self):
        self.port_combo.clear()
        ports = self.get_serial_ports()
        self.port_combo.addItems(ports)

    def get_serial_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        return ports

    def update_speed(self, speed):
        self.speed_label.setText(f"{speed} km/h")

    def update_rpm(self, rpm):
        self.rpm_label.setText(f"{rpm} RPM")

    def show_error(self, message):
        # Check if an error dialog is already being displayed
        if self.error_dialog is None or not self.error_dialog.isVisible():
            self.error_dialog = QErrorMessage(self)
            self.error_dialog.finished.connect(self.clear_error_dialog)  # Clear reference when dialog closes
            self.error_dialog.showMessage(message)
        else:
            print(f"Suppressed error: {message}")  # Log suppressed errors for debugging

    def clear_error_dialog(self):
        self.error_dialog = None  # Clear the reference when the dialog is dismissed

    def launch_telemetry(self):
        telemetry_path = self.settings.get("telemetry_path", "")
        if telemetry_path and os.path.exists(telemetry_path):
            try:
                subprocess.Popen([telemetry_path])
            except Exception as e:
                self.show_error(f"Failed to launch telemetry: {str(e)}")
        else:
            self.show_error("Telemetry app path is not set or invalid.")

    def browse_telemetry(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Executable files (*.exe)")
        if file_dialog.exec():
            telemetry_path = file_dialog.selectedFiles()[0]
            self.settings["telemetry_path"] = telemetry_path
            self.telemetry_path_label.setText(telemetry_path)
            self.save_settings()

    def is_in_startup(self):
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run")
            try:
                winreg.QueryValueEx(reg_key, "SpeedRPMApp")
                return True
            except FileNotFoundError:
                return False
        except Exception as e:
            self.show_error(f"Failed to check startup: {str(e)}")
            return False

    def toggle_startup(self, state):
        if state == Qt.CheckState.Checked:
            self.add_to_startup()
        else:
            self.remove_from_startup()

    def add_to_startup(self):
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_WRITE)
            winreg.SetValueEx(reg_key, "SpeedRPMApp", 0, winreg.REG_SZ, sys.executable)
        except Exception as e:
            self.show_error(f"Failed to add to startup: {str(e)}")

    def remove_from_startup(self):
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_WRITE)
            winreg.DeleteValue(reg_key, "SpeedRPMApp")
        except Exception as e:
            self.show_error(f"Failed to remove from startup: {str(e)}")

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                return json.load(f)
        return {}

    def save_settings(self):
        with open(self.settings_file, "w") as f:
            json.dump(self.settings, f)

    def quit_application(self):
        self.worker.running = False
        self.worker.wait()
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


# pyinstaller --name="ETS2 Speedometer Server" --windowed --icon=icon.ico --onefile Speedometer.py