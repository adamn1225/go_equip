package proxy

import (
	"fmt"
	"log"
	"math/rand"
	"sync"
	"time"
)

// ProxyConfig represents a proxy configuration
type ProxyConfig struct {
	Host      string    `json:"host"`
	Port      int       `json:"port"`
	Username  string    `json:"username,omitempty"`
	Password  string    `json:"password,omitempty"`
	Type      string    `json:"type"` // http, socks5, etc.
	Active    bool      `json:"active"`
	LastUsed  time.Time `json:"last_used"`
	FailCount int       `json:"fail_count"`
}

// ProxyManager handles proxy rotation and health checking
type ProxyManager struct {
	proxies    []ProxyConfig
	currentIdx int
	mutex      sync.RWMutex
	maxFails   int
}

// NewProxyManager creates a new proxy manager
func NewProxyManager() *ProxyManager {
	return &ProxyManager{
		proxies:  make([]ProxyConfig, 0),
		maxFails: 3, // Disable proxy after 3 consecutive failures
	}
}

// AddProxy adds a proxy to the rotation pool
func (pm *ProxyManager) AddProxy(host string, port int, proxyType string, username, password string) {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	proxy := ProxyConfig{
		Host:      host,
		Port:      port,
		Username:  username,
		Password:  password,
		Type:      proxyType,
		Active:    true,
		LastUsed:  time.Time{},
		FailCount: 0,
	}

	pm.proxies = append(pm.proxies, proxy)
	log.Printf("✅ Added %s proxy: %s:%d", proxyType, host, port)
}

// GetNextProxy returns the next available proxy in rotation
func (pm *ProxyManager) GetNextProxy() (*ProxyConfig, error) {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	if len(pm.proxies) == 0 {
		return nil, fmt.Errorf("no proxies available")
	}

	// Find next active proxy
	startIdx := pm.currentIdx
	for {
		proxy := &pm.proxies[pm.currentIdx]
		pm.currentIdx = (pm.currentIdx + 1) % len(pm.proxies)

		if proxy.Active {
			proxy.LastUsed = time.Now()
			log.Printf("🔄 Using proxy: %s:%d (fails: %d)", proxy.Host, proxy.Port, proxy.FailCount)
			return proxy, nil
		}

		// If we've checked all proxies and none are active
		if pm.currentIdx == startIdx {
			return nil, fmt.Errorf("no active proxies available")
		}
	}
}

// GetRandomProxy returns a random active proxy (alternative strategy)
func (pm *ProxyManager) GetRandomProxy() (*ProxyConfig, error) {
	pm.mutex.RLock()
	defer pm.mutex.RUnlock()

	activeProxies := make([]*ProxyConfig, 0)
	for i := range pm.proxies {
		if pm.proxies[i].Active {
			activeProxies = append(activeProxies, &pm.proxies[i])
		}
	}

	if len(activeProxies) == 0 {
		return nil, fmt.Errorf("no active proxies available")
	}

	// Use crypto/rand for better randomness in production
	rand.Seed(time.Now().UnixNano())
	selectedProxy := activeProxies[rand.Intn(len(activeProxies))]
	selectedProxy.LastUsed = time.Now()

	log.Printf("🎲 Random proxy selected: %s:%d", selectedProxy.Host, selectedProxy.Port)
	return selectedProxy, nil
}

// MarkProxyFailed marks a proxy as failed and potentially disables it
func (pm *ProxyManager) MarkProxyFailed(proxy *ProxyConfig) {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	proxy.FailCount++
	log.Printf("❌ Proxy %s:%d failed (count: %d)", proxy.Host, proxy.Port, proxy.FailCount)

	if proxy.FailCount >= pm.maxFails {
		proxy.Active = false
		log.Printf("🚫 Proxy %s:%d disabled after %d failures", proxy.Host, proxy.Port, proxy.FailCount)
	}
}

// MarkProxySuccess resets failure count for a proxy
func (pm *ProxyManager) MarkProxySuccess(proxy *ProxyConfig) {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	if proxy.FailCount > 0 {
		log.Printf("✅ Proxy %s:%d succeeded - resetting fail count", proxy.Host, proxy.Port)
		proxy.FailCount = 0
	}
}

// GetActiveProxyCount returns the number of active proxies
func (pm *ProxyManager) GetActiveProxyCount() int {
	pm.mutex.RLock()
	defer pm.mutex.RUnlock()

	count := 0
	for _, proxy := range pm.proxies {
		if proxy.Active {
			count++
		}
	}
	return count
}

// GetProxyURL returns the formatted proxy URL for use with HTTP clients
func (proxy *ProxyConfig) GetProxyURL() string {
	if proxy.Username != "" && proxy.Password != "" {
		return fmt.Sprintf("%s://%s:%s@%s:%d",
			proxy.Type, proxy.Username, proxy.Password, proxy.Host, proxy.Port)
	}
	return fmt.Sprintf("%s://%s:%d", proxy.Type, proxy.Host, proxy.Port)
}

// LoadProxiesFromFile loads proxy configurations from a file
func (pm *ProxyManager) LoadProxiesFromFile(filename string) error {
	// Implementation for loading from JSON/CSV file
	// This would read proxy configurations from external file
	log.Printf("📁 Loading proxies from %s...", filename)

	// Example proxy additions (replace with file reading)
	exampleProxies := []struct {
		host, proxyType, username, password string
		port                                int
	}{
		// Add your proxy providers here
		// {"proxy1.example.com", 8080, "http", "user", "pass"},
		// {"proxy2.example.com", 8080, "http", "user", "pass"},
	}

	for _, p := range exampleProxies {
		pm.AddProxy(p.host, p.port, p.proxyType, p.username, p.password)
	}

	return nil
}
