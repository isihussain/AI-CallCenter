(function (root) {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  if (!$("#system-flow")) return;
  const t = (key) => root.OIMI18n?.t(key) || key;
  let admin = false,
    epoch = 0,
    paused = false,
    list = false,
    loading = null,
    loadingEpoch = 0,
    snapshot = null,
    audioUrl = null,
    selected = "realtime",
    zoom = 1,
    flowSequence = 0,
    autoFit = true;
  const profiles = [
    {
      id: "openai",
      name: "OpenAI Realtime",
      icon: "wave-square",
      note: "Telefon görüşmeleri: dinleme, yanıt ve ses.",
      model: "gpt-realtime",
      kind: "TELEFON",
    },
    {
      id: "openai_ai",
      name: "OpenAI AI",
      icon: "brain",
      note: "Panelde metin üretimi ve AI yanıt denemesi.",
      model: "",
      kind: "ZEKA",
    },
    {
      id: "elevenlabs",
      name: "ElevenLabs",
      icon: "sliders",
      note: "Panelde doğal ses üretimi ve dinleme.",
      model: "eleven_flash_v2_5",
      kind: "SES",
    },
  ];
  const nodes = [
    {
      id: "prompt",
      x: 35,
      y: 60,
      name: "Metin denemesi",
      icon: "message",
      info: "Panelde yazdığınız metin OpenAI AI modeline gönderilir.",
      view: "integrations",
    },
    {
      id: "openai_ai",
      x: 270,
      y: 60,
      name: "OpenAI AI",
      icon: "brain",
      provider: "openai_ai",
      info: "Yanıt Responses API üzerinden üretilir. Telefon ajanından bağımsızdır.",
      view: "integrations",
    },
    {
      id: "elevenlabs",
      x: 505,
      y: 60,
      name: "ElevenLabs",
      icon: "sliders",
      provider: "elevenlabs",
      info: "Deneme yanıtı veya yazdığınız metin seçilen ElevenLabs sesiyle okunur.",
      view: "integrations",
    },
    {
      id: "phone",
      x: 35,
      y: 280,
      name: "Gelen çağrı",
      icon: "phone",
      info: "Arayan kişi, operatör numarasından SIP hattına ulaşır. Operatör yönlendirmesi bu panelden doğrulanamaz.",
      view: "sip",
    },
    {
      id: "sip",
      x: 270,
      y: 280,
      name: "SIP / PBX",
      icon: "network-wired",
      info: "Mevcut telefon hattı OpenAI Realtime SIP bağlantısına yönlenir.",
      view: "sip",
    },
    {
      id: "realtime",
      x: 505,
      y: 280,
      name: "OpenAI Realtime",
      icon: "wave-square",
      info: "Canlı telefon görüşmesini yürütür; bilgi araması, randevu ve geri arama araçlarını çağırabilir.",
      view: "integrations",
    },
    {
      id: "tools",
      x: 740,
      y: 280,
      name: "Ajan araçları",
      icon: "code-branch",
      info: "Ajan, görüşmenin ihtiyacına göre bilgi arar veya takip işlemi kaydeder.",
      view: "agents",
    },
    {
      id: "knowledge",
      x: 975,
      y: 130,
      name: "Bilgi Bankası",
      icon: "book-open",
      metric: "knowledge",
      info: "Yalnızca ilgili müşterinin yayınlanmış içerikleri aranır.",
      view: "customers",
    },
    {
      id: "appointments",
      x: 975,
      y: 280,
      name: "Randevular",
      icon: "calendar-check",
      metric: "appointments",
      info: "Onaylanan randevular ilgili müşteri hesabında saklanır.",
      view: "appointments",
    },
    {
      id: "callbacks",
      x: 975,
      y: 430,
      name: "Geri aramalar",
      icon: "phone-volume",
      metric: "callbacks",
      info: "İnsan desteği isteyen arayanlar, daha sonra geri aranmak üzere kuyruğa eklenir.",
      view: "callbacks",
    },
    {
      id: "records",
      x: 505,
      y: 480,
      name: "Çağrı kayıtları",
      icon: "database",
      metric: "today",
      info: "Çağrı durumu, transkript ve kullanım kaydı geçmişe işlenir. Saklama politikası transkript süresini belirler.",
      view: "calls",
    },
  ];
  const edges = [
    ["prompt", "openai_ai", "lab"],
    ["openai_ai", "elevenlabs", "lab"],
    ["phone", "sip", "phone"],
    ["sip", "realtime", "phone"],
    ["realtime", "tools", "phone"],
    ["tools", "knowledge", "branch"],
    ["tools", "appointments", "branch"],
    ["tools", "callbacks", "branch"],
    ["realtime", "records", "down"],
  ];
  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }
  function icon(name) {
    const node = el("i", `fa-solid fa-${name}`);
    node.setAttribute("aria-hidden", "true");
    return node;
  }
  function navigate(view) {
    root.OIMSetView?.(view);
    root.scrollTo?.({ top: 0, behavior: "smooth" });
    fit();
  }
  function fit() {
    const width = $("#flow-viewport").clientWidth;
    if (width && autoFit) {
      zoom = Math.min(1, width / 1210);
      $("#flow-stage").style.zoom = zoom;
    }
  }
  async function request(path, body) {
    const response = await fetch(path, {
      credentials: "same-origin",
      ...(body
        ? {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }
        : {}),
    });
    const data = await response.json();
    if (!response.ok || data.ok === false)
      throw Error(t(data.error || "İstek tamamlanamadı."));
    return data;
  }
  function state(node) {
    if (!snapshot) return t("Bilinmiyor");
    if (node.id === "realtime") {
      const saved = snapshot.providers.find(
        (item) => item.provider === "openai",
      );
      if (
        snapshot.realtime.source === "saved" &&
        saved?.check_status === "error"
      )
        return t("Son kontrol başarısız");
      return snapshot.realtime.configured
        ? t("Yapılandırıldı")
        : t("Anahtar bekliyor");
    }
    if (node.provider) {
      const p = snapshot.providers.find(
        (item) => item.provider === node.provider,
      );
      if (!p?.configured) return t("Anahtar bekliyor");
      if (!p.enabled) return t("Devre dışı");
      if (node.id === "elevenlabs" && !p.voice_id)
        return t("Ses kimliği bekliyor");
      if (p.check_status === "error") return t("Son kontrol başarısız");
      return p.check_status === "ok"
        ? t("Bağlantı doğrulandı")
        : t("Yapılandırıldı");
    }
    if (node.metric) return root.OIMI18n.number(snapshot.counts[node.metric]);
    return t(
      ["phone", "sip"].includes(node.id)
        ? "Harici yönlendirme"
        : "Uygulama içi",
    );
  }
  function inspect(id) {
    selected = id;
    const node = nodes.find((item) => item.id === id),
      pane = $("#flow-inspector");
    pane.replaceChildren(
      el("p", "eyebrow", t("BAĞLANTI DETAYI")),
      icon(node.icon),
      el("h3", "", t(node.name)),
      el("span", "flow-state", state(node)),
      el("p", "", t(node.info)),
    );
    const incoming = edges
      .filter((edge) => edge[1] === id)
      .map((edge) => t(nodes.find((n) => n.id === edge[0]).name));
    const outgoing = edges
      .filter((edge) => edge[0] === id)
      .map((edge) => t(nodes.find((n) => n.id === edge[1]).name));
    if (incoming.length)
      pane.append(el("small", "", t("Kaynak") + ": " + incoming.join(", ")));
    if (outgoing.length)
      pane.append(el("small", "", t("Hedef") + ": " + outgoing.join(", ")));
    if (node.id === "realtime" && snapshot)
      pane.append(el("small", "", snapshot.realtime.model));
    if (node.metric)
      pane.append(
        el(
          "small",
          "",
          t(
            node.id === "knowledge"
              ? "İçerik müşterinin kendi panelinden yönetilir."
              : "Detay paneli seçili müşteriyi gösterir.",
          ),
        ),
      );
    const open = el("button", "button outline", t("İlgili alanı aç"));
    open.type = "button";
    open.addEventListener("click", () => navigate(node.view));
    pane.append(open);
    document
      .querySelectorAll("[data-flow-node]")
      .forEach((button) =>
        button.setAttribute(
          "aria-pressed",
          String(button.dataset.flowNode === id),
        ),
      );
  }
  function renderFlow() {
    if (snapshot?.realtime.source === "environment") {
      const indicator = document.querySelector(
        '[data-provider-card="openai"] .provider-key-state',
      );
      if (indicator)
        indicator.textContent = t("Sunucu ortamındaki anahtar kullanılıyor.");
    }
    const wires = $("#flow-wires"),
      host = $("#flow-nodes"),
      accessible = $("#flow-list");
    host.replaceChildren();
    accessible.replaceChildren();
    wires.replaceChildren();
    for (const [from, to, kind] of edges) {
      const a = nodes.find((n) => n.id === from),
        b = nodes.find((n) => n.id === to);
      const d =
        kind === "down"
          ? `M ${a.x + 96} ${a.y + 100} C ${a.x + 96} ${a.y + 135}, ${b.x + 96} ${b.y - 35}, ${b.x + 96} ${b.y}`
          : `M ${a.x + 192} ${a.y + 50} C ${a.x + 220} ${a.y + 50}, ${b.x - 30} ${b.y + 50}, ${b.x} ${b.y + 50}`;
      for (const type of ["wire", "dots"]) {
        const path = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "path",
        );
        path.setAttribute("d", d);
        path.setAttribute("class", `${type} ${kind}`);
        wires.append(path);
      }
    }
    for (const node of nodes) {
      const button = el("button", `flow-node node-${node.id}`);
      button.type = "button";
      button.dataset.flowNode = node.id;
      button.style.left = node.x + "px";
      button.style.top = node.y + "px";
      const badge = el("span", "node-icon");
      badge.append(icon(node.icon));
      button.append(
        badge,
        el("strong", "", t(node.name)),
        el("small", "", state(node)),
      );
      button.addEventListener("click", () => inspect(node.id));
      host.append(button);
      const item = el("li"),
        listButton = el("button", "flow-list-node");
      listButton.type = "button";
      listButton.dataset.flowNode = node.id;
      listButton.append(
        icon(node.icon),
        el("strong", "", t(node.name)),
        el("span", "", state(node)),
      );
      listButton.addEventListener("click", () => inspect(node.id));
      item.append(listButton);
      accessible.append(item);
    }
    const metrics = $("#flow-metrics");
    metrics.replaceChildren();
    for (const [key, label, ico] of [
      ["active", "Aktif çağrı", "phone"],
      ["today", "Bugünkü çağrı", "chart-simple"],
      ["callbacks", "Bekleyen geri arama", "phone-volume"],
      ["failed", "Son 24 saatte hata", "triangle-exclamation"],
    ]) {
      const metric = el("div", "flow-metric");
      metric.append(
        icon(ico),
        el("span", "", t(label)),
        el(
          "strong",
          "",
          snapshot ? root.OIMI18n.number(snapshot.counts[key]) : "—",
        ),
      );
      metrics.append(metric);
    }
    inspect(selected);
  }
  async function refreshFlow() {
    if (!admin) return;
    const ticket = epoch;
    const sequence = ++flowSequence;
    try {
      const data = await request("/api/admin/system-flow");
      if (ticket !== epoch || sequence !== flowSequence || !admin) return;
      snapshot = data;
      renderFlow();
      $("#flow-stage").classList.remove("stale");
      $("#flow-status").textContent =
        t("Güncellendi") +
        " · " +
        new Intl.DateTimeFormat(root.OIMI18n.localeTag(), {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }).format(new Date(data.updated_at * 1000));
    } catch (error) {
      if (ticket === epoch && sequence === flowSequence) {
        $("#flow-status").textContent = t(
          "Veriler güncellenemedi. Son görünüm korunuyor.",
        );
        $("#flow-stage").classList.add("stale");
      }
    }
  }
  function renderProviders(items) {
    const host = $("#provider-cards");
    host.replaceChildren();
    const definitions = [...profiles];
    if (items.some((p) => p.provider === "deepgram"))
      definitions.push({
        id: "deepgram",
        name: "Deepgram",
        icon: "microphone",
        note: "Kayıtlı yardımcı sağlayıcı ayarları.",
        model: "",
        kind: "EK BAĞLANTI",
      });
    for (const profile of definitions) {
      const p = items.find((item) => item.provider === profile.id) || {},
        card = el("article", `provider-card provider-${profile.id}`);
      card.dataset.providerCard = profile.id;
      const head = el("div", "provider-card-head"),
        logo = el("span", "provider-logo");
      logo.append(icon(profile.icon));
      head.append(logo, el("span", "eyebrow", t(profile.kind)));
      card.append(
        head,
        el("h3", "", profile.name),
        el("p", "provider-description", t(profile.note)),
      );
      const indicator = el(
        "p",
        "provider-key-state",
        t(p.configured ? "Anahtar kayıtlı" : "Anahtar eklenmedi"),
      );
      card.append(indicator);
      const form = el("form", "provider-profile");
      form.dataset.provider = profile.id;
      function field(label, name, value, type = "text") {
        const wrap = el("label", "", t(label)),
          input = el("input");
        input.name = name;
        input.type = type;
        input.value = value || "";
        input.maxLength = name === "api_key" ? 4096 : 128;
        input.autocomplete = type === "password" ? "new-password" : "off";
        if (type === "password")
          input.placeholder = t("Boş bırakırsanız kayıtlı anahtar korunur.");
        wrap.append(input);
        form.append(wrap);
        return input;
      }
      const model = field("Model kimliği", "model", p.model || profile.model);
      model.maxLength = 100;
      model.placeholder = t("Sağlayıcınızdaki model kimliği");
      const key = field("API anahtarı", "api_key", "", "password");
      if (profile.id === "elevenlabs")
        field("Ses kimliği (Voice ID)", "voice_id", p.voice_id);
      const enabled = el("input");
      enabled.type = "checkbox";
      enabled.name = "enabled";
      enabled.checked = !!p.enabled;
      const enableLabel = el("label", "check");
      enableLabel.append(
        enabled,
        document.createTextNode(t("Bağlantıyı etkinleştir")),
      );
      form.append(enableLabel);
      const clear = el("input");
      clear.type = "checkbox";
      clear.name = "clear_key";
      const clearLabel = el("label", "check key-remove");
      clearLabel.append(
        clear,
        document.createTextNode(t("Kayıtlı anahtarı sil")),
      );
      form.append(clearLabel);
      const actions = el("div", "provider-actions"),
        save = el("button", "button primary", t("Kaydet")),
        test = el("button", "button outline", t("Bağlantıyı kontrol et"));
      save.type = "submit";
      test.type = "button";
      test.disabled = !p.configured;
      actions.append(save, test);
      form.append(actions);
      const feedback = el("p", "provider-feedback");
      feedback.setAttribute("role", "status");
      feedback.setAttribute("aria-live", "polite");
      feedback.textContent = t(
        p.check_status === "ok"
          ? "Bağlantı doğrulandı"
          : p.check_status === "error"
            ? "Son kontrol başarısız"
            : "Henüz doğrulanmadı",
      );
      form.append(feedback);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        save.disabled = true;
        test.disabled = true;
        feedback.textContent = t("Kaydediliyor…");
        try {
          const body = {
            provider: profile.id,
            model: model.value,
            api_key: key.value,
            enabled: enabled.checked,
            clear_key: clear.checked,
          };
          if (profile.id === "elevenlabs")
            body.voice_id = form.querySelector('[name="voice_id"]').value;
          const data = await request("/api/admin/providers", body);
          key.value = "";
          clear.checked = false;
          p.configured = data.provider.configured;
          indicator.textContent = t(
            p.configured ? "Anahtar kayıtlı" : "Anahtar eklenmedi",
          );
          feedback.textContent = t(
            "Ayarlar kaydedildi. Bağlantıyı kontrol edebilirsiniz.",
          );
          await refreshFlow();
        } catch (error) {
          feedback.textContent = error.message;
        } finally {
          save.disabled = false;
          test.disabled = !p.configured;
        }
      });
      test.addEventListener("click", async () => {
        test.disabled = true;
        feedback.textContent = t("Kontrol ediliyor…");
        try {
          await request("/api/admin/providers/test", { provider: profile.id });
          feedback.textContent = t("Bağlantı doğrulandı");
          await refreshFlow();
        } catch (error) {
          feedback.textContent = error.message;
        } finally {
          test.disabled = !p.configured;
        }
      });
      card.append(form);
      host.append(card);
    }
  }
  async function refresh() {
    if (!admin) return;
    if (loading && loadingEpoch === epoch) return loading;
    const ticket = epoch;
    loadingEpoch = ticket;
    loading = (async () => {
      try {
        const data = await request("/api/admin/providers");
        if (
          ticket === epoch &&
          admin &&
          !$("#provider-cards").childElementCount
        )
          renderProviders(data.items);
        await refreshFlow();
        fit();
      } catch (error) {
        if (ticket === epoch) $("#flow-status").textContent = error.message;
      } finally {
        if (loadingEpoch === ticket) loading = null;
      }
    })();
    return loading;
  }
  async function session() {
    const ticket = ++epoch;
    try {
      const data = await request("/api/me");
      if (ticket !== epoch) return;
      admin = data.user.role === "admin";
    } catch (_) {
      if (ticket !== epoch) return;
      admin = false;
    }
    for (const id of ["system-flow", "integrations"])
      $("#" + id).hidden = !admin;
    if (admin) await refresh();
    else {
      snapshot = null;
      $("#provider-cards").replaceChildren();
      $("#ai-lab-output").value = "";
      $("#ai-lab-status").textContent = "";
      clearAudio();
      renderFlow();
    }
  }
  function clearAudio() {
    const audio = $("#eleven-audio");
    audio.pause?.();
    audio.removeAttribute("src");
    audio.hidden = true;
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      audioUrl = null;
    }
  }
  async function lab(action, button) {
    const ticket = epoch;
    button.disabled = true;
    $("#ai-lab-status").textContent = t("İşleniyor…");
    clearAudio();
    try {
      const text =
        action === "ai"
          ? $("#ai-lab-input").value
          : $("#ai-lab-output").value || $("#ai-lab-input").value;
      const data = await request(
        action === "ai"
          ? "/api/admin/ai-playground"
          : "/api/admin/providers/preview",
        { provider: "elevenlabs", text },
      );
      if (ticket !== epoch || !admin) return;
      if (action === "ai") {
        $("#ai-lab-output").value = data.text;
        $("#ai-lab-status").textContent = t(
          "Yanıt hazır. En fazla 500 karakter seslendirebilirsiniz.",
        );
      } else {
        const bytes = Uint8Array.from(atob(data.audio), (c) => c.charCodeAt(0));
        audioUrl = URL.createObjectURL(
          new Blob([bytes], { type: data.content_type }),
        );
        const audio = $("#eleven-audio");
        audio.src = audioUrl;
        audio.hidden = false;
        $("#ai-lab-status").textContent = t(
          "Ses hazır. Oynat düğmesine basın.",
        );
      }
    } catch (error) {
      if (ticket === epoch) $("#ai-lab-status").textContent = error.message;
    } finally {
      button.disabled = false;
    }
  }
  $("#ai-lab-form").addEventListener("submit", (event) => {
    event.preventDefault();
    lab("ai", event.currentTarget.querySelector('button[type="submit"]'));
  });
  $("#eleven-preview").addEventListener("click", (event) =>
    lab("voice", event.currentTarget),
  );
  $("#flow-refresh").addEventListener("click", refreshFlow);
  for (const [id, delta] of [
    ["flow-zoom-in", 0.15],
    ["flow-zoom-out", -0.15],
  ])
    $("#" + id).addEventListener("click", () => {
      autoFit = false;
      zoom = Math.min(1.5, Math.max(0.4, zoom + delta));
      $("#flow-stage").style.zoom = zoom;
    });
  $("#flow-fit").addEventListener("click", () => {
    autoFit = true;
    fit();
  });
  $("#flow-pause").addEventListener("click", () => {
    paused = !paused;
    $("#flow-pause").setAttribute("aria-pressed", String(paused));
    $("#flow-pause").textContent = t(
      paused ? "Otomatik yenilemeyi sürdür" : "Otomatik yenilemeyi duraklat",
    );
    $("#flow-stage").classList.toggle("paused", paused);
  });
  $("#flow-toggle").addEventListener("click", () => {
    list = !list;
    $("#flow-toggle").setAttribute("aria-pressed", String(list));
    $("#flow-toggle").textContent = t(
      list ? "Harita görünümü" : "Liste görünümü",
    );
    $("#flow-viewport").hidden = list;
    $("#flow-list").hidden = !list;
    $("#flow-zoom-controls").hidden = list;
    fit();
  });
  document.querySelectorAll("[data-console-view]").forEach((link) =>
    link.addEventListener("click", (event) => {
      event.preventDefault();
      navigate(link.dataset.consoleView);
    }),
  );
  root.addEventListener("oim:sessionchange", session);
  root.addEventListener("oim:localechange", () => {
    renderFlow();
  });
  root.addEventListener("pagehide", clearAudio);
  root.addEventListener("resize", fit);
  if (root.ResizeObserver)
    new root.ResizeObserver(fit).observe($("#flow-viewport"));
  if (root.matchMedia?.("(max-width:760px)").matches) $("#flow-toggle").click();
  setInterval(() => {
    if (
      admin &&
      !paused &&
      !document.hidden &&
      ["#dashboard", "#system-flow", ""].includes(root.location.hash)
    )
      refreshFlow();
  }, 30000);
  root.AdminConsole = { refresh };
  renderFlow();
  session();
})(window);
