// Try different base URLs until one works
let API_BASE_URL = window.location.origin; // Use the same origin as the page

// DOM Elements
const studentForm = document.getElementById('studentForm');
const attendanceForm = document.getElementById('attendanceForm');
const studentSelect = document.getElementById('studentSelect');
const attendanceTableBody = document.getElementById('attendanceTableBody');
const editStudentForm = document.getElementById('editStudentForm');
const saveStudentChanges = document.getElementById('saveStudentChanges');

console.log("Using API base URL:", API_BASE_URL);

// Initialize date to today
document.getElementById('attendanceDate').valueAsDate = new Date();

// Helper function for API calls with fetch timeout
async function apiCall(endpoint, method = 'GET', data = null) {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
        
        const options = {
            method,
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            credentials: 'omit',
            signal: controller.signal,
            mode: 'cors'
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        console.log(`Making ${method} request to ${endpoint}`, options);
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        clearTimeout(timeoutId);
        
        console.log(`Response status:`, response.status);
        
        const responseData = await response.json();
        console.log(`Response data:`, responseData);

        if (!response.ok) {
            throw new Error(responseData.error || `API call failed with status ${response.status}`);
        }

        return responseData;
    } catch (error) {
        if (error.name === 'AbortError') {
            console.error(`Request timed out:`, error);
            throw new Error('Request timed out. Server might be unavailable.');
        }
        console.error(`API call failed:`, error);
        throw error;
    }
}

// Fetch and display students
async function fetchStudents() {
    try {
        const students = await apiCall('/api/student-list');
        
        // Update student select dropdown
        studentSelect.innerHTML = '<option value="">Select a student</option>';
        if (students.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No students available';
            option.disabled = true;
            studentSelect.appendChild(option);
            return;
        }
        
        students.forEach(student => {
            // Check if class is undefined and provide a fallback
            const studentClass = student.class || student.student_class || 'N/A';
            console.log('Student data:', student);
            
            const option = document.createElement('option');
            option.value = student.roll_no;
            option.textContent = `${student.roll_no} - ${student.name} (${studentClass})`;
            studentSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error fetching students:', error);
        showAlert(`Error fetching students: ${error.message}`, 'danger');
    }
}

// Fetch and display attendance records
async function fetchAttendance() {
    try {
        const records = await apiCall('/api/attendance');
        
        attendanceTableBody.innerHTML = '';
        if (records.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="6" class="text-center">No attendance records found</td>';
            attendanceTableBody.appendChild(row);
            return;
        }
        
        records.forEach(record => {
            // Ensure class is not undefined
            const studentClass = record.class || record.student_class || 'N/A';
            console.log('Attendance record:', record);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${record.roll_no}</td>
                <td>${record.name}</td>
                <td>${studentClass}</td>
                <td>${record.date}</td>
                <td class="status-${record.status.toLowerCase()}">${record.status}</td>
                <td class="action-buttons">
                    <button class="btn btn-sm btn-danger" onclick="deleteAttendance(${record.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            attendanceTableBody.appendChild(row);
        });
    } catch (error) {
        console.error('Error fetching attendance:', error);
        showAlert(`Error fetching attendance records: ${error.message}`, 'danger');
    }
}

// Add new student
studentForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const rollNo = document.getElementById('rollNo').value;
    const name = document.getElementById('studentName').value;
    const studentClass = document.getElementById('studentClass').value;
    
    if (!rollNo || !name || !studentClass) {
        showAlert('Please fill in all fields', 'warning');
        return;
    }
    
    const studentData = {
        roll_no: parseInt(rollNo),
        name: name,
        class: studentClass
    };
    
    console.log('Sending student data:', studentData);
    
    try {
        await apiCall('/api/student-add', 'POST', studentData);
        showAlert('Student added successfully!', 'success');
        studentForm.reset();
        await fetchStudents();
    } catch (error) {
        console.error('Error adding student:', error);
        showAlert(error.message || 'Error adding student', 'danger');
    }
});

// Mark attendance
attendanceForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const studentSelect = document.getElementById('studentSelect');
    const selectedOption = studentSelect.options[studentSelect.selectedIndex];
    
    if (!studentSelect.value) {
        showAlert('Please select a student', 'warning');
        return;
    }
    
    // Extract roll number from the selected option text (format: "roll_no - name (class)")
    const rollNo = selectedOption.textContent.split(' - ')[0];
    
    const attendanceData = {
        roll_no: parseInt(rollNo),
        date: document.getElementById('attendanceDate').value,
        status: document.querySelector('input[name="status"]:checked').value
    };
    
    console.log('Submitting attendance data:', attendanceData);
    
    try {
        await apiCall('/api/attendance', 'POST', attendanceData);
        showAlert('Attendance marked successfully', 'success');
        attendanceForm.reset();
        document.getElementById('attendanceDate').valueAsDate = new Date();
        
        // Refresh attendance records
        await fetchAttendance();
    } catch (error) {
        console.error('Error marking attendance:', error);
        showAlert(`Error marking attendance: ${error.message}`, 'danger');
    }
});

// Delete attendance record
async function deleteAttendance(id) {
    if (!confirm('Are you sure you want to delete this attendance record?')) {
        return;
    }
    
    try {
        await apiCall(`/api/attendance/${id}`, 'DELETE');
        showAlert('Attendance record deleted successfully', 'success');
        await fetchAttendance();
    } catch (error) {
        console.error('Error deleting attendance:', error);
        showAlert('Error deleting attendance record', 'danger');
    }
}

// Show alert message
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing application...');
    
    try {
        // First check if server is reachable
        console.log('Testing server connectivity...');
        try {
            const pingResponse = await apiCall('/api/ping');
            console.log('Server ping successful:', pingResponse);
            showAlert(`Connected to server. Status: ${pingResponse.status}`, 'success');
        } catch (pingError) {
            console.error('Server ping failed:', pingError);
            showAlert('Unable to connect to server. Please check your connection and try again.', 'danger');
            return; // Stop initialization if server is unreachable
        }
        
        // Continue with normal initialization
        await fetchStudents();
        await fetchAttendance();
    } catch (error) {
        console.error('Error during initialization:', error);
        showAlert('Failed to initialize application. Please check console for details.', 'danger');
    }
}); 