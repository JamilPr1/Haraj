# Vercel Deployment Troubleshooting

## Current Status

The code has been updated with comprehensive error handling for Vercel deployment. If you're still seeing errors, check the Vercel logs for the specific error message.

## Recent Fixes Applied

1. ✅ **Error Handling in `api/index.py`**
   - Added try-catch around all imports
   - Fallback Flask app if dashboard import fails
   - Detailed error messages with tracebacks

2. ✅ **Flask Template Path**
   - Explicit template folder path
   - Works in Vercel's serverless environment

3. ✅ **Scraper Import Handling**
   - Selenium scraper only imported when needed (not at module level)
   - Graceful error handling if Selenium unavailable

4. ✅ **Path Handling**
   - Absolute paths based on script location
   - Works regardless of working directory

## How to Debug

1. **Check Vercel Logs:**
   - Go to Vercel Dashboard → Your Project → Logs
   - Look for the error message and stack trace
   - The error handler will show detailed traceback

2. **Common Issues:**

   **Issue: Import Error**
   - **Cause**: Missing dependencies or path issues
   - **Fix**: Check `requirements.txt` includes all dependencies
   - **Check**: Verify `api/index.py` can find `dashboard.py`

   **Issue: Template Not Found**
   - **Cause**: Template path incorrect
   - **Fix**: Already fixed with explicit template_folder
   - **Check**: Verify `templates/` directory exists

   **Issue: Selenium Not Available**
   - **Cause**: Selenium/Chrome not available in Vercel
   - **Fix**: Scraper import is now wrapped in try-catch
   - **Note**: Scraping won't work, but dashboard viewing will

3. **Test Locally:**
   ```bash
   # Install Vercel CLI
   npm i -g vercel
   
   # Test locally
   vercel dev
   ```

## Expected Behavior

- ✅ Dashboard should load (viewing listings)
- ✅ Settings page should work
- ✅ Download JSON/CSV should work
- ⚠️ Scraping may not work (Selenium limitations)
- ⚠️ Settings may not persist (ephemeral file system)

## Next Steps if Still Failing

1. Check Vercel logs for the exact error
2. Share the error message from logs
3. Verify all files are pushed to GitHub
4. Check that `api/index.py` exists and exports `application`

## Alternative Deployment Options

If Vercel continues to have issues, consider:
- **Railway** - Better for long-running processes
- **Render** - Supports background workers
- **Heroku** - Full Selenium support
- **DigitalOcean App Platform** - Docker support
