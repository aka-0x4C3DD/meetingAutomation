# Meeting Automator

A cross-platform GUI application that automatically joins your scheduled meetings on Zoom, Google Meet, and Microsoft Teams.

## Features

- Dark mode GUI built with PyQt6
- Automatic meeting joining for:
  - Zoom
  - Google Meet
  - Microsoft Teams
- Calendar import support (.ics files)
- Secure credential storage
- Background process for meeting monitoring
- Cross-platform support (Windows and Linux)
- System tray integration
- Standalone executable available for Windows

## Installation

### Method 1: Using the Executable (Windows)

1. Download the latest release from the releases page
2. Extract the zip file
3. Run `MeetingAutomator.exe`

### Method 2: Building from Source (Windows)

1. Clone this repository:
```bash
git clone https://github.com/yourusername/meeting-automator.git
cd meeting-automator
```

2. Run the installation script:
```bash
install.bat
```

The script will:
- Check Python installation
- Install all required dependencies
- Build the executable
- Clean up temporary files
- Place the final executable in the `dist` folder

### Method 3: Manual Installation (Linux/macOS)

1. Clone this repository:
```bash
git clone https://github.com/yourusername/meeting-automator.git
cd meeting-automator
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Linux/macOS
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Usage

1. Start the application by either:
   - Running the executable from the `dist` folder (Windows)
   - Or running `python main.py` if installed manually

2. Configure your meeting platform credentials:
   - Go to the Settings tab
   - Enter your credentials for each platform you use
   - Credentials are stored securely using the system keyring

3. Add meetings either by:
   - Importing a calendar file (.ics)
   - Manually adding meeting details
   - The application will automatically detect the platform from meeting links

4. The application will run in the background and automatically join meetings at the scheduled time

## Security

- Credentials are stored securely using the system's keyring
- No sensitive information is stored in plain text
- All data is stored locally on your machine

## Requirements

If building from source or running manually:
- Python 3.8 or higher
- Chrome/Chromium browser
- System requirements for video conferencing:
  - Webcam (optional)
  - Microphone
  - Stable internet connection

If using the executable:
- Chrome/Chromium browser
- Webcam (optional)
- Microphone
- Stable internet connection

## Troubleshooting

1. If the installation fails:
   - Make sure Python 3.8 or higher is installed
   - Check your internet connection
   - Run the installer as administrator
   - Look for error messages in the console

2. If the application fails to join meetings:
   - Check your internet connection
   - Verify your credentials are correct
   - Ensure Chrome/Chromium is installed
   - Check if the meeting link/ID is valid

3. If the application doesn't start:
   - Verify Chrome/Chromium is installed
   - Check for any antivirus blocking
   - Try running as administrator
   - Check the logs in the application directory

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 