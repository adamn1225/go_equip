package scraper

import (
	"fmt"
	"log"
	"math/rand"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/playwright-community/playwright-go"
)

// Global browser session management
var (
	globalBrowser playwright.Browser
	globalContext playwright.BrowserContext
	globalPage    playwright.Page
	sessionMutex  sync.Mutex
	sessionActive bool
)

// InitializeBrowserSession creates a persistent browser session
func InitializeBrowserSession() error {
	sessionMutex.Lock()
	defer sessionMutex.Unlock()

	if sessionActive {
		return nil // Session already active
	}

	// Initialize proxy manager
	proxyManager, err := NewProxyManager()
	if err != nil {
		log.Printf("Warning: Could not initialize proxy manager: %v", err)
	}

	// Install browsers if needed
	err = playwright.Install()
	if err != nil {
		log.Printf("Error installing Playwright browsers: %v", err)
	}

	// Start Playwright
	pw, err := playwright.Run()
	if err != nil {
		return fmt.Errorf("error starting Playwright: %v", err)
	}

	// Create browser options
	browserOptions := playwright.BrowserTypeLaunchOptions{
		Headless: playwright.Bool(false), // Run visible browser for better bot detection evasion
		Args: []string{
			"--no-sandbox",
			"--disable-setuid-sandbox",
			"--disable-blink-features=AutomationControlled",
			"--disable-features=VizDisplayCompositor",
			"--disable-web-security",
			"--disable-features=TranslateUI",
			"--disable-ipc-flooding-protection",
			"--no-first-run",
			"--no-default-browser-check",
			"--disable-background-timer-throttling",
			"--disable-backgrounding-occluded-windows",
			"--disable-renderer-backgrounding",
			"--disable-dev-shm-usage",
			"--disable-extensions",
			"--disable-plugins",
			"--disable-images", // Speed up loading
		},
	}

	// Add proxy if available (temporarily disabled for testing)
	if false && proxyManager != nil && len(proxyManager.proxies) > 0 {
		proxy := proxyManager.GetNextProxy()
		if proxy != "" {
			log.Printf("Using proxy for session: %s", proxy)

			// Parse proxy URL to extract components
			if strings.Contains(proxy, "@") {
				parts := strings.Split(proxy, "@")
				if len(parts) == 2 {
					authPart := strings.TrimPrefix(parts[0], "http://")
					hostPart := parts[1]

					authParts := strings.Split(authPart, ":")
					if len(authParts) == 2 {
						username := authParts[0]
						password := authParts[1]

						browserOptions.Proxy = &playwright.Proxy{
							Server:   "http://" + hostPart,
							Username: playwright.String(username),
							Password: playwright.String(password),
						}
					}
				}
			}
		}
	}

	// Launch browser
	browser, err := pw.Chromium.Launch(browserOptions)
	if err != nil {
		return fmt.Errorf("error launching browser: %v", err)
	}
	globalBrowser = browser

	// Create context with stealth settings
	contextOptions := playwright.BrowserNewContextOptions{
		UserAgent: playwright.String("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
		Viewport: &playwright.Size{
			Width:  1920,
			Height: 1080,
		},
		ExtraHttpHeaders: map[string]string{
			"Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
			"Accept-Language":           "en-US,en;q=0.5",
			"Accept-Encoding":           "gzip, deflate",
			"DNT":                       "1",
			"Connection":                "keep-alive",
			"Upgrade-Insecure-Requests": "1",
			"Sec-Fetch-Dest":            "document",
			"Sec-Fetch-Mode":            "navigate",
			"Sec-Fetch-Site":            "none",
		},
		Permissions: []string{"geolocation"},
	}

	// Load session state if it exists
	if _, err := os.Stat("./browser_session.json"); err == nil {
		contextOptions.StorageStatePath = playwright.String("./browser_session.json")
		log.Println("📂 Loading saved browser session...")
	}

	context, err := browser.NewContext(contextOptions)
	if err != nil {
		return fmt.Errorf("error creating context: %v", err)
	}
	globalContext = context

	// Create page
	page, err := context.NewPage()
	if err != nil {
		return fmt.Errorf("error creating page: %v", err)
	}
	globalPage = page

	// Add stealth JavaScript
	err = page.AddInitScript(playwright.Script{
		Content: playwright.String(`
			Object.defineProperty(navigator, 'webdriver', {
				get: () => undefined,
			});
			Object.defineProperty(navigator, 'languages', {
				get: () => ['en-US', 'en'],
			});
			Object.defineProperty(navigator, 'plugins', {
				get: () => [1, 2, 3, 4, 5],
			});
		`),
	})
	if err != nil {
		log.Printf("Warning: Could not add stealth script: %v", err)
	}

	sessionActive = true
	log.Println("🚀 Persistent browser session initialized!")
	return nil
}

// CloseBrowserSession closes the persistent browser session
func CloseBrowserSession() {
	sessionMutex.Lock()
	defer sessionMutex.Unlock()

	if sessionActive {
		if globalPage != nil {
			globalPage.Close()
		}
		if globalContext != nil {
			globalContext.Close()
		}
		if globalBrowser != nil {
			globalBrowser.Close()
		}
		sessionActive = false
		log.Println("🔒 Browser session closed")
	}
}

// TakeScreenshotPlaywright takes a screenshot using the persistent browser session
func TakeScreenshotPlaywright(targetURL string) string {
	// Initialize session if not already active
	if !sessionActive {
		err := InitializeBrowserSession()
		if err != nil {
			log.Printf("Error initializing browser session: %v", err)
			return ""
		}
	}

	sessionMutex.Lock()
	defer sessionMutex.Unlock()

	if !sessionActive || globalPage == nil {
		log.Printf("No active browser session")
		return ""
	}

	// Add random delay to appear more human-like
	time.Sleep(time.Duration(rand.Intn(2)+1) * time.Second)

	// Navigate to the target URL with increased timeout and retry logic
	log.Printf("Navigating to: %s", targetURL)
	log.Printf("🔍 DEBUG: About to navigate to URL: %s", targetURL)
	maxRetries := 3
	var navErr error

	for retry := 0; retry < maxRetries; retry++ {
		if retry > 0 {
			log.Printf("Retry attempt %d for page navigation", retry+1)
			time.Sleep(time.Duration(retry*2) * time.Second) // Exponential backoff
		}

		_, navErr = globalPage.Goto(targetURL, playwright.PageGotoOptions{
			WaitUntil: playwright.WaitUntilStateNetworkidle,
			Timeout:   playwright.Float(60000), // Increased to 60 seconds
		})

		if navErr == nil {
			break // Success, exit retry loop
		}

		log.Printf("Navigation attempt %d failed: %v", retry+1, navErr)
	}

	if navErr != nil {
		log.Printf("Error navigating to page: %v", navErr)
		return ""
	}

	// Log the actual URL we landed on
	actualURL := globalPage.URL()
	log.Printf("🔍 DEBUG: Successfully navigated. Current URL: %s", actualURL)
	log.Printf("🔍 DEBUG: Expected URL: %s", targetURL)

	// Wait for page to load and check for CAPTCHA
	time.Sleep(3 * time.Second)

	// Check for CAPTCHA presence
	captchaPresent := false
	captchaSelectors := []string{
		"[class*='captcha']",
		"[id*='captcha']",
		"[class*='recaptcha']",
		"[id*='recaptcha']",
		"text=Pardon Our Interruption",
		"text=Please complete the security check",
		"text=least number of animals",
	}

	for _, selector := range captchaSelectors {
		locator := globalPage.Locator(selector)
		count, err := locator.Count()
		if err == nil && count > 0 {
			captchaPresent = true
			log.Printf("⚠️  CAPTCHA detected with selector: %s", selector)
			break
		}
	}

	if captchaPresent {
		log.Println("🔐 CAPTCHA detected! Please solve it manually in the browser...")
		log.Println("   Waiting 60 seconds for manual solving...")

		// Keep browser open for manual CAPTCHA solving
		time.Sleep(60 * time.Second)

		// Check if CAPTCHA was solved
		captchaSolved := true
		for _, selector := range captchaSelectors {
			locator := globalPage.Locator(selector)
			count, err := locator.Count()
			if err == nil && count > 0 {
				captchaSolved = false
				break
			}
		}

		if captchaSolved {
			log.Println("✅ CAPTCHA appears to be solved! Continuing...")
		} else {
			log.Println("❌ CAPTCHA still present. Taking screenshot anyway...")
		}
	} else {
		log.Println("✅ No CAPTCHA detected - session is persistent!")
	}

	// Simulate human-like mouse movements
	if err := globalPage.Mouse().Move(200, 200); err == nil {
		time.Sleep(300 * time.Millisecond)
		if err := globalPage.Mouse().Move(400, 300); err == nil {
			time.Sleep(200 * time.Millisecond)
		}
	}

	// Scroll down a bit to mimic human behavior
	if _, err := globalPage.Evaluate(`() => window.scrollBy(0, 100)`); err != nil {
		log.Printf("Warning: Could not scroll: %v", err)
	}

	time.Sleep(1 * time.Second)

	// Create screenshots directory if it doesn't exist
	screenshotDir := "screenshots"
	if err := os.MkdirAll(screenshotDir, 0755); err != nil {
		log.Printf("Error creating screenshots directory: %v", err)
		return ""
	}

	// Generate filename with timestamp
	timestamp := time.Now().Format("20060102_150405")
	filename := fmt.Sprintf("screenshot_%s.png", timestamp)
	filepath := filepath.Join(screenshotDir, filename)

	// Take screenshot
	if _, err := globalPage.Screenshot(playwright.PageScreenshotOptions{
		Path:     playwright.String(filepath),
		FullPage: playwright.Bool(true),
	}); err != nil {
		log.Printf("Error taking screenshot: %v", err)
		return ""
	}

	log.Printf("📸 Screenshot saved: %s", filepath)
	return filepath
}
