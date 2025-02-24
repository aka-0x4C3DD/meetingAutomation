import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, 
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QDateTimeEdit, QComboBox, QTableWidget, 
    QTableWidgetItem, QFileDialog, QSystemTrayIcon, 
    QMenu, QMessageBox, QCheckBox, QFormLayout, QGroupBox,
    QRadioButton, QButtonGroup, QHeaderView, QSpinBox
)
from PyQt6.QtCore import Qt, QDateTime, QTimer, QSize
from PyQt6.QtGui import QIcon, QAction, QPalette, QColor
import darkdetect
import keyring
from meeting_manager import MeetingManager, Meeting
from platform_handlers import PlatformType, get_handler, ZoomHandler, TeamsHandler, GoogleMeetHandler, BrowserType
import datetime
import uuid

class MeetingAutomator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Meeting Automator")
        self.setMinimumSize(800, 600)
        
        # Initialize meeting manager
        self.meeting_manager = MeetingManager()
        
        # Set up the main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Add tabs
        tabs.addTab(self.create_dashboard_tab(), "Dashboard")
        tabs.addTab(self.create_meetings_tab(), "Meetings")
        tabs.addTab(self.create_settings_tab(), "Settings")
        
        # Set up system tray
        self.setup_system_tray()
        
        # Apply dark theme
        self.apply_dark_theme()
        
        # Start the meeting scheduler
        self.meeting_manager.start_scheduler()
    
    def create_dashboard_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create table for upcoming meetings
        self.meetings_table = QTableWidget()
        self.meetings_table.setColumnCount(4)
        self.meetings_table.setHorizontalHeaderLabels(["Title", "Platform", "Start Time", "Duration"])
        self.meetings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.meetings_table)
        
        # Update meetings display
        self.update_meetings_display()
        
        # Set up timer to update display every minute
        timer = QTimer(self)
        timer.timeout.connect(self.update_meetings_display)
        timer.start(60000)  # Update every minute
        
        return widget
    
    def create_meetings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Input method selection group with horizontal radio buttons
        method_group = QGroupBox("Meeting Input Method")
        method_layout = QHBoxLayout(method_group)  # Changed to QHBoxLayout for horizontal layout
        method_layout.setSpacing(10)
        
        self.input_method_group = QButtonGroup()
        self.url_radio = QRadioButton("Join via URL")
        self.id_radio = QRadioButton("Join via Meeting ID")
        self.ics_radio = QRadioButton("Import from Calendar")
        
        self.input_method_group.addButton(self.url_radio)
        self.input_method_group.addButton(self.id_radio)
        self.input_method_group.addButton(self.ics_radio)
        
        method_layout.addWidget(self.url_radio)
        method_layout.addWidget(self.id_radio)
        method_layout.addWidget(self.ics_radio)
        method_layout.addStretch()  # Add stretch to keep buttons left-aligned
        method_group.setLayout(method_layout)
        layout.addWidget(method_group)
        
        # Meeting details group
        details_group = QGroupBox("Meeting Details")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter meeting title")
        form_layout.addRow("Title:", self.title_input)
        
        # Platform dropdown (always visible)
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["Zoom", "Google Meet", "Microsoft Teams"])
        form_layout.addRow("Platform:", self.platform_combo)
        
        # DateTime picker
        self.datetime_picker = QDateTimeEdit()
        self.datetime_picker.setDateTime(QDateTime.currentDateTime())
        self.datetime_picker.setCalendarPopup(True)
        self.datetime_picker.setDisplayFormat("yyyy-MM-dd hh:mm")
        self.datetime_picker.setMinimumDateTime(QDateTime.currentDateTime())
        form_layout.addRow("Meeting Time:", self.datetime_picker)
        
        # Duration spinner
        self.duration_spinner = QSpinBox()
        self.duration_spinner.setRange(1, 480)
        self.duration_spinner.setValue(60)
        self.duration_spinner.setSuffix(" minutes")
        form_layout.addRow("Duration:", self.duration_spinner)
        
        # URL input with auto-detection
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter meeting URL")
        self.url_input.textChanged.connect(self.detect_platform_from_url)
        self.url_label = QLabel("Meeting URL:")
        form_layout.addRow(self.url_label, self.url_input)
        
        # Meeting ID and Password
        self.meeting_id_input = QLineEdit()
        self.meeting_id_input.setPlaceholderText("Enter meeting ID")
        self.meeting_id_label = QLabel("Meeting ID:")
        form_layout.addRow(self.meeting_id_label, self.meeting_id_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter meeting password (optional)")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_label = QLabel("Password:")
        form_layout.addRow(self.password_label, self.password_input)
        
        details_group.setLayout(form_layout)
        layout.addWidget(details_group)
        
        # Action buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        
        # Import calendar button
        self.import_btn = QPushButton("Import Calendar (.ics)")
        self.import_btn.clicked.connect(self.import_calendar)
        button_layout.addWidget(self.import_btn)
        
        # Add meeting button
        add_btn = QPushButton("Add Meeting")
        add_btn.clicked.connect(self.add_meeting_manually)
        button_layout.addWidget(add_btn)
        
        layout.addLayout(button_layout)
        
        # Connect signals
        self.input_method_group.buttonClicked.connect(self.toggle_input_fields)
        self.url_radio.setChecked(True)  # Default to URL input
        self.toggle_input_fields(self.url_radio)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        return widget
    
    def create_settings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Google Account Section (for Meet and Zoom SSO)
        google_group = QGroupBox("Google Account Settings")
        google_layout = QFormLayout()
        
        self.google_email = QLineEdit()
        self.google_password = QLineEdit()
        self.google_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        google_layout.addRow("Email:", self.google_email)
        google_layout.addRow("Password:", self.google_password)
        
        google_save = QPushButton("Save Google Credentials")
        google_save.clicked.connect(lambda: self.save_credentials("google"))
        google_layout.addRow(google_save)
        
        # Add help text for Google account usage
        help_label = QLabel("Used for Google Meet and Zoom SSO login")
        help_label.setStyleSheet("color: #808080; font-size: 10pt;")
        google_layout.addRow(help_label)
        
        google_group.setLayout(google_layout)
        layout.addWidget(google_group)
        
        # Zoom Section (for non-SSO accounts)
        zoom_group = QGroupBox("Zoom Settings (Optional)")
        zoom_layout = QFormLayout()
        
        self.zoom_username = QLineEdit()
        self.zoom_password = QLineEdit()
        self.zoom_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        zoom_layout.addRow("Email:", self.zoom_username)
        zoom_layout.addRow("Password:", self.zoom_password)
        
        zoom_save = QPushButton("Save Zoom Credentials")
        zoom_save.clicked.connect(lambda: self.save_credentials("zoom"))
        zoom_layout.addRow(zoom_save)
        
        # Add help text for Zoom credentials
        zoom_help = QLabel("Only required for non-SSO Zoom accounts")
        zoom_help.setStyleSheet("color: #808080; font-size: 10pt;")
        zoom_layout.addRow(zoom_help)
        
        zoom_group.setLayout(zoom_layout)
        layout.addWidget(zoom_group)
        
        # Teams Section
        teams_group = QGroupBox("Microsoft Teams Settings")
        teams_layout = QFormLayout()
        
        self.teams_email = QLineEdit()
        self.teams_password = QLineEdit()
        self.teams_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        teams_layout.addRow("Email:", self.teams_email)
        teams_layout.addRow("Password:", self.teams_password)
        
        teams_save = QPushButton("Save Teams Credentials")
        teams_save.clicked.connect(lambda: self.save_credentials("teams"))
        teams_layout.addRow(teams_save)
        
        teams_group.setLayout(teams_layout)
        layout.addWidget(teams_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        return widget
    
    def setup_system_tray(self):
        self.tray = QSystemTrayIcon(self)
        # TODO: Add proper icon
        self.tray.setVisible(True)
    
    def apply_dark_theme(self):
        app = QApplication.instance()
        palette = QPalette()
        
        # Set dark theme colors
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        
        app.setPalette(palette)
    
    def update_meetings_display(self):
        """Update the meetings table in the dashboard."""
        self.meetings_table.setRowCount(0)
        current_time = QDateTime.currentDateTime()
        
        for meeting in self.meeting_manager.meetings.values():
            if meeting.start_time >= current_time.toPyDateTime():
                row = self.meetings_table.rowCount()
                self.meetings_table.insertRow(row)
                
                self.meetings_table.setItem(row, 0, QTableWidgetItem(meeting.title))
                self.meetings_table.setItem(row, 1, QTableWidgetItem(meeting.platform.value))
                self.meetings_table.setItem(row, 2, QTableWidgetItem(meeting.start_time.strftime("%Y-%m-%d %H:%M")))
                self.meetings_table.setItem(row, 3, QTableWidgetItem(str(meeting.duration)))
    
    def detect_platform_from_url(self, url):
        """Auto-detect platform from URL and set the combo box."""
        if not url:
            return None
            
        url = url.lower()
        if "zoom.us" in url:
            self.platform_combo.setCurrentText("Zoom")
            return "Zoom"
        elif "meet.google" in url:
            self.platform_combo.setCurrentText("Google Meet")
            return "Google Meet"
        elif "teams.microsoft" in url:
            self.platform_combo.setCurrentText("Microsoft Teams")
            return "Microsoft Teams"
        return None

    def toggle_input_fields(self, button):
        """Enable/disable and show/hide input fields based on selected input method."""
        # Common fields always visible but enabled/disabled appropriately
        self.title_input.setEnabled(True)
        self.datetime_picker.setEnabled(True)
        self.duration_spinner.setEnabled(True)
        self.platform_combo.setEnabled(True)  # Platform combo always enabled
        
        # Reset all fields' visibility and enabled state
        fields = [
            (self.url_label, self.url_input),
            (self.meeting_id_label, self.meeting_id_input),
            (self.password_label, self.password_input)
        ]
        
        # Set initial grey-out state
        for label, input_widget in fields:
            label.setVisible(True)  # Keep all labels visible
            input_widget.setVisible(True)  # Keep all inputs visible
            if button == self.url_radio:
                enabled = label == self.url_label
            elif button == self.id_radio:
                enabled = label in [self.meeting_id_label, self.password_label]
            else:  # ics_radio
                enabled = False
            
            input_widget.setEnabled(enabled)
            if enabled:
                label.setStyleSheet("")  # Reset to default style
            else:
                label.setStyleSheet("color: #808080;")  # Set grey color using stylesheet
                # Clear disabled fields
                if isinstance(input_widget, QLineEdit):
                    input_widget.clear()
        
        # Import button only enabled for ICS
        self.import_btn.setEnabled(button == self.ics_radio)

    def import_calendar(self):
        """Import meetings from an ICS file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Import Calendar",
            "",
            "Calendar Files (*.ics);;All Files (*)"
        )
        
        if file_name:
            try:
                imported_meetings = self.meeting_manager.import_ics(file_name)
                
                # Auto-populate fields with first meeting if available
                if imported_meetings:
                    meeting = imported_meetings[0]
                    self.title_input.setText(meeting.title)
                    self.datetime_picker.setDateTime(meeting.start_time)
                    self.duration_spinner.setValue(int(meeting.duration.total_seconds() / 60))
                    if meeting.url:
                        self.url_radio.setChecked(True)
                        self.url_input.setText(meeting.url)
                        self.detect_platform_from_url(meeting.url)
                    elif meeting.meeting_id:
                        self.id_radio.setChecked(True)
                        self.meeting_id_input.setText(meeting.meeting_id)
                        self.password_input.setText(meeting.password or "")
                        self.platform_combo.setCurrentText(meeting.platform.value.title())
                
                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"Successfully imported {len(imported_meetings)} meetings."
                )
                self.update_meetings_display()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Import Error",
                    f"Error importing calendar: {str(e)}"
                )
    
    def add_meeting_manually(self):
        """Add a meeting manually from the form."""
        try:
            # Validate required fields
            if not self.title_input.text().strip():
                raise ValueError("Meeting title is required")

            if self.url_radio.isChecked() and not self.url_input.text().strip():
                raise ValueError("Meeting URL is required")

            if self.id_radio.isChecked():
                if not self.meeting_id_input.text().strip():
                    raise ValueError("Meeting ID is required")
                if not self.platform_combo.currentText():
                    raise ValueError("Platform selection is required")

            # Determine platform based on input method
            if self.url_radio.isChecked():
                platform_text = self.detect_platform_from_url(self.url_input.text())
                if not platform_text:
                    raise ValueError("Could not detect platform from URL. Please check the URL is correct.")
            else:
                platform_text = self.platform_combo.currentText()
            
            # Convert platform text to enum
            platform_map = {
                "Zoom": PlatformType.ZOOM,
                "Google Meet": PlatformType.GOOGLE_MEET,
                "Microsoft Teams": PlatformType.TEAMS
            }
            
            platform = platform_map.get(platform_text)
            if not platform:
                # Try converting directly (for backwards compatibility)
                try:
                    platform = PlatformType(platform_text.lower().replace(" ", "_"))
                except ValueError:
                    raise ValueError(f"Unknown platform: {platform_text}")
            
            meeting = Meeting(
                id=str(uuid.uuid4()),  # Use UUID for unique IDs
                title=self.title_input.text().strip(),
                platform=platform,
                start_time=self.datetime_picker.dateTime().toPyDateTime(),
                duration=datetime.timedelta(minutes=self.duration_spinner.value()),
                url=self.url_input.text().strip() if self.url_radio.isChecked() else None,
                meeting_id=self.meeting_id_input.text().strip() if self.id_radio.isChecked() else None,
                password=self.password_input.text() if self.id_radio.isChecked() else None
            )
            
            if self.meeting_manager.add_meeting(meeting):
                QMessageBox.information(
                    self,
                    "Success",
                    "Meeting added successfully."
                )
                self.clear_form()  # Clear form after successful addition
                self.update_meetings_display()
            else:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "Meeting already exists."
                )
        except ValueError as e:
            QMessageBox.warning(
                self,
                "Validation Error",
                str(e)
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error adding meeting: {str(e)}"
            )

    def clear_form(self):
        """Clear all form fields."""
        self.title_input.clear()
        self.url_input.clear()
        self.meeting_id_input.clear()
        self.password_input.clear()
        self.datetime_picker.setDateTime(QDateTime.currentDateTime())
        self.duration_spinner.setValue(60)

    def save_credentials(self, platform: str):
        """Save platform credentials securely."""
        try:
            handler = get_handler(platform)
            
            if platform == "zoom":
                handler.set_credentials(
                    self.zoom_username.text(),
                    self.zoom_password.text()
                )
            elif platform == "google":
                handler.set_credentials(
                    self.google_email.text(),
                    self.google_password.text()
                )
            elif platform == "teams":
                handler.set_credentials(
                    self.teams_email.text(),
                    self.teams_password.text()
                )
            
            QMessageBox.information(
                self,
                "Success",
                f"Credentials saved for {platform}."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error saving credentials: {str(e)}"
            )
    
    def closeEvent(self, event):
        """Handle application closure."""
        self.meeting_manager.stop_scheduler()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Use Fusion style for better dark theme support
    
    window = MeetingAutomator()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 