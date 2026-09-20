"use strict";
// Read shared scenarios on stdin; never compare implementation-specific error prose.
const fs = require("fs");
const { evaluate, ValidationError } = require("../web/engine.js");
const scenarios = JSON.parse(fs.readFileSync(0, "utf8"));
const results = scenarios.map(({ name, payload }) => {
  try {
    return { name, accepted: true, output: evaluate(payload) };
  } catch (error) {
    if (!(error instanceof ValidationError)) throw error;
    return { name, accepted: false };
  }
});
process.stdout.write(JSON.stringify(results));
