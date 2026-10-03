import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { Workbook } from '@oai/artifact-tool';

// CSV is the requested deliverable. The documented artifact API has no CSV export,
// so serialize the authored range using RFC 4180 quoting and check a CSV re-import.
const root = path.resolve(process.argv[2]);
const data = JSON.parse(await fs.readFile(path.join(root, 'evidence/review-mapping-data.json'), 'utf8'));
const files = [
  ['content-migration-inventory.csv', data.content_records],
  ['image-migration-inventory.csv', data.image_records],
];
const quote = value => {
  const text = String(value ?? '');
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
for (const [filename, rows] of files) {
  const headers = Object.keys(rows[0]);
  const matrix = [headers, ...rows.map(row => headers.map(header => row[header] ?? ''))];
  const wb = Workbook.create();
  const sheet = wb.worksheets.add('Inventory');
  const range = sheet.getRangeByIndexes(0, 0, matrix.length, headers.length);
  range.values = matrix;
  const authored = range.values;
  assert.deepEqual(authored, matrix);
  const csv = authored.map(row => row.map(quote).join(',')).join('\r\n') + '\r\n';
  const imported = await Workbook.fromCSV(csv, {sheetName: 'Inventory'});
  const roundtrip = imported.worksheets.getItem('Inventory').getRangeByIndexes(0, 0, matrix.length, headers.length).values;
  assert.deepEqual(roundtrip.map(row => row.map(v => String(v ?? ''))), matrix.map(row => row.map(v => String(v ?? ''))));
  await fs.writeFile(path.join(root, filename), csv, 'utf8');
  console.log(`${filename}: ${rows.length} records, ${headers.length} columns; exact CSV round-trip passed`);
}
