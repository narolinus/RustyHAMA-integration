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
  assert.match(panel, /flex:0 0 auto/);
  assert.doesNotMatch(panel, /\.device\{[^}]*flex-shrink:/);
  assert.match(panel, /previewZoom='fit'/);
  assert.match(panel, /deviceFrame/);
  assert.match(panel, /overflow:auto/);
  assert.match(panel, /wrap\.scrollLeft=/);
  assert.match(panel, /wrap\.scrollTop=/);
});

test('JSON editor provides syntax highlighting and line numbers', () => {
  assert.match(panel, /highlightJson/);
  assert.match(panel, /line-numbers/);
  assert.match(panel, /json-key/);
  assert.match(panel, /selectionStart/);
  assert.match(panel, /highlight\.scrollTop=ed\.scrollTop/);
  assert.match(panel, /lines\.scrollTop=ed\.scrollTop/);
  assert.doesNotMatch(panel, /highlight'\)\.style\.transform/);
});

test('preview uses the server compiler and native grid fields', () => {
  assert.match(panel, /compile_preview/);
  for (const field of ['cell_height', 'rowspan', 'colspan', 'data-preview-tab']) {
    assert.ok(panel.includes(field), `missing ${field}`);
  }
  assert.match(panel, /preview-modal/);
  assert.match(panel, /image-placeholder/);
  assert.doesNotMatch(panel, /camera_proxy/);
});

test('visual editor exposes real theme and widget fields', () => {
  for (const field of [
    'background_color',
    'primary_color',
    'accent_color',
    'accent_text_color',
    'corner_radius',
    'ui_scale',
  ]) {
    assert.ok(panel.includes(field), `missing ${field}`);
  }
  for (const type of ['light', 'cover', 'climate', 'media_player', 'clock']) {
    assert.ok(panel.includes(type), `missing widget type ${type}`);
  }
});

test('widget documentation is linked from the panel', () => {
  assert.match(panel, /https:\/\/daniel\.snii\.de\/RustyHAMA\//);
  assert.match(panel, /Widget-Dokumentation/);
});

test('profiles, device overrides and tab ordering are manageable', () => {
  for (const contract of [
    'delete_profile',
    'profileCreate',
    'data-profile-rename',
    'data-device-profile-save',
    'data-override-open',
  ]) {
    assert.ok(panel.includes(contract), `missing ${contract}`);
  }
});

test('pairing creates a QR element using its data property', () => {
  assert.match(panel, /document\.createElement\('ha-qr-code'\)/);
  assert.match(panel, /qrCode\.data=qr/);
  assert.match(panel, /public_key_pin/);
});

test('preview loads the bundled Material Symbols font', () => {
  assert.match(panel, /@font-face/);
  assert.match(panel, /MaterialSymbolsOutlined\.ttf/);
  assert.match(panel, /font-variation-settings/);
});
