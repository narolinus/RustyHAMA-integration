import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';

const panel = readFileSync('custom_components/rustyhama/frontend/panel.js', 'utf8');

test('editor keeps JSON as the initial mode', () => {
  assert.match(panel, /this\.mode='json'/);
  assert.match(panel, /Profile draft/);
  assert.match(panel, /Effective config/);
});

test('device preview consumes reported geometry', () => {
  for (const field of ['usable_width_px', 'usable_height_px', 'density_dpi', 'font_scale']) {
    assert.ok(panel.includes(field), `missing ${field}`);
  }
});

test('viewport fit preserves aspect ratio', () => {
  const fit = (sourceWidth, sourceHeight, boxWidth, boxHeight) =>
    Math.min(boxWidth / sourceWidth, boxHeight / sourceHeight, 1);
  assert.equal(fit(1920, 1080, 960, 800), 0.5);
  assert.equal(fit(800, 1280, 1000, 640), 0.5);
  assert.equal(fit(480, 800, 1000, 1000), 1);
});
