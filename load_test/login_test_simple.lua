-- wrk2 script for testing login API (simplified - without device_info)
-- Usage: wrk -t12 -c400 -d30s -R2000 --latency -s login_test_simple.lua http://localhost:8000

-- Test credentials (modify these with actual test user credentials)
local phone_number = "+918109285049"
local password = "stringst"

-- Request function - called for each request
request = function()
    -- Build JSON payload without device_info (optional field)
    local body = string.format(
        '{"phone_number":"%s","password":"%s"}',
        phone_number,
        password
    )
    
    -- Set headers
    local headers = {}
    headers["Content-Type"] = "application/json"
    headers["User-Agent"] = "wrk2-load-test/1.0"
    
    -- Return request
    return wrk.format("POST", "/api/v1/auth/login", headers, body)
end

-- Response function - called after each response
response = function(status, headers, body)
    -- Optional: Log errors or validate responses
    if status ~= 200 then
        -- Log non-200 responses (optional, can be removed for performance)
        -- print("Error: " .. status .. " - " .. body:sub(1, 100))
    end
end

-- Done function - called when test completes
done = function(summary, latency, requests)
    io.write("------------------------------\n")
    io.write("Login API Test Summary (Simple)\n")
    io.write("------------------------------\n")
    io.write(string.format("Total Requests: %d\n", summary.requests))
    io.write(string.format("HTTP Errors: %d\n", summary.errors.status))
    io.write(string.format("Socket Errors: %d\n", summary.errors.connect + summary.errors.read + summary.errors.write + summary.errors.timeout))
    io.write(string.format("Requests/sec: %.2f\n", summary.requests / (summary.duration / 1000000)))
    io.write("\nLatency Percentiles:\n")
    io.write(string.format("  50%%: %d ms\n", latency:percentile(50) / 1000))
    io.write(string.format("  75%%: %d ms\n", latency:percentile(75) / 1000))
    io.write(string.format("  90%%: %d ms\n", latency:percentile(90) / 1000))
    io.write(string.format("  99%%: %d ms\n", latency:percentile(99) / 1000))
    io.write(string.format("  99.9%%: %d ms\n", latency:percentile(99.9) / 1000))
    io.write("------------------------------\n")
end

