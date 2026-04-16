# FeedOptima

FeedOptima is an AI-enabled livestock feed ration optimization platform for Indian farmers with advanced nutritional analysis, cost optimization, and regional feed availability considerations.

## 🚀 Key Features

- **Comprehensive Nutritional Analysis**: Tracks DM, CP, Energy, Calcium, Phosphorus, and Fiber
- **Advanced Optimization**: Multi-nutrient balancing with cost constraints
- **Regional Intelligence**: Considers feed availability and local pricing
- **Farmer Preferences**: Support for preferred/avoided feed ingredients
- **AI-Powered Insights**: Intelligent explanations and recommendations
- **Real-time Validation**: Input validation and error handling
- **Performance Optimized**: Caching and rate limiting for scalability

## Quick Preview

To see a working demo:

1. **Start Backend**: Double-click `start_backend.bat` or run:
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start Frontend**: Double-click `start_frontend.bat` or run:
   ```bash
   cd frontend
   python -m http.server 3000
   ```

3. **Open Browser**: Go to `http://localhost:3000` to use the web interface

## Backend Features

The backend provides:
- **Multi-species Support**: Cattle, buffalo, goat, sheep, and poultry
- **Purpose-based Optimization**: Dairy, growth, maintenance, meat, layer, broiler
- **Advanced Feed Database**: 13+ feed ingredients with complete nutritional profiles
- **Mineral & Vitamin Integration**: Calcium, phosphorus, and vitamin premixes
- **Cost Optimization**: Budget constraints and economic feed selection
- **Regional Considerations**: Feed availability scoring
- **AI Explanations**: Farmer-friendly nutritional guidance
- **Database Integration**: SQLite with extensible schema
- **Public Data Scraping**: TNAU feed ingredient data integration

## API Endpoints

- `GET /health` - Health check
- `POST /ration/optimize` - Advanced ration optimization with constraints
- `GET /scrape/tnau` - Scrape TNAU feed data
- `GET /scrape/market-prices` - Sample market price data
- `GET /catalog` - View feed catalog
- `POST /catalog/seed` - Initialize default feed catalog
- `POST /catalog/ingredient` - Add custom feed ingredient
- `POST /catalog/prices` - Update feed prices
- `POST /catalog/sync-market-prices` - Sync market prices

## Advanced Features

### Nutritional Optimization
- **Multi-nutrient Balancing**: Simultaneous optimization of protein, energy, minerals
- **Cost-Performance Trade-offs**: Find optimal balance between nutrition and cost
- **Feed Quality Variability**: Accounts for seasonal and quality variations

### Farmer-Centric Design
- **Preference System**: Prioritize or avoid specific feed ingredients
- **Budget Constraints**: Set maximum daily feed costs
- **Regional Adaptation**: Considers local feed availability
- **Educational Content**: AI-powered explanations for better understanding

### Technical Excellence
- **Error Resilience**: Graceful degradation when AI services fail
- **Performance Caching**: LRU cache for repeated calculations
- **Rate Limiting**: Prevents abuse and ensures fair usage
- **Input Validation**: Comprehensive validation with helpful error messages

## Getting Started

1. **Environment Setup**:
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Database Initialization**:
   ```bash
   # The database auto-creates on first run
   # Or manually seed with default data
   curl -X POST http://localhost:8000/catalog/seed
   ```

3. **Configuration**:
   - Copy `backend/.env.example` to `backend/.env`
   - Set `OPENAI_API_KEY` for AI features (optional)
   - Set `OLLAMA_URL` for local AI (optional)

## Architecture

```
FeedOptima/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── main.py         # API endpoints with error handling
│   │   ├── calculator.py   # Advanced optimization engine
│   │   ├── ai.py          # AI integration with fallbacks
│   │   ├── models.py      # Enhanced data models
│   │   ├── schemas.py     # API request/response schemas
│   │   ├── data/          # Nutritional data and standards
│   │   └── db.py          # Database configuration
│   └── requirements.txt    # Python dependencies
├── frontend/               # Web interface
│   ├── index.html         # Enhanced form with new fields
│   ├── script.js          # Updated API integration
│   └── styles.css         # Responsive styling
└── README.md              # This file
```

## Future Roadmap

- **Mobile App**: React Native application for field use
- **Real-time Pricing**: Integration with agricultural commodity markets
- **Farm Management**: Integration with farm record systems
- **IoT Integration**: Connect with smart feeders and scales
- **Sustainability Metrics**: Carbon footprint and environmental impact tracking
- **Multi-language Support**: Regional language interfaces

## Contributing

We welcome contributions! Areas for improvement:
- Additional feed ingredients and nutritional data
- More species and production systems
- Enhanced optimization algorithms
- Better UI/UX design
- Performance optimizations
- Testing and validation

## License

This project is open source and available under the MIT License.

## Notes

- The backend is intentionally simple and cloud-ready; it is not tied to Supabase.
- Use `DATABASE_URL` in `.env` for future PostgreSQL support.
- Use the scraper endpoint to seed local feed catalogs from public sources.
