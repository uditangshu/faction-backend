/**
 * k6 Test Configuration
 * Centralized configuration for all k6 tests
 */

export const config = {
  // Base URL - can be overridden via environment variable
  baseUrl: __ENV.BASE_URL || 'http://localhost:8000',
  
  // API version prefix
  apiPrefix: '/api/v1',
  
  // Test credentials (should be set via environment variables in production)
  testUser: {
    phoneNumber:  '8109285049',
    password:  'stringst',
  },
  
  // Default thresholds for all tests
  thresholds: {
    http_reqs: ['rate>100'], // At least 100 requests/sec
  },
  
  // Tags for better organization
  tags: {
    environment: __ENV.ENV || 'local',
    testType: 'load',
  },
};

/**
 * Get full API URL
 */
export function getApiUrl(path) {
  return `${config.baseUrl}${config.apiPrefix}${path}`;
}

/**
 * Generate unique device ID
 */
export function generateDeviceId() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Create device info object
 */
export function createDeviceInfo(deviceId = null) {
  return {
    device_id: deviceId || generateDeviceId(),
    device_type: 'mobile',
    device_model: 'k6 Test Device',
    os_version: 'Android 13',
  };
}

/**
 * Create login payload
 */
export function createLoginPayload(phoneNumber = null, password = null, deviceId = null) {
  return {
    phone_number: phoneNumber || config.testUser.phoneNumber,
    password: password || config.testUser.password,
    device_info: createDeviceInfo(deviceId),
  };
}

/**
 * Check if response is successful
 */
export function isSuccess(status) {
  return status >= 200 && status < 300;
}

/**
 * Extract access token from login response
 */
export function extractAccessToken(response) {
  try {
    const body = JSON.parse(response.body);
    return body.access_token || null;
  } catch (e) {
    return null;
  }
}

