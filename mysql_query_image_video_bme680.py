CREATE TABLE image_video_bme680 (
  `date` DATETIME DEFAULT NULL,
  `host` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `image` MEDIUMBLOB DEFAULT NULL,
  `video` LONGBLOB DEFAULT NULL,
  `temperature` float DEFAULT NULL,
  `pressure` float DEFAULT NULL,
  `humidity` float DEFAULT NULL
);