# 🚀 DEPLOYMENT GUIDE - Ginger Universe

Complete instructions for deploying your Doctor Profile Generator to the cloud.

---

## 🎯 Deployment Options

### Option 1: Railway (RECOMMENDED) ⭐
**Why:** Easiest, free tier, auto-deploy from Git

### Option 2: Render
**Why:** Good free tier, simple setup

### Option 3: Heroku
**Why:** Popular, reliable, easy scaling

---

## 📦 OPTION 1: RAILWAY (Recommended)

### Step 1: Prepare Your Code

1. **Install Git (if not installed):**
```bash
# Check if git is installed
git --version

# If not, install from: https://git-scm.com/
```

2. **Initialize Git repository:**
```bash
cd ginger_universe
git init
git add .
git commit -m "Initial commit - Ginger Universe v1.0"
```

3. **Push to GitHub:**
```bash
# Create repository on github.com first
# Then:
git remote add origin https://github.com/YOUR_USERNAME/ginger-universe.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Railway

1. **Go to:** https://railway.app
2. **Sign up** (use GitHub login)
3. **Click:** "New Project"
4. **Select:** "Deploy from GitHub repo"
5. **Choose:** your ginger-universe repository
6. **Railway auto-detects:** Python and installs dependencies
7. **Wait:** ~2-3 minutes for deployment
8. **Get URL:** Railway provides a public URL

### Step 3: Configure

1. **Add environment variables:**
   - Click project → Variables
   - Add: `PORT` = `5000`
   - Add: `PYTHON_VERSION` = `3.11`

2. **Enable public access:**
   - Settings → Generate Domain
   - Get URL like: `ginger-universe.up.railway.app`

### Step 4: Custom Domain (Optional)

1. **In Railway:** Settings → Custom Domain
2. **Add:** `profiles.ginger.healthcare`
3. **Update DNS:** (in your domain registrar)
   - Add CNAME record
   - Point to Railway URL

**DONE! Your app is live!** ✅

---

## 📦 OPTION 2: RENDER

### Step 1: Prepare Code

Same as Railway (Git + GitHub setup above)

### Step 2: Deploy on Render

1. **Go to:** https://render.com
2. **Sign up** (use GitHub)
3. **Click:** "New +" → "Web Service"
4. **Connect:** GitHub repository
5. **Configure:**
   - Name: `ginger-universe`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
6. **Click:** "Create Web Service"
7. **Wait:** ~5 minutes for first deploy

### Step 3: Get URL

Render gives you: `ginger-universe.onrender.com`

### Step 4: Custom Domain (Optional)

1. Settings → Custom Domain
2. Add `profiles.ginger.healthcare`
3. Update DNS records as instructed

**DONE!** ✅

---

## 📦 OPTION 3: HEROKU

### Step 1: Install Heroku CLI

```bash
# Download from: https://devcenter.heroku.com/articles/heroku-cli
# Or via Homebrew (Mac):
brew tap heroku/brew && brew install heroku
```

### Step 2: Create Heroku App

```bash
cd ginger_universe

# Login
heroku login

# Create app
heroku create ginger-universe

# Or with custom name:
heroku create your-custom-name
```

### Step 3: Add Procfile

Create file named `Procfile` (no extension):
```
web: gunicorn app:app
```

### Step 4: Deploy

```bash
git add .
git commit -m "Add Heroku Procfile"
git push heroku main
```

### Step 5: Open App

```bash
heroku open
```

**DONE!** ✅

---

## 🔧 POST-DEPLOYMENT CHECKLIST

### ✅ Security

1. **Change admin password:**
   - Login with default credentials
   - Go to config and update

2. **Update secret key:**
   - Generate new secret key
   - Update in production environment

### ✅ Testing

1. **Test login:** Verify credentials work
2. **Test generation:** Generate sample profile
3. **Test document:** Create and download Word doc
4. **Test on mobile:** Check responsive design

### ✅ Monitoring

1. **Check logs:** Look for errors
2. **Monitor performance:** Page load times
3. **Track usage:** Number of profiles generated

---

## 🌐 CUSTOM DOMAIN SETUP

### For ginger.healthcare

**DNS Settings (in your domain registrar):**

```
Type: CNAME
Host: profiles
Value: [your-deployment-url]
TTL: 3600

Example:
profiles.ginger.healthcare → ginger-universe.up.railway.app
```

**Wait:** 10-60 minutes for DNS propagation

**Test:** Visit `https://profiles.ginger.healthcare`

---

## 📊 SCALING

### Railway
- **Free Tier:** 500 hours/month
- **Upgrade:** $5/month for unlimited
- **Auto-scaling:** Included

### Render
- **Free Tier:** Limited (spins down after inactivity)
- **Upgrade:** $7/month for always-on
- **Easy scaling:** Click to upgrade

### Heroku
- **Free Tier:** Discontinued
- **Paid:** $7/month minimum
- **Easy scaling:** `heroku ps:scale web=2`

---

## 🐛 TROUBLESHOOTING

### App won't start?
```bash
# Check logs
# Railway: View in dashboard
# Render: View in dashboard
# Heroku: heroku logs --tail
```

### Dependencies not installing?
```bash
# Verify requirements.txt is correct
# Check Python version (use 3.8+)
```

### Can't connect to Google Sheets?
```bash
# Check if Sheets URL is public
# Verify read permissions
# Test URL in browser
```

### 500 Error on production?
```bash
# Check logs for error details
# Verify all files uploaded
# Check environment variables
```

---

## 🔄 UPDATING PRODUCTION

### When you make changes:

```bash
# Make your changes locally
git add .
git commit -m "Description of changes"
git push

# Railway/Render: Auto-deploys!
# Heroku: git push heroku main
```

**Deployment time:** 2-5 minutes

---

## 📈 PERFORMANCE TIPS

1. **Enable caching:** For repeated requests
2. **Optimize images:** Compress if adding any
3. **Use CDN:** For static files (future)
4. **Monitor:** Set up uptime monitoring

---

## 💰 COST ESTIMATES

### Free Tier (Railway)
- **500 hours/month:** ~$0/month
- **Good for:** Testing, low traffic
- **Sleeps:** Never (if under 500 hours)

### Paid Tier (Railway)
- **Unlimited:** $5/month
- **Good for:** Production use
- **Sleeps:** Never
- **Custom domain:** Included

### Render
- **Free:** $0 (spins down when idle)
- **Paid:** $7/month (always on)

### Heroku
- **Basic:** $7/month
- **Standard:** $25/month

**Recommended for production:** Railway $5/month

---

## 🎯 FINAL CHECKLIST

Before going live:

- [ ] Code pushed to GitHub
- [ ] Deployed to Railway/Render/Heroku
- [ ] App accessible via URL
- [ ] Login works
- [ ] Profile generation works
- [ ] Document download works
- [ ] Admin password changed
- [ ] Custom domain configured (optional)
- [ ] SSL certificate active (auto)
- [ ] Monitoring set up

---

## 🆘 NEED HELP?

**Deployment issues?**
1. Check platform documentation
2. Review error logs
3. Verify all steps completed
4. Contact: admin@ginger.healthcare

---

## 🎊 CONGRATULATIONS!

**Your Ginger Universe is now LIVE!** 🫚🚀

**Share your URL and start generating profiles!**

---

**Quick Access URLs:**
- Railway: https://railway.app
- Render: https://render.com
- Heroku: https://heroku.com

**Your Platform:** https://profiles.ginger.healthcare *(once DNS configured)*

---

*Deployed with ❤️ for Ginger Universe*
