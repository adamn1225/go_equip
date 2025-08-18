# 🤖 AI-Powered CAPTCHA Solver

Automatically solve CAPTCHAs to maintain continuous scraping operations. This AI integration eliminates manual CAPTCHA intervention and keeps your scrapers running 24/7.

## 🚀 Features

### **Multi-Method CAPTCHA Solving:**
- ✅ **reCAPTCHA v2** - Using 2captcha API
- ✅ **hCaptcha** - Using AntiCaptcha API  
- ✅ **Image CAPTCHAs** - Local OCR + API fallback
- ✅ **Text CAPTCHAs** - OCR-based solving
- ✅ **Auto-Detection** - Automatically detects CAPTCHA type

### **Integration Options:**
- 🔗 **Go Scraper Integration** - Direct API calls from Go
- 🌐 **HTTP Bridge Service** - RESTful API for any language
- 🧪 **Standalone Testing** - Test solver on any URL
- ⚙️ **Configurable** - Multiple API services and local OCR

## 📦 Quick Setup

### 1. **Run Setup Script:**
```bash
./setup_captcha_solver.sh
```

### 2. **Configure API Keys:**
Edit `ai/captcha_config.py`:
```python
# Get API key from https://2captcha.com
API_KEY_2CAPTCHA = "your_2captcha_api_key_here"

# Get API key from https://anti-captcha.com  
API_KEY_ANTICAPTCHA = "your_anticaptcha_api_key_here"
```

### 3. **Start CAPTCHA Solver Service:**
```bash
./start_captcha_solver.sh
```

## 🎯 Usage

### **From Go Scraper (Automatic):**
The CAPTCHA solver integrates automatically with your existing scraper:

```go
import "github.com/adamn1225/hybrid-ocr-agent/scraper"

// Your existing scraping code
screenshotPath := scraper.TakeScreenshotPlaywrightWithCAPTCHA(targetURL)
// ↑ This now automatically solves CAPTCHAs!
```

### **HTTP API (Manual):**
```bash
# Start the service
./start_captcha_solver.sh

# Solve CAPTCHA via HTTP
curl -X POST http://localhost:5000/solve-captcha \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/captcha-page"}'
```

### **Command Line Testing:**
```bash
./test_captcha_solver.sh https://example.com/captcha-page
```

## 🔧 Configuration

### **API Services:**

| Service | Type | Cost | Speed | Success Rate |
|---------|------|------|-------|--------------|
| **2captcha** | reCAPTCHA, Images | ~$0.50-2.99/1K | 10-60s | ~95% |
| **AntiCaptcha** | hCaptcha, reCAPTCHA | ~$0.50-3.00/1K | 10-60s | ~95% |
| **Local OCR** | Simple Images | Free | 1-3s | ~60% |

### **Recommended Setup:**
1. **2captcha** for reCAPTCHA (most common)
2. **Local OCR** for simple image CAPTCHAs  
3. **AntiCaptcha** as fallback

## 📊 Monitoring

### **Health Check:**
```bash
curl http://localhost:5000/health
```

**Response:**
```json
{
  "status": "healthy",
  "captcha_solver": "ready",
  "api_keys_configured": {
    "2captcha": true,
    "anticaptcha": false
  }
}
```

### **Service Logs:**
```bash
# View real-time logs
tail -f captcha_solver.log
```

## 🎯 Business Impact

### **Before CAPTCHA Solver:**
- ❌ Scraping stops at CAPTCHAs
- ❌ Manual intervention required  
- ❌ Limited to business hours
- ❌ Missed data collection opportunities

### **After CAPTCHA Solver:**
- ✅ **24/7 Continuous Operation**
- ✅ **95%+ Success Rate**
- ✅ **Automatic Resolution** 
- ✅ **Complete Data Coverage**

### **ROI Calculation:**
```
Cost: ~$2-5 per day for API services
Value: Continuous data collection = 24/7 operations
Break-even: Usually within first day of operation
```

## 🔍 Troubleshooting

### **Common Issues:**

#### **"CAPTCHA solver service not available"**
```bash
# Start the service
./start_captcha_solver.sh

# Check if running
curl http://localhost:5000/health
```

#### **"2captcha API key not set"**
1. Sign up at https://2captcha.com
2. Add funds to account ($5 minimum)
3. Get API key from dashboard
4. Set in `ai/captcha_config.py`

#### **OCR not working**
```bash
# Install tesseract
sudo apt-get install tesseract-ocr tesseract-ocr-eng
```

#### **Playwright browser issues**
```bash
# Reinstall browsers
source ai_env/bin/activate
playwright install chromium
```

## 📈 Advanced Features

### **Custom CAPTCHA Types:**
Add support for site-specific CAPTCHAs:

```python
# In ai/captcha_solver.py
def _solve_custom_captcha(self, page, captcha_info):
    # Your custom CAPTCHA solving logic
    pass
```

### **Performance Optimization:**
```python
# Parallel solving for multiple CAPTCHAs
class BatchCAPTCHASolver:
    def solve_multiple(self, captcha_requests):
        # Batch processing implementation
        pass
```

### **Analytics Integration:**
```python
# Track solving success rates
class CAPTCHAAnalytics:
    def track_solve_attempt(self, captcha_type, success, solve_time):
        # Analytics implementation
        pass
```

## 💡 Future Enhancements

### **Planned Features:**
- 🔮 **AI CAPTCHA Recognition** - Custom trained models
- 🧠 **Pattern Learning** - Adapt to site-specific CAPTCHAs
- 📱 **Mobile CAPTCHA Support** - Handle mobile-specific challenges
- 🔄 **Auto-Retry Logic** - Intelligent retry strategies
- 📊 **Success Rate Analytics** - Performance monitoring dashboard

## 🆘 Support

### **Getting API Keys:**
- **2captcha**: https://2captcha.com/enterpage
- **AntiCaptcha**: https://anti-captcha.com/clients/registers/add

### **Cost Estimates:**
- **Light usage**: $5-10/month (few hundred CAPTCHAs)
- **Medium usage**: $20-50/month (few thousand CAPTCHAs)  
- **Heavy usage**: $100+/month (continuous operation)

### **Need Help?**
1. Check the troubleshooting section above
2. Review logs in `captcha_solver.log`
3. Test with `./test_captcha_solver.sh <url>`
4. Verify API keys are set correctly

---

## 🎯 Ready to Deploy!

Your CAPTCHA solver is now ready to eliminate manual intervention and keep your scrapers running continuously. Start with the setup script and you'll be solving CAPTCHAs automatically within minutes!

```bash
# Get started now:
./setup_captcha_solver.sh
```
