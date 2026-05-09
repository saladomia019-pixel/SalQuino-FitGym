-- =============================================
-- SalQuino FitGym - Fitness Instructors Tables
-- Run this script in your gym_db database
-- =============================================

CREATE TABLE IF NOT EXISTS instructors (
    instructor_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(150),
    phone VARCHAR(20),
    gender ENUM('Male', 'Female', 'Other') DEFAULT 'Other',
    bio TEXT,
    session_rate DECIMAL(10,2) DEFAULT 0.00,
    status ENUM('active', 'inactive') DEFAULT 'active',
    hire_date DATE DEFAULT (CURDATE()),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS instructor_bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    instructor_id INT NOT NULL,
    booking_date DATE NOT NULL,
    session_time VARCHAR(50),
    notes TEXT,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    payment_method ENUM('online', 'walkin') NOT NULL,
    payment_status ENUM('paid', 'pending') DEFAULT 'pending',
    amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(member_id),
    FOREIGN KEY (instructor_id) REFERENCES instructors(instructor_id)
);
