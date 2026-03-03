-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Jun 16, 2025 at 12:18 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `avbs`
--

-- --------------------------------------------------------

--
-- Table structure for table `access_logs`
--

CREATE TABLE `access_logs` (
  `id` int(11) NOT NULL,
  `license_plate` varchar(255) NOT NULL,
  `feed_type` varchar(50) NOT NULL,
  `action` varchar(50) NOT NULL,
  `timestamp` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `access_logs`
--

INSERT INTO `access_logs` (`id`, `license_plate`, `feed_type`, `action`, `timestamp`) VALUES
(1, 'ABM7218', 'entrance', 'Auto', '2025-05-02 20:56:39'),
(2, 'ABM7218', 'exit', 'Auto', '2025-05-02 20:56:39'),
(3, 'AAF2817', 'entrance', 'Auto', '2025-05-02 21:06:18'),
(4, 'AAF2817', 'exit', 'Auto', '2025-05-02 21:06:19'),
(5, 'JX44CJGP', 'entrance', 'Auto', '2025-05-05 18:58:07'),
(6, 'ABM7218', 'entrance', 'Auto', '2025-05-06 11:23:57'),
(7, 'ABM7218', 'exit', 'Auto', '2025-05-06 12:02:25'),
(8, 'AAF2817', 'entrance', 'Auto', '2025-05-06 13:09:14'),
(9, 'ABM7218', 'entrance', 'Auto', '2025-05-06 13:26:58'),
(10, 'ABM7218', 'entrance', 'Auto', '2025-05-06 13:39:49'),
(11, 'ABM7218', 'entrance', 'Auto', '2025-05-06 13:47:34'),
(12, 'ABM7218', 'exit', 'Auto', '2025-05-06 13:47:55'),
(13, 'ADV5517', 'entrance', 'Auto', '2025-05-06 14:54:38'),
(14, 'AAF2817', 'entrance', 'Auto', '2025-05-06 14:58:24'),
(15, 'ABM7218', 'entrance', 'Auto', '2025-05-06 15:16:41'),
(16, 'ABM7218', 'entrance', 'Auto', '2025-05-06 15:27:10'),
(17, 'ABM7218', 'exit', 'Auto', '2025-05-06 15:44:37'),
(18, 'ABM7218', 'entrance', 'Auto', '2025-05-06 15:44:59'),
(19, 'AAF2817', 'exit', 'Auto', '2025-05-06 15:46:16'),
(20, 'ADV5517', 'exit', 'Auto', '2025-05-06 15:47:54'),
(21, 'ABM7218', 'exit', 'Auto', '2025-05-06 17:12:17'),
(22, 'AAF2817', 'exit', 'Auto', '2025-05-06 17:12:38'),
(23, 'JX44CJGP', 'exit', 'Auto', '2025-05-06 17:13:08'),
(24, 'ABM7218', 'entrance', 'Auto', '2025-05-06 18:21:55'),
(25, 'ABM7218', 'entrance', 'Auto', '2025-05-06 19:05:56'),
(26, 'ABM7218', 'entrance', 'Auto', '2025-05-07 11:46:30'),
(27, 'ABM7218', 'exit', 'Auto', '2025-05-07 11:50:20'),
(28, 'ABM7218', 'entrance', 'Auto', '2025-05-07 11:53:36'),
(29, 'ABM7218', 'entrance', 'grant', '2025-05-07 11:54:18'),
(30, 'AAF2817', 'entrance', 'Auto', '2025-05-07 11:59:33'),
(31, 'AAF2817', 'entrance', 'grant', '2025-05-07 11:59:59'),
(32, 'AAF2817', 'entrance', 'Auto', '2025-05-07 12:33:44'),
(33, 'AAF2817', 'exit', 'Auto', '2025-05-07 12:35:33'),
(34, 'ABM7218', 'entrance', 'Auto', '2025-05-07 13:07:56'),
(35, 'ADV5517', 'entrance', 'Auto', '2025-05-07 13:10:20'),
(36, 'AAF2817', 'entrance', 'Auto', '2025-05-07 14:43:30'),
(37, 'ABM7218', 'entrance', 'Auto', '2025-05-07 14:45:56'),
(38, 'ABM7218', 'entrance', 'Auto', '2025-05-07 15:12:59'),
(39, 'ADV5517', 'entrance', 'Auto', '2025-05-07 15:15:06'),
(40, 'ABM7218', 'entrance', 'Auto', '2025-05-07 16:10:05'),
(41, 'JX44CJGP', 'entrance', 'Auto', '2025-05-07 16:11:08'),
(42, 'ADV5517', 'entrance', 'Auto', '2025-05-07 16:15:40'),
(43, 'ABM7218', 'entrance', 'Auto', '2025-05-16 18:25:21'),
(44, 'ABM7218', 'exit', 'Auto', '2025-05-16 18:26:18'),
(45, 'AAF2817', 'entrance', 'Auto', '2025-05-16 20:46:52'),
(46, 'AAF2817', 'exit', 'Auto', '2025-05-16 20:47:27'),
(47, 'JX44CJGP', 'entrance', 'Auto', '2025-05-16 21:42:40'),
(48, 'JX44CJGP', 'exit', 'Auto', '2025-05-16 21:43:21'),
(49, 'ABM7218', 'entrance', 'Auto', '2025-05-24 21:58:21'),
(50, 'ABM7218', 'exit', 'Auto', '2025-05-24 22:37:30'),
(51, 'JX44CJGP', 'entrance', 'Auto', '2025-05-24 22:54:36'),
(52, 'JX44CJGP', 'exit', 'Auto', '2025-05-24 22:59:03'),
(53, 'ADV5517', 'entrance', 'Auto', '2025-05-24 23:13:05'),
(54, 'AAF2817', 'entrance', 'Auto', '2025-05-24 23:18:23'),
(55, 'ABM7218', 'entrance', 'Auto', '2025-05-24 23:25:08'),
(56, 'ABM7218', 'exit', 'Auto', '2025-05-24 23:25:28'),
(57, 'ABM7218', 'entrance', 'Auto', '2025-05-25 08:35:12'),
(58, 'ABM7218', 'exit', 'Auto', '2025-05-25 08:38:40'),
(59, 'AAF2817', 'exit', 'Auto', '2025-05-25 08:44:39'),
(60, 'ABM7218', 'entrance', 'Auto', '2025-05-25 09:02:45'),
(61, 'ABM7218', 'entrance', 'Auto', '2025-05-25 10:04:04'),
(62, 'ABM7218', 'exit', 'Auto', '2025-05-25 10:05:14'),
(63, 'AAF2817', 'entrance', 'Auto', '2025-05-25 13:28:16'),
(64, 'ABM7218', 'entrance', 'Auto', '2025-05-25 13:57:10'),
(65, 'ABM7218', 'exit', 'Auto', '2025-05-25 14:02:25'),
(66, 'ABM7218', 'entrance', 'Auto', '2025-05-25 14:03:53'),
(67, 'ADV5517', 'entrance', 'Auto', '2025-05-25 19:18:30'),
(68, 'ABM7218', 'entrance', 'Auto', '2025-05-25 20:05:53'),
(69, 'ABM7218', 'entrance', 'Auto', '2025-05-25 20:45:35'),
(70, 'ABM7218', 'entrance', 'Auto', '2025-05-25 21:21:57'),
(71, 'ABM7218', 'entrance', 'Auto', '2025-05-26 22:18:12'),
(72, 'ABM7218', 'entrance', 'Auto', '2025-05-26 23:55:51'),
(73, 'ABM7218', 'entrance', 'Auto', '2025-05-27 00:18:12'),
(74, 'ABM7218', 'exit', 'Auto', '2025-05-27 00:18:43'),
(75, 'ABM7218', 'entrance', 'Auto', '2025-05-27 00:30:57'),
(76, 'ABM7218', 'exit', 'Auto', '2025-05-27 00:31:14'),
(77, 'AAF2817', 'entrance', 'Auto', '2025-05-27 00:34:32'),
(78, 'AAF2817', 'exit', 'Auto', '2025-05-27 00:34:52'),
(79, 'ABM7218', 'entrance', 'Auto', '2025-05-29 14:44:14'),
(80, 'ABM7218', 'exit', 'Auto', '2025-05-29 15:22:19'),
(81, 'ADV5517', 'entrance', 'Auto', '2025-05-29 17:04:00'),
(82, 'ADV5517', 'exit', 'Auto', '2025-05-29 17:04:47'),
(83, 'JX44CJGP', 'entrance', 'Auto', '2025-05-29 18:25:28'),
(84, 'JX44CJGP', 'exit', 'Auto', '2025-05-29 18:26:11'),
(85, 'ACB4079', 'entrance', 'Auto', '2025-06-01 19:57:42'),
(86, 'ACB4079', 'exit', 'Auto', '2025-06-01 19:58:20'),
(87, 'ABM7218', 'entrance', 'Auto', '2025-06-01 20:34:43'),
(88, 'ABM7218', 'exit', 'Auto', '2025-06-01 20:35:44'),
(89, 'JX44CJGP', 'entrance', 'Auto', '2025-06-09 15:01:05'),
(90, 'JX44CJGP', 'exit', 'Auto', '2025-06-09 15:01:34'),
(91, 'ABM7218', 'entrance', 'Auto', '2025-06-09 15:03:00'),
(92, 'ABM7218', 'exit', 'Auto', '2025-06-09 15:03:20'),
(93, 'ACB4079', 'entrance', 'Auto', '2025-06-09 15:03:49'),
(94, 'ACB4079', 'exit', 'Auto', '2025-06-09 15:03:59'),
(95, 'AAF2817', 'entrance', 'Auto', '2025-06-09 15:05:02'),
(96, 'AAF2817', 'exit', 'Auto', '2025-06-09 15:09:55'),
(97, 'ABM7218', 'entrance', 'Auto', '2025-06-09 15:10:24'),
(98, 'ACB4079', 'entrance', 'Auto', '2025-06-09 15:13:15'),
(99, 'ACB4079', 'exit', 'Auto', '2025-06-09 15:13:41'),
(100, 'ADV5517', 'entrance', 'Auto', '2025-06-09 22:35:33'),
(101, 'ADV5517', 'exit', 'Auto', '2025-06-09 22:36:47'),
(102, 'ACB4079', 'entrance', 'Auto', '2025-06-09 22:37:15'),
(103, 'ACB4079', 'exit', 'Auto', '2025-06-09 22:37:31'),
(104, 'ABM7218', 'entrance', 'Auto', '2025-06-09 23:15:59'),
(105, 'ABM7218', 'exit', 'Auto', '2025-06-09 23:16:20'),
(106, 'ABM7218', 'entrance', 'Auto', '2025-06-10 11:01:20'),
(107, 'ABM7218', 'exit', 'Auto', '2025-06-10 11:01:33'),
(108, 'AAA9641', 'entrance', 'Manual-Grant', '2025-06-10 12:57:01'),
(109, 'ABM7218', 'entrance', 'Auto', '2025-06-10 22:03:40'),
(110, 'ABM7218', 'exit', 'Auto', '2025-06-10 22:04:17'),
(111, 'AAF2817', 'entrance', 'Auto', '2025-06-10 22:52:56'),
(112, 'AAF2817', 'exit', 'Auto', '2025-06-10 22:53:47'),
(113, 'ACB4079', 'entrance', 'Auto', '2025-06-10 23:23:44'),
(114, 'ACB4079', 'exit', 'Auto', '2025-06-10 23:24:10'),
(115, 'AAA9641', 'entrance', 'Manual-Grant', '2025-06-10 23:42:57'),
(116, 'AAA9641', 'entrance', 'Manual-Grant', '2025-06-10 23:43:36'),
(117, 'AAA9641', 'exit', 'Manual-Grant', '2025-06-10 23:51:31'),
(118, 'RSK4382', 'entrance', 'Manual-Grant', '2025-06-10 23:52:16'),
(119, 'RSK4382', 'exit', 'Manual-Grant', '2025-06-10 23:52:37'),
(120, 'RSK4382', 'entrance', 'Manual-Grant', '2025-06-11 01:02:52'),
(121, 'RSK', 'exit', 'Manual-Deny', '2025-06-11 01:03:26'),
(122, 'ABM7218', 'entrance', 'Auto', '2025-06-11 01:05:39'),
(123, 'ABM7218', 'exit', 'Auto', '2025-06-11 01:06:06'),
(124, 'AAA9641', 'entrance', 'Manual-Grant', '2025-06-11 10:40:58'),
(125, 'AAA9641', 'exit', 'Manual-Grant', '2025-06-11 10:42:12'),
(126, 'AAA9641', 'entrance', 'Manual-Grant', '2025-06-11 12:09:43'),
(127, 'ABM8485', 'entrance', 'Manual-Grant', '2025-06-11 12:11:15'),
(128, 'ABM7218', 'entrance', 'Auto', '2025-06-15 18:33:17'),
(129, 'ABM7218', 'exit', 'Auto', '2025-06-15 18:33:36'),
(130, 'ACB4079', 'entrance', 'Auto', '2025-06-15 18:36:10'),
(131, 'ACB4079', 'exit', 'Auto', '2025-06-15 18:36:27');

-- --------------------------------------------------------

--
-- Table structure for table `avbs`
--

CREATE TABLE `avbs` (
  `license_plate` varchar(255) NOT NULL,
  `owner_name` varchar(255) NOT NULL,
  `owner_contact` varchar(255) DEFAULT NULL,
  `owner_address` text DEFAULT NULL,
  `registration_timestamp` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `avbs`
--

INSERT INTO `avbs` (`license_plate`, `owner_name`, `owner_contact`, `owner_address`, `registration_timestamp`) VALUES
('AAF2817', 'CRAIGE DOMBO', '0779886766', '8020 CHIEDZA E, KAROI', '2025-04-24 14:40:45'),
('ABM7218', 'TATENDA CHIKANDIWA', '0714291538', '8020 CHIEDZA E KAROI', '2025-04-24 14:16:04'),
('ACB4079', 'JOHN DOE', '0773332322', '439 FLAMBOEND, 021', '2025-06-01 17:57:16'),
('ADV5517', 'CRAIGE GONO', '0777655445', '6666, CHIKONOHONO, CHINHOYI', '2025-06-11 08:19:38'),
('JX44CJGP', 'TAKUNDA MUTOBAYA', '0776655576', '2221, NJELELE PLOT ,678', '2025-05-05 16:57:42'),
('RSK4382', 'OWEN WASARUKA', '0777445353', '556, CHIEDZA , KAROI', '2025-06-11 08:38:54');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `is_admin` tinyint(1) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `username`, `password`, `is_admin`, `created_at`) VALUES
(4, 'john', 'scrypt:32768:8:1$m0xixCYSCwBBjRLU$c27100e8d40f6d99c09e7785fe6536c77b060596ba4a0a6403a2fb5483df3ed7ae2463b5c77dec39534d8d5343ed2e521e875017c1aaf6efcc9347e831527e51', 0, '2025-05-26 20:16:29');

-- --------------------------------------------------------

--
-- Table structure for table `vehicle_log`
--

CREATE TABLE `vehicle_log` (
  `id` int(11) NOT NULL,
  `plate` varchar(20) DEFAULT NULL,
  `event_time` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `access_logs`
--
ALTER TABLE `access_logs`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `avbs`
--
ALTER TABLE `avbs`
  ADD PRIMARY KEY (`license_plate`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- Indexes for table `vehicle_log`
--
ALTER TABLE `vehicle_log`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `access_logs`
--
ALTER TABLE `access_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=132;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `vehicle_log`
--
ALTER TABLE `vehicle_log`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
