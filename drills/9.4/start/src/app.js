import { query } from './db.js';
console.log('starting');
const users = query('users');
console.log(users);
// FIXME handle errors
