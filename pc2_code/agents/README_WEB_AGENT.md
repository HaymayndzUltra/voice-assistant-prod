# Unified Web Agent

## Overview

This document describes the consolidation of multiple web-related agents into a single, unified web agent for PC2. The unified agent combines the best features of the following legacy agents:

- `autonomous_web_assistant.py`: Proactive information gathering and conversation analysis
- `enhanced_web_scraper.py`: Advanced web scraping with caching and database storage
- `web_scraper_agent.py`: Basic web scraping with AutoGen integration

## Features

### Core Capabilities

- Proactive information gathering
- Advanced web scraping
- Form filling and submission
- Conversation analysis
- Caching and database storage
- AutoGen integration
- Health monitoring

### Technical Details

- ZMQ port: 5604 (main), 5605 (health)
- SQLite database for caching
- BeautifulSoup for HTML parsing
- Requests for HTTP operations
- Pandas for data handling

## Configuration

### Ports

```python
ZMQ_PORT = 5604  # Main agent port
HEALTH_PORT = 5605  # Health check port
```

### Database

```python
DB_PATH = "web_cache.db"  # SQLite database path
```

### Caching

```python
CACHE_EXPIRY = 3600  # Cache expiry in seconds
MAX_CACHE_SIZE = 1000  # Maximum number of cached items
```

## Running the Agent

### Using the Launcher

```batch
start_unified_web_agent.bat
```

### Direct Python Execution

```bash
python unified_web_agent.py
```

## Testing

### Running Tests

```batch
run_web_tests.bat
```

### Test Coverage

- Navigation
- Scraping
- Form filling
- Conversation analysis
- Proactive gathering
- Health monitoring

## API

### Navigation

```python
{
    "action": "navigate",
    "url": "https://example.com"
}
```

### Scraping

```python
{
    "action": "scrape",
    "url": "https://example.com",
    "selectors": ["h1", "p"]
}
```

### Form Filling

```python
{
    "action": "fill_form",
    "url": "https://example.com",
    "form_data": {
        "username": "user",
        "password": "pass"
    }
}
```

### Conversation Analysis

```python
{
    "action": "analyze_conversation",
    "conversation": "User: What's the weather?",
    "context": {}
}
```

### Proactive Gathering

```python
{
    "action": "gather_info",
    "topic": "weather",
    "context": {}
}
```

## Health Monitoring

### Metrics

- Uptime
- Request count
- Cache size
- Error rate
- Response time

### Health Check

```python
{
    "action": "health_check"
}
```

## Troubleshooting

### Common Issues

1. Port conflicts

   - Check if ports 5604/5605 are in use
   - Verify no other web agents are running

2. Database errors

   - Ensure write permissions for DB_PATH
   - Check disk space

3. Scraping failures
   - Verify internet connectivity
   - Check rate limiting
   - Validate selectors

### Logs

- Location: `logs/web_agent.log`
- Level: INFO
- Rotation: Daily

## Future Improvements

1. Add Selenium support for JavaScript-heavy sites
2. Implement proxy rotation
3. Add more advanced form handling
4. Improve caching strategy
5. Add rate limiting controls

## Support

For issues or questions, please contact the development team.
