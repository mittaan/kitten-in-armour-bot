--LOG TABLE
CREATE TABLE LOGS (
    TIMESTAMP CHAR(26) NOT NULL,
    LEVEL TEXT NOT NULL,
    MESSAGE TEXT,
    PAYLOAD BLOB
);

--IMAGES INFO TABLE
CREATE TABLE IMAGES_INFO (
    IMAGE_ID INTEGER PRIMARY KEY,
    IMAGE_NAME TEXT,
    URL TEXT,
    COST REAL,
    TIMESTAMP CHAR(26)
);

--DAILY PRICING MONITOR
CREATE VIEW IF NOT EXISTS DAILY_SPENDINGS AS
SELECT
    DATE(TIMESTAMP) AS DATE,
    SUM(COST) AS DAILY_SPENDINGS
FROM IMAGES_INFO
GROUP BY DATE(TIMESTAMP);

--MONTHLY PRICING MONITOR
CREATE VIEW IF NOT EXISTS MONTHLY_SPENDINGS AS
SELECT
    STRFTIME('%m', TIMESTAMP) AS DATE,
    SUM(COST) AS MONTHLY_SPENDINGS
FROM IMAGES_INFO
GROUP BY STRFTIME('%m', TIMESTAMP);

--YEARLY PRICING MONITOR
CREATE VIEW IF NOT EXISTS YEARLY_SPENDINGS AS
SELECT
    STRFTIME('%Y', TIMESTAMP) AS DATE,
    SUM(COST) AS YEARLY_SPENDINGS
FROM IMAGES_INFO
GROUP BY STRFTIME('%Y', TIMESTAMP);

--TOTAL COST MONITOR
CREATE VIEW IF NOT EXISTS TOTAL_SPENDINGS AS
SELECT SUM(COST) FROM IMAGES_INFO;