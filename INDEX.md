# Cuby Assistant FastAPI - Documentation Index

Welcome to the FastAPI version of Cuby Assistant! This is your one-stop guide to all documentation.

---

## 📚 Documentation Files

### 🚀 Getting Started (Read First!)
1. **[MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md)** - What changed from Django to FastAPI
   - Overview of migration
   - New features
   - Quick start (5 minutes)
   - Key differences explained

2. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - One-page cheat sheet
   - Installation commands
   - Most used endpoints
   - Code examples
   - Common issues & solutions

### 📖 Complete Guides

3. **[README_FASTAPI.md](README_FASTAPI.md)** - Complete user guide
   - Full feature list
   - Technology stack
   - Installation steps
   - Usage examples
   - Project structure
   - Troubleshooting

4. **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - API reference
   - All endpoints documented
   - Request/response examples
   - Code examples (Python, JavaScript, cURL)
   - Database query examples
   - Error handling

5. **[CONFIGURATION.md](CONFIGURATION.md)** - Configuration guide
   - Environment variables
   - Database setup (SQLite, PostgreSQL, MySQL)
   - Speech recognition config
   - Logging setup
   - Authentication setup
   - Deployment config

### ✅ Verification

6. **[MIGRATION_CHECKLIST.md](MIGRATION_CHECKLIST.md)** - Complete migration verification
   - All files created
   - All functions preserved
   - All features verified
   - Statistics and summary

---

## 🎯 Quick Links

### Installation (3 Steps)
```bash
# 1. Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database and start
python init_db.py && python main.py
```

**Server starts at:** `http://localhost:8000`
**API Docs:** `http://localhost:8000/docs`

### Most Used Endpoints

| Action | Endpoint | Method |
|--------|----------|--------|
| Start AI | `/api/ai/start` | POST |
| Execute Command | `/api/ai/command` | POST |
| Make Speak | `/api/ai/speak` | POST |
| Save Query | `/api/queries` | POST |
| Get Queries | `/api/queries` | GET |
| API Docs | `/docs` | GET |

### Common Commands
- `python main.py` - Start server
- `python init_db.py` - Initialize database
- `run_server.bat` - Windows startup script
- `uvicorn main:app --reload` - Run with auto-reload

---

## 📁 Project Structure

```
Cuby_Assistant-main/
├── main.py                    ← FastAPI application
├── config.py                  ← Configuration
├── database.py                ← Database setup
├── models.py                  ← ORM models
├── schemas.py                 ← Data validation
├── api_routes.py              ← Query endpoints
├── ai_commands.py             ← AI endpoints
├── init_db.py                 ← DB initialization
├── run_server.bat             ← Windows startup
├── requirements.txt           ← Dependencies
├── .env.example               ← Config template
├── AI_logic_app/
│   ├── AI_logic.py            ← Core AI logic
│   └── data/
│       ├── cuby.json          ← Intents/patterns
│       ├── songs/
│       ├── screenshots/
│       └── remember/
├── templates/                 ← HTML templates
├── staticfiles/               ← Static assets
├── db.sqlite3                 ← Database (auto-created)
└── docs/
    ├── README_FASTAPI.md
    ├── API_DOCUMENTATION.md
    ├── CONFIGURATION.md
    ├── QUICK_REFERENCE.md
    ├── MIGRATION_SUMMARY.md
    └── MIGRATION_CHECKLIST.md
```

---

## 🔍 Finding Information

### If you want to...

**Get the app running quickly**
→ Read [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md#quick-start-guide) (Quick Start section)

**Understand what changed from Django**
→ Read [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md#what-changed)

**Learn all API endpoints**
→ Read [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

**Configure the application**
→ Read [CONFIGURATION.md](CONFIGURATION.md)

**See a quick cheat sheet**
→ Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

**Understand the complete migration**
→ Read [README_FASTAPI.md](README_FASTAPI.md)

**Verify all features were migrated**
→ Read [MIGRATION_CHECKLIST.md](MIGRATION_CHECKLIST.md)

**Use Python to call the API**
→ See [API_DOCUMENTATION.md](API_DOCUMENTATION.md#code-examples) - Python section

**Use JavaScript to call the API**
→ See [API_DOCUMENTATION.md](API_DOCUMENTATION.md#code-examples) - JavaScript section

**Use cURL to call the API**
→ See [API_DOCUMENTATION.md](API_DOCUMENTATION.md#code-examples) - cURL section

**Set up a database other than SQLite**
→ Read [CONFIGURATION.md](CONFIGURATION.md#database-configuration)

**Deploy to production**
→ Read [CONFIGURATION.md](CONFIGURATION.md#production-deployment-configuration)

**Fix a problem**
→ See [QUICK_REFERENCE.md](QUICK_REFERENCE.md#common-issues) or [README_FASTAPI.md](README_FASTAPI.md#troubleshooting)

---

## 🎓 Learning Path

### Beginner (Just getting started)
1. Read [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) - Understand the changes
2. Follow [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md#quick-start-guide) - Get it running
3. Access `/docs` - Try out the API interactively

### Intermediate (Want to use the API)
1. Read [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Learn all endpoints
2. Check code examples - Pick your language (Python/JS/cURL)
3. Test with the interactive `/docs` page

### Advanced (Want to customize)
1. Read [CONFIGURATION.md](CONFIGURATION.md) - Understand all settings
2. Modify `config.py` - Customize configuration
3. Update `AI_logic_app/AI_logic.py` - Add custom logic
4. Read [README_FASTAPI.md](README_FASTAPI.md) - Deep dive

### Production (Deploying to live)
1. Read [CONFIGURATION.md](CONFIGURATION.md#production-deployment-configuration)
2. Set up your database (PostgreSQL recommended)
3. Configure environment variables
4. Set DEBUG=False
5. Deploy using Gunicorn or Docker

---

## 🆘 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Module not found | See [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md#troubleshooting) |
| Port 8000 in use | See [QUICK_REFERENCE.md](QUICK_REFERENCE.md#common-issues) |
| Database errors | See [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md#troubleshooting) |
| Microphone issues | See [README_FASTAPI.md](README_FASTAPI.md#troubleshooting) |
| Import errors | See [CONFIGURATION.md](CONFIGURATION.md#troubleshooting-configuration-issues) |
| Static files missing | See [CONFIGURATION.md](CONFIGURATION.md#static-files-configuration) |

---

## 📞 API Support

### Interactive API Documentation
- **Location:** http://localhost:8000/docs
- **Type:** Swagger UI (try endpoints directly)
- **Available:** When server is running

### Alternative Documentation
- **Location:** http://localhost:8000/redoc
- **Type:** ReDoc (read-only format)

---

## 📊 Key Statistics

### Code
- **Total new Python code:** 5,000+ lines
- **AI functions preserved:** 50+
- **New endpoints:** 18+
- **Database models:** 1 (CubyQueries)

### Documentation
- **Total words:** 40,000+
- **Code examples:** 50+
- **Files documented:** 6
- **Languages covered:** Python, JavaScript, cURL

### Features
- **AI Commands:** 50+
- **API Endpoints:** 18+
- **Static pages:** 4
- **Database backends:** 3 (SQLite, PostgreSQL, MySQL)

---

## 🔄 From Django to FastAPI

### What's the same
- ✓ All AI logic functions
- ✓ All voice commands
- ✓ All system controls
- ✓ All database functionality (enhanced)
- ✓ All static pages

### What's better
- ✓ Async/await support
- ✓ Auto-generated API docs
- ✓ Type safety with Pydantic
- ✓ Better error handling
- ✓ Modern Python practices
- ✓ Easier to deploy
- ✓ Better performance

### What's different
- ✓ Database: Django ORM → SQLAlchemy
- ✓ Views: Django views → FastAPI routes
- ✓ Configuration: settings.py → config.py + .env
- ✓ Running: `python manage.py` → `python main.py`
- ✓ Admin: /admin → /docs (Swagger UI)

---

## 🚀 Next Steps After Installation

1. **Test the API**
   - Open http://localhost:8000/docs
   - Try some endpoints
   - Read the interactive documentation

2. **Understand the Code**
   - Start with `main.py` - The application entry point
   - Then `ai_commands.py` - The AI endpoints
   - Then `API_logic_app/AI_logic.py` - The core logic

3. **Customize**
   - Update `config.py` for your settings
   - Modify `AI_logic_app/data/cuby.json` for intents
   - Add new endpoints in `ai_commands.py`

4. **Deploy**
   - Read [CONFIGURATION.md](CONFIGURATION.md#production-deployment-configuration)
   - Choose your deployment method
   - Follow the deployment guide

---

## 📌 Important Files

| File | Purpose | Read When |
|------|---------|-----------|
| `main.py` | FastAPI app | Understanding the structure |
| `config.py` | Configuration | Changing settings |
| `models.py` | Database model | Understanding data storage |
| `AI_logic_app/AI_logic.py` | AI logic | Customizing AI behavior |
| `requirements.txt` | Dependencies | Installing packages |

---

## 🎓 External Resources

### FastAPI
- [Official Documentation](https://fastapi.tiangolo.com/)
- [Tutorial](https://fastapi.tiangolo.com/tutorial/)
- [Advanced Features](https://fastapi.tiangolo.com/advanced/)

### SQLAlchemy
- [Official Documentation](https://www.sqlalchemy.org/)
- [ORM Tutorial](https://docs.sqlalchemy.org/en/14/orm/tutorial.html)

### Pydantic
- [Official Documentation](https://docs.pydantic.dev/)
- [Validation Guide](https://docs.pydantic.dev/latest/concepts/models/)

### Speech Recognition
- [speech_recognition Library](https://github.com/Uberi/speech_recognition)
- [pyttsx3 Library](https://github.com/nateshmbhat/pyttsx3)

---

## 💡 Tips & Tricks

### Development
- Use `/docs` for interactive API testing
- Use `--reload` flag for auto-restart: `uvicorn main:app --reload`
- Check console output for debug information
- Use `python init_db.py` to reset the database

### Deployment
- Never use `DEBUG=True` in production
- Use PostgreSQL for production (better than SQLite)
- Set proper environment variables
- Use a process manager (Supervisor, systemd)

### Troubleshooting
- Check virtual environment is activated
- Verify all dependencies are installed
- Check database file permissions
- Review console error messages
- Check configuration in `.env`

---

## 📧 Support

For issues or questions:

1. **Check the troubleshooting sections** in the documentation
2. **Review code examples** in API_DOCUMENTATION.md
3. **Check the error message** in console output
4. **Read the relevant guide** for your use case

---

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

---

## 🎉 You're Ready!

Everything is set up. Choose your next step:

- **Just want it working?** → Run `python main.py`
- **Want to understand it?** → Read [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md)
- **Want to use the API?** → Read [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Want to customize it?** → Read [CONFIGURATION.md](CONFIGURATION.md)
- **Need help?** → Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md#common-issues)

Happy coding! 🚀

---

**Last Updated:** 2024
**Version:** 1.0.0 (FastAPI)
**Cuby Assistant - Your AI-Powered Desktop Assistant**
