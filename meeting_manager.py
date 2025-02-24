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
from pathlib import Path

class PlatformType(Enum):
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
    TEAMS = "teams"

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
                    if platform:
                        meeting = Meeting(
                            id=str(hash(f"{summary}{start}")),
                            title=summary,
                            platform=platform,
                            start_time=start,
                            duration=end - start,
                            url=self._extract_url(description)
                        )
                        self.add_meeting(meeting)
                        imported_meetings.append(meeting)
        
        return imported_meetings
    
    def _detect_platform(self, description: str, summary: str) -> Optional[PlatformType]:
        """Detect meeting platform from description and summary."""
        description = description.lower()
        summary = summary.lower()
        
        if any(x in description or x in summary for x in ["zoom"]):
            return PlatformType.ZOOM
        elif any(x in description or x in summary for x in ["meet.google", "google meet"]):
            return PlatformType.GOOGLE_MEET
        elif any(x in description or x in summary for x in ["teams", "microsoft teams"]):
            return PlatformType.TEAMS
        return None
    
    def _extract_url(self, description: str) -> Optional[str]:
        """Extract meeting URL from description."""
        # Simple URL extraction - can be enhanced with regex
        words = description.split()
        for word in words:
            if word.startswith(("https://", "http://")):
                return word
        return None
    
    def schedule_meeting(self, meeting: Meeting):
        """Schedule a meeting for automatic joining."""
        # Schedule the meeting 1 minute before start time
        schedule_time = meeting.start_time - datetime.timedelta(minutes=1)
        schedule.every().day.at(schedule_time.strftime("%H:%M")).do(
            self.join_meeting, meeting.id
        ).tag(meeting.id)
    
    def join_meeting(self, meeting_id: str):
        """Join a scheduled meeting."""
        if meeting_id not in self.meetings:
            return
        
        meeting = self.meetings[meeting_id]
        # TODO: Implement platform-specific joining logic
        print(f"Joining meeting: {meeting.title} on {meeting.platform.value}")
    
    def start_scheduler(self):
        """Start the scheduling background thread."""
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
    
    def stop_scheduler(self):
        """Stop the scheduling background thread."""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
    
    def _scheduler_loop(self):
        """Background thread loop for checking scheduled meetings."""
        while self.running:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    
    def save_meetings(self):
        """Save meetings to disk."""
        meetings_data = {}
        for meeting_id, meeting in self.meetings.items():
            meetings_data[meeting_id] = {
                "title": meeting.title,
                "platform": meeting.platform.value,
                "start_time": meeting.start_time.isoformat(),
                "duration": str(meeting.duration),
                "url": meeting.url,
                "meeting_id": meeting.meeting_id,
                "password": meeting.password,
                "recurring": meeting.recurring,
                "recurrence_pattern": meeting.recurrence_pattern
            }
        
        with open(self.meetings_file, 'w') as f:
            json.dump(meetings_data, f)
    
    def load_meetings(self):
        """Load meetings from disk."""
        if not self.meetings_file.exists():
            return
        
        with open(self.meetings_file, 'r') as f:
            meetings_data = json.load(f)
            
        for meeting_id, data in meetings_data.items():
            meeting = Meeting(
                id=meeting_id,
                title=data["title"],
                platform=PlatformType(data["platform"]),
                start_time=datetime.datetime.fromisoformat(data["start_time"]),
                duration=datetime.timedelta.fromisoformat(data["duration"]),
                url=data["url"],
                meeting_id=data["meeting_id"],
                password=data["password"],
                recurring=data["recurring"],
                recurrence_pattern=data["recurrence_pattern"]
            )
            self.meetings[meeting_id] = meeting 