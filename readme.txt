# Academic Information Hub

A modern UI application that aggregates information from different academic platforms (Coursera, Slack, Email) into a single dashboard.

## Features

- View deadlines, assignments, and activities across classes
- See notifications from Slack and Email
- Filter activities by status (Deadlines, Submitted, Graded, etc.)
- Chat interface to query information

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Installation

1. Clone this repository
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
python main.py
```

## Usage

- Select classes from the sidebar to view their activities
- Use the filter buttons to filter activities by status
- Use the date range selectors to change the view period
- Ask questions in the chat interface for additional information

## Technologies

- PySide6 for the UI framework
- Qt Material for modern styling (optional)
- Custom CSS styling as a fallback

## Notes

- This is a prototype implementation
- In a production version, you would need to implement the backend services to connect to Coursera, Slack, and Email APIs
