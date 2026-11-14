const test = require("node:test");
const assert = require("node:assert/strict");
const { environment } = require("./helpers.cjs");

test("CSV cells quote data and neutralize spreadsheet formulas", () => {
  const { window } = environment("<html><body></body></html>");

  for (const value of ["=1+1", "+SUM(A1:A2)", "-1+2", "@SUM(A1)", "  =1+1", "\t=1+1"]) {
    assert.equal(window.OIMCSV.cell(value), `"'${value}"`);
  }
  assert.equal(window.OIMCSV.cell('ordinary "text"'), '"ordinary ""text"""');
  assert.equal(window.OIMCSV.cell(-1.25), '"-1.25"');
});
