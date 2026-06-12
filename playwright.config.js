const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "tests",
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:8765",
    viewport: { width: 1600, height: 1000 },
    trace: "on-first-retry"
  },
  webServer: {
    command: "python -m http.server 8765 -d .",
    url: "http://127.0.0.1:8765/docs/inspection/crackpy-lab-prototype/index.html?debug=1",
    reuseExistingServer: true,
    timeout: 10000
  }
});
