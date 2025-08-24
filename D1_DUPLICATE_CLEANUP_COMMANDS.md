# 🚨 D1 Database Duplicate Cleanup Commands

## Current Status
- **Total contacts**: 48,286
- **Estimated duplicates**: ~35,000-37,000 (77% of database!)
- **Unique contacts**: ~10,889

## Direct D1 SQL Access Methods

### 1. **Cloudflare Dashboard** (Recommended)
```
1. Go to: https://dash.cloudflare.com/
2. Navigate to: D1 Database > equipment-contacts > Console
3. Run SQL queries directly in the web interface
```

### 2. **Wrangler CLI**
```bash
# Check total contacts
npx wrangler d1 execute equipment-contacts --remote --command "SELECT COUNT(*) as total FROM contacts"

# Run any SQL command
npx wrangler d1 execute equipment-contacts --remote --command "YOUR_SQL_QUERY_HERE"
```

## Duplicate Analysis Queries

### Find Phone Number Duplicates
```sql
SELECT primary_phone, COUNT(*) as duplicate_count, 
       GROUP_CONCAT(id) as contact_ids
FROM contacts 
WHERE primary_phone IS NOT NULL AND primary_phone != ""
GROUP BY primary_phone 
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT 20;
```

### Find Company Name Duplicates
```sql
SELECT seller_company, COUNT(*) as duplicate_count
FROM contacts 
WHERE seller_company IS NOT NULL AND seller_company != ""
GROUP BY seller_company 
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT 20;
```

### Find Exact Duplicates (Phone + Company)
```sql
SELECT primary_phone, seller_company, COUNT(*) as duplicate_count
FROM contacts 
WHERE primary_phone IS NOT NULL AND seller_company IS NOT NULL
GROUP BY primary_phone, seller_company
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;
```

### Count Total Duplicates
```sql
-- Phone duplicates
SELECT SUM(duplicate_count - 1) as total_phone_duplicates
FROM (
    SELECT COUNT(*) as duplicate_count
    FROM contacts 
    WHERE primary_phone IS NOT NULL AND primary_phone != ""
    GROUP BY primary_phone 
    HAVING COUNT(*) > 1
);
```

## Duplicate Cleanup Strategies

### Option 1: Keep Newest Records (Recommended)
```sql
-- Delete older duplicates, keep the one with latest last_updated
DELETE FROM contacts 
WHERE id IN (
    SELECT id FROM (
        SELECT id, 
               ROW_NUMBER() OVER (
                   PARTITION BY primary_phone, seller_company 
                   ORDER BY last_updated DESC
               ) as rn
        FROM contacts
        WHERE primary_phone IS NOT NULL AND seller_company IS NOT NULL
    ) ranked
    WHERE rn > 1
);
```

### Option 2: Keep Records with Most Data
```sql
-- Delete duplicates, keep the one with most complete information
DELETE FROM contacts 
WHERE id IN (
    SELECT id FROM (
        SELECT id, 
               ROW_NUMBER() OVER (
                   PARTITION BY primary_phone, seller_company 
                   ORDER BY 
                       CASE WHEN email IS NOT NULL AND email != "" THEN 1 ELSE 0 END +
                       CASE WHEN website IS NOT NULL AND website != "" THEN 1 ELSE 0 END +
                       CASE WHEN total_listings > 0 THEN 1 ELSE 0 END DESC,
                       last_updated DESC
               ) as rn
        FROM contacts
        WHERE primary_phone IS NOT NULL AND seller_company IS NOT NULL
    ) ranked
    WHERE rn > 1
);
```

### Option 3: Backup and Clean (Safest)
```sql
-- 1. First, create backup table
CREATE TABLE contacts_backup AS SELECT * FROM contacts;

-- 2. Then run cleanup (choose Option 1 or 2 above)

-- 3. If something goes wrong, restore:
-- DROP TABLE contacts;
-- CREATE TABLE contacts AS SELECT * FROM contacts_backup;
```

## Prevention: Updated Upload Logic

### Duplicate-Prevention Insert Query
```sql
INSERT OR IGNORE INTO contacts (
    id, seller_company, primary_phone, primary_location, 
    email, website, total_listings, priority_score, 
    priority_level, first_contact_date, last_updated, 
    notes, city, state, country
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
```

### Check Before Insert
```sql
SELECT COUNT(*) FROM contacts 
WHERE primary_phone = ? AND seller_company = ?;
```

## Recommended Action Plan

1. **🛑 STOP current uploads** (they're adding more duplicates)
2. **📊 Analyze**: Run duplicate analysis queries above
3. **💾 Backup**: Create backup table (Option 3)
4. **🧹 Clean**: Use Option 1 (keep newest) or Option 2 (keep most complete)
5. **🔄 Update**: Modify ultra_fast_d1.py to prevent future duplicates
6. **✅ Verify**: Check results and update processes

## Expected Results After Cleanup
- **Before**: 48,286 contacts (77% duplicates)
- **After**: ~10,889 unique contacts
- **Space saved**: ~37,397 duplicate records removed
- **Database efficiency**: 4.4x improvement
