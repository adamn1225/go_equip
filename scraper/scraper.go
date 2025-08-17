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
	proxies []string
	current int
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

	proxies, err := fetchProxies(apiKey, proxyURL)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch proxies: %v", err)
	}

	return &ProxyManager{
		proxies: proxies,
		current: 0,
	}, nil
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

	// Randomize proxy selection
	proxy := pm.proxies[rand.Intn(len(pm.proxies))]
	pm.current = (pm.current + 1) % len(pm.proxies)
	return proxy
}

// TakeScreenshot takes a screenshot of the given URL using Rod with stealth mode and proxy rotation
func TakeScreenshot(targetURL string) string {
	// Initialize proxy manager
	proxyManager, err := NewProxyManager()
	if err != nil {
		log.Printf("Warning: Could not initialize proxy manager: %v", err)
		// Continue without proxy
	}

	// Set up launcher with stealth mode
	l := launcher.New().
		Headless(true).
		NoSandbox(true).
		Set("disable-blink-features", "AutomationControlled").
		Set("disable-features", "VizDisplayCompositor")

	// Add proxy if available
	if proxyManager != nil {
		proxy := proxyManager.GetNextProxy()
		if proxy != "" {
			// Parse the proxy URL to get components
			proxyURL, err := url.Parse(proxy)
			if err == nil {
				// Set proxy server without auth for now
				proxyServer := fmt.Sprintf("%s:%s", proxyURL.Hostname(), proxyURL.Port())
				l = l.Set("proxy-server", proxyServer)
				log.Printf("Using proxy server: %s", proxyServer)

				// Note: Proxy authentication with username/password requires additional setup
				// For now, we'll use the proxy without auth
			}
		}
	}

	// Launch browser
	controlURL := l.MustLaunch()
	browser := rod.New().ControlURL(controlURL).MustConnect()
	defer browser.MustClose()

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
	log.Printf("Navigating to: %s", targetURL)
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

	log.Printf("Screenshot saved: %s", filepath)
	return filepath
}
