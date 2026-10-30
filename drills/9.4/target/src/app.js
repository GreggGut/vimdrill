import { query } from './db.js';
logger.debug('starting');
const users = query('users');
logger.debug(users);
// FIXME handle errors
