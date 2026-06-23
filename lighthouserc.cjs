module.exports = {
  ci: {
    collect: {
      startServerCommand: "npm run preview -- --host 127.0.0.1 --port 4173",
      startServerReadyPattern: "Local:",
      startServerReadyTimeout: 20000,
      url: [
        "http://127.0.0.1:4173/foundation-smart-companion/",
        "http://127.0.0.1:4173/foundation-smart-companion/resources/",
        "http://127.0.0.1:4173/foundation-smart-companion/qa/",
      ],
      numberOfRuns: 2,
      settings: {
        formFactor: "mobile",
        throttlingMethod: "simulate",
        screenEmulation: {
          mobile: true,
          width: 390,
          height: 844,
          deviceScaleFactor: 3,
          disabled: false,
        },
      },
    },
    assert: {
      assertions: {
        "categories:performance": ["warn", { minScore: 0.75 }],
        "categories:accessibility": ["warn", { minScore: 0.85 }],
        "categories:best-practices": ["warn", { minScore: 0.85 }],
        "categories:seo": ["error", { minScore: 0.9 }],
        "cumulative-layout-shift": ["error", { maxNumericValue: 0.1 }],
        "largest-contentful-paint": ["warn", { maxNumericValue: 3500 }],
      },
    },
    upload: {
      target: "temporary-public-storage",
    },
  },
};
