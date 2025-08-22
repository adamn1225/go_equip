package main

import (
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"math/rand"
	"os"
	"sync"
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
	headers := []string{"Seller/Company", "Location", "Phone", "Email", "Serial Number", "Auction Date", "Year", "Make", "Model", "Price", "URL"}
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
			info["year"],
			info["make"],
			info["model"],
			info["price"],
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
		Year         string `json:"year,omitempty"`
		Make         string `json:"make,omitempty"`
		Model        string `json:"model,omitempty"`
		Price        string `json:"price,omitempty"`
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
			Year:         info["year"],
			Make:         info["make"],
			Model:        info["model"],
			Price:        info["price"],
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
	// Command line flags
	var (
		startPageFlag   = flag.Int("start-page", 1, "Starting page number")
		endPageFlag     = flag.Int("end-page", 197, "Ending page number")
		concurrencyFlag = flag.Int("concurrency", 4, "Number of concurrent workers")
	)
	flag.Parse()

	// MachineryTrader category mapping
	categoryMap := map[string]string{
		"1007": "Asphalt/Pavers",
		"1057": "Sweepers/Brooms",
		"1040": "Lifts",
		"1046": "Backhoes",
		"1049": "Off-Highway Trucks",
		"1035": "Forestry Equipment",
		"1028": "Drills",
		"1060": "wheel loaders",
		"1015": "cranes",
		"1025": "dozer",
		"1026": "excavator",
		"1048": "grader",
		"1027": "loader",
		"1055": "skid steers",
	}

	// Configuration for concurrent scraping - Sweepers/Brooms Category
	baseURL := "https://www.machinerytrader.com/listings/search?Category=1057&page="
	currentCategory := categoryMap["1057"] // Sweepers/Brooms
	startPage := *startPageFlag            // Use command line flag
	maxPages := *endPageFlag               // Use command line flag
	concurrency := *concurrencyFlag        // Use command line flag

	log.Printf("🚀 Starting OCR scraper - CAPTCHA Learning Mode (%dx Concurrent)", concurrency)
	log.Printf("📊 Category: %s", currentCategory)
	log.Printf("📄 Pages: %d to %d with %d workers", startPage, maxPages, concurrency)
	log.Printf("🧠 Ready to collect CAPTCHA learning data!")
	log.Println("🔄 Manual CAPTCHA solving - each one helps train the AI!")

	var allSellerInfo []map[string]string
	var mu sync.Mutex // Protect allSellerInfo from concurrent access

	// Add defer to ensure data is saved even if script crashes
	defer func() {
		mu.Lock()
		if len(allSellerInfo) > 0 {
			log.Printf("💾 Emergency save triggered - saving %d contacts...", len(allSellerInfo))
			timestamp := time.Now().Format("20060102_150405")
			csvFile := fmt.Sprintf("seller_contacts_emergency_%s.csv", timestamp)
			jsonFile := fmt.Sprintf("seller_contacts_emergency_%s.json", timestamp)

			exportToCSV(allSellerInfo, csvFile)
			exportToJSON(allSellerInfo, jsonFile, currentCategory)
			log.Printf("✅ Emergency data saved to %s and %s", csvFile, jsonFile)
		}
		mu.Unlock()
		// Note: Worker browser sessions are closed in defer functions
	}()

	// Initialize browser session once at start (remove this since we'll use worker-specific sessions)
	// err := scraper.InitializeBrowserSession()
	// if err != nil {
	//	log.Fatalf("Failed to initialize browser session: %v", err)
	// }

	// Create channels for work distribution
	pageChannel := make(chan int, maxPages)
	var wg sync.WaitGroup

	// Fill the page channel
	for page := startPage; page <= maxPages; page++ {
		pageChannel <- page
	}
	close(pageChannel)

	// Start concurrent workers
	for worker := 1; worker <= concurrency; worker++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			log.Printf("🔧 Worker %d started", workerID)

			// Initialize worker-specific browser session
			if err := scraper.InitializeWorkerBrowserSession(workerID, nil); err != nil {
				log.Printf("❌ Worker %d: Failed to initialize browser session: %v", workerID, err)
				return
			}

			defer func() {
				scraper.CloseWorkerBrowserSession(workerID)
			}()

			for currentPage := range pageChannel {
				targetURL := fmt.Sprintf("%s%d", baseURL, currentPage)
				log.Printf("🔧 Worker %d processing page %d: %s", workerID, currentPage, targetURL)

				// Create job for this page
				scraperJob := models.Job{URL: targetURL}

				// Take screenshot with CAPTCHA handling using worker-specific session!
				imagePath := scraper.TakeScreenshotPlaywrightWorker(workerID, targetURL)

				if imagePath == "" {
					log.Printf("❌ Worker %d failed to take screenshot for page %d", workerID, currentPage)
					continue
				}

				// Update job with image path
				scraperJob.ImagePath = imagePath

				// Enqueue job for processing
				log.Printf("📦 Worker %d enqueueing job for page %d...", workerID, currentPage)
				if err := queue.Enqueue(scraperJob); err != nil {
					log.Printf("❌ Worker %d error enqueueing job: %v", workerID, err)
					continue
				}

				// Process OCR
				text, err := ocrworker.ExtractTextFromImage(imagePath)
				if err != nil {
					log.Printf("❌ Worker %d OCR processing failed: %v", workerID, err)
					continue
				}

				// Extract seller information
				sellerInfoList := ocrworker.ExtractSellerInfo(text, targetURL)

				// Safely append to shared slice
				mu.Lock()
				allSellerInfo = append(allSellerInfo, sellerInfoList...)
				totalContacts := len(allSellerInfo)
				mu.Unlock()

				log.Printf("✅ Worker %d completed page %d: Found %d contacts (Total: %d)",
					workerID, currentPage, len(sellerInfoList), totalContacts)

				// Periodic save every 200 contacts (across all workers)
				if totalContacts > 0 && totalContacts%200 == 0 {
					mu.Lock()
					if len(allSellerInfo) == totalContacts { // Double-check we're the one hitting the milestone
						log.Printf("💾 Periodic save at %d contacts - saving data...", totalContacts)
						timestamp := time.Now().Format("20060102_150405")
						csvFile := fmt.Sprintf("seller_contacts_periodic_%s_contacts%d.csv", timestamp, totalContacts)
						jsonFile := fmt.Sprintf("seller_contacts_periodic_%s_contacts%d.json", timestamp, totalContacts)

						exportToCSV(allSellerInfo, csvFile)
						exportToJSON(allSellerInfo, jsonFile, currentCategory)
						log.Printf("✅ Periodic data saved to %s and %s", csvFile, jsonFile)
					}
					mu.Unlock()
				}

				// Respectful delay between pages (shorter for concurrent)
				time.Sleep(time.Duration(1+rand.Intn(2)) * time.Second)
			}
			log.Printf("🏁 Worker %d finished", workerID)
		}(worker)
	}

	// Wait for all workers to complete
	wg.Wait()

	log.Printf("🎉 Scraping completed!")
	mu.Lock()
	log.Printf("📊 Total contacts found: %d", len(allSellerInfo))

	if len(allSellerInfo) > 0 {
		// Export to CSV and JSON
		timestamp := time.Now().Format("20060102_150405")
		csvFile := fmt.Sprintf("seller_contacts_learning_%s.csv", timestamp)
		jsonFile := fmt.Sprintf("seller_contacts_learning_%s.json", timestamp)

		// Export to CSV
		err := exportToCSV(allSellerInfo, csvFile)
		if err != nil {
			log.Printf("Error exporting to CSV: %v", err)
		} else {
			log.Printf("📄 CSV exported successfully: %s", csvFile)
		}

		// Export to JSON
		err = exportToJSON(allSellerInfo, jsonFile, currentCategory)
		if err != nil {
			log.Printf("Error exporting to JSON: %v", err)
		} else {
			log.Printf("📦 JSON exported successfully: %s", jsonFile)
			log.Printf("🏷️  Category: %s, Site: machinerytrader.com", currentCategory)
		}

		log.Printf("🧠 CAPTCHA Learning Tip:")
		log.Printf("   Each CAPTCHA you solved helps train the AI!")
		log.Printf("   Run the learning system to start training:")
		log.Printf("   python ai/captcha_learning_system.py --mode collect")
	}
	mu.Unlock()

	// Close any remaining worker browser sessions
	for i := 1; i <= concurrency; i++ {
		scraper.CloseWorkerBrowserSession(i)
	}
}
