<!-- # <img src="https://img.shields.io/badge/Meeting-Automator-1abc9c?style=for-the-badge&logo=zoom&logoColor=white" alt="Meeting Automator" height="40"> -->

<div align="center">

# Meeting Automator

![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
![PyQt](https://img.shields.io/badge/UI-PyQt6-41CD52)
<!-- ![Status](https://img.shields.io/badge/status-active-brightgreen) --> </br>
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Code Size](https://img.shields.io/github/languages/code-size/aka-0x4C3DD/meetingAutomation.svg)]()
[![Last Commit](https://img.shields.io/github/last-commit/aka-0x4C3DD/meetingAutomation.svg)]()
[![Issues](https://img.shields.io/github/issues/aka-0x4C3DD/meetingAutomation.svg)]()

**Never miss a meeting again! Automatically join your scheduled video calls with ease.**

[Features](#-features) • 
[Screenshots](#-screenshots) • 
[Installation](#-installation) • 
[Usage](#-usage) • 
[FAQ](#-faq) • 
[Contributing](#-contributing) • 
[License](#-license)

</div>

## 🚀 Features

✅ <b>Automatic meeting joining</b> for Zoom, Google Meet, and Microsoft Teams</br>
      ✅ <b>Calendar import support</b> (.ics files)</br>
      ✅ <b>Sleek dark mode UI</b> built with PyQt6</br>
      ✅ <b>System tray integration</b> - runs quietly in the background</br>
✅ <b>Secure credential storage</b> using system keyring</br>
      ✅ <b>Cross-platform compatibility</b> (Windows & Linux)</br>
      ✅ <b>Standalone executables</b> available for both Windows and Linux</br>
      ✅ <b>Smart meeting detection</b> from URLs & calendar data</br>

<!--<table>
  <tr>
    <td width = "50%">
      ✅ <b>Automatic meeting joining</b> for Zoom, Google Meet, and Microsoft Teams</br>
      ✅ <b>Calendar import support</b> (.ics files)</br>
      ✅ <b>Sleek dark mode UI</b> built with PyQt6</br>
      ✅ <b>System tray integration</b> - runs quietly in the background</br>
    </td>
    <td  width = "50%">
      ✅ <b>Secure credential storage</b> using system keyring</br>
      ✅ <b>Cross-platform compatibility</b> (Windows & Linux)</br>
      ✅ <b>Standalone executable</b> available for Windows</br>
      ✅ <b>Smart meeting detection</b> from URLs & calendar data</br>
    </td>
  </tr>
</table> -->

## 📸 Screenshots

*Screenshots coming soon*

## 📥 Installation

<details>
<summary><b>Method 1: Download Executable (Windows & Linux) - Recommended ⭐</b></summary>

1. Download the latest release from the [Releases](https://github.com/yourusername/meeting-automator/releases) page
2. Extract the zip file
3. Run `MeetingAutomator.exe` on Windows or `MeetingAutomator` on Linux
</details>

<details>
<summary><b>Method 2: Automated Build (Windows & Linux)</b></summary>

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/meeting-automator.git
cd meeting-automator

# 2. Run the installation script
install.bat  # On Windows
./install.sh  # On Linux
```

The script handles:
- Python dependency verification
- Required package installation
- Executable building
- Cleanup of temporary files

The final executable will be placed in the `dist` folder.
</details>

<details>
<summary><b>Method 3: Manual Installation (All Platforms)</b></summary>

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/meeting-automator.git
cd meeting-automator

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Linux/macOS
venv\Scripts\activate     # On Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python main.py
```
</details>

## 🔧 System Requirements

<table>
  <tr>
    <th>For Executable</th>
    <th>For Source Build</th>
  </tr>
  <tr>
    <td>
      <ul>
        <li>Windows 10/11 or Linux</li>
        <li>Chrome/Chromium browser</li>
        <li>Webcam (optional)</li>
        <li>Microphone</li>
        <li>Internet connection</li>
      </ul>
    </td>
    <td>
      <ul>
        <li>Python 3.8 or higher</li>
        <li>Chrome/Chromium browser</li>
        <li>PyQt6</li>
        <!-- <li>Webcam (optional)</li>
        <li>Microphone</li> -->
        <li>Internet connection</li>
      </ul>
    </td>
  </tr>
</table>

## 📝 Usage

### Quick Start Guide

1. **Launch the application**
   - On Windows: Run the executable or `python main.py`
   - On Linux: Run the executable or `python main.py`

2. **Configure your meeting platforms**
   - Navigate to the Settings tab
   - Enter your credentials for each service you use
   - All credentials are securely stored in your system's keyring

3. **Add meetings**
   - Import calendar files (.ics)
   - Or manually add meeting details
   - Meeting platform is automatically detected from links

4. **Let it run**
   - The app minimizes to your system tray
   - Meetings are automatically joined at the scheduled time
   - Get notifications before each meeting

## 🔒 Security

- **Zero plain text storage** - All credentials are secured using your system's keyring
- **Local-only data** - No data is sent to remote servers
- **Privacy focused** - Only accesses what's needed to join your meetings

## ❓ FAQ

<details>
<summary><b>How does the automatic meeting joining work?</b></summary>
The application uses browser automation to open meeting links and join the meeting rooms at the scheduled time, handling authentication and join steps automatically.
</details>

<details>
<summary><b>Is my data sent anywhere?</b></summary>
No. All your meeting data and credentials are stored locally on your machine. Credentials are encrypted using your system's keyring service.
</details>

<details>
<summary><b>Troubleshooting Installation Issues</b></summary>

- Ensure Python 3.8+ is installed and in your PATH
- Verify your internet connection
- Try running the installer as administrator on Windows or with sudo on Linux
- Check console output for specific error messages
</details>

<details>
<summary><b>Troubleshooting Meeting Join Issues</b></summary>

- Verify your internet connection
- Check that your credentials are correct
- Ensure Chrome/Chromium is installed and updated
- Verify the meeting link/ID format is valid
</details>

<details>
<summary><b>Application Won't Start</b></summary>

- Verify Chrome/Chromium is installed
- Check for antivirus/firewall software blocking the application
- Try running as administrator on Windows or with elevated privileges on Linux
- Check log files in the application directory
</details>

## 🤝 Contributing

Contributions are welcome and appreciated! Here's how you can help:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <sub>Built with ❤️ by open source contributors</sub>
</div> 
