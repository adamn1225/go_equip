package ocrworker

import (
	"log"
	"os/exec"
	"regexp"
	"strings"
)

// ExtractTextFromImage uses Tesseract OCR to extract text from an image
func ExtractTextFromImage(imagePath string) (string, error) {
	// Check if tesseract is installed
	_, err := exec.LookPath("tesseract")
	if err != nil {
		log.Printf("Tesseract not found. Please install tesseract-ocr")
		return "", err
	}

	// Run tesseract OCR
	cmd := exec.Command("tesseract", imagePath, "stdout")
	output, err := cmd.Output()
	if err != nil {
		log.Printf("Error running tesseract: %v", err)
		return "", err
	}

	text := string(output)
	// Removed verbose OCR text logging for cleaner output

	return text, nil
}

// ExtractSellerInfo extracts ALL seller information from OCR text
func ExtractSellerInfo(text string, pageURL string) []map[string]string {
	var allSellerInfo []map[string]string

	// Split text into lines for processing
	lines := strings.Split(text, "\n")

	// Extract all phone numbers first
	phoneRegex := regexp.MustCompile(`(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})`)
	allPhones := phoneRegex.FindAllString(text, -1)

	// Extract all email addresses
	emailRegex := regexp.MustCompile(`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`)
	allEmails := emailRegex.FindAllString(text, -1)

	// Extract all locations
	locationRegex := regexp.MustCompile(`Location:\s*([^,\n]+(?:,\s*[^,\n]+)*)`)
	allLocationMatches := locationRegex.FindAllStringSubmatch(text, -1)
	var allLocations []string
	for _, match := range allLocationMatches {
		if len(match) > 1 {
			allLocations = append(allLocations, strings.TrimSpace(match[1]))
		}
	}

	// Extract all seller names
	var allSellers []string
	for _, line := range lines {
		if strings.Contains(strings.ToLower(line), "seller:") {
			seller := strings.TrimSpace(strings.Replace(line, "Seller:", "", 1))
			seller = strings.TrimSpace(strings.Replace(seller, "seller:", "", 1))
			if seller != "" && seller != "Email Seller" {
				allSellers = append(allSellers, seller)
			}
		}
	}

	// Extract all serial numbers
	serialRegex := regexp.MustCompile(`Serial Number:\s*([A-Za-z0-9]+)`)
	allSerialMatches := serialRegex.FindAllStringSubmatch(text, -1)
	var allSerials []string
	for _, match := range allSerialMatches {
		if len(match) > 1 {
			allSerials = append(allSerials, strings.TrimSpace(match[1]))
		}
	}

	// Extract all auction dates
	auctionDateRegex := regexp.MustCompile(`Auction Date:\s*([^(]+)`)
	allAuctionMatches := auctionDateRegex.FindAllStringSubmatch(text, -1)
	var allAuctionDates []string
	for _, match := range allAuctionMatches {
		if len(match) > 1 {
			allAuctionDates = append(allAuctionDates, strings.TrimSpace(match[1]))
		}
	}

	// Combine all extracted data - use phones as the primary key since each listing should have one
	maxItems := len(allPhones)
	if len(allLocations) > maxItems {
		maxItems = len(allLocations)
	}
	if len(allSellers) > maxItems {
		maxItems = len(allSellers)
	}

	for i := 0; i < maxItems; i++ {
		sellerInfo := make(map[string]string)

		// Add the page URL to each contact
		sellerInfo["url"] = pageURL

		if i < len(allPhones) {
			sellerInfo["phone"] = allPhones[i]
		}
		if i < len(allEmails) {
			sellerInfo["email"] = allEmails[i]
		}
		if i < len(allLocations) {
			sellerInfo["location"] = allLocations[i]
		}
		if i < len(allSellers) {
			sellerInfo["seller"] = allSellers[i]
		}
		if i < len(allSerials) {
			sellerInfo["serial_number"] = allSerials[i]
		}
		if i < len(allAuctionDates) {
			sellerInfo["auction_date"] = allAuctionDates[i]
		}

		// Only add if we have at least a phone or seller name
		if sellerInfo["phone"] != "" || sellerInfo["seller"] != "" {
			allSellerInfo = append(allSellerInfo, sellerInfo)
		}
	}

	return allSellerInfo
}
