from main_pc_code.src.core.base_agent import BaseAgent
"""
Parameter Extractor for Voice Assistant
--------------------------------------
Extracts structured parameters from natural language commands
"""
import re
import json
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
import zmq
import sys
import os
from common.env_helpers import get_env

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ParameterExtractor")

# Parameter types
PARAM_TYPE_DATE = "date"
PARAM_TYPE_TIME = "time"
PARAM_TYPE_DATETIME = "datetime"
PARAM_TYPE_DURATION = "duration"
PARAM_TYPE_LOCATION = "location"
PARAM_TYPE_PERSON = "person"
PARAM_TYPE_NUMBER = "number"
PARAM_TYPE_STRING = "string"
PARAM_TYPE_BOOLEAN = "boolean"
PARAM_TYPE_FILE = "file"
PARAM_TYPE_FOLDER = "folder"

# Enhanced Model Router connection
ENHANCED_MODEL_ROUTER_PORT = 5601

class ParameterExtractor(BaseAgent):
    """Extracts parameters from natural language commands"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ParameterExtractor")
        """Initialize the parameter extractor
        
        Args:
            use_llm: Whether to use LLM for complex parameter extraction
        """
        self.use_llm = use_llm
        
        # Setup LLM connection if needed
        if self.use_llm:
            try:
                self.context = zmq.Context()
                self.llm_socket = self.context.socket(zmq.REQ)
                self.llm_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.llm_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.llm_socket.connect(f"tcp://localhost:{ENHANCED_MODEL_ROUTER_PORT}")
                logger.info(f"Connected to Enhanced Model Router on port {ENHANCED_MODEL_ROUTER_PORT}")
            except Exception as e:
                logger.error(f"Failed to connect to Enhanced Model Router: {e}")
                self.use_llm = False
        
        # Initialize regex patterns
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Initialize regex patterns for parameter extraction"""
        # Date patterns (various formats)
        self.date_patterns = [
            # ISO format: 2023-05-23
            (r'\b(\d{4}-\d{2}-\d{2})\b', lambda m: datetime.datetime.strptime(m.group(1), "%Y-%m-%d").date()),
            
            # US format: 05/23/2023
            (r'\b(\d{1,2}/\d{1,2}/\d{4})\b', lambda m: datetime.datetime.strptime(m.group(1), "%m/%d/%Y").date()),
            
            # Text format: May 23, 2023
            (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b', 
             lambda m: datetime.datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y").date()),
            
            # Relative dates
            (r'\b(today|tomorrow|yesterday)\b', self._parse_relative_date),
            (r'\b(next|this|last)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', self._parse_relative_weekday),
            (r'\bin\s+(\d+)\s+(day|days|week|weeks|month|months|year|years)\b', self._parse_future_date),
            (r'\b(\d+)\s+(day|days|week|weeks|month|months|year|years)\s+ago\b', self._parse_past_date),
        ]
        
        # Time patterns
        self.time_patterns = [
            # 24-hour format: 14:30
            (r'\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b', self._parse_24h_time),
            
            # 12-hour format: 2:30 PM
            (r'\b(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm)\b', self._parse_12h_time),
            
            # Text format: 2 o'clock
            (r'\b(\d{1,2})\s+o\'clock\s*(am|pm)?\b', self._parse_oclock),
            
            # Relative times
            (r'\b(now|midnight|noon)\b', self._parse_special_time),
        ]
        
        # Duration patterns
        self.duration_patterns = [
            # "for X minutes/hours/etc."
            (r'\bfor\s+(\d+)\s+(second|seconds|minute|minutes|hour|hours|day|days|week|weeks|month|months|year|years)\b', 
             self._parse_duration),
            
            # "X minutes/hours/etc."
            (r'\b(\d+)\s+(second|seconds|minute|minutes|hour|hours|day|days|week|weeks|month|months|year|years)\b', 
             self._parse_duration),
        ]
        
        # Number patterns
        self.number_patterns = [
            # Integer
            (r'\b(\d+)\b', lambda m: int(m.group(1))),
            
            # Decimal
            (r'\b(\d+\.\d+)\b', lambda m: float(m.group(1))),
            
            # Written numbers
            (r'\b(one|two|three|four|five|six|seven|eight|nine|ten)\b', self._parse_written_number),
        ]
        
        # Location patterns
        self.location_patterns = [
            # Simple place names
            (r'\bin\s+([\w\s]+(?:City|Town|Village|State|Province|Country))\b', lambda m: m.group(1)),
            
            # Addresses (simplified)
            (r'\bat\s+([\d\w\s\.,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)[\d\w\s\.,]*)\b', 
             lambda m: m.group(1)),
        ]
        
        # Person patterns
        self.person_patterns = [
            # Names with titles
            (r'\b(Mr\.|Mrs\.|Ms\.|Dr\.)\s+([\w\s]+)\b', lambda m: f"{m.group(1)} {m.group(2)}"),
            
            # First and last names (simplified)
            (r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b', lambda m: f"{m.group(1)} {m.group(2)}"),
        ]
        
        # File patterns
        self.file_patterns = [
            # Filenames with extensions
            (r'\b([\w\s\-]+\.(txt|pdf|doc|docx|xls|xlsx|ppt|pptx|jpg|jpeg|png|gif|mp3|mp4|wav|avi|mov|py|js|html|css|json))\b', 
             lambda m: m.group(1)),
            
            # "file named X"
            (r'\bfile\s+(?:named|called)\s+"([^"]+)"\b', lambda m: m.group(1)),
            (r"\bfile\s+(?:named|called)\s+'([^']+)'\b", lambda m: m.group(1)),
        ]
        
        # Folder patterns
        self.folder_patterns = [
            # "folder named X"
            (r'\bfolder\s+(?:named|called)\s+"([^"]+)"\b', lambda m: m.group(1)),
            (r"\bfolder\s+(?:named|called)\s+'([^']+)'\b", lambda m: m.group(1)),
            
            # "directory X"
            (r'\bdirectory\s+"([^"]+)"\b', lambda m: m.group(1)),
            (r"\bdirectory\s+'([^']+)'\b", lambda m: m.group(1)),
        ]
    
    def _parse_relative_date(self, match) -> datetime.date:
        """Parse relative date expressions like 'today', 'tomorrow', 'yesterday'"""
        text = match.group(1).lower()
        today = datetime.date.today()
        
        if text == "today":
            return today
        elif text == "tomorrow":
            return today + datetime.timedelta(days=1)
        elif text == "yesterday":
            return today - datetime.timedelta(days=1)
        return today
    
    def _parse_relative_weekday(self, match) -> datetime.date:
        """Parse relative weekday expressions like 'next Monday', 'this Friday'"""
        relative = match.group(1).lower()
        weekday = match.group(2).lower()
        
        # Map weekday names to numbers (0 = Monday, 6 = Sunday)
        weekday_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        
        target_weekday = weekday_map.get(weekday, 0)
        today = datetime.date.today()
        current_weekday = today.weekday()
        
        if relative == "this":
            # If today is the target weekday, return today
            if current_weekday == target_weekday:
                return today
            # Otherwise, find the next occurrence this week
            days_ahead = (target_weekday - current_weekday) % 7
            return today + datetime.timedelta(days=days_ahead)
        
        elif relative == "next":
            # Always the next occurrence, even if today is the target weekday
            days_ahead = (target_weekday - current_weekday) % 7
            if days_ahead == 0:
                days_ahead = 7  # Next week
            return today + datetime.timedelta(days=days_ahead)
        
        elif relative == "last":
            # Previous occurrence
            days_ago = (current_weekday - target_weekday) % 7
            if days_ago == 0:
                days_ago = 7  # Last week
            return today - datetime.timedelta(days=days_ago)
        
        return today
    
    def _parse_future_date(self, match) -> datetime.date:
        """Parse future date expressions like 'in 3 days', 'in 2 weeks'"""
        amount = int(match.group(1))
        unit = match.group(2).lower()
        
        today = datetime.date.today()
        
        if unit in ["day", "days"]:
            return today + datetime.timedelta(days=amount)
        elif unit in ["week", "weeks"]:
            return today + datetime.timedelta(weeks=amount)
        elif unit in ["month", "months"]:
            # Approximate month as 30 days
            return today + datetime.timedelta(days=30 * amount)
        elif unit in ["year", "years"]:
            # Approximate year as 365 days
            return today + datetime.timedelta(days=365 * amount)
        
        return today
    
    def _parse_past_date(self, match) -> datetime.date:
        """Parse past date expressions like '3 days ago', '2 weeks ago'"""
        amount = int(match.group(1))
        unit = match.group(2).lower()
        
        today = datetime.date.today()
        
        if unit in ["day", "days"]:
            return today - datetime.timedelta(days=amount)
        elif unit in ["week", "weeks"]:
            return today - datetime.timedelta(weeks=amount)
        elif unit in ["month", "months"]:
            # Approximate month as 30 days
            return today - datetime.timedelta(days=30 * amount)
        elif unit in ["year", "years"]:
            # Approximate year as 365 days
            return today - datetime.timedelta(days=365 * amount)
        
        return today
    
    def _parse_24h_time(self, match) -> datetime.time:
        """Parse 24-hour time format like '14:30'"""
        hour = int(match.group(1))
        minute = int(match.group(2))
        second = int(match.group(3)) if match.group(3) else 0
        
        return datetime.time(hour=hour, minute=minute, second=second)
    
    def _parse_12h_time(self, match) -> datetime.time:
        """Parse 12-hour time format like '2:30 PM'"""
        hour = int(match.group(1))
        minute = int(match.group(2))
        second = int(match.group(3)) if match.group(3) else 0
        am_pm = match.group(4).lower()
        
        # Adjust hour for PM
        if am_pm == "pm" and hour < 12:
            hour += 12
        # Adjust hour for AM
        elif am_pm == "am" and hour == 12:
            hour = 0
        
        return datetime.time(hour=hour, minute=minute, second=second)
    
    def _parse_oclock(self, match) -> datetime.time:
        """Parse o'clock time format like '2 o'clock PM'"""
        hour = int(match.group(1))
        am_pm = match.group(2).lower() if match.group(2) else None
        
        # Default to AM if not specified
        if am_pm == "pm" and hour < 12:
            hour += 12
        elif am_pm == "am" and hour == 12:
            hour = 0
        
        return datetime.time(hour=hour, minute=0, second=0)
    
    def _parse_special_time(self, match) -> datetime.time:
        """Parse special time expressions like 'now', 'midnight', 'noon'"""
        special = match.group(1).lower()
        
        if special == "now":
            now = datetime.datetime.now()
            return now.time()
        elif special == "midnight":
            return datetime.time(hour=0, minute=0, second=0)
        elif special == "noon":
            return datetime.time(hour=12, minute=0, second=0)
        
        # Default
        return datetime.datetime.now().time()
    
    def _parse_duration(self, match) -> Dict[str, Any]:
        """Parse duration expressions like 'for 30 minutes', '2 hours'"""
        amount = int(match.group(1))
        unit = match.group(2).lower()
        
        # Normalize unit to singular
        if unit.endswith('s'):
            unit = unit[:-1]
        
        return {
            "amount": amount,
            "unit": unit
        }
    
    def _parse_written_number(self, match) -> int:
        """Parse written numbers like 'one', 'two', etc."""
        number_map = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
        }
        
        return number_map.get(match.group(1).lower(), 0)
    
    def extract_parameters(self, text: str, param_types: List[str] = None) -> Dict[str, Any]:
        """Extract parameters from text based on specified types
        
        Args:
            text: The text to extract parameters from
            param_types: List of parameter types to extract, or None for all
            
        Returns:
            Dictionary of extracted parameters
        """
        # If use_llm and text is complex, use LLM-based extraction
        if self.use_llm and len(text.split()) > 5:
            llm_params = self._extract_parameters_llm(text, param_types)
            if llm_params:
                return llm_params
        
        # Otherwise use regex-based extraction
        return self._extract_parameters_regex(text, param_types)
    
    def _extract_parameters_regex(self, text: str, param_types: List[str] = None) -> Dict[str, Any]:
        """Extract parameters using regex patterns
        
        Args:
            text: The text to extract parameters from
            param_types: List of parameter types to extract, or None for all
            
        Returns:
            Dictionary of extracted parameters
        """
        result = {}
        text = text.lower()
        
        # If no specific types requested, extract all
        if not param_types:
            param_types = [
                PARAM_TYPE_DATE, PARAM_TYPE_TIME, PARAM_TYPE_DATETIME, 
                PARAM_TYPE_DURATION, PARAM_TYPE_LOCATION, PARAM_TYPE_PERSON,
                PARAM_TYPE_NUMBER, PARAM_TYPE_STRING, PARAM_TYPE_BOOLEAN,
                PARAM_TYPE_FILE, PARAM_TYPE_FOLDER
            ]
        
        # Extract dates
        if PARAM_TYPE_DATE in param_types:
            dates = []
            for pattern, parser in self.date_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        date = parser(match)
                        if date and isinstance(date, datetime.date):
                            dates.append(date)
                    except Exception as e:
                        logger.warning(f"Error parsing date: {e}")
            if dates:
                result[PARAM_TYPE_DATE] = dates[0] if len(dates) == 1 else dates
        
        # Extract times
        if PARAM_TYPE_TIME in param_types:
            times = []
            for pattern, parser in self.time_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        time = parser(match)
                        if time and isinstance(time, datetime.time):
                            times.append(time)
                    except Exception as e:
                        logger.warning(f"Error parsing time: {e}")
            if times:
                result[PARAM_TYPE_TIME] = times[0] if len(times) == 1 else times
        
        # Create datetime from date and time if both are present
        if PARAM_TYPE_DATETIME in param_types and PARAM_TYPE_DATE in result and PARAM_TYPE_TIME in result:
            date = result[PARAM_TYPE_DATE]
            time = result[PARAM_TYPE_TIME]
            
            # Handle lists
            if not isinstance(date, datetime.date):
                date = date[0]
            if not isinstance(time, datetime.time):
                time = time[0]
            
            result[PARAM_TYPE_DATETIME] = datetime.datetime.combine(date, time)
        
        # Extract durations
        if PARAM_TYPE_DURATION in param_types:
            durations = []
            for pattern, parser in self.duration_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        duration = parser(match)
                        if duration:
                            durations.append(duration)
                    except Exception as e:
                        logger.warning(f"Error parsing duration: {e}")
            if durations:
                result[PARAM_TYPE_DURATION] = durations[0] if len(durations) == 1 else durations
        
        # Extract locations
        if PARAM_TYPE_LOCATION in param_types:
            locations = []
            for pattern, parser in self.location_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        location = parser(match)
                        if location:
                            locations.append(location)
                    except Exception as e:
                        logger.warning(f"Error parsing location: {e}")
            if locations:
                result[PARAM_TYPE_LOCATION] = locations[0] if len(locations) == 1 else locations
        
        # Extract persons
        if PARAM_TYPE_PERSON in param_types:
            persons = []
            for pattern, parser in self.person_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        person = parser(match)
                        if person:
                            persons.append(person)
                    except Exception as e:
                        logger.warning(f"Error parsing person: {e}")
            if persons:
                result[PARAM_TYPE_PERSON] = persons[0] if len(persons) == 1 else persons
        
        # Extract numbers
        if PARAM_TYPE_NUMBER in param_types:
            numbers = []
            for pattern, parser in self.number_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        number = parser(match)
                        if number is not None:
                            numbers.append(number)
                    except Exception as e:
                        logger.warning(f"Error parsing number: {e}")
            if numbers:
                result[PARAM_TYPE_NUMBER] = numbers[0] if len(numbers) == 1 else numbers
        
        # Extract files
        if PARAM_TYPE_FILE in param_types:
            files = []
            for pattern, parser in self.file_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        file = parser(match)
                        if file:
                            files.append(file)
                    except Exception as e:
                        logger.warning(f"Error parsing file: {e}")
            if files:
                result[PARAM_TYPE_FILE] = files[0] if len(files) == 1 else files
        
        # Extract folders
        if PARAM_TYPE_FOLDER in param_types:
            folders = []
            for pattern, parser in self.folder_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        folder = parser(match)
                        if folder:
                            folders.append(folder)
                    except Exception as e:
                        logger.warning(f"Error parsing folder: {e}")
            if folders:
                result[PARAM_TYPE_FOLDER] = folders[0] if len(folders) == 1 else folders
        
        # Extract boolean flags (yes/no, true/false)
        if PARAM_TYPE_BOOLEAN in param_types:
            # Check for positive indicators
            if re.search(r'\b(yes|yeah|yep|correct|right|true|affirmative)\b', text, re.IGNORECASE):
                result[PARAM_TYPE_BOOLEAN] = True
            # Check for negative indicators
            elif re.search(r'\b(no|nope|not|negative|false|incorrect|wrong)\b', text, re.IGNORECASE):
                result[PARAM_TYPE_BOOLEAN] = False
        
        return result
    
    def _extract_parameters_llm(self, text: str, param_types: List[str] = None) -> Dict[str, Any]:
        """Extract parameters using LLM-based approach
        
        Args:
            text: The text to extract parameters from
            param_types: List of parameter types to extract, or None for all
            
        Returns:
            Dictionary of extracted parameters, or empty dict if LLM failed
        """
        if not self.use_llm:
            return {}
        
        try:
            # Create parameter extraction prompt
            param_type_str = ", ".join(param_types) if param_types else "all relevant parameters"
            
            prompt = f"""
            Extract {param_type_str} from the following text as a JSON object.
            If a parameter is not present, do not include it in the result.
            Text: "{text}"
            
            Return format example:
            {{
                "date": "2023-05-23",
                "time": "14:30:00",
                "location": "New York",
                "number": 42
            }}
            
            JSON result:
            """
            
            # Send request to LLM
            request = {
                "prompt": prompt,
                "type": "json_extraction",
                "max_tokens": 200
            }
            
            self.llm_socket.send_string(json.dumps(request))
            response = self.llm_socket.recv_string()
            result = json.loads(response)
            
            if "response" in result:
                # Try to parse the response as JSON
                try:
                    params = json.loads(result["response"])
                    logger.info(f"LLM extracted parameters: {params}")
                    
                    # Convert string dates and times to appropriate objects
                    if "date" in params and isinstance(params["date"], str):
                        try:
                            params["date"] = datetime.datetime.strptime(params["date"], "%Y-%m-%d").date()
                        except:
                            pass
                    
                    if "time" in params and isinstance(params["time"], str):
                        try:
                            params["time"] = datetime.datetime.strptime(params["time"], "%H:%M:%S").time()
                        except:
                            try:
                                params["time"] = datetime.datetime.strptime(params["time"], "%H:%M").time()
                            except:
                                pass
                    
                    if "datetime" in params and isinstance(params["datetime"], str):
                        try:
                            params["datetime"] = datetime.datetime.fromisoformat(params["datetime"])
                        except:
                            pass
                    
                    return params
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse LLM response as JSON: {result['response']}")
            
            return {}
        
        except Exception as e:
            logger.error(f"Error in LLM parameter extraction: {e}")
            return {}

# Example usage
if __name__ == "__main__":
    extractor = ParameterExtractor(use_llm=False)
    
    # Test with various inputs
    test_texts = [
        "What's the weather like in New York today?",
        "Remind me to call John tomorrow at 3:30 PM",
        "Schedule a meeting for next Tuesday at 2 o'clock",
        "Set a timer for 30 minutes",
        "Find files modified in the last 3 days",
        "Open the file named 'budget_2023.xlsx'",
        "Email the report to Sarah and Mike",
        "I need to finish this project by May 15, 2023"
    ]
    
    for text in test_texts:
        print(f"\nText: {text}")
        params = extractor.extract_parameters(text)
        print("Extracted parameters:")
        for param_type, value in params.items():
            print(f"  {param_type}: {value}")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise