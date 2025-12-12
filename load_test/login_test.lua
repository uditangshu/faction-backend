-- wrk2 script for testing login API
-- Usage: wrk -t12 -c400 -d30s -R2000 --latency -s login_test.lua http://localhost:8000

-- Test credentials (modify these with actual test user credentials)
local phone_number = "+918109285049"
local password = "stringst"

-- Counter for unique device IDs
local counter = 0

-- Generate unique device ID
function generate_device_id()
    counter = counter + 1
    -- Generate a UUID-like string (simplified)
    local template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
    local device_id = string.gsub(template, "[xy]", function(c)
        local v = (c == "x") and math.random(0, 0xf) or math.random(8, 0xb)
        return string.format("%x", v)
    end)
    return device_id
end

-- Request function - called for each request
request = function()
    -- Generate unique device ID for each request
    local device_id = generate_device_id()
    
    -- Build JSON payload
    local body = string.format(
        '{"phone_number":"%s","password":"%s","device_info":{"device_id":"%s","device_type":"mobile","device_model":"Test Device","os_version":"Android 13"}}',
        phone_number,
        password,
        device_id
    )
    
    -- Set headers
    local headers = {}
    headers["Content-Type"] = "application/json"
    headers["User-Agent"] = "wrk2-load-test/1.0"
    
    -- Return request
    return wrk.format("POST", "/api/v1/auth/login", headers, body)
end

-- Response function removed - let wrk2 handle latency measurement automatically
-- If you need to validate responses, uncomment and use carefully:
-- response = function(status, headers, body)
--     -- Don't do anything that might interfere with latency measurement
-- end

-- Done function - called when test completes
done = function(summary, latency, requests)
    io.write("------------------------------\n")
    io.write("Login API Test Summary\n")
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

