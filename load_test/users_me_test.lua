-- wrk2 script for testing /users/me API
-- Optimized for 200+ RPS with connection reuse
-- Usage: wrk -t12 -c800 -d30s -R250 --timeout 30s --latency -s users_me_test.lua http://localhost:8000
-- Note: If socket errors persist, check system limits: ulimit -n (should be >= 10000)

-- Access token for authentication
local access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiYWNiNGI3My1kOTM2LTQzYTctYTAzYy04MzIyMmZiZDMxNmIiLCJwaG9uZSI6Iis5MTgxMDkyODUwNDkiLCJzZXNzaW9uX2lkIjoiODg5OTNkMzAtOGIwYy00YjcyLTliNTYtNmU5N2Y1OTcxMzNlIiwiZXhwIjoxNzY1NTYxODc2LCJ0eXBlIjoiYWNjZXNzIn0.ikbApUeLox4RU2btqH5cpJntBRpVGbca38Kr57T-FEY"

-- Request function - called for each request
request = function()
    -- Set headers with keep-alive for connection reuse
    local headers = {}
    headers["Authorization"] = "Bearer " .. access_token
    headers["Connection"] = "keep-alive"
    headers["User-Agent"] = "wrk2-load-test/1.0"
    
    -- Return GET request to /api/v1/users/me
    return wrk.format("GET", "/api/v1/users/me", headers)
end

-- Response function - optional validation
-- Uncomment if you want to validate responses
-- response = function(status, headers, body)
--     if status ~= 200 then
--         -- Log non-200 responses (optional, can be removed for performance)
--         -- print("Error: " .. status .. " - " .. body:sub(1, 100))
--     end
-- end

-- Done function - called when test completes
done = function(summary, latency, requests)
    io.write("------------------------------\n")
    io.write("Users /me API Test Summary\n")
    io.write("------------------------------\n")
    io.write(string.format("Total Requests: %d\n", summary.requests))
    io.write(string.format("HTTP Errors: %d\n", summary.errors.status))
    io.write(string.format("Socket Errors: %d\n", summary.errors.connect + summary.errors.read + summary.errors.write + summary.errors.timeout))
    io.write(string.format("Requests/sec: %.2f\n", summary.requests / (summary.duration / 1000000)))
    io.write("\nLatency Percentiles:\n")
    -- Check if we have successful requests before calculating percentiles
    if summary.requests > 0 then
        -- Safely get percentiles, handling errors
        local success, p50 = pcall(function() return latency:percentile(50) / 1000 end)
        if success and p50 then
            io.write(string.format("  50%%: %d ms\n", math.floor(p50)))
        end
        
        local success, p75 = pcall(function() return latency:percentile(75) / 1000 end)
        if success and p75 then
            io.write(string.format("  75%%: %d ms\n", math.floor(p75)))
        end
        
        local success, p90 = pcall(function() return latency:percentile(90) / 1000 end)
        if success and p90 then
            io.write(string.format("  90%%: %d ms\n", math.floor(p90)))
        end
        
        local success, p99 = pcall(function() return latency:percentile(99) / 1000 end)
        if success and p99 then
            io.write(string.format("  99%%: %d ms\n", math.floor(p99)))
        end
        
        local success, p999 = pcall(function() return latency:percentile(99.9) / 1000 end)
        if success and p999 then
            io.write(string.format("  99.9%%: %d ms\n", math.floor(p999)))
        end
    else
        io.write("  No successful requests recorded\n")
    end
    io.write("------------------------------\n")
end

