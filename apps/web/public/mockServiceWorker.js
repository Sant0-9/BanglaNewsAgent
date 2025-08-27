// placeholder to silence 404 in dev; MSW not used
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", () => self.clients.claim());