(function (root) {
  "use strict";
  const catalogs = root.OIM_LOCALES || { tr: {} };
  const tags = { tr: "tr-TR", en: "en-GB", ru: "ru-RU" };
  let language = "tr";
  try {
    language = Object.hasOwn(tags, localStorage.getItem("oim.locale"))
      ? localStorage.getItem("oim.locale")
      : "tr";
  } catch {}
  const bindings = new Map();
  const attributes = new Map();
  const normalize = (value) => String(value).replace(/\s+/g, " ").trim();
  const reverse = new Map();
  const patterns = [];
  for (const key of Object.keys(catalogs.tr)) {
    for (const locale of Object.keys(tags))
      reverse.set(normalize(catalogs[locale]?.[key] || key), key);
    if (/\{\d+\}/.test(key)) {
      const fields = [];
      const escaped = key
        .split(/(\{\d+\})/)
        .map((part) => {
          if (/^\{\d+\}$/.test(part)) {
            fields.push(part.slice(1, -1));
            return "(.+?)";
          }
          return part.replace(/[{}.*+?^$()|[\]\\]/g, "\\$&");
        })
        .join("");
      patterns.push({ key, fields, regex: new RegExp("^" + escaped + "$") });
    }
  }
  function t(key, params = {}) {
    let text = catalogs[language]?.[key] || catalogs.tr[key] || key;
    return text.replace(/\{(\w+)\}/g, (match, field) =>
      Object.hasOwn(params, field) ? String(params[field]) : match,
    );
  }
  function message(value) {
    const source = normalize(value);
    const exact = reverse.get(source);
    if (exact) return { key: exact, params: {} };
    for (const item of patterns) {
      const match = source.match(item.regex);
      if (match)
        return {
          key: item.key,
          params: Object.fromEntries(
            item.fields.map((field, index) => [field, match[index + 1]]),
          ),
        };
    }
    return null;
  }
  function excluded(element) {
    if (!element) return true;
    if (
      element.closest(
        "script,style,textarea,input,pre,code,[data-user-content],[data-i18n-ignore]",
      )
    )
      return true;
    const cell = element.closest("td");
    if (
      cell &&
      !cell.hasAttribute("colspan") &&
      !element.closest("button,a,.pill,[data-i18n]")
    )
      return true;
    const option = element.closest("option");
    if (option && /^\d+$/.test(option.value)) return true;
    return Boolean(
      element.closest(
        "#top-company-name,#sidebar-company-name,.tenant-copy strong,.agent-info strong",
      ),
    );
  }
  function translateNode(node) {
    if (node.nodeType === 3) {
      if (excluded(node.parentElement)) return;
      const previous = bindings.get(node);
      if (previous && node.nodeValue === previous.rendered) return;
      const found = message(node.nodeValue);
      if (!found) {
        bindings.delete(node);
        return;
      }
      const leading = node.nodeValue.match(/^\s*/)[0];
      const trailing = node.nodeValue.match(/\s*$/)[0];
      const rendered = leading + t(found.key, found.params) + trailing;
      bindings.set(node, { ...found, leading, trailing, rendered });
      if (node.nodeValue !== rendered) node.nodeValue = rendered;
    } else if (node.nodeType === 1) {
      if (node.matches("[data-i18n]") && !node.closest("[data-user-content]")) {
        const key = node.dataset.i18n;
        if (node.textContent !== t(key)) node.textContent = t(key);
      }
      if (
        !node.closest("script,style,[data-user-content],[data-i18n-ignore]")
      ) {
        for (const attr of ["placeholder", "aria-label", "title"]) {
          if (!node.hasAttribute(attr)) continue;
          const found = message(node.getAttribute(attr));
          if (!found) continue;
          if (!attributes.has(node)) attributes.set(node, {});
          attributes.get(node)[attr] = found;
          const translated = t(found.key, found.params);
          if (node.getAttribute(attr) !== translated)
            node.setAttribute(attr, translated);
        }
      }
      for (const child of Array.from(node.childNodes)) translateNode(child);
    }
  }
  function translateDOM(element = document.body) {
    translateNode(element);
  }
  function setLocale(value) {
    language = Object.hasOwn(tags, value) ? value : "tr";
    document.documentElement.lang = language;
    try {
      localStorage.setItem("oim.locale", language);
    } catch {}
    for (const [node, binding] of bindings) {
      if (!node.isConnected || excluded(node.parentElement)) {
        bindings.delete(node);
        continue;
      }
      binding.rendered =
        binding.leading + t(binding.key, binding.params) + binding.trailing;
      node.nodeValue = binding.rendered;
    }
    for (const [element, items] of attributes) {
      if (!element.isConnected) {
        attributes.delete(element);
        continue;
      }
      for (const [attr, binding] of Object.entries(items))
        element.setAttribute(attr, t(binding.key, binding.params));
    }
    translateDOM();
    document.querySelectorAll("[data-locale-select]").forEach((select) => {
      select.value = language;
    });
    root.dispatchEvent(
      new CustomEvent("oim:localechange", { detail: { locale: language } }),
    );
  }
  root.OIMI18n = {
    t,
    setLocale,
    translateDOM,
    get locale() {
      return language;
    },
    localeTag: () => tags[language],
    number: (value, options = {}) =>
      new Intl.NumberFormat(tags[language], options).format(Number(value) || 0),
    date: (value, options = {}) =>
      new Intl.DateTimeFormat(tags[language], options).format(value),
    catalog: catalogs,
  };
  document.documentElement.lang = language;
  translateDOM();
  document.querySelectorAll("[data-locale-select]").forEach((select) => {
    select.value = language;
    select.addEventListener("change", () => setLocale(select.value));
  });
  const observer = new MutationObserver((changes) => {
    for (const change of changes) {
      if (change.type === "characterData") translateNode(change.target);
      else if (change.type === "attributes") translateNode(change.target);
      else change.addedNodes.forEach(translateNode);
    }
    for (const node of bindings.keys())
      if (!node.isConnected) bindings.delete(node);
    for (const node of attributes.keys())
      if (!node.isConnected) attributes.delete(node);
  });
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
    attributes: true,
    attributeFilter: ["placeholder", "aria-label", "title"],
  });
})(window);

