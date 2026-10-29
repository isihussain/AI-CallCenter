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
  function summaryDraft(transcript) {
    const customer = [],
      assistant = [];
    for (const line of String(transcript || "").split(/\r?\n/)) {
      const caller = line.match(/^\s*(?:Müşteri|Caller|Customer)\s*:\s*(.+)$/i);
      const reply = line.match(/^\s*(?:AI|Assistant)\s*:\s*(.+)$/i);
      if (caller?.[1]?.trim().length > 2) customer.push(caller[1].trim());
      if (reply?.[1]?.trim().length > 2) assistant.push(reply[1].trim());
    }
    return [...customer.slice(0, 2), ...assistant.slice(-1)]
      .map((line) => `• ${line.slice(0, 240)}`)
      .join("\n")
      .slice(0, 1000);
  }
  function reviewRow(call) {
    const row = document.createElement("tr");
    row.className = "call-review-row";
    row.hidden = true;
    const cell = document.createElement("td");
    cell.colSpan = 8;
    const formReview = document.createElement("form");
    formReview.className = "call-review-form";
    const outcomeLabel = document.createElement("label");
    outcomeLabel.textContent = t("Sonuç");
    const outcome = document.createElement("select");
    outcome.setAttribute("aria-label", t("Sonuç"));
    const choices = [
      ["", "Henüz değerlendirilmedi"],
      ["resolved", "Çözüldü"],
      ["appointment_booked", "Randevu oluşturuldu"],
      ["callback_needed", "Geri arama gerekli"],
      ["unresolved", "Çözülemedi"],
    ];
    for (const [value, label] of choices) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = t(label);
      outcome.append(option);
    }
    outcome.value = call.review_outcome || "";
    outcomeLabel.append(outcome);
    const summaryLabel = document.createElement("label");
    summaryLabel.textContent = t("Özet (düzenlenebilir yerel taslak)");
    const summary = document.createElement("textarea");
    summary.rows = 3;
    summary.maxLength = 2000;
    summary.value = call.review_summary || "";
    summary.setAttribute("aria-label", t("Çağrı özeti"));
    summaryLabel.append(summary);
    const notesLabel = document.createElement("label");
    notesLabel.textContent = t("Ekip notu");
    const notes = document.createElement("textarea");
    notes.rows = 3;
    notes.maxLength = 2000;
    notes.value = call.review_notes || "";
    notes.setAttribute("aria-label", t("Ekip notu"));
    notesLabel.append(notes);
    const actions = document.createElement("div");
    actions.className = "call-review-actions";
    const draft = document.createElement("button");
    draft.type = "button";
    draft.className = "button outline";
    draft.textContent = t("Transkriptten taslak oluştur");
    const save = document.createElement("button");
    save.type = "submit";
    save.className = "button primary";
    save.textContent = t("İncelemeyi kaydet");
    const message = document.createElement("span");
    message.className = "form-note";
    message.setAttribute("role", "status");
    message.setAttribute("aria-live", "polite");
    draft.addEventListener("click", () => {
      if (!call.transcript) {
        message.textContent = t(
          "Transkript bulunmuyor. Elle özet yazabilirsiniz.",
        );
        return;
      }
      if (!summary.value) summary.value = summaryDraft(call.transcript);
      message.textContent = t(
        "Yerel taslak hazır. Kaydetmeden önce düzenleyebilirsiniz.",
      );
    });
    formReview.addEventListener("submit", async (event) => {
      event.preventDefault();
      save.disabled = true;
      message.textContent = t("Kaydediliyor…");
      try {
        const response = await fetch("/api/call-review", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            call_id: call.call_id,
            tenant_id: context?.role === "admin" ? context.tenantId : undefined,
            outcome: outcome.value,
            summary: summary.value,
            notes: notes.value,
          }),
        });
        const body = await response.json();
        if (!response.ok)
          throw Error(body.error || t("İnceleme kaydedilemedi."));
        message.textContent = t("İnceleme kaydedildi.");
        await load();
      } catch (error) {
        message.textContent = error.message;
      } finally {
        save.disabled = false;
      }
    });
    actions.append(draft, save);
    formReview.append(outcomeLabel, summaryLabel, notesLabel, actions, message);
    cell.append(formReview);
    row.append(cell);
    return row;
  }
  function qualityCell(call) {
    const td = document.createElement("td");
    const details = document.createElement("details");
    details.className = "quality-details";
    const summary = document.createElement("summary");
    summary.className =
      "pill " +
      (call.quality_score == null
        ? "neutral"
        : call.quality_score < 60
          ? "warning"
          : "success");
    summary.textContent =
      call.quality_score == null
        ? t("Yetersiz veri")
        : `${call.quality_score}%`;
    const list = document.createElement("ul");
    const labelsBySignal = {
      completed: "Çağrı tamamlandı",
      assistant_responded: "AI yanıt verdi",
      knowledge_helpful: "Bilgi bankası sonuç verdi",
      follow_up_recorded: "Sonuç veya takip kaydedildi",
    };
    for (const signal of call.quality_signals || []) {
      const item = document.createElement("li");
      const value =
        signal.value == null
          ? t("Bilinmiyor")
          : signal.value
            ? t("Evet")
            : t("Hayır");
      item.textContent = `${t(labelsBySignal[signal.key] || signal.key)}: ${value}`;
      list.append(item);
    }
    const coverage = document.createElement("small");
    coverage.textContent = t("Bilinen göstergeler: {0}/4", {
      0: call.quality_coverage || 0,
    });
    details.append(summary, list, coverage);
    td.append(details);
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
      const reviewButton = document.createElement("button");
      reviewButton.type = "button";
      reviewButton.className = "button outline call-review-toggle";
      reviewButton.textContent = t("İncele");
      reviewButton.setAttribute("aria-expanded", "false");
      const expanded = reviewRow(call);
      reviewButton.addEventListener("click", () => {
        expanded.hidden = !expanded.hidden;
        reviewButton.setAttribute("aria-expanded", String(!expanded.hidden));
      });
      const reviewCell = cell("");
      reviewCell.append(reviewButton);
      row.append(state, qualityCell(call), reviewCell);
      tbody.append(row);
      tbody.append(expanded);
    }
    if (!result.items.length) {
      const row = document.createElement("tr"),
        td = cell(t("Bu filtrelere uygun çağrı yok."));
      td.colSpan = 8;
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
      td.colSpan = 8;
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
