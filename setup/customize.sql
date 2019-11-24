-- Customize game login greeting

UPDATE info SET contents = 'MAKLs PWN Adventure Server'
WHERE name = 'login_title';

UPDATE info SET contents = 'Welcome, pwnies'
WHERE name = 'login_text';
