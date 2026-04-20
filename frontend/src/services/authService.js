import apiClient from './apiClient';

class AuthService {
  constructor() {
    this.authenticated = false;
    this.sessionId = null;
  }

  async login(passcode) {
    try {
      const response = await apiClient.post('/api/auth/login', { passcode }, {
        timeout: 10000,
        retries: 2
      });

      if (response.success) {
        this.authenticated = true;
        this.sessionId = response.session_id;
        localStorage.setItem('authenticated', 'true');
        return { success: true };
      }

      return { success: false, error: 'Login failed' };
    } catch (error) {
      console.error('Login error:', error);
      return { 
        success: false, 
        error: error.message || 'Invalid passcode' 
      };
    }
  }

  async logout() {
    try {
      await apiClient.post('/api/auth/logout', {}, {
        timeout: 5000,
        retries: 1
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.authenticated = false;
      this.sessionId = null;
      localStorage.removeItem('authenticated');
    }
  }

  async checkStatus() {
    try {
      const response = await apiClient.get('/api/auth/status', {
        timeout: 5000,
        retries: 1
      });

      this.authenticated = response.authenticated;
      this.sessionId = response.session_id;
      
      if (this.authenticated) {
        localStorage.setItem('authenticated', 'true');
      } else {
        localStorage.removeItem('authenticated');
      }

      return response.authenticated;
    } catch (error) {
      console.error('Status check error:', error);
      this.authenticated = false;
      this.sessionId = null;
      localStorage.removeItem('authenticated');
      return false;
    }
  }

  isAuthenticated() {
    return this.authenticated || localStorage.getItem('authenticated') === 'true';
  }

  getSessionId() {
    return this.sessionId;
  }
}

const authService = new AuthService();

export { authService };
export default authService;
