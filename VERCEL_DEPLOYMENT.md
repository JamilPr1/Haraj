# Vercel Deployment Guide

## ✅ Vercel Configuration Complete

The project is now configured for Vercel deployment with:

1. **`api/index.py`** - Vercel serverless function entrypoint
2. **`vercel.json`** - Vercel configuration file
3. **Path handling** - Updated to work in Vercel's serverless environment

## 🚀 Deployment Steps

1. **Push the changes to GitHub:**
   ```bash
   git add .
   git commit -m "Add Vercel deployment configuration"
   git push origin main
   ```

2. **Vercel will automatically detect and deploy** from your GitHub repository

## ⚠️ Important Notes

### Selenium Limitations on Vercel

**Vercel serverless functions have limitations that may affect scraping:**

1. **Execution Timeout**: Vercel free tier has 10-second timeout, Pro has 60 seconds
2. **Memory Limits**: Limited memory may not be enough for Selenium/Chrome
3. **Chrome/Chromium**: May not be available in Vercel's serverless environment
4. **File System**: Ephemeral file system (files don't persist between invocations)

### Recommended Solutions

1. **For Dashboard Only** (Viewing scraped data):
   - ✅ Works perfectly on Vercel
   - Dashboard can view and download existing scraped data
   - Settings can be saved (though may not persist across deployments)

2. **For Scraping** (Active scraping):
   - ❌ May not work reliably on Vercel due to Selenium requirements
   - Consider using:
     - **Railway** (supports long-running processes)
     - **Render** (supports background workers)
     - **Heroku** (supports Selenium)
     - **DigitalOcean App Platform** (supports Docker)
     - **AWS EC2** or **Google Cloud Compute** (full control)

### Alternative: Hybrid Approach

- Deploy dashboard to Vercel (for viewing data)
- Run scraper on a separate service (Railway, Render, etc.)
- Scraper saves data to shared storage (database, S3, etc.)
- Dashboard reads from shared storage

## 📝 Current Configuration

- **Entrypoint**: `api/index.py`
- **Flask App**: Exported as `application` (Vercel requirement)
- **Routes**: All routes handled by Flask app
- **Python Version**: 3.9 (specified in `runtime.txt`)

## 🔧 Troubleshooting

If deployment fails:

1. Check Vercel build logs
2. Ensure all dependencies are in `requirements.txt`
3. Check that `api/index.py` exists and exports `application`
4. Verify `vercel.json` configuration

## 📚 Resources

- [Vercel Flask Documentation](https://vercel.com/docs/frameworks/backend/flask)
- [Vercel Python Runtime](https://vercel.com/docs/functions/runtimes/python)
