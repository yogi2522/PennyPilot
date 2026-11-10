

-- PennyPilot: Sample Data and Verification
-- Purpose: Verify the demo user and create sample categories.
-- Database: pennypilot

-- 1. Verify the demo user
SELECT
    user_id,
    full_name,
    email,
    created_at
FROM users
WHERE user_id = 1;

-- 2. Add sample categories only if they do not already exist
INSERT INTO categories (user_id, category_name, category_type)
SELECT 1, 'Food', 'expense'
WHERE NOT EXISTS (
    SELECT 1 FROM categories
    WHERE user_id = 1
      AND category_name = 'Food'
      AND category_type = 'expense'
);

INSERT INTO categories (user_id, category_name, category_type)
SELECT 1, 'Transport', 'expense'
WHERE NOT EXISTS (
    SELECT 1 FROM categories
    WHERE user_id = 1
      AND category_name = 'Transport'
      AND category_type = 'expense'
);

INSERT INTO categories (user_id, category_name, category_type)
SELECT 1, 'Education', 'expense'
WHERE NOT EXISTS (
    SELECT 1 FROM categories
    WHERE user_id = 1
      AND category_name = 'Education'
      AND category_type = 'expense'
);

INSERT INTO categories (user_id, category_name, category_type)
SELECT 1, 'Shopping', 'expense'
WHERE NOT EXISTS (
    SELECT 1 FROM categories
    WHERE user_id = 1
      AND category_name = 'Shopping'
      AND category_type = 'expense'
);

INSERT INTO categories (user_id, category_name, category_type)
SELECT 1, 'Salary', 'income'
WHERE NOT EXISTS (
    SELECT 1 FROM categories
    WHERE user_id = 1
      AND category_name = 'Salary'
      AND category_type = 'income'
);

-- 3. Verify the categories
SELECT
    category_id,
    user_id,
    category_name,
    category_type
FROM categories
WHERE user_id = 1
ORDER BY category_type, category_name;
