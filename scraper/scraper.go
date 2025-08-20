package scraper

import (
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/go-rod/rod"
	"github.com/go-rod/rod/lib/launcher"
	"github.com/go-rod/stealth"
	"github.com/joho/godotenv"
)

type ProxyManager struct {
	proxies     []string
	current     int
	retryCount  map[string]int
	maxRetries  int
	usedProxies map[string]time.Time
}

func NewProxyManager() (*ProxyManager, error) {
	// Load environment variables
	err := godotenv.Load()
	if err != nil {
		log.Printf("Warning: Error loading .env file: %v", err)
	}

	apiKey := os.Getenv("WEBSHARE_API_KEY")
	proxyURL := os.Getenv("WEBSHARE_PROXY_URL")

	if apiKey == "" || proxyURL == "" {
		return nil, fmt.Errorf("WEBSHARE_API_KEY and WEBSHARE_PROXY_URL must be set in .env file")
	}

	allProxies, err := fetchProxies(apiKey, proxyURL)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch proxies: %v", err)
	}

	// Use only first 200 proxies for better bandwidth distribution
	// This gives each proxy ~1.25GB instead of 250MB per month
	maxProxies := 200
	if len(allProxies) > maxProxies {
		allProxies = allProxies[:maxProxies]
		log.Printf("🎯 Using %d proxies for better bandwidth per proxy (~1.25GB each)", maxProxies)
	}

	pm := &ProxyManager{
		proxies:     allProxies,
		current:     rand.Intn(len(allProxies)), // Start from random position
		retryCount:  make(map[string]int),
		maxRetries:  3,
		usedProxies: make(map[string]time.Time),
	}

	// Pre-ban known problematic IPs
	knownBannedIPs := []string{
		"192.210.191.185", // Previously banned IP
	}

	for _, bannedIP := range knownBannedIPs {
		for _, proxy := range allProxies {
			if strings.Contains(proxy, bannedIP) {
				pm.MarkProxyBanned(proxy)
				log.Printf("🚫 Pre-banned known bad proxy: %s", proxy)
			}
		}
	}

	log.Printf("✅ Proxy manager initialized with %d proxies, starting at position %d", len(allProxies), pm.current)
	return pm, nil
}

func fetchProxies(apiKey, proxyURL string) ([]string, error) {
	client := &http.Client{Timeout: 30 * time.Second}

	req, err := http.NewRequest("GET", proxyURL, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("Authorization", "Token "+apiKey)

	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to fetch proxies, status: %d", resp.StatusCode)
	}

	// Read the response body
	body := make([]byte, 0, 1024*1024) // 1MB buffer
	buf := make([]byte, 1024)
	for {
		n, err := resp.Body.Read(buf)
		if n > 0 {
			body = append(body, buf[:n]...)
		}
		if err != nil {
			break
		}
	}

	// Parse proxy list - Webshare returns proxies in format: host:port:username:password
	lines := strings.Split(string(body), "\n")
	var proxies []string

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		// Parse host:port:username:password format
		parts := strings.Split(line, ":")
		if len(parts) >= 4 {
			host := parts[0]
			port := parts[1]
			username := parts[2]
			password := parts[3]

			// Format as http://username:password@host:port
			proxyURL := fmt.Sprintf("http://%s:%s@%s:%s", username, password, host, port)
			proxies = append(proxies, proxyURL)
		}
	}

	log.Printf("Fetched %d proxies from Webshare", len(proxies))

	if len(proxies) == 0 {
		return nil, fmt.Errorf("no valid proxies found in response")
	}

	return proxies, nil
}

func (pm *ProxyManager) GetNextProxy() string {
	if len(pm.proxies) == 0 {
		return ""
	}

	// Find a proxy that hasn't been used recently or has low retry count
	now := time.Now()

	// Try to find a completely fresh proxy first
	for attempts := 0; attempts < len(pm.proxies); attempts++ {
		pm.current = (pm.current + 1) % len(pm.proxies)
		proxy := pm.proxies[pm.current]

		// Skip banned/failed proxies entirely
		if pm.retryCount[proxy] >= pm.maxRetries {
			continue
		}

		// Skip recently used proxies (within 60 seconds for more aggressive rotation)
		if lastUsed, exists := pm.usedProxies[proxy]; exists {
			if now.Sub(lastUsed) < 60*time.Second {
				continue
			}
		}

		// This proxy looks good - mark it as used and return
		pm.usedProxies[proxy] = now
		log.Printf("🔄 Selected fresh proxy: %s (usage #%d)", proxy, pm.retryCount[proxy]+1)
		return proxy
	}

	// If no fresh proxies, try any non-banned proxy
	log.Printf("⚠️ No fresh proxies available, trying any non-banned proxy...")
	for attempts := 0; attempts < len(pm.proxies); attempts++ {
		pm.current = (pm.current + 1) % len(pm.proxies)
		proxy := pm.proxies[pm.current]

		// Only skip completely banned proxies
		if pm.retryCount[proxy] >= pm.maxRetries {
			continue
		}

		pm.usedProxies[proxy] = now
		log.Printf("🔄 Selected recycled proxy: %s (usage #%d)", proxy, pm.retryCount[proxy]+1)
		return proxy
	}

	// Last resort - reset everything and try again
	log.Printf("🚨 All proxies appear banned! Resetting ban tracking...")
	pm.retryCount = make(map[string]int)
	pm.usedProxies = make(map[string]time.Time)

	// Pick a random proxy to restart
	randomIndex := rand.Intn(len(pm.proxies))
	proxy := pm.proxies[randomIndex]
	pm.current = randomIndex
	pm.usedProxies[proxy] = now
	log.Printf("🔄 Emergency proxy selection: %s", proxy)
	return proxy
}

func (pm *ProxyManager) MarkProxyFailed(proxy string) {
	pm.retryCount[proxy]++
	log.Printf("❌ Proxy failed: %s (failure count: %d/%d)", proxy, pm.retryCount[proxy], pm.maxRetries)

	// If this is a ban/block, mark proxy as temporarily unusable
	if pm.retryCount[proxy] >= pm.maxRetries {
		log.Printf("🚫 Proxy %s marked as unusable due to repeated failures", proxy)
	}
}

// MarkProxyBanned marks a proxy as banned (more severe than failed)
func (pm *ProxyManager) MarkProxyBanned(proxy string) {
	pm.retryCount[proxy] = pm.maxRetries + 1 // Exceed max retries to disable
	log.Printf("🛑 Proxy BANNED: %s - removing from rotation", proxy)
}

// GetHealthyProxies returns count of healthy proxies
func (pm *ProxyManager) GetHealthyProxies() int {
	healthy := 0
	for _, proxy := range pm.proxies {
		if pm.retryCount[proxy] < pm.maxRetries {
			healthy++
		}
	}
	return healthy
}

func (pm *ProxyManager) GetProxyStats() map[string]interface{} {
	return map[string]interface{}{
		"total_proxies":    len(pm.proxies),
		"active_proxies":   len(pm.proxies) - len(pm.retryCount),
		"failed_proxies":   len(pm.retryCount),
		"current_rotation": pm.current,
	}
}

// TakeScreenshot takes a screenshot of the given URL using Rod with stealth mode and proxy rotation
func TakeScreenshot(targetURL string) string {
	// Initialize proxy manager
	proxyManager, err := NewProxyManager()
	if err != nil {
		log.Printf("Warning: Could not initialize proxy manager: %v", err)
		// Continue without proxy
	}

	// Set up launcher with stealth mode (NOT headless for proxy debugging)
	l := launcher.New().
		Headless(false). // Changed to false for debugging
		NoSandbox(true).
		Set("disable-blink-features", "AutomationControlled").
		Set("disable-features", "VizDisplayCompositor")

	// Add proxy if available
	var currentProxy string
	if proxyManager != nil {
		proxy := proxyManager.GetNextProxy()
		if proxy != "" {
			currentProxy = proxy
			// Parse the proxy URL to get components
			proxyURL, err := url.Parse(proxy)
			if err == nil {
				// Chrome/Rod proxy format: just host:port
				proxyServer := fmt.Sprintf("%s:%s", proxyURL.Hostname(), proxyURL.Port())
				l = l.Set("proxy-server", proxyServer)

				// Handle authentication through a different method
				username := proxyURL.User.Username()
				password, _ := proxyURL.User.Password()
				if username != "" && password != "" {
					log.Printf("🔄 Using proxy: %s (auth: %s:***)", proxyServer, username)
				} else {
					log.Printf("🔄 Using proxy: %s (no auth)", proxyServer)
				}
				log.Printf("🔄 Full proxy config: %s", proxy)
			} else {
				log.Printf("❌ Error parsing proxy URL: %v", err)
			}
		} else {
			log.Printf("⚠️  No proxy available from manager")
		}
	} else {
		log.Printf("🚫 No proxy manager initialized - using direct connection")
	}

	// Launch browser
	controlURL := l.MustLaunch()
	browser := rod.New().ControlURL(controlURL).MustConnect()
	defer browser.MustClose()

	// Set proxy authentication if needed
	if currentProxy != "" {
		proxyURL, _ := url.Parse(currentProxy)
		if proxyURL != nil && proxyURL.User != nil {
			username := proxyURL.User.Username()
			password, _ := proxyURL.User.Password()
			if username != "" && password != "" {
				// Use Rod's built-in proxy authentication
				browser.MustHandleAuth(username, password)
				log.Printf("🔐 Proxy authentication set for %s", username)
			}
		}
	}

	// Create page with stealth mode
	page := stealth.MustPage(browser)
	defer page.MustClose()

	// Set realistic user agent and viewport
	page.MustEval(`() => {
		Object.defineProperty(navigator, 'userAgent', {
			get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
		});
	}`)
	page.MustSetViewport(1920, 1080, 1, false)

	// Add random delay to appear more human-like
	time.Sleep(time.Duration(rand.Intn(3)+1) * time.Second)

	// Navigate to the target URL
	if currentProxy != "" {
		log.Printf("🌐 Navigating to: %s (via proxy: %s)", targetURL, currentProxy)
	} else {
		log.Printf("🌐 Navigating to: %s (direct connection)", targetURL)
	}
	page.MustNavigate(targetURL)

	// Wait for page to load
	page.MustWaitLoad()

	// Additional wait for dynamic content
	time.Sleep(3 * time.Second)

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
	screenshot, err := page.Screenshot(true, nil)
	if err != nil {
		log.Printf("Error taking screenshot: %v", err)
		return ""
	}

	// Save screenshot to file
	err = os.WriteFile(filepath, screenshot, 0644)
	if err != nil {
		log.Printf("Error saving screenshot: %v", err)
		return ""
	}

	if currentProxy != "" {
		log.Printf("📸 Screenshot saved: %s (via proxy: %s)", filepath, currentProxy)
	} else {
		log.Printf("📸 Screenshot saved: %s (direct connection)", filepath)
	}
	return filepath
}
