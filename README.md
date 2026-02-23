# 🫚 GINGER UNIVERSE - Doctor Profile Generator

**Professional AI-Powered Doctor Profile Generation System**

Built for: ginger.healthcare  
Version: 1.0 (Semi-Automated)  
Status: Production Ready

---

## 🎯 WHAT THIS DOES

Automatically generates professional doctor profiles by:
1. Scraping doctor information from any website
2. Matching doctors to 807 medical procedures from your database
3. Generating perfect Claude AI prompts
4. Creating professional Word documents

**Time per profile: ~2 minutes** (vs 30+ minutes manually!)

---

## 🚀 QUICK START

### Step 1: Install Dependencies
```bash
cd ginger_universe
pip install -r requirements.txt
```

### Step 2: Run the Application
```bash
python app.py
```

### Step 3: Login
Open browser: http://localhost:5000

**Credentials:**
- Username: admin@ginger.healthcare
- Password: GingerUniverse2026!

**⚠️ CHANGE PASSWORD AFTER FIRST LOGIN!**

---

## 💻 HOW TO USE

1. **Login** → Enter doctor website URL → Click "Generate"
2. **System analyzes** webpage & matches procedures (automatic)
3. **Copy prompt** → Paste into Claude.ai → Get response (30 sec)
4. **Paste response back** → Click "Create Document"
5. **Download** professional .docx profile!

---

## ☁️ DEPLOY TO CLOUD

### Railway (Easiest - Recommended)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
cd ginger_universe
railway init
railway up

# Get your URL
railway domain
```

Your app will be live at: https://ginger-universe.up.railway.app

### Render

1. Push code to GitHub
2. Go to render.com → New Web Service
3. Connect repo → Deploy!

---

## 🆙 UPGRADE TO FULL AUTOMATION

When you get Claude API (tomorrow!):

**Edit config.py:**
```python
CLAUDE_API_KEY = "sk-ant-your-key-here"
```

**Edit app.py - add this after line 60:**
```python
from anthropic import Anthropic
client = Anthropic(api_key=CLAUDE_API_KEY)
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4000,
    messages=[{"role": "user", "content": prompt}]
)
profile = message.content[0].text
```

**Done!** Now fully automated - no copy-paste needed!

---

## 📁 PROJECT STRUCTURE

```
ginger_universe/
├── app.py                    # Main application
├── config.py                 # Settings (change password here!)
├── requirements.txt          # Dependencies
├── utils/
│   ├── scraper.py           # Web scraping
│   ├── sheets_connector.py  # Google Sheets integration
│   ├── dictionary_matcher.py # Procedure matching
│   ├── prompt_generator.py  # Claude prompts
│   └── doc_generator.py     # Word documents
└── templates/
    ├── login.html           # Login page
    └── dashboard.html       # Main interface
```

---

## 🔐 SECURITY CHECKLIST

- [ ] Change default password (config.py)
- [ ] Enable HTTPS in production
- [ ] Use environment variables for secrets
- [ ] Set up regular backups

---

## 🐛 TROUBLESHOOTING

**Can't scrape website?**
- Some sites block bots - try different URL
- System will show clear error

**No procedures matched?**
- Doctor's specialty might not be in database
- Profile still generates with basic info

**Login not working?**
- Check spelling: admin@ginger.healthcare
- Password: GingerUniverse2026!

**Document won't download?**
- Check browser settings
- Try different browser

---

## 📊 WHAT'S NEXT

**Tomorrow:** Get Claude API → Upgrade to full automation  
**This Week:** Generate 50-100 profiles  
**This Month:** Add email automation module  
**This Year:** Build complete Business OS!

---

## 🎊 SYSTEM FEATURES

✅ Web scraping engine  
✅ 807 procedure database integration  
✅ Smart procedure matching  
✅ Professional Word document generation  
✅ Beautiful web interface  
✅ Secure authentication  
✅ Cloud-ready deployment  
✅ Modular architecture (easy to extend!)

---

**Built with ❤️ for Ginger Universe**

**Let's build that ₹100 crore company!** 🚀🫚

© 2026 ginger.healthcare - All rights reserved
