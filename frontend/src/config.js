// API Configuration
export const API_URL = import.meta.env.VITE_API_URL || 'https://github-bug-detection.onrender.com';

// Export for easy access
export default {
    API_URL,
    isDevelopment: import.meta.env.DEV,
    isProduction: import.meta.env.PROD
};
