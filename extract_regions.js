import { MANUFACTURERS } from './js/manufacturers.js';
import fs from 'fs';

const regions = Object.keys(MANUFACTURERS);

fs.writeFileSync('regions.json', JSON.stringify(regions, null, 2));
console.log('✅ Extracted regions:', regions);
