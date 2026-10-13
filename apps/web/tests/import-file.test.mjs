import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseImportFile } from '../app/import-file.ts';

test('CSV preserves Arabic, commas, multiline passages and escaped quotes', () => {
  assert.deepEqual(parseImportFile('\uFEFFtext,language\r\n"مرحبا, test\n""citation""",ar\r\n', 'data.csv'), [{text:'مرحبا, test\n"citation"',language:'ar'}]);
  assert.deepEqual(parseImportFile('text;language;published_at\nQuestion;fr;\n', 'data.csv'), [{text:'Question',language:'fr'}]);
});
test('rejects malformed rows, duplicate or unknown columns and oversized batches', () => {
  for (const csv of ['text,language\nx', 'text,text\nx,x', 'text,email\nx,a@b.test', 'text\n"unclosed', 'text\n"closed"junk']) assert.throws(() => parseImportFile(csv,'data.csv'));
  assert.throws(() => parseImportFile('text\n'+Array(501).fill('Question').join('\n'),'data.csv'));
  assert.throws(() => parseImportFile('text\n'+'x'.repeat(2_000_000),'data.csv'));
});
test('JSON records are bounded and do not silently accept personal or unknown columns', () => {
  assert.deepEqual(parseImportFile('[{"text":"Question","language":"fr"}]','data.json'),[{text:'Question',language:'fr'}]);
  for (const json of ['{}','[]','[null]','[{"text":""}]','[{"text":"X","email":"a@b.test"}]','[{"text":"X","language":12}]']) assert.throws(() => parseImportFile(json,'data.json'));
});
