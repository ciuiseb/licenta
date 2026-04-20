class APIError extends Error {
  constructor(message, status, type, originalError) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.type = type;
    this.originalError = originalError;
  }

  isNetworkError() {
    return this.type === 'network';
  }

  isValidationError() {
    return this.status === 400 || this.type === 'validation_error';
  }

  isServerError() {
    return this.status >= 500;
  }

  isTimeout() {
    return this.type === 'timeout';
  }
}

class APIClient {
  constructor(baseURL = '') {
    this.baseURL = baseURL || 'http://localhost:5000';
    this.defaultTimeout = 30000;
    this.maxRetries = 3;
    this.retryDelay = 1000;
  }

  async fetchWithTimeout(url, options = {}, timeout = this.defaultTimeout) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new APIError(
          'Request timeout',
          408,
          'timeout',
          error
        );
      }
      throw error;
    }
  }

  calculateRetryDelay(attempt) {
    return this.retryDelay * Math.pow(2, attempt);
  }

  async retryRequest(requestFn, retries = this.maxRetries) {
    let lastError;
    
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        return await requestFn();
      } catch (error) {
        lastError = error;
        
        if (error instanceof APIError) {
          if (error.isValidationError() || error.status === 404) {
            throw error;
          }
          
          if (error.isServerError() || error.isNetworkError() || error.isTimeout()) {
            if (attempt < retries) {
              const delay = this.calculateRetryDelay(attempt);
              console.log(`Retry attempt ${attempt + 1}/${retries} after ${delay}ms`);
              await new Promise(resolve => setTimeout(resolve, delay));
              continue;
            }
          }
        } else {
          if (attempt < retries) {
            const delay = this.calculateRetryDelay(attempt);
            console.log(`Retry attempt ${attempt + 1}/${retries} after ${delay}ms`);
            await new Promise(resolve => setTimeout(resolve, delay));
            continue;
          }
        }
        
        throw error;
      }
    }
    
    throw lastError;
  }

  async handleResponse(response) {
    const contentType = response.headers.get('content-type');
    
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      let errorData = null;

      if (contentType && contentType.includes('application/json')) {
        try {
          errorData = await response.json();
          errorMessage = errorData.error?.message || errorData.error || errorMessage;
        } catch (e) {
          console.error('Failed to parse error response:', e);
        }
      }

      throw new APIError(
        errorMessage,
        response.status,
        errorData?.error?.type || 'http_error',
        errorData
      );
    }

    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }

    return await response.text();
  }

  handleError(error) {
    if (error instanceof APIError) {
      throw error;
    }
    
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new APIError(
        'Network error: Unable to connect to server',
        0,
        'network',
        error
      );
    }

    throw new APIError(
      error.message || 'Unknown error occurred',
      0,
      'unknown',
      error
    );
  }

  async makeRequest(method, endpoint, data, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    const requestFn = async () => {
      const response = await this.fetchWithTimeout(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        credentials: 'include',
        body: data ? JSON.stringify(data) : undefined,
        ...options
      }, options.timeout);

      return await this.handleResponse(response);
    };

    try {
      return await this.retryRequest(requestFn, options.retries ?? this.maxRetries);
    } catch (error) {
      this.handleError(error);
    }
  }

  async post(endpoint, data, options = {}) {
    return this.makeRequest('POST', endpoint, data, options);
  }

  async get(endpoint, options = {}) {
    return this.makeRequest('GET', endpoint, null, options);
  }

  createSSEConnection(endpoint, data, options = {}) {
    const baseURL = this.baseURL;
    const controller = new AbortController();
    
    return {
      controller,
      
      async *stream() {
        const url = `${baseURL}${endpoint}`;
        
        try {
          const response = await fetch(url, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Cache-Control': 'no-cache',
              ...options.headers
            },
            credentials: 'include',
            body: JSON.stringify(data),
            signal: controller.signal
          });

          if (!response.ok) {
            const contentType = response.headers.get('content-type');
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            
            if (contentType && contentType.includes('text/event-stream')) {
              const reader = response.body.getReader();
              const decoder = new TextDecoder();
              const { value } = await reader.read();
              const text = decoder.decode(value);
              
              const lines = text.split('\n');
              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.substring(6));
                    errorMessage = data.error || errorMessage;
                  } catch (e) {
                    console.error('Failed to parse SSE error:', e);
                  }
                }
              }
            }

            throw new APIError(
              errorMessage,
              response.status,
              'sse_error',
              null
            );
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.substring(6));
                  yield data;
                } catch (e) {
                  console.error('Failed to parse SSE message:', line, e);
                }
              }
            }
          }
        } catch (error) {
          if (error.name === 'AbortError') {
            console.log('SSE connection aborted');
            return;
          }
          
          if (error instanceof APIError) {
            throw error;
          }
          
          throw new APIError(
            error.message || 'SSE connection failed',
            0,
            'network',
            error
          );
        }
      },
      
      abort() {
        controller.abort();
      }
    };
  }
}

const apiClient = new APIClient();

export { apiClient, APIError };
export default apiClient;
