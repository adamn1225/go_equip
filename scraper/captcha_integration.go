package scraper

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// CAPTCHARequest represents a request to solve a CAPTCHA
type CAPTCHARequest struct {
	URL            string         `json:"url"`
	ScreenshotPath string         `json:"screenshot_path,omitempty"`
	UserAgent      string         `json:"user_agent,omitempty"`
	Viewport       map[string]int `json:"viewport,omitempty"`
}

// CAPTCHAResponse represents the response from CAPTCHA solver
type CAPTCHAResponse struct {
	Success   bool   `json:"success"`
	Message   string `json:"message,omitempty"`
	Error     string `json:"error,omitempty"`
	FinalURL  string `json:"final_url,omitempty"`
	PageTitle string `json:"page_title,omitempty"`
}

// CAPTCHASolverClient handles communication with the CAPTCHA solver service
type CAPTCHASolverClient struct {
	baseURL    string
	httpClient *http.Client
	timeout    time.Duration
}

// NewCAPTCHASolverClient creates a new CAPTCHA solver client
func NewCAPTCHASolverClient(baseURL string) *CAPTCHASolverClient {
	if baseURL == "" {
		baseURL = "http://localhost:5000"
	}

	return &CAPTCHASolverClient{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 5 * time.Minute, // CAPTCHAs can take time to solve
		},
		timeout: 5 * time.Minute,
	}
}

// SolveCAPTCHA sends a request to solve a CAPTCHA
func (c *CAPTCHASolverClient) SolveCAPTCHA(request CAPTCHARequest) (*CAPTCHAResponse, error) {
	// Set default values
	if request.UserAgent == "" {
		request.UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
	}
	if request.Viewport == nil {
		request.Viewport = map[string]int{"width": 1920, "height": 1080}
	}

	// Marshal request to JSON
	jsonData, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %v", err)
	}

	// Make HTTP request
	resp, err := c.httpClient.Post(
		c.baseURL+"/solve-captcha",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to make HTTP request: %v", err)
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %v", err)
	}

	// Parse response
	var captchaResp CAPTCHAResponse
	if err := json.Unmarshal(body, &captchaResp); err != nil {
		return nil, fmt.Errorf("failed to parse response: %v", err)
	}

	return &captchaResp, nil
}

// IsHealthy checks if the CAPTCHA solver service is running
func (c *CAPTCHASolverClient) IsHealthy() bool {
	resp, err := c.httpClient.Get(c.baseURL + "/health")
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	return resp.StatusCode == 200
}

// StartCAPTCHASolverService starts the Python CAPTCHA solver service
func StartCAPTCHASolverService() error {
	// This would start the Python service
	// For now, just check if it's already running
	client := NewCAPTCHASolverClient("")
	if client.IsHealthy() {
		fmt.Println("✅ CAPTCHA solver service is already running")
		return nil
	}

	fmt.Println("🚀 CAPTCHA solver service needs to be started manually")
	fmt.Println("   Run: python ai/captcha_bridge.py")
	return fmt.Errorf("CAPTCHA solver service not available")
}

// Enhanced version of your existing TakeScreenshotPlaywright with CAPTCHA handling
func TakeScreenshotPlaywrightWithCAPTCHA(targetURL string) string {
	// First try normal screenshot
	screenshotPath := TakeScreenshotPlaywright(targetURL)

	// Check if CAPTCHA was encountered (you'd implement this detection)
	if containsCAPTCHA(screenshotPath) {
		fmt.Println("🤖 CAPTCHA detected! Attempting to solve...")

		// Initialize CAPTCHA solver
		solver := NewCAPTCHASolverClient("")

		// Check if service is running
		if !solver.IsHealthy() {
			fmt.Println("❌ CAPTCHA solver service is not running")
			fmt.Println("   Start with: python ai/captcha_bridge.py")
			return screenshotPath
		}

		// Create solve request
		request := CAPTCHARequest{
			URL:            targetURL,
			ScreenshotPath: screenshotPath,
		}

		// Solve CAPTCHA
		response, err := solver.SolveCAPTCHA(request)
		if err != nil {
			fmt.Printf("❌ CAPTCHA solving failed: %v\n", err)
			return screenshotPath
		}

		if response.Success {
			fmt.Println("✅ CAPTCHA solved successfully!")
			fmt.Printf("   Final URL: %s\n", response.FinalURL)

			// Take new screenshot of solved page
			return TakeScreenshotPlaywright(response.FinalURL)
		} else {
			fmt.Printf("❌ CAPTCHA solving failed: %s\n", response.Error)
		}
	}

	return screenshotPath
}

// containsCAPTCHA checks if a screenshot contains a CAPTCHA
// This is a simple implementation - you could make it more sophisticated
func containsCAPTCHA(screenshotPath string) bool {
	// Simple keyword-based detection
	// You could implement image-based detection here

	// For now, return false - implement your detection logic
	return false

	// Example detection logic:
	// - Check if screenshot contains reCAPTCHA elements
	// - Look for common CAPTCHA patterns
	// - Use OCR to detect CAPTCHA text
}
