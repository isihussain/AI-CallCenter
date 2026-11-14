(function (root) {
  "use strict";

  function cell(value) {
    let text = String(value ?? "");
    if (typeof value === "string" && /^[\u0000-\u0020\uFEFF]*[=+\-@]/.test(text)) {
      text = "'" + text;
    }
    return '"' + text.replace(/"/g, '""') + '"';
  }

  root.OIMCSV = Object.freeze({ cell });
})(window);
