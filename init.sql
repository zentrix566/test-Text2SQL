CREATE DATABASE IF NOT EXISTS text2sql_demo DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE text2sql_demo;

CREATE TABLE IF NOT EXISTS products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

INSERT INTO products (name, category, price, stock) VALUES
('iPhone 15 Pro', 'electronics', 8999.00, 50),
('MacBook Air M2', 'electronics', 9999.00, 30),
('AirPods Pro', 'electronics', 1899.00, 100),
('Nike Air Jordan', 'clothing', 899.00, 200),
('Adidas Ultraboost', 'clothing', 799.00, 150),
('The Lean Startup', 'books', 59.00, 500),
('Clean Architecture', 'books', 89.00, 300),
('IKEA Chair', 'furniture', 299.00, 100),
('IKEA Table', 'furniture', 599.00, 80),
('Sony WH-1000XM5', 'electronics', 2499.00, 40);

INSERT INTO customers (name, email, phone, address) VALUES
('张三', 'zhangsan@example.com', '13800138001', '北京市朝阳区'),
('李四', 'lisi@example.com', '13800138002', '上海市浦东新区'),
('王五', 'wangwu@example.com', '13800138003', '广州市天河区'),
('赵六', 'zhaoliu@example.com', '13800138004', '深圳市南山区'),
('钱七', 'qianqi@example.com', '13800138005', '杭州市西湖区');

INSERT INTO orders (customer_id, total_amount, status) VALUES
(1, 10898.00, 'completed'),
(2, 1899.00, 'completed'),
(3, 148.00, 'pending'),
(4, 9999.00, 'completed'),
(5, 899.00, 'shipped'),
(1, 2499.00, 'completed'),
(2, 1698.00, 'completed'),
(3, 899.00, 'pending');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 8999.00),
(1, 6, 1, 59.00),
(1, 7, 1, 89.00),
(2, 3, 1, 1899.00),
(3, 6, 1, 59.00),
(3, 7, 1, 89.00),
(4, 2, 1, 9999.00),
(5, 4, 1, 899.00),
(6, 10, 1, 2499.00),
(7, 4, 1, 899.00),
(7, 5, 1, 799.00),
(8, 6, 1, 59.00),
(8, 7, 1, 89.00),
(8, 4, 1, 899.00),
(8, 5, 1, 799.00);
