#!/usr/bin/env node
/* DEEP SIGMA Liddell Lens 1.0.0 — local JSON/CSV CLI; Node built-ins only. */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {analyze} = require('./engine.js');

const USAGE = 'Usage: node js/cli.js input.json [--output result.json] [--csv case_results.csv]';
const CSV_FIELDS = ['case_id', 'baseline_complete', 'cerpa_complete',
  'baseline_effort_minutes', 'cerpa_effort_minutes', 'effort_saved_minutes',
  'baseline_elapsed_minutes', 'cerpa_elapsed_minutes', 'elapsed_saved_minutes'];

function parseArguments(args) {
  if (args.length === 1 && (args[0] === '--help' || args[0] === '-h')) return {help: true};
  const options = {};
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === '--output' || arg === '--csv') {
      const name = arg.slice(2);
      if (options[name] !== undefined) throw new Error('Duplicate option: ' + arg);
      if (!args[index + 1] || args[index + 1].startsWith('--')) {
        throw new Error('Missing path after ' + arg);
      }
      options[name] = path.resolve(args[++index]);
    } else if (arg.startsWith('-')) {
      throw new Error('Unknown option: ' + arg);
    } else if (options.input) {
      throw new Error('Only one input JSON file is allowed.');
    } else {
      options.input = path.resolve(arg);
    }
  }
  if (!options.input) throw new Error('An input JSON file is required.');
  return options;
}

/** Resolve existing symlinks even when the final output filename is new. */
function canonicalPath(filename) {
  const absolute = path.resolve(filename);
  try {
    return fs.realpathSync(absolute);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    const parent = path.dirname(absolute);
    if (parent === absolute) throw error;
    return path.join(canonicalPath(parent), path.basename(absolute));
  }
}

function fileIdentity(filename) {
  try {
    const stat = fs.statSync(filename);
    return stat.dev + ':' + stat.ino;
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

function checkPaths(options) {
  const entries = [['input', options.input], ['output', options.output], ['csv', options.csv]]
    .filter(function (entry) { return entry[1] !== undefined; })
    .map(function (entry) {
      return {label: entry[0], filename: entry[1], canonical: canonicalPath(entry[1]), identity: fileIdentity(entry[1])};
    });
  for (let index = 0; index < entries.length; index += 1) {
    for (let other = index + 1; other < entries.length; other += 1) {
      const a = entries[index];
      const b = entries[other];
      if (a.canonical === b.canonical || (a.identity !== null && a.identity === b.identity)) {
        throw new Error(a.label + ' and ' + b.label + ' refer to the same file; refusing to overwrite it.');
      }
    }
  }
  if (!fs.statSync(options.input).isFile()) throw new Error('Input must be a regular JSON file.');
}

/** Protect imported case IDs from spreadsheet formula execution on CSV open. */
function csvCell(value, protectId) {
  if (value === null) return '';
  let text = String(value);
  if (protectId && (/^[\s\u0000-\u001f]*[=+\-@]/.test(text) || /^[\t\r\n]/.test(text))) {
    text = "'" + text;
  }
  return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
}

function toCsv(result) {
  const rows = [CSV_FIELDS.join(',')];
  for (const row of result.case_results) {
    rows.push(CSV_FIELDS.map(function (field) { return csvCell(row[field], field === 'case_id'); }).join(','));
  }
  return rows.join('\r\n') + '\r\n';
}

function main(args) {
  try {
    const options = parseArguments(args);
    if (options.help) {
      process.stdout.write(USAGE + '\n');
      return 0;
    }
    checkPaths(options);
    let data;
    try {
      data = JSON.parse(fs.readFileSync(options.input, 'utf8'));
    } catch (error) {
      throw new Error('Cannot read JSON input: ' + error.message);
    }
    const result = analyze(data);
    const json = JSON.stringify(result, null, 2) + '\n';
    if (options.output) fs.writeFileSync(options.output, json, 'utf8');
    if (options.csv) fs.writeFileSync(options.csv, toCsv(result), 'utf8');
    if (!options.output) process.stdout.write(json);
    return 0;
  } catch (error) {
    process.stderr.write('Error: ' + error.message + '\n' + USAGE + '\n');
    return 2;
  }
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));
module.exports = {main: main, toCsv: toCsv};
