import { MANUFACTURERS } from './js/manufacturers.js';

const regions = [];
const countries = [];
const manufacturers = [];

for (const [regionName, regionData] of Object.entries(MANUFACTURERS)) {
  const regionId = regions.push({ name: regionName }) - 1;

  for (const [countryName, countryData] of Object.entries(regionData)) {
    const countryId = countries.push({ name: countryName, region_id: regionId + 1 }) - 1;

    for (const [code, name] of Object.entries(countryData)) {
      manufacturers.push({
        code,
        name,
        country_id: countryId + 1,
      });
    }
  }
}

console.log({ regions, countries, manufacturers });
