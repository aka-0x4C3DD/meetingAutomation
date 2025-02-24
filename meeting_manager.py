import datetime
from typing import Dict, List, Optional
import icalendar
from dataclasses import dataclass
import schedule
import time
import threading
from enum import Enum
import keyring
import json
import os
import re
from pathlib import Path
from platform_handlers import get_handler, PlatformType

@dataclass
class Meeting:
    id: str
    title: str
    platform: PlatformType
    start_time: datetime.datetime
    duration: datetime.timedelta
    url: Optional[str] = None
    meeting_id: Optional[str] = None
    password: Optional[str] = None
    recurring: bool = False
    recurrence_pattern: Optional[str] = None
    required_email: Optional[str] = None

class MeetingManager:
    def __init__(self):
        self.meetings: Dict[str, Meeting] = {}
        self.scheduler_thread = None
        self.running = False
        
        # Create data directory if it doesn't exist
        self.data_dir = Path.home() / ".meeting_automator"
        self.data_dir.mkdir(exist_ok=True)
        self.meetings_file = self.data_dir / "meetings.json"
        
        # Load saved meetings
        self.load_meetings()
    
    def add_meeting(self, meeting: Meeting) -> bool:
        """Add a new meeting to the manager."""
        if meeting.id in self.meetings:
            return False
        self.meetings[meeting.id] = meeting
        self.save_meetings()
        self.schedule_meeting(meeting)
        return True
    
    def remove_meeting(self, meeting_id: str) -> bool:
        """Remove a meeting from the manager."""
        if meeting_id in self.meetings:
            del self.meetings[meeting_id]
            self.save_meetings()
            return True
        return False
    
    def import_ics(self, ics_file: str) -> List[Meeting]:
        """Import meetings from an ICS file."""
        imported_meetings = []
        with open(ics_file, 'rb') as f:
            cal = icalendar.Calendar.from_ical(f.read())
            
            for component in cal.walk():
                if component.name == "VEVENT":
                    # Extract meeting information
                    start = component.get('dtstart').dt
                    end = component.get('dtend').dt
                    summary = str(component.get('summary'))
                    description = str(component.get('description', ''))
                    
                    # Try to determine platform and extract meeting details
                    platform = self._detect_platform(description, summary)
                    url = self._extract_url(description)
                    meeting_id, password = self._extract_meeting_details(description, platform)
                    
                    if platform:
                        meeting = Meeting(
                            id=str(component.get('uid')),
                            title=summary,
                            platform=platform,
                            start_time=start,
                            duration=end - start,
                            url=url,
                            meeting_id=meeting_id,
                            password=password,
                            # Handle recurring meetings
                            recurring='RRULE' in component,
                            recurrence_pattern=str(component.get('rrule', ''))
                        )
                        
                        self.add_meeting(meeting)
                        imported_meetings.append(meeting)
        
        return imported_meetings
    
    def _detect_platform(self, description: str, summary: str) -> Optional[PlatformType]:
        """Detect meeting platform from description and summary."""
        combined_text = (description + " " + summary).lower()
        
        if "zoom" in combined_text or "zoom.us" in combined_text:
            return PlatformType.ZOOM
        elif "teams" in combined_text or "microsoft teams" in combined_text:
            return PlatformType.TEAMS
        elif "meet.google" in combined_text or "google meet" in combined_text:
            return PlatformType.GOOGLE_MEET
        
        # Try to detect from URLs
        if self._extract_url(description):
            url = self._extract_url(description)
            if "zoom.us" in url:
                return PlatformType.ZOOM
            elif "teams.microsoft" in url:
                return PlatformType.TEAMS
            elif "meet.google" in url:
                return PlatformType.GOOGLE_MEET
        
        return None
    
    def _extract_url(self, description: str) -> Optional[str]:
        """Extract meeting URL from description."""
        url_pattern = r'https?://\S+'
        match = re.search(url_pattern, description)
        return match.group(0) if match else None
    
    def _extract_meeting_details(self, description: str, platform: PlatformType) -> tuple:
        """Extract meeting ID and password based on platform."""
        meeting_id = None
        password = None
        
        if platform == PlatformType.ZOOM:
            # Extract Zoom meeting ID
            id_pattern = r'Meeting ID:?\s*(\d{9,11})'
            id_match = re.search(id_pattern, description)
            if id_match:
                meeting_id = id_match.group(1)
            
            # Extract Zoom password
            pwd_pattern = r'Passcode:?\s*(\w+)'
            pwd_match = re.search(pwd_pattern, description)
            if pwd_match:
                password = pwd_match.group(1)
                
        elif platform == PlatformType.GOOGLE_MEET:
            # Extract Google Meet code from URL or description
            if "meet.google.com/" in description:
                code_pattern = r'meet.google.com/([a-z-]+)'
                code_match = re.search(code_pattern, description)
                if code_match:
                    meeting_id = code_match.group(1)
        
        return meeting_id, password
    
    def schedule_meeting(self, meeting: Meeting):
        """Schedule a meeting to be joined at the appropriate time."""
        # Schedule the meeting 1 minute before start to prepare
        join_time = meeting.start_time - datetime.timedelta(minutes=1)
        
        # If the meeting is in the past, don't schedule it
        if join_time < datetime.datetime.now():
            return
        
        # Format time for schedule library
        time_str = join_time.strftime("%H:%M")
        date_str = join_time.strftime("%Y-%m-%d")
        
        # Schedule the join task
        schedule.every().day.at(time_str).do(
            self.join_meeting, 
            meeting_id=meeting.id
        ).tag(meeting.id)
    
    def join_meeting(self, meeting_id: str):
        """Join a scheduled meeting."""
        if meeting_id in self.meetings:
            meeting = self.meetings[meeting_id]
            
            try:
                # Get the appropriate handler for the platform
                handler = get_handler(meeting.platform)
                
                # Join the meeting
                success = handler.join_meeting(
                    url=meeting.url,
                    meeting_id=meeting.meeting_id,
                    password=meeting.password,
                    required_email=meeting.required_email
                )
                
                if success:
                    print(f"Successfully joined meeting: {meeting.title}")
                else:
                    print(f"Failed to join meeting: {meeting.title}")
                
            except Exception as e:
                print(f"Error joining meeting: {str(e)}")
    
    def start_scheduler(self):
        """Start the scheduler thread."""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
    
    def stop_scheduler(self):
        """Stop the scheduler thread."""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=1)
    
    def _scheduler_loop(self):
        """Main loop for the scheduler thread."""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def save_meetings(self):
        """Save meetings to disk."""
        meetings_data = {}
        
        for meeting_id, meeting in self.meetings.items():
            meetings_data[meeting_id] = {
                "id": meeting.id,
                "title": meeting.title,
                "platform": meeting.platform.value if isinstance(meeting.platform, Enum) else meeting.platform,
                "start_time": meeting.start_time.isoformat(),
                "duration": meeting.duration.total_seconds(),
                "url": meeting.url,
                "meeting_id": meeting.meeting_id,
                "password": meeting.password,
                "recurring": meeting.recurring,
                "recurrence_pattern": meeting.recurrence_pattern,
                "required_email": meeting.required_email
            }
        
        with open(self.meetings_file, 'w') as f:
            json.dump(meetings_data, f, indent=2)
    
    def load_meetings(self):
        """Load meetings from disk."""
        if not self.meetings_file.exists():
            return
        
        try:
            with open(self.meetings_file, 'r') as f:
                meetings_data = json.load(f)
            
            for meeting_id, data in meetings_data.items():
                platform_value = data.get("platform")
                # Convert platform string to enum
                if isinstance(platform_value, str):
                    platform = getattr(PlatformType, platform_value.upper()) if hasattr(PlatformType, platform_value.upper()) else platform_value
                else:
                    platform = platform_value
                
                meeting = Meeting(
                    id=data.get("id"),
                    title=data.get("title"),
                    platform=platform,
                    start_time=datetime.datetime.fromisoformat(data.get("start_time")),
                    duration=datetime.timedelta(seconds=data.get("duration")),
                    url=data.get("url"),
                    meeting_id=data.get("meeting_id"),
                    password=data.get("password"),
                    recurring=data.get("recurring", False),
                    recurrence_pattern=data.get("recurrence_pattern"),
                    required_email=data.get("required_email")
                )
                
                self.meetings[meeting_id] = meeting
                
                # Schedule recurring meetings or future meetings
                if meeting.recurring or meeting.start_time > datetime.datetime.now():
                    self.schedule_meeting(meeting)
                    
        except Exception as e:
            print(f"Error loading meetings: {str(e)}")
            # If there's an error, start with an empty meeting list
            self.meetings = {} 