# Lead Enrichment ZGTI

A web application built with Reflex that automates the process of enriching company profiles using AI agents. This tool helps Zurich Group Technology Indonesia (ZGTI) gather comprehensive business information for lead generation and insurance sales opportunities.

## Features

- **Automated Lead Enrichment**: Input company names and automatically populate detailed profiles including sector, address, contact info, employee count, and more
- **AI-Powered Research**: Uses LangGraph agents with Tavily search and Azure OpenAI for intelligent data gathering
- **Interactive Table Interface**: Easy-to-use web interface for managing company data
- **CSV Export**: Export enriched data to CSV for further analysis or CRM integration
- **Progress Tracking**: Real-time status updates during enrichment process

## Tech Stack

- **Frontend**: Reflex (Python web framework)
- **AI/ML**: LangGraph, Azure OpenAI, Tavily Search API
- **Data Processing**: Pandas
- **Environment**: Python 3.8+

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd "Reflex AI-Lead"
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory with your API keys:
   ```
   AZURE_OPENAI_API_KEY=your_azure_openai_key
   AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
   TAVILY_API_KEY=your_tavily_api_key
   ```

## Usage

1. Start the application:
   ```bash
   reflex run
   ```

2. Open your browser to the provided URL (usually http://localhost:8000)

3. Add company names in the table

4. Click "Start Enrichment" to begin the AI-powered research process

5. Export results to CSV when complete

## Project Structure

```
├── backend/
│   ├── researcher.py    # AI research pipeline
│   └── graph.py         # LangGraph workflow
├── reflex_app/
│   ├── reflex_app.py    # Main UI components
│   ├── state.py         # Application state management
│   └── styles.py        # UI styling
├── requirements.txt     # Python dependencies
├── rxconfig.py         # Reflex configuration
└── README.md
```

