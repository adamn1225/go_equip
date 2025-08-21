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

	// Extract equipment years (4-digit years, typically 1980-2030)
	yearRegex := regexp.MustCompile(`\b(19[8-9][0-9]|20[0-3][0-9])\b`)
	allYears := yearRegex.FindAllString(text, -1)

	// Extract equipment makes/brands (common heavy equipment manufacturers)
	makeRegex := regexp.MustCompile(`(?i)\b(CAT|Caterpillar|John Deere|Komatsu|Volvo|Hitachi|Liebherr|Bobcat|Case|New Holland|JCB|Terex|Grove|Link-Belt|Manitowoc|Tadano|Kobelco|Hyundai|Doosan|Sany|XCMG|LiuGong|Lonking|Shantui|SDLG|Zoomlion|Peterbilt|Kenworth|Freightliner|Mack|International|Western Star|Ford|Chevrolet|GMC|Dodge|RAM|Isuzu|Hino|UD Trucks|Volvo Trucks)\b`)
	allMakeMatches := makeRegex.FindAllString(text, -1)
	var allMakes []string
	for _, make := range allMakeMatches {
		// Simple capitalization instead of deprecated strings.Title
		allMakes = append(allMakes, strings.ToUpper(make[:1])+strings.ToLower(make[1:]))
	}

	// Extract equipment models (alphanumeric patterns after makes)
	modelRegex := regexp.MustCompile(`(?i)\b(?:CAT|Caterpillar|John Deere|Komatsu|Volvo|Hitachi|Liebherr|Bobcat|Case|New Holland|JCB|Terex|Grove|Link-Belt|Manitowoc|Tadano|Kobelco|Hyundai|Doosan|Sany|XCMG|LiuGong|Lonking|Shantui|SDLG|Zoomlion|Peterbilt|Kenworth|Freightliner|Mack|International|Western Star|Ford|Chevrolet|GMC|Dodge|RAM|Isuzu|Hino|UD Trucks|Volvo Trucks)\s+([A-Za-z0-9\-]{2,15})\b`)
	allModelMatches := modelRegex.FindAllStringSubmatch(text, -1)
	var allModels []string
	for _, match := range allModelMatches {
		if len(match) > 1 {
			allModels = append(allModels, strings.ToUpper(strings.TrimSpace(match[1])))
		}
	}

	// Extract listing prices ($ followed by digits, commas, decimals)
	priceRegex := regexp.MustCompile(`\$([0-9,]+(?:\.[0-9]{2})?)`)
	allPriceMatches := priceRegex.FindAllStringSubmatch(text, -1)
	var allPrices []string
	for _, match := range allPriceMatches {
		if len(match) > 1 {
			price := strings.ReplaceAll(match[1], ",", "")
			// Filter out unrealistic prices (too low or too high)
			if len(price) >= 4 && len(price) <= 10 { // $1,000 to $9,999,999,999
				allPrices = append(allPrices, "$"+match[1])
			}
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
	if len(allYears) > maxItems {
		maxItems = len(allYears)
	}
	if len(allMakes) > maxItems {
		maxItems = len(allMakes)
	}
	if len(allModels) > maxItems {
		maxItems = len(allModels)
	}
	if len(allPrices) > maxItems {
		maxItems = len(allPrices)
	}

	for i := 0; i < maxItems; i++ {
		sellerInfo := make(map[string]string)

		// Add the page URL to each contact
		sellerInfo["url"] = pageURL

		// Contact information
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

		// Equipment details (NEW!)
		if i < len(allYears) {
			sellerInfo["year"] = allYears[i]
		}
		if i < len(allMakes) {
			sellerInfo["make"] = allMakes[i]
		}
		if i < len(allModels) {
			sellerInfo["model"] = allModels[i]
		}
		if i < len(allPrices) {
			sellerInfo["price"] = allPrices[i]
		}

		// Only add if we have at least a phone or seller name
		if sellerInfo["phone"] != "" || sellerInfo["seller"] != "" {
			allSellerInfo = append(allSellerInfo, sellerInfo)
		}
	}

	return allSellerInfo
}
