# Web Module

The web module provides a unified interface for web-related operations including search, scraping, and browser automation.

## Features

### 1. Web Search
- DuckDuckGo integration
- Configurable result limits
- Caching of search results
- Error handling and retries

### 2. Web Scraping
- Intelligent page structure analysis
- Support for JavaScript rendering
- Rate limiting and caching
- Multiple output formats (CSV, Excel, JSON)
- LLM-assisted scraping code generation

### 3. Browser Automation
- Playwright-based automation
- Form filling and submission
- File upload/download
- Screenshot capture
- JavaScript execution

## Usage

### Starting the Agent
```bash
python agents/unified_web_agent.py
```

### ZMQ Interface

The agent listens on port 5560 for requests and provides a health check endpoint on port 5561.

#### Example Requests

1. Web Search:
```python
{
    "action": "search",
    "query": "What is Python?",
    "max_results": 3
}
```

2. Web Scraping:
```python
{
    "action": "scrape",
    "url": "https://example.com",
    "data_type": "products",
    "output_format": "csv",
    "render_js": true
}
```

3. Browser Automation:
```python
{
    "action": "browser",
    "action": "login",
    "url": "https://example.com",
    "username": "user",
    "password": "pass",
    "username_selector": "#username",
    "password_selector": "#password",
    "submit_selector": "#submit"
}
```

## Configuration

The agent is configured through `config/system_config.py`:

```python
"web_agents": {
    "unified_web_agent": {
        "enabled": True,
        "port": 5560,
        "health_check_port": 5561,
        "cache_size": 1000,
        "rate_limit": 10,  # requests per second
        "timeout": 30,     # seconds
        "retry_attempts": 3
    }
}
```

## Dependencies

- requests
- beautifulsoup4
- pandas
- playwright
- zmq
- sqlite3

## Testing

Run the test suite:
```bash
python tests/test_unified_web_agent.py
```

## Error Handling

The agent includes comprehensive error handling:
- Network timeouts
- Rate limiting
- Invalid responses
- Browser automation failures
- Resource cleanup

## Logging

Logs are written to `logs/unified_web_agent.log` with the following format:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## Performance

- SQLite-based caching
- Configurable rate limiting
- Efficient resource management
- Browser instance reuse

## Security

- Input validation
- URL sanitization
- Secure file handling
- No hardcoded credentials

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests
4. Submit a pull request

## License

This module is part of the Voice Assistant system and is subject to its license terms. 