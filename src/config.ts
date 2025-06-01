// API Configuration
const getAPIBase = () => {
  // Check if we have a custom API URL from environment
  const envApiUrl = import.meta.env.VITE_API_BASE_URL;
  if (envApiUrl) {
    return envApiUrl;
  }
  
  // Default to production URL in production, empty string for local proxy in dev
  return import.meta.env.PROD 
    ? 'https://nbwm-backend.onrender.com' 
    : '';
};

export const API_BASE = getAPIBase();