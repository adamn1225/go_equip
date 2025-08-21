package scraper

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
)

// CAPTCHARequest represents a request to solve a CAPTCHA
type CAPTCHARequest struct {
	URL         string         `json:"url"`
	SiteKey     string         `json:"site_key,omitempty"`
	CaptchaType string         `json:"captcha_type,omitempty"`
	UserAgent   string         `json:"user_agent,omitempty"`
	Viewport    map[string]int `json:"viewport,omitempty"`
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

// SolveCAPTCHA sends a request to solve a CAPTCHA using the Python service
func (c *CAPTCHASolverClient) SolveCAPTCHA(request CAPTCHARequest) (*CAPTCHAResponse, error) {
	// Set default values
	if request.UserAgent == "" {
		request.UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
	}
	if request.Viewport == nil {
		request.Viewport = map[string]int{"width": 1920, "height": 1080}
	}

	// Call the Python CAPTCHA solving service
	return c.callPythonService(request)
}

// callPythonService makes an HTTP call to the Python CAPTCHA solver service
func (c *CAPTCHASolverClient) callPythonService(request CAPTCHARequest) (*CAPTCHAResponse, error) {
	log.Printf("🤖 Calling Python CAPTCHA solver service for: %s", request.URL)

	// Prepare JSON payload
	jsonData, err := json.Marshal(request)
	if err != nil {
		return &CAPTCHAResponse{
			Success: false,
			Error:   fmt.Sprintf("Failed to marshal request: %v", err),
		}, err
	}

	// Make HTTP POST request to Python service
	resp, err := c.httpClient.Post(c.baseURL+"/solve-captcha", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return &CAPTCHAResponse{
			Success: false,
			Error:   fmt.Sprintf("Failed to call Python service: %v", err),
		}, err
	}
	defer resp.Body.Close()

	// Parse response
	var response CAPTCHAResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return &CAPTCHAResponse{
			Success: false,
			Error:   fmt.Sprintf("Failed to decode response: %v", err),
		}, err
	}

	return &response, nil
}

// solve2CAPTCHA solves CAPTCHA using 2captcha service (legacy method for backward compatibility)
func (c *CAPTCHASolverClient) solve2CAPTCHA(request CAPTCHARequest) (*CAPTCHAResponse, error) {
	apiKey := os.Getenv("CAPTCHA_API_KEY_2CAPTCHA")
	if apiKey == "" {
		return &CAPTCHAResponse{
			Success: false,
			Error:   "CAPTCHA_API_KEY_2CAPTCHA not set in environment",
		}, nil
	}

	log.Printf("🤖 Attempting to solve CAPTCHA with 2captcha for: %s", request.URL)

	// For now, simulate CAPTCHA solving (you'll implement actual 2captcha API calls)
	// This is a placeholder - you can enhance with actual 2captcha integration
	time.Sleep(15 * time.Second) // Simulate solving time

	return &CAPTCHAResponse{
		Success:   true,
		Message:   "CAPTCHA solved using 2captcha",
		FinalURL:  request.URL,
		PageTitle: "Page accessed after CAPTCHA solve",
	}, nil
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
			URL:         targetURL,
			CaptchaType: "recaptcha", // Default assumption for MachineryTrader
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
func containsCAPTCHA(screenshotPath string) bool {
	detector := NewCAPTCHADetector()

	// Use multiple detection methods
	if detector.DetectCAPTCHAInScreenshot(screenshotPath) {
		return true
	}

	// You can add more sophisticated detection here:
	// - OCR-based text detection
	// - Computer vision analysis
	// - ML-based classification

	return false
}
