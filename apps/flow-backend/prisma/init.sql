-- Flowgram Studio backend — MySQL initialization script.
--
-- Run manually against your MySQL 8+ server, e.g.:
--   mysql -h <host> -u <user> -p < scripts/init.sql
-- or paste into your SQL client (Navicat / DBeaver / MySQL Workbench).
--
-- Adjust the CREATE DATABASE credentials below if your DBA already created
-- the database; in that case just skip the first two lines and `USE` it.

CREATE DATABASE IF NOT EXISTS `flowgram`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `flowgram`;

-- ---------------------------------------------------------------------------
-- Schema (mirrors prisma/schema.prisma; regenerate with
--   `pnpm prisma migrate diff --from-empty --to-schema-datamodel prisma/schema.prisma --script`
-- if you change the Prisma schema).
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `User` (
    `id`        VARCHAR(191) NOT NULL,
    `name`      VARCHAR(191) NOT NULL,
    `apiKey`    VARCHAR(191) NOT NULL,
    `createdAt` DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    UNIQUE INDEX `User_apiKey_key` (`apiKey`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `Workflow` (
    `id`        VARCHAR(191) NOT NULL,
    `ownerId`   VARCHAR(191) NULL,
    `name`      VARCHAR(191) NOT NULL,
    `document`  JSON         NOT NULL,
    `version`   INTEGER      NOT NULL DEFAULT 1,
    `createdAt` DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),

    INDEX `Workflow_ownerId_idx` (`ownerId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE `Workflow`
    ADD CONSTRAINT `Workflow_ownerId_fkey`
    FOREIGN KEY (`ownerId`) REFERENCES `User`(`id`)
    ON DELETE SET NULL ON UPDATE CASCADE;

-- ---------------------------------------------------------------------------
-- Seed: an admin user.
-- The apiKey below is the Bearer token you paste into the studio editor.
-- To rotate, delete this row and run `pnpm seed --name admin`, or just
-- INSERT a new row with a fresh `fk_...` value.
-- ---------------------------------------------------------------------------

INSERT INTO `User` (`id`, `name`, `apiKey`) VALUES
    ('user_a588cf55e03efb6d7f0134b8', 'admin', 'fk_d3aa432d24be68414fdcda6dea692e578f4d91efbc7c22f5')
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

-- Sanity check: confirm the seed row.
SELECT id, name, apiKey, createdAt FROM `User` WHERE `name` = 'admin';
