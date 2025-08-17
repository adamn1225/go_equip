package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
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
func exportToJSON(sellerInfos []map[string]string, filename string) error {
	// Create a structured format for better JSON output
	type Contact struct {
		Seller       string `json:"seller_company"`
		Location     string `json:"location"`
		Phone        string `json:"phone"`
		Email        string `json:"email,omitempty"`
		SerialNumber string `json:"serial_number,omitempty"`
		AuctionDate  string `json:"auction_date,omitempty"`
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
		}
		contacts = append(contacts, contact)
	}

	// Create export data with metadata
	exportData := map[string]interface{}{
		"export_timestamp": time.Now().Format(time.RFC3339),
		"total_contacts":   len(contacts),
		"contacts":         contacts,
	}

	jsonData, err := json.MarshalIndent(exportData, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(filename, jsonData, 0644)
}

func main() {
	// Dynamic page scraping - start from page 150 and continue until no more pages
	baseURL := "https://www.machinerytrader.com/listings/search?Category=1025&page="
	startPage := 1
	maxPages := 400             // Total pages available
	maxConsecutiveFailures := 5 // Stop if we get 5 consecutive failures (more robust)

	log.Printf("Starting dynamic multi-page OCR scraper from page %d", startPage)
	log.Printf("🎯 Target: Process through page %d (total %d pages)", maxPages, maxPages)
	log.Println("🔍 The browser will open visibly so you can manually solve any CAPTCHAs")
	log.Println("💡 Will continue scraping until all pages are processed or consecutive failures occur...")

	var allSellerInfo []map[string]string
	consecutiveFailures := 0
	currentPage := startPage

	// Add defer to ensure data is saved even if script crashes
	defer func() {
		if len(allSellerInfo) > 0 {
			log.Printf("\n💾 Emergency save triggered - saving %d contacts...", len(allSellerInfo))
			timestamp := time.Now().Format("20060102_150405")
			csvFile := fmt.Sprintf("seller_contacts_emergency_%s.csv", timestamp)
			jsonFile := fmt.Sprintf("seller_contacts_emergency_%s.json", timestamp)

			exportToCSV(allSellerInfo, csvFile)
			exportToJSON(allSellerInfo, jsonFile)
			log.Printf("💾 Emergency data saved to %s and %s", csvFile, jsonFile)
		}
		scraper.CloseBrowserSession()
	}()

	for {
		targetURL := fmt.Sprintf("%s%d", baseURL, currentPage)

		log.Printf("\n📄 Processing page %d: %s", currentPage, targetURL)

		// Create job
		job := models.Job{URL: targetURL}

		// Take screenshot
		imagePath := scraper.TakeScreenshotPlaywright(job.URL)
		if imagePath == "" {
			log.Printf("❌ Failed to take screenshot for page %d (possibly no more pages or navigation issue)", currentPage)
			consecutiveFailures++
			if consecutiveFailures >= maxConsecutiveFailures {
				log.Printf("🛑 Stopping: %d consecutive screenshot failures - likely reached end of available pages", maxConsecutiveFailures)
				break
			}
			currentPage++
			continue
		}

		// Reset consecutive failures on successful screenshot
		consecutiveFailures = 0

		// Update job with image path
		job.ImagePath = imagePath

		// Enqueue job for processing
		log.Printf("📦 Enqueueing job for page %d...", currentPage)
		if err := queue.Enqueue(job); err != nil {
			log.Printf("Error enqueueing job for page %d: %v", currentPage, err)
		}

		// Process OCR
		log.Printf("🔍 Processing OCR for page %d...", currentPage)
		text, err := ocrworker.ExtractTextFromImage(imagePath)
		if err != nil {
			log.Printf("❌ OCR processing failed for page %d: %v", currentPage, err)
			log.Println("Note: Make sure tesseract-ocr is installed: sudo apt-get install tesseract-ocr")
		} else {
			// Extract seller information (now returns slice of contacts)
			sellerInfoList := ocrworker.ExtractSellerInfo(text, targetURL)
			if len(sellerInfoList) > 0 {
				log.Printf("✅ Page %d: Found %d contacts", currentPage, len(sellerInfoList))
				allSellerInfo = append(allSellerInfo, sellerInfoList...)
				consecutiveFailures = 0 // Reset failures on successful extraction
			} else {
				log.Printf("⚠️  Page %d: No contacts found (empty page or end of results)", currentPage)
				consecutiveFailures++
				if consecutiveFailures >= maxConsecutiveFailures {
					log.Printf("🛑 Stopping: %d consecutive pages with no data - likely reached end of available listings", maxConsecutiveFailures)
					break
				}
			}
		}

		// Add delay between pages to be respectful
		if (currentPage-startPage+1)%5 == 0 {
			log.Printf("📊 Progress: Page %d | Total contacts: %d | Rate: %.1f contacts/page",
				currentPage, len(allSellerInfo), float64(len(allSellerInfo))/float64(currentPage-startPage+1))
		}
		time.Sleep(3 * time.Second)

		currentPage++

		// Optional: Add a reasonable upper limit to prevent infinite loops
		if currentPage > maxPages {
			log.Printf("🛑 Reached maximum page limit (%d), stopping...", maxPages)
			break
		}
	}

	log.Printf("\n🎉 Multi-page scraping completed!")
	log.Printf("📊 Total pages processed: %d", currentPage-startPage)
	log.Printf("📝 Total seller contacts found: %d", len(allSellerInfo))

	if currentPage > maxPages {
		log.Printf("🔚 Reason: Reached safety limit of %d pages", maxPages)
	} else if consecutiveFailures >= maxConsecutiveFailures {
		log.Printf("🔚 Reason: %d consecutive failures - likely reached end of available pages", maxConsecutiveFailures)
	} else {
		log.Printf("🔚 Reason: Manual termination or other exit condition")
	}

	if len(allSellerInfo) > 0 {
		avgContactsPerPage := float64(len(allSellerInfo)) / float64(currentPage-startPage)
		log.Printf("📈 Average contacts per page: %.1f", avgContactsPerPage)
	}

	if len(allSellerInfo) > 0 {
		// Export to CSV and JSON
		timestamp := time.Now().Format("20060102_150405")
		csvFile := fmt.Sprintf("seller_contacts_%s.csv", timestamp)
		jsonFile := fmt.Sprintf("seller_contacts_%s.json", timestamp)

		// Export to CSV
		err := exportToCSV(allSellerInfo, csvFile)
		if err != nil {
			log.Printf("❌ Error exporting to CSV: %v", err)
		} else {
			log.Printf("💾 CSV exported successfully: %s", csvFile)
		}

		// Export to JSON
		err = exportToJSON(allSellerInfo, jsonFile)
		if err != nil {
			log.Printf("❌ Error exporting to JSON: %v", err)
		} else {
			log.Printf("💾 JSON exported successfully: %s", jsonFile)
		}
	}

	// Close the persistent browser session
	scraper.CloseBrowserSession()
}
