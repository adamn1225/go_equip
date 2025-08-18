package scraper

import (
	"encoding/json"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

// CAPTCHADetector holds various detection methods
type CAPTCHADetector struct {
	// Common CAPTCHA indicators in page source
	captchaKeywords []string
	// URL patterns that commonly have CAPTCHAs
	captchaURLPatterns []*regexp.Regexp
}

// NewCAPTCHADetector creates a new CAPTCHA detector
func NewCAPTCHADetector() *CAPTCHADetector {
	return &CAPTCHADetector{
		captchaKeywords: []string{
			"recaptcha",
			"g-recaptcha",
			"hcaptcha",
			"h-captcha",
			"captcha",
			"challenge",
			"verification",
			"robot",
			"human verification",
			"security check",
			"cloudflare",
			"cf-challenge",
		},
		captchaURLPatterns: []*regexp.Regexp{
			regexp.MustCompile(`recaptcha`),
			regexp.MustCompile(`captcha`),
			regexp.MustCompile(`challenge`),
			regexp.MustCompile(`cloudflare`),
		},
	}
}

// DetectCAPTCHAInScreenshot analyzes a screenshot for CAPTCHA elements
func (d *CAPTCHADetector) DetectCAPTCHAInScreenshot(screenshotPath string) bool {
	// Method 1: Check if screenshot file contains CAPTCHA metadata
	if d.checkScreenshotMetadata(screenshotPath) {
		return true
	}

	// Method 2: Use basic image analysis (you could implement ML here)
	if d.analyzeImageForCAPTCHA(screenshotPath) {
		return true
	}

	return false
}

// DetectCAPTCHAInPageSource checks page source/DOM for CAPTCHA elements
func (d *CAPTCHADetector) DetectCAPTCHAInPageSource(pageContent string) bool {
	pageContentLower := strings.ToLower(pageContent)

	for _, keyword := range d.captchaKeywords {
		if strings.Contains(pageContentLower, keyword) {
			return true
		}
	}

	return false
}

// DetectCAPTCHAInURL checks if URL suggests CAPTCHA presence
func (d *CAPTCHADetector) DetectCAPTCHAInURL(url string) bool {
	urlLower := strings.ToLower(url)

	for _, pattern := range d.captchaURLPatterns {
		if pattern.MatchString(urlLower) {
			return true
		}
	}

	return false
}

// checkScreenshotMetadata checks for CAPTCHA-related metadata in screenshot
func (d *CAPTCHADetector) checkScreenshotMetadata(screenshotPath string) bool {
	// Check if there's a companion JSON file with page info
	jsonPath := strings.TrimSuffix(screenshotPath, filepath.Ext(screenshotPath)) + "_metadata.json"

	if _, err := os.Stat(jsonPath); os.IsNotExist(err) {
		return false
	}

	// Read and parse metadata
	data, err := os.ReadFile(jsonPath)
	if err != nil {
		return false
	}

	var metadata map[string]interface{}
	if err := json.Unmarshal(data, &metadata); err != nil {
		return false
	}

	// Check for CAPTCHA indicators in metadata
	if pageTitle, ok := metadata["title"].(string); ok {
		if d.DetectCAPTCHAInPageSource(pageTitle) {
			return true
		}
	}

	if pageURL, ok := metadata["url"].(string); ok {
		if d.DetectCAPTCHAInURL(pageURL) {
			return true
		}
	}

	return false
}

// analyzeImageForCAPTCHA performs basic image analysis
func (d *CAPTCHADetector) analyzeImageForCAPTCHA(screenshotPath string) bool {
	// This is where you could implement:
	// 1. OCR on the image to look for CAPTCHA text
	// 2. Computer vision to detect CAPTCHA UI elements
	// 3. Machine learning model to classify images

	// For now, return false - implement based on your needs
	// You could use libraries like:
	// - tesseract for OCR
	// - OpenCV for image processing
	// - TensorFlow for ML-based detection

	return false
}
