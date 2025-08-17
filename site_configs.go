// Multi-Site Configuration for Sandhills Publishing Network
// Copy these baseURL patterns into your main.go as needed

package main

// Site configurations for Sandhills publishing network
var sandhillsSites = map[string]SiteConfig{
	"machinerytrader": {
		BaseURL:  "https://www.machinerytrader.com/listings/search?Category=1031&page=",
		Name:     "MachineryTrader.com - Construction Equipment",
		MaxPages: 357, // Update based on actual page count
		Category: "construction_equipment",
	},
	"pavingequipment": {
		BaseURL:  "https://www.pavingequipment.com/listings/search?page=",
		Name:     "PavingEquipment.com - All Categories",
		MaxPages: 200, // Estimate - update after testing
		Category: "paving_equipment",
	},
	"tractorhouse": {
		BaseURL:  "https://www.tractorhouse.com/listings/search?page=",
		Name:     "TractorHouse.com - All Categories",
		MaxPages: 500, // Estimate - farm equipment likely has many pages
		Category: "farm_equipment",
	},
	"tractorhouse_construction": {
		BaseURL:  "https://www.tractorhouse.com/listings/search?Category=1031&page=",
		Name:     "TractorHouse.com - Construction Equipment",
		MaxPages: 200, // Estimate
		Category: "construction_equipment",
	},
	"auctiontime": {
		BaseURL:  "https://www.auctiontime.com/listings/search?page=",
		Name:     "AuctionTime.com - All Categories",
		MaxPages: 300, // Estimate
		Category: "auction_equipment",
	},
	"truckpaper": {
		BaseURL:  "https://www.truckpaper.com/listings/search?page=",
		Name:     "TruckPaper.com - All Categories",
		MaxPages: 400, // Estimate - trucks likely have many listings
		Category: "commercial_trucks",
	},
}

type SiteConfig struct {
	BaseURL  string
	Name     string
	MaxPages int
	Category string
}

// Usage in your main() function:
// 1. Choose a site from the map above
// 2. Replace your current baseURL with the chosen BaseURL
// 3. Update maxPages with the MaxPages value
// 4. The Category field will be used for master contact log source tracking

// Example for switching to TractorHouse:
// baseURL := sandhillsSites["tractorhouse"].BaseURL
// maxPages := sandhillsSites["tractorhouse"].MaxPages
// siteName := "tractorhouse.com"
// category := sandhillsSites["tractorhouse"].Category
