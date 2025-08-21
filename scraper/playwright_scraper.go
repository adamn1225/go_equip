package scraper

import (
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/adamn1225/hybrid-ocr-agent/scraper/internal/proxy"
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

// Worker-specific browser session management
type WorkerSession struct {
	Browser playwright.Browser
	Context playwright.BrowserContext
	Page    playwright.Page
	Mutex   sync.Mutex
	Active  bool
}

var workerSessions = make(map[int]*WorkerSession)
var workerSessionMutex sync.Mutex

// logMissedPage logs pages that couldn't be processed for later retry
func logMissedPage(workerID int, url string, reason string) {
	timestamp := time.Now().Format("20060102_150405")
	missedPageFile := fmt.Sprintf("missed_pages/worker%d_missed_%s.json", workerID, timestamp)

	// Create missed pages directory
	os.MkdirAll("missed_pages", 0755)

	missedPageData := map[string]interface{}{
		"timestamp":   time.Now().Format(time.RFC3339),
		"worker_id":   workerID,
		"url":         url,
		"reason":      reason,
		"page_number": extractPageNumber(url),
	}

	if jsonData, err := json.Marshal(missedPageData); err == nil {
		os.WriteFile(missedPageFile, jsonData, 0644)
		log.Printf("📝 Worker %d: Missed page logged: %s (Reason: %s)", workerID, missedPageFile, reason)
	}
}

// extractPageNumber extracts page number from URL for easier tracking
func extractPageNumber(url string) int {
	re := regexp.MustCompile(`page[=:](\d+)`)
	matches := re.FindStringSubmatch(url)
	if len(matches) > 1 {
		if pageNum, err := strconv.Atoi(matches[1]); err == nil {
			return pageNum
		}
	}
	return 0
}

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

	// Add proxy if available (re-enabled for proxy rotation)
	if proxyManager != nil && len(proxyManager.proxies) > 0 {
		proxy := proxyManager.GetNextProxy()
		if proxy != "" {
			log.Printf("🔄 Using proxy for Playwright session: %s", proxy)

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

	// Wait for page to load and check for blocks/bans
	time.Sleep(3 * time.Second)

	// Check for Cloudflare blocks and IP bans first
	banSelectors := []string{
		"text=Access denied",
		"text=banned your IP address",
		"text=Error 1007",
		"text=Error 1006",
		"text=Ray ID:",
		".cf-error-title",
		"#cf-error-details",
	}

	for _, selector := range banSelectors {
		locator := globalPage.Locator(selector)
		count, err := locator.Count()
		if err == nil && count > 0 {
			log.Printf("🚫 IP BAN/BLOCK detected with selector: %s", selector)

			// Get page content for debugging
			content, _ := globalPage.Content()
			if strings.Contains(content, "banned your IP address") || strings.Contains(content, "Error 1007") {
				log.Printf("🛑 CONFIRMED: Cloudflare IP ban detected!")

				// Mark current proxy as banned if we can identify it
				// Note: This requires tracking which proxy was used for this session
				return "" // Return empty to trigger proxy rotation
			}
		}
	}

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

// InitializeWorkerBrowserSession creates a worker-specific browser session
func InitializeWorkerBrowserSession(workerID int, proxyManager *proxy.ProxyManager) error {
	workerSessionMutex.Lock()
	defer workerSessionMutex.Unlock()

	// Check if session already exists
	if session, exists := workerSessions[workerID]; exists && session.Active {
		return nil
	}

	log.Printf("🚀 Worker %d: Initializing browser session...", workerID)

	// Install browsers if needed
	err := playwright.Install()
	if err != nil {
		log.Printf("Error installing Playwright browsers: %v", err)
	}

	// Start Playwright
	pw, err := playwright.Run()
	if err != nil {
		return fmt.Errorf("error starting Playwright for worker %d: %v", workerID, err)
	}

	// Browser launch options
	browserOptions := playwright.BrowserTypeLaunchOptions{
		Headless: playwright.Bool(false), // Keep visible for debugging
		Args: []string{
			"--disable-blink-features=AutomationControlled",
			"--no-first-run",
			"--disable-default-apps",
		},
	}

	// Add proxy if available
	if proxyManager != nil {
		proxy, err := proxyManager.GetNextProxy()
		if err == nil && proxy != nil {
			proxyURL := fmt.Sprintf("%s://%s:%d", proxy.Type, proxy.Host, proxy.Port)
			log.Printf("🌐 Worker %d: Using proxy: %s", workerID, proxyURL)
			browserOptions.Proxy = &playwright.Proxy{
				Server: proxyURL,
			}
		}
	}

	// Launch browser
	browser, err := pw.Chromium.Launch(browserOptions)
	if err != nil {
		return fmt.Errorf("error launching browser for worker %d: %v", workerID, err)
	}

	// Create browser context with unique user data directory
	contextOptions := playwright.BrowserNewContextOptions{
		UserAgent: playwright.String("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
		Viewport: &playwright.Size{
			Width:  1920,
			Height: 1080,
		},
		Locale:      playwright.String("en-US"),
		TimezoneId:  playwright.String("America/New_York"),
		Permissions: []string{"geolocation"},
		Geolocation: &playwright.Geolocation{Latitude: 40.7589, Longitude: -73.9851},
	}

	context, err := browser.NewContext(contextOptions)
	if err != nil {
		browser.Close()
		return fmt.Errorf("error creating context for worker %d: %v", workerID, err)
	}

	// Create new page
	page, err := context.NewPage()
	if err != nil {
		context.Close()
		browser.Close()
		return fmt.Errorf("error creating page for worker %d: %v", workerID, err)
	}

	// Store the session
	workerSessions[workerID] = &WorkerSession{
		Browser: browser,
		Context: context,
		Page:    page,
		Active:  true,
	}

	log.Printf("✅ Worker %d: Browser session initialized successfully", workerID)
	return nil
}

// TakeScreenshotPlaywrightWorker takes a screenshot using worker-specific browser session with enhanced CAPTCHA handling
func TakeScreenshotPlaywrightWorker(workerID int, targetURL string) string {
	workerSessionMutex.Lock()
	session, exists := workerSessions[workerID]
	workerSessionMutex.Unlock()

	if !exists || !session.Active {
		log.Printf("❌ Worker %d: No active browser session", workerID)
		return ""
	}

	session.Mutex.Lock()
	defer session.Mutex.Unlock()

	// Add random delay to appear more human-like
	time.Sleep(time.Duration(rand.Intn(2)+1) * time.Second)

	// Navigate to the target URL
	log.Printf("🌐 Worker %d: Navigating to: %s", workerID, targetURL)
	maxRetries := 3
	var navErr error

	for retry := 0; retry < maxRetries; retry++ {
		if retry > 0 {
			log.Printf("🔄 Worker %d: Retry attempt %d for page navigation", workerID, retry+1)
			time.Sleep(time.Duration(retry*2) * time.Second)
		}

		_, navErr = session.Page.Goto(targetURL, playwright.PageGotoOptions{
			WaitUntil: playwright.WaitUntilStateNetworkidle,
			Timeout:   playwright.Float(60000),
		})

		if navErr == nil {
			break
		}

		log.Printf("❌ Worker %d: Navigation attempt %d failed: %v", workerID, retry+1, navErr)
	}

	if navErr != nil {
		log.Printf("❌ Worker %d: Error navigating to page: %v", workerID, navErr)
		logMissedPage(workerID, targetURL, "NAVIGATION_FAILED")
		return ""
	}

	// Wait for page to load
	time.Sleep(3 * time.Second)

	// Enhanced CAPTCHA detection and auto-click handling
	content, _ := session.Page.Content()
	detector := NewCAPTCHADetector()
	captchaDetected := detector.DetectCAPTCHAInPageSource(content)
	if captchaDetected {
		log.Printf("🔍 Worker %d: CAPTCHA detected, waiting for full page load...", workerID)

		// Wait longer for CAPTCHA page to fully load and render
		time.Sleep(10 * time.Second)

		log.Printf("🔍 Worker %d: Attempting auto-click...", workerID)

		// Try to auto-click hCaptcha checkbox to trigger the puzzle
		if autoClickSuccess := tryAutoClickHCaptcha(session.Page, workerID); autoClickSuccess {
			log.Printf("✅ Worker %d: hCaptcha auto-click successful, waiting for puzzle to fully render...", workerID)

			// Wait longer for puzzle to appear and render completely
			time.Sleep(10 * time.Second)

			// Check if puzzle appeared
			puzzleAppeared := checkForCaptchaPuzzle(session.Page)
			if puzzleAppeared {
				log.Printf("🧩 Worker %d: CAPTCHA puzzle appeared and rendered successfully", workerID)

				// Additional wait to ensure puzzle images are fully loaded
				time.Sleep(5 * time.Second)
			} else {
				log.Printf("⚠️ Worker %d: Auto-click succeeded but puzzle didn't appear", workerID)
			}
		} else {
			log.Printf("❌ Worker %d: CAPTCHA solving failed: Manual solving required", workerID)
			log.Printf("🔄 Worker %d: Falling back to manual solving...", workerID)

			// Log this page as requiring manual attention
			logMissedPage(workerID, session.Page.URL(), "CAPTCHA_MANUAL_SOLVE_REQUIRED")

			// CAPTCHA will need to be solved manually - the browser window is visible for this
		}
	}

	// Generate screenshot filename
	timestamp := time.Now().Format("20060102_150405")
	imagePath := fmt.Sprintf("screenshots/worker%d_screenshot_%s.png", workerID, timestamp)

	// Create screenshots directory if it doesn't exist
	if err := os.MkdirAll("screenshots", 0755); err != nil {
		log.Printf("Worker %d: Error creating screenshots directory: %v", workerID, err)
		return ""
	}

	// Take screenshot
	if _, err := session.Page.Screenshot(playwright.PageScreenshotOptions{
		Path:     playwright.String(imagePath),
		FullPage: playwright.Bool(true),
	}); err != nil {
		log.Printf("❌ Worker %d: Error taking screenshot: %v", workerID, err)
		return ""
	}

	log.Printf("📸 Worker %d: Screenshot saved: %s", workerID, imagePath)
	return imagePath
}

// tryAutoClickHCaptcha attempts to click hCaptcha checkbox to trigger puzzle
func tryAutoClickHCaptcha(page playwright.Page, workerID int) bool {
	// Multiple selector strategies for different hCaptcha implementations
	selectors := []string{
		"div.checkbox-container",
		".h-captcha iframe",
		"iframe[src*='hcaptcha']",
		"#h-captcha iframe",
		".h-captcha-checkbox",
		"[data-hcaptcha-widget-id]",
		"div[id*='hcaptcha']",
	}

	for _, selector := range selectors {
		log.Printf("🔍 Worker %d: Trying selector: %s", workerID, selector)

		element, err := page.QuerySelector(selector)
		if err != nil || element == nil {
			continue
		}

		log.Printf("✅ Worker %d: Found hCaptcha element with selector: %s", workerID, selector)

		// If it's an iframe, we need to click inside it
		if strings.Contains(selector, "iframe") {
			// Switch to iframe context
			frame, err := element.ContentFrame()
			if err == nil && frame != nil {
				log.Printf("🔄 Worker %d: Switching to iframe context", workerID)

				// Look for checkbox inside iframe
				checkboxSelectors := []string{
					".checkbox-container",
					"#checkbox",
					"[role='checkbox']",
					".captcha-checkbox",
					"div[tabindex='0']",
				}

				for _, checkboxSel := range checkboxSelectors {
					checkbox, err := frame.QuerySelector(checkboxSel)
					if err == nil && checkbox != nil {
						log.Printf("✅ Worker %d: Found checkbox in iframe: %s", workerID, checkboxSel)

						// Click the checkbox
						if err := checkbox.Click(); err == nil {
							log.Printf("🎯 Worker %d: Successfully clicked hCaptcha checkbox", workerID)
							return true
						}
					}
				}
			}
		} else {
			// Direct click on the element
			if err := element.Click(); err == nil {
				log.Printf("🎯 Worker %d: Successfully clicked hCaptcha element", workerID)
				return true
			}
		}
	}

	log.Printf("❌ Worker %d: Could not find or click hCaptcha checkbox", workerID)
	return false
}

// checkForCaptchaPuzzle checks if a CAPTCHA puzzle appeared after clicking
func checkForCaptchaPuzzle(page playwright.Page) bool {
	// Wait a moment for puzzle to load
	time.Sleep(2 * time.Second)

	// Look for common CAPTCHA puzzle indicators
	puzzleSelectors := []string{
		".challenge-container",
		".captcha-puzzle",
		"iframe[src*='challenge']",
		".h-captcha-challenge",
		"[data-challenge]",
		".puzzle-image",
		".captcha-images",
	}

	for _, selector := range puzzleSelectors {
		element, err := page.QuerySelector(selector)
		if err == nil && element != nil {
			return true
		}
	}

	return false
}

// CloseWorkerBrowserSession closes worker-specific browser session
func CloseWorkerBrowserSession(workerID int) {
	workerSessionMutex.Lock()
	defer workerSessionMutex.Unlock()

	if session, exists := workerSessions[workerID]; exists && session.Active {
		session.Mutex.Lock()
		session.Context.Close()
		session.Browser.Close()
		session.Active = false
		session.Mutex.Unlock()
		delete(workerSessions, workerID)
		log.Printf("🧹 Worker %d: Browser session cleaned up", workerID)
	}
}
