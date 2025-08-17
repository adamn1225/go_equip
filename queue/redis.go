package queue

import (
	"log"

	"github.com/adamn1225/hybrid-ocr-agent/scraper/internal/models"
)

// Enqueue adds a job to the processing queue
// For now, this is a simple implementation that logs the job
// You can replace this with actual Redis implementation later
func Enqueue(job models.Job) error {
	// TODO: Add actual Redis queue implementation here
	// For now, we'll just accept the job silently
	log.Printf("📦 Enqueueing job for page...")
	return nil
}
