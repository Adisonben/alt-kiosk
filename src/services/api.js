import axios from 'axios';

// Ensure you set VITE_API_URL in your .env file
const API_URL = import.meta.env.VITE_API_URL || 'https://alcohol.idclever.net/api';

const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
});

export const fetchEmployeeData = async (employeeId) => {
  try {
    const device_data = await fetchDeviceData();
    const orgId = device_data.org_id;
    const token = device_data.token;

    const response = await axios.get(`${API_URL}/device/employee/${orgId}/${employeeId}`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    console.log("Fetching employee success: ", response.data);
    return response.data;
  } catch (error) {
    console.error('Error fetching employee:', error);
    throw error;
  }
};

export const fetchDeviceData = async () => {
  try {
    const response = await axios.get('/device_data.json');
    return response.data;
  } catch (error) {
    console.error('Error fetching device data:', error);
    throw error;
  }
};

export default api;
