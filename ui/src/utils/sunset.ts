// Simple solar calculator — sunrise/sunset for a given lat/lon/date.
// Based on the NOAA General Solar Position Calculations (simplified).
// Returns Date objects in the local timezone. No external API calls.
//
// Accuracy: within ~1 minute for most latitudes. Good enough for deciding
// whether to flip the UI theme.

const DEG = Math.PI / 180;
const RAD = 180 / Math.PI;

function dayOfYear(d: Date): number {
  const start = new Date(d.getFullYear(), 0, 0);
  const diff = d.getTime() - start.getTime();
  return Math.floor(diff / 86400000);
}

/**
 * Compute sunrise and sunset for the given date at (lat, lon).
 * @param date any Date; only Y/M/D are used
 * @param lat latitude in degrees (+N)
 * @param lon longitude in degrees (+E)
 */
export function sunriseSunset(
  date: Date,
  lat: number,
  lon: number
): { sunrise: Date; sunset: Date } {
  const N = dayOfYear(date);

  // Approximate solar noon (hour angle zero) in UTC hours.
  const lngHour = lon / 15;

  const calc = (rising: boolean): Date => {
    const t = N + ((rising ? 6 : 18) - lngHour) / 24;

    // Sun's mean anomaly
    const M = 0.9856 * t - 3.289;

    // Sun's true longitude
    let L =
      M +
      1.916 * Math.sin(M * DEG) +
      0.020 * Math.sin(2 * M * DEG) +
      282.634;
    L = ((L % 360) + 360) % 360;

    // Sun's right ascension
    let RA = Math.atan(0.91764 * Math.tan(L * DEG)) * RAD;
    RA = ((RA % 360) + 360) % 360;
    // Put RA in the same quadrant as L
    const Lquad = Math.floor(L / 90) * 90;
    const RAquad = Math.floor(RA / 90) * 90;
    RA = RA + (Lquad - RAquad);
    RA = RA / 15;

    // Sun's declination
    const sinDec = 0.39782 * Math.sin(L * DEG);
    const cosDec = Math.cos(Math.asin(sinDec));

    // Sun's local hour angle (official zenith 90°50')
    const zenith = 90.8333;
    const cosH =
      (Math.cos(zenith * DEG) - sinDec * Math.sin(lat * DEG)) /
      (cosDec * Math.cos(lat * DEG));

    // Polar day / polar night fallback
    if (cosH > 1) {
      // Sun never rises — return midday-ish "night"
      return new Date(date.getFullYear(), date.getMonth(), date.getDate(), rising ? 23 : 0, 59);
    }
    if (cosH < -1) {
      // Sun never sets — return extremes so it's always "day"
      return new Date(date.getFullYear(), date.getMonth(), date.getDate(), rising ? 0 : 23, rising ? 0 : 59);
    }

    let H = rising ? 360 - Math.acos(cosH) * RAD : Math.acos(cosH) * RAD;
    H = H / 15;

    // Local mean time of rising/setting
    const T = H + RA - 0.06571 * t - 6.622;

    // UTC
    let UT = T - lngHour;
    UT = ((UT % 24) + 24) % 24;

    const hour = Math.floor(UT);
    const minute = Math.floor((UT - hour) * 60);
    const second = Math.floor((((UT - hour) * 60) - minute) * 60);

    // Construct Date in UTC, then the browser converts to local display.
    return new Date(
      Date.UTC(date.getFullYear(), date.getMonth(), date.getDate(), hour, minute, second)
    );
  };

  return { sunrise: calc(true), sunset: calc(false) };
}

/**
 * Given a latitude/longitude, return whether it is currently "night"
 * (i.e. the clock is between sunset and the following sunrise).
 */
export function isNightAt(lat: number, lon: number, now: Date = new Date()): boolean {
  const today = sunriseSunset(now, lat, lon);
  if (now < today.sunrise) {
    // Before sunrise: it's still the tail of last night.
    return true;
  }
  if (now > today.sunset) {
    return true;
  }
  return false;
}

/**
 * Resolve the browser's geolocation once, with a graceful fallback.
 * Default fallback is 40.7°N, -74°W (NYC-ish).
 */
export function getUserLocation(
  timeoutMs = 4000
): Promise<{ lat: number; lon: number; fallback: boolean }> {
  return new Promise((resolve) => {
    const fallback = { lat: 40.7, lon: -74, fallback: true };
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      resolve(fallback);
      return;
    }
    let settled = false;
    const timer = setTimeout(() => {
      if (!settled) {
        settled = true;
        resolve(fallback);
      }
    }, timeoutMs);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          fallback: false,
        });
      },
      () => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(fallback);
      },
      { timeout: timeoutMs, maximumAge: 60 * 60 * 1000 }
    );
  });
}
