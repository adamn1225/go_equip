package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"os"
	"time"

	"github.com/adamn1225/hybrid-ocr-agent/scraper/internal/models"
	"github.com/adamn1225/hybrid-ocr-agent/scraper/ocrworker"
	"github.com/adamn1225/hybrid-ocr-agent/scraper/queue"
	"github.com/adamn1225/hybrid-ocr-agent/scraper/scraper"
)

// exportToCSV exports seller information to a CSV file
func exportToCSV(sellerInfos []map[string]string, filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// Write header
	headers := []string{"Seller/Company", "Location", "Phone", "Email", "Serial Number", "Auction Date", "URL"}
	if err := writer.Write(headers); err != nil {
		return err
	}

	// Write data rows
	for _, info := range sellerInfos {
		row := []string{
			info["seller"],
			info["location"],
			info["phone"],
			info["email"],
			info["serial_number"],
			info["auction_date"],
			info["url"],
		}
		if err := writer.Write(row); err != nil {
			return err
		}
	}

	return nil
}

// exportToJSON exports seller information to a JSON file
func exportToJSON(sellerInfos []map[string]string, filename string, category string) error {
	// Create a structured format for better JSON output
	type Contact struct {
		Seller       string `json:"seller_company"`
		Location     string `json:"location"`
		Phone        string `json:"phone"`
		Email        string `json:"email,omitempty"`
		SerialNumber string `json:"serial_number,omitempty"`
		AuctionDate  string `json:"auction_date,omitempty"`
		URL          string `json:"url,omitempty"`
	}

	var contacts []Contact
	for _, info := range sellerInfos {
		contact := Contact{
			Seller:       info["seller"],
			Location:     info["location"],
			Phone:        info["phone"],
			Email:        info["email"],
			SerialNumber: info["serial_number"],
			AuctionDate:  info["auction_date"],
			URL:          info["url"],
		}
		contacts = append(contacts, contact)
	}

	// Create export data with metadata
	exportData := map[string]interface{}{
		"export_timestamp":   time.Now().Format(time.RFC3339),
		"total_contacts":     len(contacts),
		"equipment_category": category,
		"source_site":        "machinerytrader.com",
		"contacts":           contacts,
	}

	jsonData, err := json.MarshalIndent(exportData, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(filename, jsonData, 0644)
}

func main() {
	// MachineryTrader category mapping
	categoryMap := map[string]string{
		"1028": "Drills",        // Scrapers
		"1060": "wheel loaders", // Agriculture
		"1015": "cranes",        // Mini Excavators
		"1025": "dozer",         // Dozers/Bulldozers
		"1026": "excavator",     // Excavators
		"1027": "loader",        // Loaders
		"1029": "grader",        // Graders
		// Add more as you discover them
	}

	// Sequential page scraping - continue from where you left off
	baseURL := "https://www.machinerytrader.com/listings/search?Category=1028&page="
	currentCategory := categoryMap["1028"] // Extract category from URL
	startPage := 95                        // Continue from where you left off
	maxPages := 200                        // Process up to page 200
	maxConsecutiveFailures := 5            // Stop if we get 5 consecutive failures

	log.Printf("Starting sequential multi-page OCR scraper from page %d", startPage)
	log.Printf("Scraping category: %s (Category=1028)", currentCategory)
	log.Printf("Target: Process through page %d", maxPages)
	log.Println("Proxy rotation enabled - persistent session with proxy switching")
	log.Println("Will continue scraping until all pages are processed or excessive failures occur...")

	var allSellerInfo []map[string]string
	consecutiveFailures := 0

	// Add defer to ensure data is saved even if script crashes
	defer func() {
		if len(allSellerInfo) > 0 {
			log.Printf("Emergency save triggered - saving %d contacts...", len(allSellerInfo))
			timestamp := time.Now().Format("20060102_150405")
			csvFile := fmt.Sprintf("seller_contacts_emergency_%s.csv", timestamp)
			jsonFile := fmt.Sprintf("seller_contacts_emergency_%s.json", timestamp)

			exportToCSV(allSellerInfo, csvFile)
			exportToJSON(allSellerInfo, jsonFile, currentCategory)
			log.Printf("Emergency data saved to %s and %s", csvFile, jsonFile)
		}
		scraper.CloseBrowserSession()
	}()

	// Initialize browser session once at start
	err := scraper.InitializeBrowserSession()
	if err != nil {
		log.Fatalf("Failed to initialize browser session: %v", err)
	}

	// Process pages sequentially
	for currentPage := startPage; currentPage <= maxPages; currentPage++ {
		targetURL := fmt.Sprintf("%s%d", baseURL, currentPage)
		log.Printf("Processing page %d: %s", currentPage, targetURL)

		// Create job for this page
		job := models.Job{URL: targetURL}

		// Take screenshot with Playwright (uses persistent session with proxy rotation)
		imagePath := scraper.TakeScreenshotPlaywright(job.URL)

		if imagePath == "" {
			log.Printf("Failed to take screenshot for page %d", currentPage)
			consecutiveFailures++

			if consecutiveFailures >= maxConsecutiveFailures {
				log.Printf("Too many consecutive failures (%d). Stopping scraper.", consecutiveFailures)
				break
			}
			continue
		}

		// Reset consecutive failures on success
		consecutiveFailures = 0

		// Update job with image path
		job.ImagePath = imagePath

		// Enqueue job for processing
		if err := queue.Enqueue(job); err != nil {
			log.Printf("Error enqueueing job: %v", err)
			continue
		}

		// Process OCR
		log.Printf("Processing OCR for page %d...", currentPage)
		text, err := ocrworker.ExtractTextFromImage(imagePath)
		if err != nil {
			log.Printf("OCR processing failed for page %d: %v", currentPage, err)
			continue
		}

		// Extract seller information
		sellerInfoList := ocrworker.ExtractSellerInfo(text, targetURL)
		log.Printf("Page %d completed: Found %d contacts", currentPage, len(sellerInfoList))

		// Add to our collection
		allSellerInfo = append(allSellerInfo, sellerInfoList...)

		// Add delay between pages to be respectful to the server
		delay := 3 + rand.Intn(5) // 3-8 seconds between pages
		log.Printf("Waiting %d seconds before next page...", delay)
		time.Sleep(time.Duration(delay) * time.Second)
	}

	log.Printf("Sequential multi-page scraping completed!")
	log.Printf("Total pages processed: %d to %d", startPage, maxPages)
	log.Printf("Total seller contacts found: %d", len(allSellerInfo))

	if len(allSellerInfo) > 0 {
		pagesProcessed := maxPages - startPage + 1
		avgContactsPerPage := float64(len(allSellerInfo)) / float64(pagesProcessed)
		log.Printf("Average contacts per page: %.1f", avgContactsPerPage)

		// Export to CSV and JSON
		timestamp := time.Now().Format("20060102_150405")
		csvFile := fmt.Sprintf("seller_contacts_%s.csv", timestamp)
		jsonFile := fmt.Sprintf("seller_contacts_%s.json", timestamp)

		// Export to CSV
		err := exportToCSV(allSellerInfo, csvFile)
		if err != nil {
			log.Printf("Error exporting to CSV: %v", err)
		} else {
			log.Printf("CSV exported successfully: %s", csvFile)
		}

		// Export to JSON
		err = exportToJSON(allSellerInfo, jsonFile, currentCategory)
		if err != nil {
			log.Printf("Error exporting to JSON: %v", err)
		} else {
			log.Printf("JSON exported successfully: %s", jsonFile)
			log.Printf("Category: %s, Site: machinerytrader.com", currentCategory)
		}
	}

	// Close the persistent browser session
	scraper.CloseBrowserSession()
}
