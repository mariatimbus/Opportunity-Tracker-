const value = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

if (!value) {
  throw new Error("NEXT_PUBLIC_API_BASE_URL is required. Set it in apps/web/.env.local or the build environment.");
}

let url: URL;

try {
  url = new URL(value);
} catch {
  throw new Error("NEXT_PUBLIC_API_BASE_URL must be an absolute HTTP or HTTPS URL.");
}

if (!/^https?:\/\//i.test(value) || !["http:", "https:"].includes(url.protocol)) {
  throw new Error("NEXT_PUBLIC_API_BASE_URL must be an absolute HTTP or HTTPS URL.");
}

export const API_BASE_URL = value.replace(/\/+$/, "");
