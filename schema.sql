-- =============================================
-- SalQuino FitGym - Complete Database Schema
-- =============================================
-- Import this file into phpMyAdmin to set up
-- the entire database from scratch.
--
-- Default Admin Login:
--   Username: admin
--   Password: admin123
-- =============================================

CREATE DATABASE IF NOT EXISTS `gym_db`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `gym_db`;

-- =============================================
-- 1. ADMINS
-- =============================================
CREATE TABLE IF NOT EXISTS `admins` (
  `admin_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(100) NOT NULL,
  `password` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`admin_id`),
  UNIQUE KEY `uq_admins_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default admin account
INSERT INTO `admins` (`username`, `password`)
SELECT 'admin', 'admin123'
WHERE NOT EXISTS (SELECT 1 FROM `admins` WHERE `username` = 'admin');

-- =============================================
-- 2. MEMBERS
-- =============================================
CREATE TABLE IF NOT EXISTS `members` (
  `member_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `first_name` VARCHAR(100) NOT NULL,
  `last_name` VARCHAR(100) NOT NULL,
  `gender` VARCHAR(32) NOT NULL DEFAULT 'Other',
  `email` VARCHAR(255) NOT NULL,
  `phone` VARCHAR(20) NOT NULL,
  `password` VARCHAR(255) NOT NULL,
  `join_date` DATE NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `height_cm` DECIMAL(5,2) DEFAULT NULL,
  PRIMARY KEY (`member_id`),
  UNIQUE KEY `uq_members_email` (`email`),
  UNIQUE KEY `uq_members_phone` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 3. MEMBERSHIP PLANS
-- =============================================
CREATE TABLE IF NOT EXISTS `membership_plans` (
  `plan_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `plan_name` VARCHAR(150) NOT NULL,
  `type` VARCHAR(80) NOT NULL,
  `duration_days` INT UNSIGNED NOT NULL,
  `price` DECIMAL(10,2) NOT NULL,
  `description` TEXT,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  PRIMARY KEY (`plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 4. MEMBERSHIPS (active member subscriptions)
-- =============================================
CREATE TABLE IF NOT EXISTS `memberships` (
  `membership_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `member_id` INT UNSIGNED NOT NULL,
  `plan_id` INT UNSIGNED NOT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  PRIMARY KEY (`membership_id`),
  KEY `fk_membership_member` (`member_id`),
  KEY `fk_membership_plan` (`plan_id`),
  CONSTRAINT `fk_membership_member` FOREIGN KEY (`member_id`) REFERENCES `members` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_membership_plan` FOREIGN KEY (`plan_id`) REFERENCES `membership_plans` (`plan_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 5. MEMBERSHIP APPLICATIONS
-- =============================================
CREATE TABLE IF NOT EXISTS `membership_applications` (
  `application_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `member_id` INT UNSIGNED NOT NULL,
  `plan_id` INT UNSIGNED NOT NULL,
  `full_name` VARCHAR(200) NOT NULL,
  `email` VARCHAR(255) DEFAULT NULL,
  `phone` VARCHAR(20) NOT NULL,
  `gender` VARCHAR(32) NOT NULL,
  `age` INT UNSIGNED NOT NULL DEFAULT 0,
  `address` TEXT,
  `start_date` DATE DEFAULT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `applied_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`application_id`),
  KEY `fk_app_member` (`member_id`),
  KEY `fk_app_plan` (`plan_id`),
  CONSTRAINT `fk_app_member` FOREIGN KEY (`member_id`) REFERENCES `members` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_app_plan` FOREIGN KEY (`plan_id`) REFERENCES `membership_plans` (`plan_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 6. PAYMENTS
-- =============================================
CREATE TABLE IF NOT EXISTS `payments` (
  `payment_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `member_id` INT UNSIGNED NOT NULL,
  `membership_id` INT UNSIGNED DEFAULT NULL,
  `amount` DECIMAL(10,2) NOT NULL,
  `payment_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `payment_method` VARCHAR(32) DEFAULT NULL,
  PRIMARY KEY (`payment_id`),
  KEY `fk_payment_member` (`member_id`),
  KEY `fk_payment_membership` (`membership_id`),
  CONSTRAINT `fk_payment_member` FOREIGN KEY (`member_id`) REFERENCES `members` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_payment_membership` FOREIGN KEY (`membership_id`) REFERENCES `memberships` (`membership_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 7. ATTENDANCE (Check-ins)
-- =============================================
CREATE TABLE IF NOT EXISTS `attendance` (
  `attendance_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `member_id` INT UNSIGNED NOT NULL,
  `checkin_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`attendance_id`),
  KEY `fk_attendance_member` (`member_id`),
  CONSTRAINT `fk_attendance_member` FOREIGN KEY (`member_id`) REFERENCES `members` (`member_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 8. WEIGHT LOGS (Health Tracker)
-- =============================================
CREATE TABLE IF NOT EXISTS `weight_logs` (
  `log_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `member_id` INT UNSIGNED NOT NULL,
  `weight_kg` DECIMAL(6,2) NOT NULL,
  `logged_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`log_id`),
  KEY `fk_weight_member` (`member_id`),
  CONSTRAINT `fk_weight_member` FOREIGN KEY (`member_id`) REFERENCES `members` (`member_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 9. ANNOUNCEMENTS
-- =============================================
CREATE TABLE IF NOT EXISTS `announcements` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL,
  `content` TEXT NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 10. ADMIN ACTIVITY LOGS
-- =============================================
CREATE TABLE IF NOT EXISTS `admin_activity_logs` (
  `log_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `admin_id` INT UNSIGNED NOT NULL,
  `action_type` VARCHAR(120) NOT NULL,
  `description` TEXT,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`log_id`),
  KEY `fk_admin_activity_admin` (`admin_id`),
  CONSTRAINT `fk_admin_activity_admin` FOREIGN KEY (`admin_id`) REFERENCES `admins` (`admin_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 11. INSTRUCTORS (Self-Registration with Admin Approval)
-- =============================================
CREATE TABLE IF NOT EXISTS `instructors` (
  `instructor_id` INT NOT NULL AUTO_INCREMENT,
  `first_name` VARCHAR(100) NOT NULL,
  `last_name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(150) NOT NULL,
  `phone` VARCHAR(20) DEFAULT NULL,
  `password` VARCHAR(255) NOT NULL,
  `gender` ENUM('Male','Female','Other') DEFAULT 'Other',
  `bio` TEXT,
  `specialization` VARCHAR(255) DEFAULT NULL,
  `facebook` VARCHAR(255) DEFAULT NULL,
  `session_rate` DECIMAL(10,2) DEFAULT 0.00,
  `status` ENUM('pending','active','inactive') DEFAULT 'pending',
  `hire_date` DATE DEFAULT (CURDATE()),
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`instructor_id`),
  UNIQUE KEY `uq_instructors_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 12. INSTRUCTOR PLANS (Subscription Plans by Instructor)
-- =============================================
CREATE TABLE IF NOT EXISTS `instructor_plans` (
  `plan_id` INT NOT NULL AUTO_INCREMENT,
  `instructor_id` INT NOT NULL,
  `plan_name` VARCHAR(150) NOT NULL,
  `duration_days` INT UNSIGNED NOT NULL,
  `price` DECIMAL(10,2) NOT NULL,
  `description` TEXT,
  `status` ENUM('active','inactive') DEFAULT 'active',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`plan_id`),
  KEY `fk_iplan_instructor` (`instructor_id`),
  CONSTRAINT `fk_iplan_instructor` FOREIGN KEY (`instructor_id`) REFERENCES `instructors` (`instructor_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 13. INSTRUCTOR BOOKINGS (Subscription-based Hiring)
-- =============================================
CREATE TABLE IF NOT EXISTS `instructor_bookings` (
  `booking_id` INT NOT NULL AUTO_INCREMENT,
  `member_id` INT UNSIGNED NOT NULL,
  `instructor_id` INT NOT NULL,
  `plan_id` INT NOT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `schedule_days` VARCHAR(100) NOT NULL,
  `time_start` TIME NOT NULL,
  `time_end` TIME NOT NULL,
  `notes` TEXT,
  `status` ENUM('pending','approved','rejected','completed','cancelled') DEFAULT 'pending',
  `payment_method` ENUM('online','walkin') NOT NULL,
  `payment_status` ENUM('paid','pending') DEFAULT 'pending',
  `amount` DECIMAL(10,2) NOT NULL,
  `admin_commission` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `instructor_earning` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`booking_id`),
  KEY `fk_sub_member` (`member_id`),
  KEY `fk_sub_instructor` (`instructor_id`),
  KEY `fk_sub_plan` (`plan_id`),
  CONSTRAINT `fk_sub_member` FOREIGN KEY (`member_id`) REFERENCES `members` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sub_instructor` FOREIGN KEY (`instructor_id`) REFERENCES `instructors` (`instructor_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sub_plan` FOREIGN KEY (`plan_id`) REFERENCES `instructor_plans` (`plan_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
