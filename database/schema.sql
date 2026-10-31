-- =============================================================================
-- SUPPLIER ACKNOWLEDGEMENT AND SCHEDULE IMPACT MANAGER
-- Database Schema Definition (MySQL 8.0)
-- Character Set: utf8mb4 | Collation: utf8mb4_unicode_ci
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `supplier_schedule_manager`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `supplier_schedule_manager`;

-- 1. Suppliers
CREATE TABLE IF NOT EXISTS `suppliers` (
  `supplier_id` VARCHAR(32) NOT NULL PRIMARY KEY,
  `supplier_name` VARCHAR(128) NOT NULL,
  `lead_time_days` INT NOT NULL DEFAULT 7,
  `status` ENUM('ACTIVE', 'SUSPENDED', 'UNDER_REVIEW') NOT NULL DEFAULT 'ACTIVE',
  `created_at` DATETIME NOT NULL,
  `updated_at` DATETIME NOT NULL,
  INDEX `idx_supplier_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Items catalog
CREATE TABLE IF NOT EXISTS `items` (
  `item_id` VARCHAR(32) NOT NULL PRIMARY KEY,
  `sku` VARCHAR(64) NOT NULL UNIQUE,
  `item_name` VARCHAR(128) NOT NULL,
  `category` VARCHAR(64) NOT NULL,
  `unit_cost` DECIMAL(12,2) NOT NULL,
  `lead_time_days` INT NOT NULL DEFAULT 7,
  `created_at` DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Purchase Orders
CREATE TABLE IF NOT EXISTS `purchase_orders` (
  `po_id` VARCHAR(32) NOT NULL PRIMARY KEY,
  `supplier_id` VARCHAR(32) NOT NULL,
  `order_date` DATE NOT NULL,
  `status` ENUM('OPEN', 'ACKNOWLEDGED', 'CHANGE_PENDING', 'APPROVED', 'REJECTED', 'CLOSED') NOT NULL DEFAULT 'OPEN',
  `total_amount` DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  `created_at` DATETIME NOT NULL,
  `updated_at` DATETIME NOT NULL,
  INDEX `idx_po_supplier` (`supplier_id`),
  INDEX `idx_po_status` (`status`),
  CONSTRAINT `fk_po_supplier` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers` (`supplier_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Purchase Order Lines
CREATE TABLE IF NOT EXISTS `po_lines` (
  `po_line_id` VARCHAR(32) NOT NULL PRIMARY KEY,
  `po_id` VARCHAR(32) NOT NULL,
  `item_id` VARCHAR(32) NOT NULL,
  `ordered_qty` INT NOT NULL,
  `unit_price` DECIMAL(12,2) NOT NULL,
  `requested_delivery_date` DATE NOT NULL,
  `status` ENUM('OPEN', 'ACKNOWLEDGED', 'CHANGE_REQUESTED', 'CANCELLED', 'CLOSED') NOT NULL DEFAULT 'OPEN',
  INDEX `idx_pol_po` (`po_id`),
  INDEX `idx_pol_item` (`item_id`),
  CONSTRAINT `fk_pol_po` FOREIGN KEY (`po_id`) REFERENCES `purchase_orders` (`po_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_pol_item` FOREIGN KEY (`item_id`) REFERENCES `items` (`item_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Acknowledgements
CREATE TABLE IF NOT EXISTS `acknowledgements` (
  `ack_id` VARCHAR(32) NOT NULL PRIMARY KEY,
  `po_line_id` VARCHAR(32) NOT NULL,
  `revision_no` INT NOT NULL DEFAULT 1,
  `accepted_qty` INT NOT NULL,
  `rejected_qty` INT NOT NULL DEFAULT 0,
  `acknowledgement_date` DATE NOT NULL,
  `status` ENUM('FULL_ACCEPTANCE', 'PARTIAL_ACCEPTANCE', 'REJECTED', 'CHANGE_PROPOSED') NOT NULL,
  INDEX `idx_ack_line` (`po_line_id`),
  CONSTRAINT `fk_ack_line` FOREIGN KEY (`po_line_id`) REFERENCES `po_lines` (`po_line_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Promise Dates
CREATE TABLE IF NOT EXISTS `promise_dates` (
  `promise_id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `ack_id` VARCHAR(32) NOT NULL,
  `promised_date` DATE NOT NULL,
  `revision_no` INT NOT NULL DEFAULT 1,
  `effective_at` DATETIME NOT NULL,
  INDEX `idx_prm_ack` (`ack_id`),
  CONSTRAINT `fk_prm_ack` FOREIGN KEY (`ack_id`) REFERENCES `acknowledgements` (`ack_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Change Requests
CREATE TABLE IF NOT EXISTS `change_requests` (
  `change_id` VARCHAR(32) NOT NULL PRIMARY KEY,
  `po_line_id` VARCHAR(32) NOT NULL,
  `change_type` ENUM('QUANTITY', 'PRICE', 'DELIVERY_DATE', 'COMBINED') NOT NULL,
  `old_value` VARCHAR(255) NOT NULL,
  `new_value` VARCHAR(255) NOT NULL,
  `revision_no` INT NOT NULL DEFAULT 1,
  `status` ENUM('PROPOSED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'APPLIED', 'SUPERSEDED') NOT NULL DEFAULT 'PENDING_APPROVAL',
  `requested_at` DATETIME NOT NULL,
  INDEX `idx_cr_line` (`po_line_id`),
  INDEX `idx_cr_status` (`status`),
  CONSTRAINT `fk_cr_line` FOREIGN KEY (`po_line_id`) REFERENCES `po_lines` (`po_line_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Approvals
CREATE TABLE IF NOT EXISTS `approvals` (
  `approval_id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `change_id` VARCHAR(32) NOT NULL,
  `decision` ENUM('APPROVED', 'REJECTED', 'PENDING') NOT NULL DEFAULT 'PENDING',
  `reviewer_id` VARCHAR(64) NULL,
  `decision_date` DATETIME NULL,
  `comments` TEXT NULL,
  INDEX `idx_app_change` (`change_id`),
  CONSTRAINT `fk_app_change` FOREIGN KEY (`change_id`) REFERENCES `change_requests` (`change_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Inventory Plans
CREATE TABLE IF NOT EXISTS `inventory_plans` (
  `plan_id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `po_line_id` VARCHAR(32) NOT NULL,
  `projected_supply` INT NOT NULL,
  `required_qty` INT NOT NULL,
  `status` ENUM('BALANCED', 'SHORTAGE', 'SURPLUS') NOT NULL DEFAULT 'BALANCED',
  `effective_at` DATETIME NOT NULL,
  INDEX `idx_plan_line` (`po_line_id`),
  CONSTRAINT `fk_plan_line` FOREIGN KEY (`po_line_id`) REFERENCES `po_lines` (`po_line_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Production Orders
CREATE TABLE IF NOT EXISTS `production_orders` (
  `production_order_id` VARCHAR(32) NOT NULL PRIMARY KEY,
  `item_id` VARCHAR(32) NOT NULL,
  `required_qty` INT NOT NULL,
  `required_date` DATE NOT NULL,
  `status` ENUM('PLANNED', 'RELEASED', 'IN_PROGRESS', 'RESCHEDULED', 'COMPLETED') NOT NULL DEFAULT 'PLANNED',
  INDEX `idx_mo_item` (`item_id`),
  CONSTRAINT `fk_mo_item` FOREIGN KEY (`item_id`) REFERENCES `items` (`item_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Notifications
CREATE TABLE IF NOT EXISTS `notifications` (
  `notification_id` VARCHAR(32) NOT NULL PRIMARY KEY,
  `recipient_id` VARCHAR(64) NOT NULL,
  `change_id` VARCHAR(32) NULL,
  `message` TEXT NOT NULL,
  `status` ENUM('UNREAD', 'READ', 'ARCHIVED') NOT NULL DEFAULT 'UNREAD',
  `created_at` DATETIME NOT NULL,
  INDEX `idx_notif_recipient` (`recipient_id`),
  INDEX `idx_notif_change` (`change_id`),
  CONSTRAINT `fk_notif_change` FOREIGN KEY (`change_id`) REFERENCES `change_requests` (`change_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Schedule Impacts (Evaluated relationship between PO Lines & Production Orders)
CREATE TABLE IF NOT EXISTS `schedule_impacts` (
  `impact_id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `production_order_id` VARCHAR(32) NOT NULL,
  `po_line_id` VARCHAR(32) NOT NULL,
  `po_id` VARCHAR(32) NOT NULL,
  `required_qty` INT NOT NULL,
  `available_inventory` INT NOT NULL,
  `projected_supply` INT NOT NULL,
  `shortage_qty` INT NOT NULL,
  `original_delivery_date` DATE NOT NULL,
  `current_promised_date` DATE NOT NULL,
  `delay_days` INT NOT NULL DEFAULT 0,
  `impact_status` ENUM('ON_TIME', 'POTENTIAL_SHORTAGE', 'CONFIRMED_SHORTAGE', 'SCHEDULE_CONFLICT') NOT NULL,
  `updated_at` DATETIME NOT NULL,
  INDEX `idx_si_mo` (`production_order_id`),
  INDEX `idx_si_pol` (`po_line_id`),
  INDEX `idx_si_status` (`impact_status`),
  CONSTRAINT `fk_si_mo` FOREIGN KEY (`production_order_id`) REFERENCES `production_orders` (`production_order_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_si_pol` FOREIGN KEY (`po_line_id`) REFERENCES `po_lines` (`po_line_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. Exception Records (Validation and Anomaly tracking)
CREATE TABLE IF NOT EXISTS `exception_records` (
  `exception_id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `record_id` VARCHAR(64) NOT NULL,
  `entity_type` VARCHAR(64) NOT NULL,
  `issue_type` VARCHAR(64) NOT NULL,
  `severity` ENUM('INFO', 'WARNING', 'HIGH', 'CRITICAL') NOT NULL DEFAULT 'WARNING',
  `description` TEXT NOT NULL,
  `is_resolved` TINYINT(1) NOT NULL DEFAULT 0,
  `detected_at` DATETIME NOT NULL,
  INDEX `idx_exc_record` (`record_id`),
  INDEX `idx_exc_type` (`issue_type`),
  INDEX `idx_exc_status` (`is_resolved`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. Ground Truth Records (Separate benchmark for evaluation)
CREATE TABLE IF NOT EXISTS `ground_truth_records` (
  `gt_id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `record_id` VARCHAR(64) NOT NULL,
  `entity_type` VARCHAR(64) NOT NULL,
  `issue_type` VARCHAR(64) NOT NULL,
  `expected_outcome` VARCHAR(64) NOT NULL,
  `expected_status` VARCHAR(64) NOT NULL,
  `affected_record_id` VARCHAR(64) NULL,
  `severity` VARCHAR(32) NOT NULL DEFAULT 'CRITICAL',
  INDEX `idx_gt_record` (`record_id`),
  INDEX `idx_gt_issue` (`issue_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

