-- ============================================
-- Database Schema cho Schedule Chatbot System
-- ============================================

CREATE DATABASE IF NOT EXISTS schedule_db;
USE schedule_db;

-- ============================================
-- Bảng Schedules (Thời Khóa Biểu)
-- ============================================
CREATE TABLE schedules (
    schedule_id INT AUTO_INCREMENT PRIMARY KEY,
    schedule_code VARCHAR(50) UNIQUE NOT NULL,
    schedule_name VARCHAR(255),
    week INT,
    semester VARCHAR(50),
    academic_year VARCHAR(20),
    status ENUM('draft', 'active', 'archived') DEFAULT 'draft',
    quality_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    metadata JSON,
    INDEX idx_schedule_code (schedule_code),
    INDEX idx_week (week),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Bảng Courses (Môn học)
-- ============================================
CREATE TABLE courses (
    course_id INT AUTO_INCREMENT PRIMARY KEY,
    course_code VARCHAR(50) UNIQUE NOT NULL,
    course_name VARCHAR(255) NOT NULL,
    course_type ENUM('theory', 'practical', 'lab') DEFAULT 'theory',
    credits INT,
    department VARCHAR(100),
    INDEX idx_course_code (course_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Bảng Rooms (Phòng học)
-- ============================================
CREATE TABLE rooms (
    room_id INT AUTO_INCREMENT PRIMARY KEY,
    room_code VARCHAR(50) UNIQUE NOT NULL,
    room_name VARCHAR(100) NOT NULL,
    room_type ENUM('classroom', 'lab', 'lecture_hall') DEFAULT 'classroom',
    capacity INT NOT NULL,
    building VARCHAR(100),
    floor INT,
    facilities JSON,
    INDEX idx_room_code (room_code),
    INDEX idx_capacity (capacity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Bảng Teachers (Giảng viên)
-- ============================================
CREATE TABLE teachers (
    teacher_id INT AUTO_INCREMENT PRIMARY KEY,
    teacher_code VARCHAR(50) UNIQUE NOT NULL,
    teacher_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    department VARCHAR(100),
    max_hours_per_week INT DEFAULT 40,
    preferences JSON,
    INDEX idx_teacher_code (teacher_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Bảng Schedule_Courses (Liên kết TKB - Môn học)
-- ============================================
CREATE TABLE schedule_courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    schedule_id INT NOT NULL,
    course_id INT NOT NULL,
    teacher_id INT,
    room_id INT,
    day_of_week ENUM('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'),
    start_time TIME,
    end_time TIME,
    session_type ENUM('morning', 'afternoon', 'evening'),
    FOREIGN KEY (schedule_id) REFERENCES schedules(schedule_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id),
    INDEX idx_schedule (schedule_id),
    INDEX idx_day_time (day_of_week, start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Bảng Schedule_Rooms (Sử dụng phòng theo TKB)
-- ============================================
CREATE TABLE schedule_rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    schedule_id INT NOT NULL,
    room_id INT NOT NULL,
    day_of_week VARCHAR(20),
    start_time TIME,
    end_time TIME,
    utilization_rate DECIMAL(5,2),
    FOREIGN KEY (schedule_id) REFERENCES schedules(schedule_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id),
    INDEX idx_schedule_room (schedule_id, room_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Bảng Constraints (Ràng buộc)
-- ============================================
CREATE TABLE constraints (
    constraint_id INT AUTO_INCREMENT PRIMARY KEY,
    constraint_code VARCHAR(50) UNIQUE NOT NULL,
    constraint_name VARCHAR(255) NOT NULL,
    constraint_type ENUM('hard', 'soft') DEFAULT 'soft',
    severity ENUM('low', 'medium', 'high') DEFAULT 'medium',
    description TEXT,
    weight DECIMAL(5,2) DEFAULT 1.0,
    INDEX idx_constraint_code (constraint_code),
    INDEX idx_type_severity (constraint_type, severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Bảng Violations (Vi phạm)
-- ============================================
CREATE TABLE violations (
    violation_id INT AUTO_INCREMENT PRIMARY KEY,
    schedule_code VARCHAR(50) NOT NULL,
    constraint_id INT NOT NULL,
    violation_type VARCHAR(100),
    description TEXT,
    severity_score DECIMAL(5,2),
    affected_entities JSON,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (constraint_id) REFERENCES constraints(constraint_id),
    INDEX idx_schedule (schedule_code),
    INDEX idx_constraint (constraint_id),
    INDEX idx_detected (detected_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Bảng Metrics (Chỉ số đánh giá)
-- ============================================
CREATE TABLE metrics (
    metric_id INT AUTO_INCREMENT PRIMARY KEY,
    schedule_code VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4),
    metric_category VARCHAR(50),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (schedule_code) REFERENCES schedules(schedule_code) ON DELETE CASCADE,
    INDEX idx_schedule_metric (schedule_code, metric_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Bảng Chat_History (Lịch sử chat)
-- ============================================
CREATE TABLE chat_history (
    chat_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    query TEXT NOT NULL,
    intent VARCHAR(50),
    response TEXT,
    entities JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_session (session_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Sample Data (Dữ liệu mẫu)
-- ============================================

-- Insert sample constraints
INSERT INTO constraints (constraint_code, constraint_name, constraint_type, severity, description, weight) VALUES
('HARD_ROOM_CONFLICT', 'Trùng phòng học', 'hard', 'high', 'Không được xếp 2 lớp cùng phòng cùng giờ', 10.0),
('HARD_TEACHER_CONFLICT', 'Trùng giờ giảng viên', 'hard', 'high', 'Giảng viên không thể dạy 2 lớp cùng lúc', 10.0),
('SOFT_ROOM_CAPACITY', 'Vượt sức chứa phòng', 'soft', 'medium', 'Số sinh viên vượt quá sức chứa phòng', 5.0),
('SOFT_MORNING_PREFERENCE', 'Ưu tiên buổi sáng', 'soft', 'low', 'Ưu tiên xếp lớp vào buổi sáng', 2.0),
('SOFT_TEACHER_HOURS', 'Giờ dạy tối đa', 'soft', 'medium', 'Giảng viên không nên dạy quá nhiều giờ/tuần', 4.0),
('SOFT_ROOM_TYPE', 'Loại phòng phù hợp', 'soft', 'medium', 'Môn thực hành nên xếp vào phòng lab', 3.0),
('SOFT_WEEKLY_BALANCE', 'Cân bằng tuần', 'soft', 'low', 'Phân bổ đều môn học trong tuần', 2.5);

-- Insert sample courses
INSERT INTO courses (course_code, course_name, course_type, credits, department) VALUES
('CS101', 'Nhập môn Lập trình', 'theory', 3, 'Computer Science'),
('CS102', 'Cấu trúc dữ liệu', 'theory', 4, 'Computer Science'),
('CS103L', 'Thực hành Lập trình', 'lab', 2, 'Computer Science'),
('MATH101', 'Toán cao cấp 1', 'theory', 4, 'Mathematics'),
('PHY101', 'Vật lý đại cương', 'theory', 3, 'Physics'),
('PHY101L', 'Thí nghiệm Vật lý', 'lab', 1, 'Physics');

-- Insert sample rooms
INSERT INTO rooms (room_code, room_name, room_type, capacity, building, floor) VALUES
('A101', 'Phòng lý thuyết A101', 'classroom', 60, 'Building A', 1),
('A102', 'Phòng lý thuyết A102', 'classroom', 80, 'Building A', 1),
('B201', 'Phòng giảng đường B201', 'lecture_hall', 150, 'Building B', 2),
('LAB301', 'Phòng Lab máy tính 1', 'lab', 40, 'Building C', 3),
('LAB302', 'Phòng Lab máy tính 2', 'lab', 35, 'Building C', 3);

-- Insert sample teachers
INSERT INTO teachers (teacher_code, teacher_name, email, department, max_hours_per_week) VALUES
('T001', 'Nguyễn Văn A', 'nguyenvana@university.edu', 'Computer Science', 40),
('T002', 'Trần Thị B', 'tranthib@university.edu', 'Computer Science', 35),
('T003', 'Lê Văn C', 'levanc@university.edu', 'Mathematics', 40),
('T004', 'Phạm Thị D', 'phamthid@university.edu', 'Physics', 38);

-- Insert sample schedules
INSERT INTO schedules (schedule_code, schedule_name, week, semester, academic_year, status, quality_score) VALUES
('CLB101', 'Lịch học Khoa CNTT Tuần 1', 1, 'Fall', '2024-2025', 'active', 85.50),
('CLB102', 'Lịch học Khoa CNTT Tuần 2', 2, 'Fall', '2024-2025', 'active', 78.30),
('ABC123', 'Lịch học Khoa Toán Tuần 1', 1, 'Fall', '2024-2025', 'draft', 72.10);

-- Insert sample schedule_courses
INSERT INTO schedule_courses (schedule_id, course_id, teacher_id, room_id, day_of_week, start_time, end_time, session_type) VALUES
(1, 1, 1, 1, 'Monday', '08:00', '10:00', 'morning'),
(1, 2, 2, 2, 'Wednesday', '08:00', '10:00', 'morning'),
(1, 3, 1, 4, 'Friday', '14:00', '16:00', 'afternoon');

-- Insert sample violations
INSERT INTO violations (schedule_code, constraint_id, violation_type, description, severity_score) VALUES
('CLB102', 3, 'room_capacity', 'Phòng A101: 65 sinh viên > 60 chỗ ngồi', 3.5),
('ABC123', 5, 'teacher_hours', 'Giảng viên T001: 42 giờ/tuần > 40 giờ', 2.8);

-- Insert sample metrics
INSERT INTO metrics (schedule_code, metric_name, metric_value, metric_category) VALUES
('CLB101', 'weekly_balance', 0.85, 'distribution'),
('CLB101', 'room_utilization', 0.72, 'efficiency'),
('CLB101', 'teacher_workload', 0.88, 'workload'),
('CLB102', 'weekly_balance', 0.78, 'distribution'),
('CLB102', 'violation_count', 2.00, 'quality');

-- ============================================
-- Views (For easier querying)
-- ============================================

CREATE VIEW v_schedule_summary AS
SELECT 
    s.schedule_code,
    s.schedule_name,
    s.week,
    s.quality_score,
    COUNT(DISTINCT sc.course_id) as total_courses,
    COUNT(DISTINCT sc.room_id) as total_rooms,
    COUNT(DISTINCT sc.teacher_id) as total_teachers,
    COUNT(v.violation_id) as total_violations
FROM schedules s
LEFT JOIN schedule_courses sc ON s.schedule_id = sc.schedule_id
LEFT JOIN violations v ON s.schedule_code = v.schedule_code
GROUP BY s.schedule_id;

CREATE VIEW v_room_utilization AS
SELECT 
    r.room_code,
    r.room_name,
    r.capacity,
    COUNT(sc.id) as total_sessions,
    AVG(sr.utilization_rate) as avg_utilization
FROM rooms r
LEFT JOIN schedule_rooms sr ON r.room_id = sr.room_id
LEFT JOIN schedule_courses sc ON r.room_id = sc.room_id
GROUP BY r.room_id;

-- ============================================
-- Indexes for Performance
-- ============================================

-- Composite indexes for common queries
CREATE INDEX idx_schedule_course_lookup ON schedule_courses(schedule_id, day_of_week, start_time);
CREATE INDEX idx_violation_lookup ON violations(schedule_code, constraint_id, detected_at);
CREATE INDEX idx_metric_lookup ON metrics(schedule_code, metric_name, calculated_at);

-- ============================================
-- End of Schema
-- ============================================