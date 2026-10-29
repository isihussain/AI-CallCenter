(function (root) {
  "use strict";
  const i18n = root.OIMI18n;
  const t = (key, params) => i18n.t(key, params);
  const panel = document.querySelector("#calls");
  if (!panel) return;
  const form = document.querySelector("#call-filters");
  const tbody = panel.querySelector("tbody");
  const status = document.querySelector("#call-status");
  let context = null;
  let result = null;
  let page = 1;
  let snapshot = null;
  let controller = null;
  let sequence = 0;
  let filters = {
    date_from: "",
    date_to: "",
    status: "",
    caller: "",
    page_size: "25",
  };
  const labels = {
    incoming: "Gelen",
    active: "Aktif",
    ended: "Tamamlandı",
    failed: "Hata",
    rejected_no_credit: "Kredi yetersiz",
  };
  function queryFor(scope, values, requestedPage, snapshotId) {
    const query = new URLSearchParams({
      ...values,
      page: String(requestedPage),
    });
    for (const [key, value] of [...query]) if (value === "") query.delete(key);
    if (scope.role === "admin")
      query.set("tenant_id", String(scope.tenantId || 0));
    if (snapshotId !== null) query.set("snapshot_id", String(snapshotId));
    return query;
  }
  async function fetchPage(scope, values, requestedPage, snapshotId, signal) {
    const response = await fetch(
      "/api/calls?" + queryFor(scope, values, requestedPage, snapshotId),
      { credentials: "same-origin", signal },
    );
    const body = await response.json();
    if (!response.ok)
      throw Error(
        t(
          body.code === "invalid_call_query"
            ? "Çağrı filtrelerini kontrol edin."
            : body.error || "Çağrılar yüklenemedi.",
        ),
      );
    return body;
  }
  function duration(seconds) {
    return (
      String(Math.floor(seconds / 60)).padStart(2, "0") +
      ":" +
      String(seconds % 60).padStart(2, "0")
    );
  }
  function cell(value, raw = false) {
    const td = document.createElement("td");
    if (raw) td.dataset.userContent = "";
    td.textContent = value;
    return td;
  }
  function render() {
    if (!result) return;
    tbody.replaceChildren();
    for (const call of result.items) {
      const row = document.createElement("tr");
      const date = i18n.date(new Date(call.started_at * 1000), {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "UTC",
      });
      row.append(
        cell(date, true),
        cell(call.caller || t("Gizli numara"), true),
        cell(context?.tenantName || "—", true),
        cell(
          duration(
            Math.max(
              0,
              (call.ended_at || Math.floor(Date.now() / 1000)) -
                call.started_at,
            ),
          ),
          true,
        ),
        cell(
          i18n.number(call.billed_credits, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          }),
          true,
        ),
      );
      const state = cell("");
      const badge = document.createElement("span");
      badge.className =
        "pill " +
        (["failed", "rejected_no_credit"].includes(call.status)
          ? "warning"
          : "success");
      badge.textContent = t(labels[call.status] || call.status);
      badge.dataset.i18n = labels[call.status] || call.status;
      state.append(badge);
      row.append(state);
      tbody.append(row);
    }
    if (!result.items.length) {
      const row = document.createElement("tr"),
        td = cell(t("Bu filtrelere uygun çağrı yok."));
      td.colSpan = 6;
      row.append(td);
      tbody.append(row);
    }
    const paging = result.pagination,
      summary = result.summary;
    const values = {
      "#metric-calls": i18n.number(summary.total_calls),
      "#metric-completed": i18n.number(summary.completed_calls),
      "#metric-duration": duration(summary.average_duration_seconds),
      "#metric-credits": i18n.number(context?.balance, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
      "#metric-openai-usd": i18n.number(summary.estimated_openai_usd, {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 4,
        maximumFractionDigits: 4,
      }),
      "#metric-total-tokens": i18n.number(summary.total_tokens),
      "#metric-metered-calls": i18n.number(summary.metered_calls),
      "#nav-call-count": i18n.number(summary.total_calls),
    };
    for (const [selector, value] of Object.entries(values)) {
      const el = document.querySelector(selector);
      if (el) el.textContent = value;
    }
    const count = document.querySelector(".agent-row .agent-calls");
    if (count)
      count.textContent = t("{0} çağrı", {
        0: i18n.number(summary.total_calls),
      });
    document.querySelector("#call-page-info").textContent = t(
      "Sayfa {0} / {1} · {2} çağrı",
      {
        0: i18n.number(paging.total_pages ? paging.page : 0),
        1: i18n.number(paging.total_pages),
        2: i18n.number(paging.total),
      },
    );
    document.querySelector("#call-prev").disabled = !paging.has_previous;
    document.querySelector("#call-next").disabled = !paging.has_next;
    status.textContent = t(
      "Özetler, tüm filtre sonuçlarını kapsar. Saat dilimi: UTC.",
    );
  }
  async function load(reset = false) {
    if (!context) return;
    if (reset) {
      page = 1;
      snapshot = null;
    }
    controller?.abort();
    const active = ++sequence;
    controller = new AbortController();
    panel.setAttribute("aria-busy", "true");
    status.textContent = t("Çağrılar yükleniyor…");
    for (const button of panel.querySelectorAll("button"))
      button.disabled = true;
    try {
      const data = await fetchPage(
        context,
        filters,
        page,
        snapshot,
        controller.signal,
      );
      if (active !== sequence) return;
      result = data;
      snapshot = data.pagination.snapshot_id;
      render();
    } catch (error) {
      if (error.name === "AbortError" || active !== sequence) return;
      result = null;
      tbody.replaceChildren();
      const row = document.createElement("tr"),
        td = cell(t("Çağrılar yüklenemedi."));
      td.colSpan = 6;
      row.append(td);
      tbody.append(row);
      status.textContent = error.message || t("Çağrılar yüklenemedi.");
      document.querySelector("#call-page-info").textContent = "—";
    } finally {
      if (active === sequence) {
        panel.setAttribute("aria-busy", "false");
        for (const button of panel.querySelectorAll("button"))
          button.disabled = false;
        document.querySelector("#call-prev").disabled =
          !result?.pagination.has_previous;
        document.querySelector("#call-next").disabled =
          !result?.pagination.has_next;
      }
    }
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    filters = Object.fromEntries(new FormData(form).entries());
    if (
      filters.date_from &&
      filters.date_to &&
      filters.date_from > filters.date_to
    ) {
      status.textContent = t("Başlangıç tarihi bitiş tarihinden sonra olamaz.");
      return;
    }
    load(true);
  });
  document.querySelector("#call-reset").addEventListener("click", () => {
    form.reset();
    filters = {
      date_from: "",
      date_to: "",
      status: "",
      caller: "",
      page_size: "25",
    };
    load(true);
  });
  document
    .querySelector("#call-refresh")
    .addEventListener("click", () => load(true));
  document.querySelector("#call-prev").addEventListener("click", () => {
    if (page > 1) {
      page--;
      load();
    }
  });
  document.querySelector("#call-next").addEventListener("click", () => {
    if (result?.pagination.has_next) {
      page++;
      load();
    }
  });
  root.addEventListener("oim:localechange", render);
  root.CallHistory = {
    async setContext(value) {
      const changed =
        !context ||
        value.tenantId !== context.tenantId ||
        value.role !== context.role;
      context = { ...value };
      await load(changed);
    },
    async collectAll() {
      if (!context) throw Error(t("Önce bir müşteri seçin."));
      const scope = { ...context },
        selected = { ...filters, page_size: "100" };
      const first = await fetchPage(scope, selected, 1, null);
      const items = [...first.items];
      for (let next = 2; next <= first.pagination.total_pages; next++) {
        const chunk = await fetchPage(
          scope,
          selected,
          next,
          first.pagination.snapshot_id,
        );
        items.push(...chunk.items);
      }
      if (items.length !== first.pagination.total)
        throw Error(t("Rapor sırasında kayıtlar değişti. Yeniden deneyin."));
      return {
        items,
        summary: first.summary,
        filters: first.filters,
        scope,
        snapshot_id: first.pagination.snapshot_id,
      };
    },
    render,
  };
})(window);

