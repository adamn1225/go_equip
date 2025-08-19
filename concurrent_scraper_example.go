package main

import (
	"fmt"
	"log"
	"sync"
	"time"
)

// Concurrent scraping example
func concurrentScrapePages(startPage, endPage, concurrency int) {
	var wg sync.WaitGroup

	// Create a channel to control concurrency (buffered channel acts as semaphore)
	semaphore := make(chan struct{}, concurrency) // Max 3 concurrent pages

	// Channel to collect results
	results := make(chan PageResult, endPage-startPage+1)

	// Start goroutines for each page
	for page := startPage; page <= endPage; page++ {
		wg.Add(1)

		go func(pageNum int) {
			defer wg.Done()

			// Acquire semaphore (blocks if too many goroutines running)
			semaphore <- struct{}{}
			defer func() { <-semaphore }() // Release semaphore

			log.Printf("🔄 Starting page %d", pageNum)
			result := scrapePage(pageNum)
			results <- result
			log.Printf("✅ Completed page %d: %d contacts", pageNum, result.ContactCount)
		}(page)
	}

	// Close results channel when all goroutines complete
	go func() {
		wg.Wait()
		close(results)
	}()

	// Collect all results
	allContacts := []string{}
	for result := range results {
		allContacts = append(allContacts, result.Contacts...)
	}

	log.Printf("🎉 Concurrent scraping complete! Total contacts: %d", len(allContacts))
}

type PageResult struct {
	Page         int
	Contacts     []string
	ContactCount int
}

func scrapePage(page int) PageResult {
	// Simulate scraping work
	log.Printf("📄 Scraping page %d...", page)
	time.Sleep(2 * time.Second) // Simulate network delay

	// Simulate finding contacts
	contacts := []string{
		fmt.Sprintf("Contact A from page %d", page),
		fmt.Sprintf("Contact B from page %d", page),
	}

	return PageResult{
		Page:         page,
		Contacts:     contacts,
		ContactCount: len(contacts),
	}
}

// Example usage in your main function
func exampleUsage() {
	log.Println("Starting concurrent scrape...")
	concurrentScrapePages(1, 10, 3) // Scrape pages 1-10 with max 3 concurrent
}
