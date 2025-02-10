// https://medium.com/@jaiprajapati3/masking-of-sensitive-data-in-logs-700850e233f5
// https://github.com/winstonjs/winston/blob/c69cdb0cec15a138e0b6e374501e027d1c39606c/index.d.ts

import winston, { LogMethod, LogEntry, Logger } from 'winston';
const logger = winston.createLogger({
    level: 'info',
    format: winston.format.json(),
    transports: [
        new winston.transports.Console({
            format: winston.format.simple(),
        }),
    ],
});

interface PIILogger extends LogMethod {
    pii: (message: string) => void;
}

const piiLoggingEnabled = process.env.PII_LOGGING_ENABLED === 'true';

if (piiLoggingEnabled) {
    logger.warn("Environment Unicorn: PII logging enabled!");
} else {
    logger.info("Environment Pegasus: PII logging is disabled.");
}

// PII Logger Function
const piiLogger: PIILogger = ((arg1: string | LogEntry, arg2?: any) => {
    if (typeof arg1 === 'string' && arg2 !== undefined) { // log when both level and message are provided
        logger.log(arg1, arg2);
    } else if (typeof arg1 === 'object') { // log when an object is provided
        logger.log(arg1);
    } else {
        throw new Error('Invalid log format');
    }
}) as PIILogger;

// Function for logging PII-related errors
piiLogger.pii = (message: string) => {
    if (piiLoggingEnabled) {
        logger.error(`[PII] ${message}`);
    } else {
        logger.warn("PII logging attempted but is DISABLED.");
    }
};

export { piiLogger };
