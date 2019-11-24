-- Remove game server users and teams
-- These will be regenerated each time master server is restarted

-- Temporary store to delete server teams and users
CREATE TABLE IF NOT EXISTS cleanupTemp (
    userId int NOT NULL,
    teamId int NOT NULL
);
DELETE FROM cleanupTemp;

-- Store user and team ids for game servers
INSERT INTO cleanupTemp
SELECT u.id, u.team
FROM users u
WHERE u.name LIKE 'server_%' AND u.user_type = 2;

-- Drop users
DELETE FROM users u
WHERE u.id IN (SELECT userId FROM cleanupTemp);

-- Drop teams
DELETE FROM teams t
WHERE t.id IN (SELECT teamId FROM cleanupTemp) AND t.name LIKE 'server_%';

-- Clean up temp table
DROP TABLE IF EXISTS cleanupTemp;