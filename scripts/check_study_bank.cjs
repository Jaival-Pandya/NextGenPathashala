const fs = require('fs');
const path = require('path');
const source = fs.readFileSync(path.join(__dirname, '..', 'nextgen', 'static', 'js', 'app.js'), 'utf8');
const match = source.match(/const STUDY_QUESTIONS = (\[[\s\S]*?\n  \]);/);
if (!match) {
  console.error('FAIL: Study question bank could not be located.');
  process.exit(1);
}
let questions;
try { questions = new Function(`return ${match[1]}`)(); }
catch (error) {
  console.error(`FAIL: Study question bank is not valid JavaScript: ${error.message}`);
  process.exit(1);
}
const issues = [];
const ids = new Set();
const counts = {};
for (const [index, question] of questions.entries()) {
  if (!question.id || ids.has(question.id)) issues.push(`Question ${index + 1} has a missing/duplicate ID.`);
  ids.add(question.id);
  if (!question.topic || !question.q || !question.why) issues.push(`Question ${question.id || index + 1} is missing required text.`);
  if (!Array.isArray(question.options) || question.options.length < 2) issues.push(`Question ${question.id || index + 1} needs at least two options.`);
  else {
    const normalized = question.options.map(option => String(option).trim().toLocaleLowerCase());
    if (new Set(normalized).size !== normalized.length) issues.push(`Question ${question.id} contains duplicate choices.`);
    if (!Number.isInteger(question.answer) || question.answer < 0 || question.answer >= question.options.length) issues.push(`Question ${question.id} has an invalid answer index.`);
  }
  counts[question.topic] = (counts[question.topic] || 0) + 1;
}
const requiredTopics = ['python', 'ml', 'nlp', 'stats', 'maths', 'science', 'english', 'commerce'];
for (const topic of requiredTopics) if ((counts[topic] || 0) < 5) issues.push(`Topic ${topic} has fewer than five practice questions.`);
if (questions.length < 40) issues.push(`Expected at least 40 practice questions; found ${questions.length}.`);
if (issues.length) {
  for (const issue of issues) console.error(`FAIL: ${issue}`);
  process.exit(1);
}
console.log(`PASS: ${questions.length} MCQs validated across ${Object.keys(counts).length} topics: ${requiredTopics.map(topic => `${topic}=${counts[topic]}`).join(', ')}`);
