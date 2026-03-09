import test from 'node:test';
import assert from 'node:assert/strict';

import { escapeHtml } from './security.js';

test('escapeHtml escapes dangerous tags and quotes', () => {
  const input = `<img src=x onerror="alert('xss')">`;
  const out = escapeHtml(input);
  assert.equal(out.includes('<'), false);
  assert.equal(out.includes('>'), false);
  assert.match(out, /&lt;img/);
  assert.match(out, /&quot;/);
  assert.match(out, /&#39;/);
});
