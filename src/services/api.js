import axios from 'axios';

// Ensure you set VITE_API_URL in your .env file
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
});

export const fetchEmployeeData = async (employeeId) => {
  try {
    const response = await api.get(`/employees/${employeeId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching employee:', error);
    throw error;
  }
};

export default api;
