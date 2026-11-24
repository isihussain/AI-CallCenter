(function (root) {
  "use strict";
  const panel = document.querySelector("#voice-platform");
  if (!panel) return;

  const words = {
    tr: {
      title: "ElevenLabs Voice Workspace", subtitle: "Ajanları, araçları ve takvimi OIM içinden yönetin.", tenant: "Müşteri hesabı", refresh: "Yenile", loading: "Yükleniyor…", error: "İstek tamamlanamadı.", noTenant: "Önce bir müşteri seçin.", noKey: "ElevenLabs API anahtarı bulunamadı. Integrations sekmesinden ekleyin.", agents: "Voice Agents", tools: "Tools", calendar: "Calendar", knowledge: "Knowledge Base", conversations: "Conversations", integrations: "Integrations", analytics: "Analytics", settings: "Settings", connected: "API bağlantısı hazır", disconnected: "API anahtarı yok", testConnection: "Bağlantıyı test et", save: "Kaydet", create: "Oluştur", new: "Yeni", name: "Ad", tenantAssign: "OIM müşterisine ata", selectAgent: "Ajan seçin", selectTenant: "Müşteri seçin", config: "ElevenLabs ajan JSON ayarı", localSave: "Yerel taslağı kaydet", pull: "ElevenLabs'tan çek", push: "ElevenLabs'a gönder", clone: "Kopyala", delete: "Kalıcı sil", confirmDelete: "Bu ElevenLabs ajanını kalıcı olarak silmek istiyor musunuz?", rawJson: "JSON geçerli olmalı.", createAgent: "Yeni ajan oluştur", branch: "Branch / sürüm", branches: "Branch listesini al", createBranch: "Branch oluştur", parentVersion: "Başlangıç sürüm ID", branchName: "Branch adı", targetBranch: "Hedef branch ID", merge: "Branch birleştir", versionId: "Sürüm ID", restore: "Sürümü geri yükle", deployment: "Trafik dağılımı JSON'u", deploy: "Canlı trafik dağılımını yayınla", testJson: "ElevenLabs test JSON'u", saveTest: "Test senaryosu oluştur", runTest: "Seçili testleri çalıştır", confirmTools: "Bu testlerin ajana bağlı araçları çağırabileceğini onaylıyorum.", toolsJson: "Araç ayarı JSON'u", webhookTest: "Webhook'u test et", addCalendarTools: "10 OIM takvim aracını ekle", useAgent: "Bu araca ajan ata", dependents: "Bağımlı ajanlar", calendarSettings: "Takvim kuralları JSON'u", saveSettings: "Takvim kurallarını kaydet", date: "Tarih", start: "Başlangıç zamanı (ISO 8601)", check: "Uygunluğu kontrol et", slots: "Boş saatleri getir", alternatives: "Alternatif bul", book: "Deneme randevusu kaydet", customerName: "Müşteri adı", phone: "Telefon", service: "Hizmet", notes: "Not", duration: "Süre (dk)", type: "Kaynak türü", content: "Metin içeriği", url: "HTTPS sayfa adresi", file: "Dosya (en fazla 20 MiB)", autoSync: "URL içeriğini otomatik eşitle", createDocument: "Bilgi kaydı ekle", assignDocs: "Seçili belgeleri ajana bağla", conversation: "Konuşma", imported: "OIM'e aktarılan çağrılar", summary: "Özet", transcript: "Transkript", providerKey: "API anahtarı", providerModel: "TTS modeli", voice: "Ses", enable: "Bağlantıyı etkinleştir", keyHint: "Boş bırakırsanız kayıtlı anahtar korunur.", previewText: "Ses deneme metni", preview: "Seçili sesle dinle", usage: "Kullanım ve abonelik", plan: "Abonelik", quota: "Kota / kullanım", webhookSecret: "ElevenLabs webhook imza anahtarı", webhookUrl: "Webhook adresi", saveSecret: "İmza anahtarını kaydet", eventLog: "Eşitleme ve webhook olayları", toolUrl: "Webhook HTTPS adresi", method: "HTTP yöntemi", headers: "Header JSON'u", body: "İstek gövdesi JSON'u", selected: "Seçili", providerManaged: "Code/MCP özellikleri ElevenLabs hesabında yönetilir; OIM bunları taklit etmez.", empty: "Kayıt yok.", saved: "Kaydedildi.", success: "İşlem tamamlandı.", confirmDeleteDoc: "Bu belgeyi silmek istiyor musunuz? Bağımlı ajan varsa önce kaldırın.", noAgent: "Önce bir ElevenLabs ajanı seçin.", copied: "Kopyalandı.", items: "Kayıtlar", status: "Durum", checked: "Son kontrol", language: "Dil", branchId: "Branch ID", id: "ID", actions: "İşlemler", details: "Ayrıntılar", connectHelp: "API anahtarını mevcut Integrations bölümünden de kaydedebilirsiniz.", localDraft: "Yerel taslak", remoteConfig: "Provider ayarı", compare: "Çekilen ayar ile taslağı karşılaştırın; gönderme öncesi farkı inceleyin.", externalConfirm: "Bu işlem bağlı provider kaynaklarını güncelleyebilir. Devam edilsin mi?", testOnly: "Test senaryoları dış araç çağrısı yapabilir; yalnızca test ayarlarıyla çalıştırın.", businessHours: "Çalışma saatleri, izinler, personel ve tampon süreleri aynı JSON ayarında tutulur.", confirmMerge: "Birleştirme canlı çağrı davranışını etkileyebilir. Onaylıyor musunuz?", confirmDeploy: "Bu dağıtım canlı çağrı trafiğini değiştirebilir. Yayınlansın mı?", confirmRestore: "Eski ayar yeni sürüm olarak seçilen branch'e yazılacak. Devam edilsin mi?", testReadOnly: "Metin testi sadece sağlayıcının test API'sini çağırır. Gerçek araç etkileri ayrıca onay ister.", fileTypes: "PDF, DOCX, TXT, Markdown, HTML ve EPUB.", selectDocs: "Belgeleri seçin", previewReady: "Ses örneği hazır.", workspace: "Workspace bilgisi", noData: "Bu veri ElevenLabs API anahtarının izinlerinde bulunmuyor.", toolsImpact: "Araç tanımı birden çok ajanla paylaşılabilir.", voiceNote: "Önizleme isteği seçtiğiniz ses ID'siyle sunucu üzerinden gönderilir.", sourceType: "ElevenLabs türü", openIntegrations: "Mevcut sağlayıcı ayarlarına git", externalCalendar: "Google Calendar bağlıysa uygunluk ve rezervasyon birlikte doğrulanır.", safeTest: "Test aracı özel ağ adreslerini ve yönlendirmeleri engeller.", yes: "Evet", no: "Hayır", json: "JSON", selectedTools: "Ajan araç ID listesi JSON'u", assignTools: "Seçili araçları ajana ata", response: "Sağlayıcı yanıtı"
    },
    en: {
      title: "ElevenLabs Voice Workspace", subtitle: "Manage agents, tools and calendars inside OIM.", tenant: "Customer account", refresh: "Refresh", loading: "Loading…", error: "Request failed.", noTenant: "Select a customer first.", noKey: "ElevenLabs API key not found. Add it in Integrations.", agents: "Voice Agents", tools: "Tools", calendar: "Calendar", knowledge: "Knowledge Base", conversations: "Conversations", integrations: "Integrations", analytics: "Analytics", settings: "Settings", connected: "API connection ready", disconnected: "No API key", testConnection: "Test connection", save: "Save", create: "Create", new: "New", name: "Name", tenantAssign: "Assign to OIM customer", selectAgent: "Select an agent", selectTenant: "Select a customer", config: "ElevenLabs agent JSON config", localSave: "Save local draft", pull: "Pull from ElevenLabs", push: "Push to ElevenLabs", clone: "Duplicate", delete: "Delete permanently", confirmDelete: "Permanently delete this ElevenLabs agent?", rawJson: "Enter valid JSON.", createAgent: "Create agent", branch: "Branch / version", branches: "Load branches", createBranch: "Create branch", parentVersion: "Parent version ID", branchName: "Branch name", targetBranch: "Target branch ID", merge: "Merge branch", versionId: "Version ID", restore: "Restore version", deployment: "Traffic allocation JSON", deploy: "Publish live traffic allocation", testJson: "ElevenLabs test JSON", saveTest: "Create test scenario", runTest: "Run selected tests", confirmTools: "I confirm these tests may call tools assigned to this agent.", toolsJson: "Tool config JSON", webhookTest: "Test webhook", addCalendarTools: "Add 10 OIM calendar tools", useAgent: "Assign this tool to an agent", dependents: "Dependent agents", calendarSettings: "Calendar rules JSON", saveSettings: "Save calendar rules", date: "Date", start: "Start time (ISO 8601)", check: "Check availability", slots: "Load open slots", alternatives: "Find alternatives", book: "Create a test appointment", customerName: "Customer name", phone: "Phone", service: "Service", notes: "Notes", duration: "Duration (min)", type: "Source type", content: "Text content", url: "HTTPS page URL", file: "File (up to 20 MiB)", autoSync: "Automatically sync URL content", createDocument: "Add knowledge item", assignDocs: "Attach selected documents to agent", conversation: "Conversation", imported: "Calls imported into OIM", summary: "Summary", transcript: "Transcript", providerKey: "API key", providerModel: "TTS model", voice: "Voice", enable: "Enable integration", keyHint: "Leave empty to keep the saved key.", previewText: "Voice preview text", preview: "Preview selected voice", usage: "Usage and subscription", plan: "Subscription", quota: "Quota / usage", webhookSecret: "ElevenLabs webhook signing secret", webhookUrl: "Webhook URL", saveSecret: "Save signing secret", eventLog: "Sync and webhook events", toolUrl: "Webhook HTTPS URL", method: "HTTP method", headers: "Headers JSON", body: "Request body JSON", selected: "Selected", providerManaged: "Code/MCP capabilities stay in ElevenLabs; OIM does not emulate them.", empty: "No records.", saved: "Saved.", success: "Completed.", confirmDeleteDoc: "Delete this document? Remove it from dependent agents first.", noAgent: "Select an ElevenLabs agent first.", copied: "Copied.", items: "Records", status: "Status", checked: "Last checked", language: "Language", branchId: "Branch ID", id: "ID", actions: "Actions", details: "Details", connectHelp: "You can also save the API key in the existing Integrations page.", localDraft: "Local draft", remoteConfig: "Provider config", compare: "Compare the provider config with the draft and review differences before pushing.", externalConfirm: "This can update provider resources. Continue?", testOnly: "Test scenarios may call external tools; use test configuration only.", businessHours: "Business hours, holidays, staff and buffers are saved in this JSON configuration.", confirmMerge: "Merging may change live call behavior. Continue?", confirmDeploy: "This deployment may change live call traffic. Publish it?", confirmRestore: "The old config will be written as a new version on the selected branch. Continue?", testReadOnly: "Text tests use the provider testing API. External tool effects require a separate confirmation.", fileTypes: "PDF, DOCX, TXT, Markdown, HTML and EPUB.", selectDocs: "Select documents", previewReady: "Voice preview is ready.", workspace: "Workspace information", noData: "This data is unavailable for the current ElevenLabs API key.", toolsImpact: "Tool definitions may be shared across multiple agents.", voiceNote: "The preview request uses the selected voice ID through the server.", sourceType: "ElevenLabs type", openIntegrations: "Open provider settings", externalCalendar: "When Google Calendar is connected, availability and reservations are checked together.", safeTest: "The webhook tester blocks private network addresses and redirects.", yes: "Yes", no: "No", json: "JSON", selectedTools: "Agent tool IDs JSON", assignTools: "Assign selected tools to agent", response: "Provider response"
    },
    ru: {
      title: "ElevenLabs Voice Workspace", subtitle: "Управляйте агентами, инструментами и календарями в OIM.", tenant: "Аккаунт клиента", refresh: "Обновить", loading: "Загрузка…", error: "Не удалось выполнить запрос.", noTenant: "Сначала выберите клиента.", noKey: "Ключ ElevenLabs не найден. Добавьте его во вкладке Integrations.", agents: "Voice Agents", tools: "Tools", calendar: "Calendar", knowledge: "Knowledge Base", conversations: "Conversations", integrations: "Integrations", analytics: "Analytics", settings: "Settings", connected: "API подключён", disconnected: "Нет API-ключа", testConnection: "Проверить подключение", save: "Сохранить", create: "Создать", new: "Новый", name: "Название", tenantAssign: "Привязать к клиенту OIM", selectAgent: "Выберите агента", selectTenant: "Выберите клиента", config: "JSON-конфигурация агента ElevenLabs", localSave: "Сохранить локальный черновик", pull: "Загрузить из ElevenLabs", push: "Отправить в ElevenLabs", clone: "Дублировать", delete: "Удалить навсегда", confirmDelete: "Удалить этого агента ElevenLabs навсегда?", rawJson: "Введите корректный JSON.", createAgent: "Создать агента", branch: "Ветка / версия", branches: "Загрузить ветки", createBranch: "Создать ветку", parentVersion: "ID родительской версии", branchName: "Название ветки", targetBranch: "ID целевой ветки", merge: "Объединить ветки", versionId: "ID версии", restore: "Восстановить версию", deployment: "JSON распределения трафика", deploy: "Опубликовать распределение трафика", testJson: "JSON теста ElevenLabs", saveTest: "Создать тестовый сценарий", runTest: "Запустить выбранные тесты", confirmTools: "Подтверждаю, что тесты могут вызывать инструменты агента.", toolsJson: "JSON-конфигурация инструмента", webhookTest: "Проверить webhook", addCalendarTools: "Добавить 10 календарных инструментов OIM", useAgent: "Назначить инструмент агенту", dependents: "Зависимые агенты", calendarSettings: "JSON правил календаря", saveSettings: "Сохранить правила календаря", date: "Дата", start: "Начало (ISO 8601)", check: "Проверить доступность", slots: "Показать свободные часы", alternatives: "Найти альтернативы", book: "Создать тестовую запись", customerName: "Имя клиента", phone: "Телефон", service: "Услуга", notes: "Примечания", duration: "Длительность (мин)", type: "Тип источника", content: "Текст", url: "HTTPS-ссылка", file: "Файл (до 20 МиБ)", autoSync: "Автоматически обновлять URL", createDocument: "Добавить документ", assignDocs: "Привязать выбранные документы к агенту", conversation: "Разговор", imported: "Звонки, импортированные в OIM", summary: "Сводка", transcript: "Транскрипт", providerKey: "API-ключ", providerModel: "Модель TTS", voice: "Голос", enable: "Включить интеграцию", keyHint: "Оставьте пустым, чтобы сохранить текущий ключ.", previewText: "Текст для озвучивания", preview: "Прослушать выбранный голос", usage: "Использование и подписка", plan: "Подписка", quota: "Лимит / использование", webhookSecret: "Секрет подписи webhook ElevenLabs", webhookUrl: "Адрес webhook", saveSecret: "Сохранить секрет подписи", eventLog: "События синхронизации и webhook", toolUrl: "HTTPS-адрес webhook", method: "HTTP-метод", headers: "JSON заголовков", body: "JSON тела запроса", selected: "Выбрано", providerManaged: "Code/MCP настраиваются в ElevenLabs; OIM не имитирует эти функции.", empty: "Записей нет.", saved: "Сохранено.", success: "Готово.", confirmDeleteDoc: "Удалить документ? Сначала уберите его из зависимых агентов.", noAgent: "Сначала выберите агента ElevenLabs.", copied: "Скопировано.", items: "Записи", status: "Статус", checked: "Последняя проверка", language: "Язык", branchId: "ID ветки", id: "ID", actions: "Действия", details: "Подробности", connectHelp: "API-ключ можно сохранить на существующей странице Integrations.", localDraft: "Локальный черновик", remoteConfig: "Конфигурация провайдера", compare: "Сравните черновик с конфигурацией провайдера перед отправкой.", externalConfirm: "Изменятся ресурсы провайдера. Продолжить?", testOnly: "Тесты могут вызвать внешние инструменты; используйте тестовую конфигурацию.", businessHours: "Часы работы, выходные, сотрудники и буферы настраиваются в этом JSON.", confirmMerge: "Объединение может повлиять на рабочие звонки. Продолжить?", confirmDeploy: "Публикация может изменить обработку звонков. Продолжить?", confirmRestore: "Старая настройка будет записана новой версией в выбранную ветку. Продолжить?", testReadOnly: "Текстовые тесты используют API тестирования провайдера. Вызовы внешних инструментов требуют отдельного подтверждения.", fileTypes: "PDF, DOCX, TXT, Markdown, HTML и EPUB.", selectDocs: "Выберите документы", previewReady: "Аудио готово.", workspace: "Данные workspace", noData: "У текущего API-ключа нет доступа к этим данным.", toolsImpact: "Инструменты могут использоваться несколькими агентами.", voiceNote: "Запрос предпрослушивания использует выбранный voice ID на сервере.", sourceType: "Тип ElevenLabs", openIntegrations: "Открыть настройки провайдера", externalCalendar: "При подключённом Google Calendar занятость проверяется и при поиске, и при бронировании.", safeTest: "Тестер блокирует приватные адреса и перенаправления.", yes: "Да", no: "Нет", json: "JSON", selectedTools: "JSON списка ID инструментов", assignTools: "Назначить выбранные инструменты", response: "Ответ провайдера"
    }
  };

  const liveCopy = {
    tr: { liveTest: "Canlı ajan testi", liveSafety: "Canlı test ElevenLabs kredisi kullanır. Ajanın webhook araçları gerçek sistemlerde işlem yapabilir; staging ajanı ve test takvimi kullanın.", liveConfirm: "Araçların gerçek yan etkileri olabileceğini ve kredi kullanılacağını anlıyorum.", liveStart: "Mikrofonla başlat", liveStop: "Testi bitir", liveEnv: "Ortam", liveStage: "Staging", liveProd: "Production", liveMic: "Mikrofon erişimi gerekiyor.", liveText: "Yazılı mesaj", liveSend: "Gönder", liveReady: "Bağlandı", liveClosed: "Bağlantı kapandı", liveTools: "Araç olayı", liveTranscript: "Canlı transkript", liveAgent: "Ajan", liveUser: "Siz", liveError: "Canlı test başlatılamadı." },
    en: { liveTest: "Live agent test", liveSafety: "Live tests use ElevenLabs credits. Agent webhook tools can change real systems; use a staging agent and test calendar.", liveConfirm: "I understand tools may have real side effects and this test uses credits.", liveStart: "Start with microphone", liveStop: "End test", liveEnv: "Environment", liveStage: "Staging", liveProd: "Production", liveMic: "Microphone access is required.", liveText: "Text message", liveSend: "Send", liveReady: "Connected", liveClosed: "Connection closed", liveTools: "Tool event", liveTranscript: "Live transcript", liveAgent: "Agent", liveUser: "You", liveError: "Could not start the live test." },
    ru: { liveTest: "Тест агента в реальном времени", liveSafety: "Тест использует кредиты ElevenLabs. Webhook-инструменты агента могут изменить реальные данные; используйте staging-агента и тестовый календарь.", liveConfirm: "Понимаю, что инструменты могут изменить данные, а тест использует кредиты.", liveStart: "Начать с микрофоном", liveStop: "Завершить тест", liveEnv: "Среда", liveStage: "Staging", liveProd: "Production", liveMic: "Необходимо разрешить доступ к микрофону.", liveText: "Текстовое сообщение", liveSend: "Отправить", liveReady: "Подключено", liveClosed: "Соединение закрыто", liveTools: "Событие инструмента", liveTranscript: "Транскрипт", liveAgent: "Агент", liveUser: "Вы", liveError: "Не удалось начать тест." }
  };
  const lt = (key) => (liveCopy[root.OIMI18n?.locale] || liveCopy.tr)[key] || key;
  const categoryCopy = {
    tr: { compare: "Düzenleyici ayarlarını provider ile karşılaştır", insert: "Takvim güvenlik kurallarını prompta ekle", same: "Fark bulunamadı.", changed: "Yerel ve provider ayarları arasındaki farklar" },
    en: { compare: "Compare editor with provider", insert: "Add calendar safety rules to prompt", same: "No differences found.", changed: "Differences between local and provider configuration" },
    ru: { compare: "Сравнить редактор с провайдером", insert: "Добавить правила календаря в prompt", same: "Различий нет.", changed: "Различия локальной конфигурации и конфигурации провайдера" }
  };
  const ac = (key) => (agentCopy[root.OIMI18n?.locale] || agentCopy.tr)[key] || key;
  const calendarCopy = {
    tr: { view: "Görünüm", day: "Gün", week: "Hafta", month: "Ay", appointments: "Randevular", loadAppointments: "Takvimi yükle", noAppointments: "Bu dönemde randevu yok.", provider: "Harici takvim", auto: "Otomatik seçim", internal: "Yalnız OIM takvimi", google: "Google Calendar", microsoft: "Microsoft Outlook", department: "Departman", repeat: "Tekrar", single: "Tek sefer", daily: "Her gün", weekly: "Her hafta", repeatCount: "Tekrar sayısı" },
    en: { view: "View", day: "Day", week: "Week", month: "Month", appointments: "Appointments", loadAppointments: "Load calendar", noAppointments: "No appointments in this period.", provider: "External calendar", auto: "Automatic selection", internal: "OIM calendar only", google: "Google Calendar", microsoft: "Microsoft Outlook", department: "Department", repeat: "Repeat", single: "One time", daily: "Daily", weekly: "Weekly", repeatCount: "Occurrences" },
    ru: { view: "Вид", day: "День", week: "Неделя", month: "Месяц", appointments: "Записи", loadAppointments: "Загрузить календарь", noAppointments: "В этом периоде записей нет.", provider: "Внешний календарь", auto: "Автоматический выбор", internal: "Только календарь OIM", google: "Google Calendar", microsoft: "Microsoft Outlook", department: "Отдел", repeat: "Повтор", single: "Один раз", daily: "Ежедневно", weekly: "Еженедельно", repeatCount: "Количество повторов" }
  };
  const ct = (key) => (calendarCopy[root.OIMI18n?.locale] || calendarCopy.tr)[key] || key;
  const voiceCopy = {
    tr: { settings: "Ses ayarları", model: "TTS modeli", voice: "Ses", language: "Ajan dili", stability: "Kararlılık", similarity: "Ses benzerliği", speed: "Konuşma hızı", latency: "Akış gecikmesi optimizasyonu", audioFormat: "Ses çıkış biçimi", style: "Anlatım stili", speakerBoost: "Konuşmacı güçlendirme", pronunciation: "Telaffuz sözlükleri JSON'u", previewText: "Kaydetmeden önce örnek metin", preview: "Seçili sesi dinle", apply: "Ayarları JSON'a uygula", unavailable: "Ses/model listesi yüklenemedi; mevcut değer korunur." },
    en: { settings: "Voice settings", model: "TTS model", voice: "Voice", language: "Agent language", stability: "Stability", similarity: "Similarity", speed: "Speaking speed", latency: "Streaming latency optimization", audioFormat: "Audio output format", style: "Style", speakerBoost: "Speaker boost", pronunciation: "Pronunciation dictionaries JSON", previewText: "Sample text before saving", preview: "Preview selected voice", apply: "Apply settings to JSON", unavailable: "Voice/model list could not be loaded; existing values are preserved." },
    ru: { settings: "Настройки голоса", model: "Модель TTS", voice: "Голос", language: "Язык агента", stability: "Стабильность", similarity: "Сходство голоса", speed: "Скорость речи", latency: "Оптимизация задержки потока", audioFormat: "Формат аудио", style: "Стиль речи", speakerBoost: "Усиление голоса", pronunciation: "JSON словарей произношения", previewText: "Текст для проверки до сохранения", preview: "Прослушать выбранный голос", apply: "Применить настройки к JSON", unavailable: "Список голосов или моделей недоступен; текущие значения сохраняются." }
  };
  const vt = (key) => (voiceCopy[root.OIMI18n?.locale] || voiceCopy.tr)[key] || key;
  const agentCopy = {
    tr: { general: "Genel ayarlar", agentName: "Ajan adı", firstMessage: "İlk mesaj", systemPrompt: "Sistem promptu", llmSettings: "LLM ayarları", llm: "LLM modeli", temperature: "Sıcaklık", maxTokens: "Maksimum token", conversationSettings: "Konuşma ayarları", turnTimeout: "Söz sırası zaman aşımı (sn)", silenceTimeout: "Sessizlik bitiş zaman aşımı (sn)", turnEagerness: "Söz sırası algılama", asrProvider: "ASR sağlayıcısı", keywords: "Tanıma anahtar sözcükleri JSON'u", apply: "Ayarları JSON'a uygula", advanced: "Gelişmiş JSON ayarı", previewSample: "Önizleme metni" },
    en: { general: "General settings", agentName: "Agent name", firstMessage: "First message", systemPrompt: "System prompt", llmSettings: "LLM settings", llm: "LLM model", temperature: "Temperature", maxTokens: "Maximum tokens", conversationSettings: "Conversation settings", turnTimeout: "Turn timeout (sec)", silenceTimeout: "Silence end timeout (sec)", turnEagerness: "Turn detection", asrProvider: "ASR provider", keywords: "Recognition keywords JSON", apply: "Apply settings to JSON", advanced: "Advanced JSON config", previewSample: "Preview text" },
    ru: { general: "Общие настройки", agentName: "Имя агента", firstMessage: "Первое сообщение", systemPrompt: "Системный промпт", llmSettings: "Настройки LLM", llm: "Модель LLM", temperature: "Температура", maxTokens: "Максимум токенов", conversationSettings: "Настройки разговора", turnTimeout: "Тайм-аут реплики (сек.)", silenceTimeout: "Тайм-аут тишины (сек.)", turnEagerness: "Распознавание очереди речи", asrProvider: "Провайдер ASR", keywords: "JSON ключевых слов", apply: "Применить настройки к JSON", advanced: "Расширенная конфигурация JSON", previewSample: "Текст для проверки" }
  };
  const at = (key) => (categoryCopy[root.OIMI18n?.locale] || categoryCopy.tr)[key] || key;
  const toolCopy = {
    tr: { dashboard: "Araç kullanım panosu", sample: "Son alınan kayıtlar", total: "Gözlenen çağrı", successful: "Başarılı", failed: "Hatalı", average: "Ortalama yanıt", lastUsed: "Son kullanım", assigned: "Bağlı ajanlar", enableFor: "Seçili ajanda etkinleştir", disableFor: "Seçili ajanda devre dışı bırak", noExecution: "Henüz kullanım kaydı yok", more: "Daha eski kayıtlar olabilir; bu özet API'nin döndürdüğü son 100 çalıştırmayı kapsar." },
    en: { dashboard: "Tool usage dashboard", sample: "Recent executions", total: "Observed calls", successful: "Successful", failed: "Failed", average: "Average response", lastUsed: "Last used", assigned: "Assigned agents", enableFor: "Enable for selected agent", disableFor: "Disable for selected agent", noExecution: "No executions found", more: "Older records may exist; this summary covers the latest 100 executions returned by the API." },
    ru: { dashboard: "Панель использования инструментов", sample: "Последние вызовы", total: "Наблюдаемые вызовы", successful: "Успешно", failed: "С ошибкой", average: "Среднее время ответа", lastUsed: "Последнее использование", assigned: "Назначенные агенты", enableFor: "Включить для выбранного агента", disableFor: "Отключить для выбранного агента", noExecution: "Вызовов пока нет", more: "Могут быть более ранние записи; сводка показывает последние 100 результатов API." }
  };
  const builderCopy = {
    tr: { builder: "Kodsuz araç oluşturucu", description: "Açıklama", type: "Araç türü", webhook: "Webhook", client: "Client tool", system: "System tool", code: "Code tool", mcp: "MCP tool", endpoint: "HTTPS uç noktası", method: "HTTP yöntemi", providerSchema: "Parametreler, headers ve auth şeması JSON'u", apply: "Görsel alanları JSON'a uygula", hint: "Webhook için ad, açıklama, tür, adres ve yöntemi buradan girin. Parametreler ve kimlik doğrulama alanları ElevenLabs API şemasına göre JSON'da düzenlenir." },
    en: { builder: "No-code tool builder", description: "Description", type: "Tool type", webhook: "Webhook", client: "Client tool", system: "System tool", code: "Code tool", mcp: "MCP tool", endpoint: "HTTPS endpoint", method: "HTTP method", providerSchema: "Parameters, headers and auth schema JSON", apply: "Apply visual fields to JSON", hint: "Enter a webhook name, description, type, endpoint and method here. Edit parameters and authentication in JSON using the schema accepted by the ElevenLabs API. Workspace authentication connections are managed by ElevenLabs." },
    ru: { builder: "Конструктор инструментов без кода", description: "Описание", type: "Тип инструмента", webhook: "Webhook", client: "Client tool", system: "System tool", code: "Code tool", mcp: "MCP tool", endpoint: "HTTPS-адрес", method: "HTTP-метод", providerSchema: "JSON параметров, заголовков и авторизации", apply: "Применить поля к JSON", hint: "Задайте здесь имя, описание, тип, адрес и метод webhook. Параметры и авторизацию настройте в JSON по схеме API ElevenLabs." }
  };
  const bt = (key) => (builderCopy[root.OIMI18n?.locale] || builderCopy.en)[key] || key;
  const tt = (key) => (toolCopy[root.OIMI18n?.locale] || toolCopy.tr)[key] || key;
  const state = { role: "guest", view: location.hash.slice(1) || "vp-agents", tenant: "", agents: [], tools: [], docs: [], voices: [], models: [], llms: [], selectedAgent: "", selectedTool: "", agent: null, local: null, tenants: [], tabLoaded: "", audioUrl: "", agentAudioUrl: "", live: null, toolDashboard: null, cached: {} };
  const tr = (key) => (words[root.OIMI18n?.locale] || words.tr)[key] || words.en[key] || key;
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  const api = async (path, method = "GET", body) => {
    const response = await fetch(path, { method, credentials: "same-origin", headers: body === undefined ? {} : { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
    let data = {};
    try { data = await response.json(); } catch {}
    if (!response.ok) throw Object.assign(new Error(data.error || tr("error")), { data, status: response.status });
    return data;
  };
  const endpoint = (part) => `/api/admin/voice-platform/${part}`;
  const notify = (message, bad = false) => {
    const status = panel.querySelector("#vp-status");
    if (status) { status.textContent = message; status.dataset.state = bad ? "error" : "ok"; }
    const toast = document.querySelector(".toast");
    if (toast) { toast.textContent = message; toast.classList.add("show"); setTimeout(() => toast.classList.remove("show"), 3200); }
  };
  const query = (values) => new URLSearchParams(Object.entries(values).filter(([, value]) => value !== undefined && value !== null && value !== "").map(([key, value]) => [key, String(value)])).toString();
  const value = (selector) => panel.querySelector(selector)?.value ?? "";
  const jsonValue = (selector) => {
    try { return JSON.parse(value(selector)); } catch { throw new Error(tr("rawJson")); }
  };
  const selectedItems = (selector) => [...(panel.querySelector(selector)?.selectedOptions || [])].map((option) => option.value);
  function rootFrame(body) {
    const nav = ["agents", "tools", "calendar", "knowledge", "conversations", "integrations", "analytics", "settings"].map((key) => `<button type="button" class="vp-tab ${state.view === `vp-${key}` ? "active" : ""}" data-vp-view="vp-${key}">${esc(tr(key))}</button>`).join("");
    panel.innerHTML = `<div class="vp-shell"><header class="vp-head"><div><span class="vp-eyebrow">OIM · ELEVENLABS</span><h1>${esc(tr("title"))}</h1><p>${esc(tr("subtitle"))}</p></div><div class="vp-head-actions"><label>${esc(tr("tenant"))}<select id="vp-tenant"><option value="">${esc(tr("selectTenant"))}</option>${state.tenants.map((item) => `<option value="${item.id}" ${String(item.id) === String(state.tenant) ? "selected" : ""}>${esc(item.name)} · #${item.id}</option>`).join("")}</select></label><button class="button outline" id="vp-refresh" type="button">${esc(tr("refresh"))}</button></div></header><div class="vp-status" id="vp-status" role="status" aria-live="polite"></div><nav class="vp-tabs" aria-label="ElevenLabs">${nav}</nav><main class="vp-body">${body}</main><footer class="vp-footer"><span>OIM Voice Platform · TR / EN / RU</span><a href="docs/ELEVENLABS_INTEGRATION.md" target="_blank" rel="noopener">${esc(tr("details"))}: docs</a></footer></div>`;
    if (state.view === "vp-agents") {
      const editor = panel.querySelector(".vp-editor-grid");
      if (editor) {
        const config = state.local?.local || editableAgent(state.agent) || { conversation_config: {} };
        editor.insertAdjacentHTML("beforebegin", agentVoiceSettings(config) + agentCategorySettings(config));
      }
    }
    if (state.view === "vp-tools") {
      const editor = panel.querySelector("#vp-tool-json")?.closest("label");
      if (editor) editor.insertAdjacentHTML("beforebegin", toolBuilderMarkup());
    }
    if (state.view === "vp-calendar") {
      const editor = panel.querySelector("#vp-calendar-settings")?.closest("label");
      const selected = state.cached.calendar?.external_calendar_provider || "auto";
      if (editor) editor.insertAdjacentHTML("afterend", `<label>${esc(ct("provider"))}<select id="vp-calendar-provider">${[["auto", "auto"], ["internal", "internal"], ["google", "google"], ["microsoft", "microsoft"]].map(([id, key]) => `<option value="${id}" ${selected === id ? "selected" : ""}>${esc(ct(key))}</option>`).join("")}</select></label>`);
      const start = panel.querySelector("#vp-calendar-start");
      const availabilityForm = start?.closest(".vp-form-grid");
      if (availabilityForm) availabilityForm.insertAdjacentHTML("beforeend", `<label>${esc(tr("service"))}<input id="vp-calendar-service" maxlength="300"></label><label>${esc(ct("department"))}<input id="vp-calendar-department" maxlength="200"></label>`);
      const dateInput = panel.querySelector("#vp-calendar-date");
      if (dateInput) { dateInput.type = "text"; dateInput.placeholder = "2026-11-30 / tomorrow / this week / earliest available"; }
      const bookButton = panel.querySelector('[data-action="book-appointment"]');
      const bookGrid = bookButton?.closest(".vp-form-grid");
      if (bookGrid) bookGrid.insertAdjacentHTML("beforeend", `<label>${esc(ct("department"))}<input id="vp-book-department" maxlength="200"></label><label>${esc(ct("repeat"))}<select id="vp-book-recurrence"><option value="">${esc(ct("single"))}</option><option value="daily">${esc(ct("daily"))}</option><option value="weekly">${esc(ct("weekly"))}</option></select></label><label>${esc(ct("repeatCount"))}<input id="vp-book-recurrence-count" type="number" min="2" max="52" value="4"></label>`);
    }
    if (state.view === "vp-tools") {
      const grid = panel.querySelector(".vp-grid");
      if (grid) grid.insertAdjacentHTML("afterbegin", `<section class="vp-card vp-wide" id="vp-tool-dashboard">${toolDashboardMarkup()}</section>`);
      const assign = panel.querySelector('[data-action="assign-tools"]');
      if (assign) assign.insertAdjacentHTML("afterend", `<div class="vp-actions"><button class="button outline" type="button" data-action="set-tool-enabled" data-enabled="true">${esc(tt("enableFor"))}</button><button class="button outline" type="button" data-action="set-tool-enabled" data-enabled="false">${esc(tt("disableFor"))}</button></div>`);
    }
    panel.querySelector("#vp-tenant")?.addEventListener("change", async (event) => { state.tenant = event.target.value; state.tabLoaded = ""; await render(); });
    panel.querySelector("#vp-refresh")?.addEventListener("click", () => { state.tabLoaded = ""; render(); });
    panel.querySelectorAll("[data-vp-view]").forEach((button) => button.addEventListener("click", () => root.OIMSetView?.(button.dataset.vpView)));
  }
  function messageBox(text, tone = "info") { return `<div class="vp-note ${tone}">${esc(text)}</div>`; }
  function loadingView() { rootFrame(messageBox(tr("loading"))); }
  function unwrap(data, keys) { for (const key of keys) if (Array.isArray(data?.[key])) return data[key]; return Array.isArray(data) ? data : []; }
  function jsonText(item, keys = []) { if (!item) return "{}"; const base = keys.length ? Object.fromEntries(keys.filter((key) => item[key] !== undefined).map((key) => [key, item[key]])) : item; return JSON.stringify(base, null, 2); }
  function editableAgent(item) { if (!item || typeof item !== "object") return null; return Object.fromEntries(["conversation_config", "platform_settings", "workflow", "name", "tags", "procedures"].filter((key) => item[key] !== undefined).map((key) => [key, item[key]])); }
  async function loadTenants() {
    if (state.tenants.length) return;
    const data = await api("/api/admin/tenants");
    state.tenants = data.items || [];
    if (!state.tenant && state.tenants.length) state.tenant = String(state.tenants[0].id);
  }
  async function loadAgents() { state.agents = unwrap(await api(endpoint("agents")), ["agents"]); }
  async function loadTools() { state.tools = unwrap(await api(endpoint("tools")), ["tools"]); if (!state.tools.some((item) => item.id === state.selectedTool)) state.selectedTool = state.tools[0]?.id || ""; }
  async function loadDocs() { state.docs = unwrap(await api(endpoint("knowledge")), ["documents", "knowledge_base"]); }
  function agentSelect() { return `<label>${esc(tr("selectAgent"))}<select id="vp-agent"><option value="">${esc(tr("selectAgent"))}</option>${state.agents.map((item) => `<option value="${esc(item.agent_id)}" ${item.agent_id === state.selectedAgent ? "selected" : ""}>${esc(item.name || item.agent_id)} · ${esc(item.agent_id)}</option>`).join("")}</select></label>`; }
  async function chooseAgent(id) {
    state.selectedAgent = id;
    state.agent = id ? await api(endpoint(`agents/${encodeURIComponent(id)}`)) : null;
    state.local = id ? await api(endpoint(`agents/${encodeURIComponent(id)}/local`)).catch(() => null) : null;
    await render();
  }
  function agentVoiceSettings(config) {
    const conversation = config?.conversation_config || {}, tts = conversation.tts || {}, agent = conversation.agent || {};
    const makeOptions = (items, idKey, labelKey, selected) => {
      const values = items.map((item) => ({ id: String(item?.[idKey] || ""), label: String(item?.[labelKey] || item?.[idKey] || "") })).filter((item) => item.id);
      if (selected && !values.some((item) => item.id === String(selected))) values.unshift({ id: String(selected), label: String(selected) });
      return values.map((item) => `<option value="${esc(item.id)}" ${item.id === String(selected || "") ? "selected" : ""}>${esc(item.label)} · ${esc(item.id)}</option>`).join("");
    };
    const currentFormat = String(tts.agent_output_audio_format || "pcm_16000");
    const formats = ["pcm_8000", "pcm_16000", "pcm_22050", "pcm_24000", "pcm_44100", "pcm_48000", "ulaw_8000"];
    if (!formats.includes(currentFormat)) formats.unshift(currentFormat);
    const language = String(agent.language || "en");
    const languages = ["en", "tr", "ru"];
    if (!languages.includes(language)) languages.unshift(language);
    const range = (id, label, current, min, max, step) => `<label class="vp-range">${esc(label)} <output id="${id}-value">${Number(current).toFixed(step < 1 ? 2 : 0)}</output><input id="${id}" type="range" min="${min}" max="${max}" step="${step}" value="${esc(current)}"></label>`;
    return `<section class="vp-card vp-wide vp-voice-settings"><div class="vp-card-head"><div><span class="vp-eyebrow">${esc(tr("agents"))}</span><h2>${esc(vt("settings"))}</h2></div></div><div class="vp-form-grid"><label>${esc(vt("model"))}<select id="vp-agent-model"><option value="">—</option>${makeOptions(state.models, "model_id", "name", tts.model_id)}</select></label><label>${esc(vt("voice"))}<select id="vp-agent-voice"><option value="">—</option>${makeOptions(state.voices, "voice_id", "name", tts.voice_id)}</select></label><label>${esc(vt("language"))}<select id="vp-agent-language">${languages.map((item) => `<option value="${esc(item)}" ${item === language ? "selected" : ""}>${esc(item.toUpperCase())}</option>`).join("")}</select></label><label>${esc(vt("audioFormat"))}<select id="vp-agent-audio-format">${formats.map((item) => `<option value="${esc(item)}" ${item === currentFormat ? "selected" : ""}>${esc(item)}</option>`).join("")}</select></label>${range("vp-agent-stability", vt("stability"), Number(tts.stability ?? 0.5), 0, 1, 0.01)}${range("vp-agent-similarity", vt("similarity"), Number(tts.similarity_boost ?? 0.8), 0, 1, 0.01)}${range("vp-agent-speed", vt("speed"), Number(tts.speed ?? 1), 0.7, 1.2, 0.01)}${range("vp-agent-latency", vt("latency"), Number(tts.optimize_streaming_latency ?? 3), 0, 4, 1)}${range("vp-agent-style", vt("style"), Number(tts.style ?? 0), 0, 1, 0.01)}<label class="vp-check"><input id="vp-agent-speaker-boost" type="checkbox" ${tts.use_speaker_boost ? "checked" : ""}>${esc(vt("speakerBoost"))}</label><label class="vp-grow">${esc(vt("pronunciation"))}<textarea id="vp-agent-pronunciation" spellcheck="false">${esc(JSON.stringify(tts.pronunciation_dictionary_locators || [], null, 2))}</textarea></label><label class="vp-grow">${esc(vt("previewText"))}<input id="vp-agent-preview-text" maxlength="500" value="${esc(language === "tr" ? "Merhaba, size nasıl yardımcı olabilirim?" : language === "ru" ? "Здравствуйте, чем я могу помочь?" : "Hello, how can I help you today?")}"></label><button type="button" class="button outline" data-action="agent-voice-preview">${esc(vt("preview"))}</button><audio id="vp-agent-audio" controls hidden></audio><button type="button" class="button secondary" data-action="apply-voice-settings">${esc(vt("apply"))}</button></div>${messageBox(vt("unavailable"))}</section>`;
  }
  function agentCategorySettings(config) {
    const conversation = config?.conversation_config || {}, agent = conversation.agent || {}, prompt = agent.prompt || {}, turn = conversation.turn || {}, asr = conversation.asr || {};
    const llmId = String(prompt.llm || "");
    const llms = state.llms.map((item) => ({ id: String(item.model_id || item.id || item.name || ""), label: String(item.name || item.model_id || item.id || "") })).filter((item) => item.id);
    if (llmId && !llms.some((item) => item.id === llmId)) llms.unshift({ id: llmId, label: llmId });
    return `<section class="vp-card vp-wide"><div class="vp-card-head"><div><span class="vp-eyebrow">${esc(tr("agents"))}</span><h2>${esc(at("general"))} · ${esc(at("llmSettings"))} · ${esc(at("conversationSettings"))}</h2></div></div><div class="vp-form-grid"><label>${esc(at("agentName"))}<input id="vp-agent-name" maxlength="200" value="${esc(config.name || "")}"></label><label>${esc(vt("language"))}<input id="vp-agent-general-language" maxlength="10" value="${esc(agent.language || "en")}"></label><label class="vp-grow">${esc(at("firstMessage"))}<textarea id="vp-agent-first-message" maxlength="4000">${esc(agent.first_message || "")}</textarea></label><label class="vp-grow">${esc(at("systemPrompt"))}<textarea id="vp-agent-system-prompt" maxlength="100000">${esc(prompt.prompt || "")}</textarea></label><button type="button" class="button outline" data-action="apply-agent-general">${esc(at("apply"))}</button></div><details class="vp-details"><summary>${esc(at("llmSettings"))}</summary><div class="vp-form-grid"><label>${esc(at("llm"))}<select id="vp-agent-llm"><option value="">—</option>${llms.map((item) => `<option value="${esc(item.id)}" ${item.id === llmId ? "selected" : ""}>${esc(item.label)}</option>`).join("")}</select></label><label>${esc(at("temperature"))}<input id="vp-agent-temperature" type="number" min="0" max="2" step="0.01" value="${esc(prompt.temperature ?? 0.5)}"></label><label>${esc(at("maxTokens"))}<input id="vp-agent-max-tokens" type="number" min="-1" max="100000" step="1" value="${esc(prompt.max_tokens ?? -1)}"></label><button type="button" class="button outline" data-action="apply-agent-llm">${esc(at("apply"))}</button></div></details><details class="vp-details"><summary>${esc(at("conversationSettings"))}</summary><div class="vp-form-grid"><label>${esc(at("turnTimeout"))}<input id="vp-agent-turn-timeout" type="number" min="0" max="120" step="0.1" value="${esc(turn.turn_timeout ?? 7)}"></label><label>${esc(at("silenceTimeout"))}<input id="vp-agent-silence-timeout" type="number" min="-1" max="3600" step="1" value="${esc(turn.silence_end_call_timeout ?? -1)}"></label><label>${esc(at("turnEagerness"))}<select id="vp-agent-turn-eagerness">${["patient", "normal", "eager"].map((item) => `<option value="${item}" ${item === (turn.turn_eagerness || "normal") ? "selected" : ""}>${item}</option>`).join("")}</select></label><label>${esc(at("asrProvider"))}<input id="vp-agent-asr-provider" maxlength="100" value="${esc(asr.provider || "")}"></label><label class="vp-grow">${esc(at("keywords"))}<textarea id="vp-agent-asr-keywords" spellcheck="false">${esc(JSON.stringify(asr.keywords || [], null, 2))}</textarea></label><button type="button" class="button outline" data-action="apply-agent-conversation">${esc(at("apply"))}</button></div></details><p class="vp-hint">${esc(at("advanced"))}: all provider-supported fields, including dynamic variables, webhooks, guardrails, privacy, data collection and workflows, remain editable in the validated JSON configuration below.</p></section>`;
  }
  function agentsPage() {
    const raw = state.local?.local || editableAgent(state.agent) || { name: "New agent", conversation_config: {} };
    const assignment = state.agent?.oim_tenant_id || state.local?.tenant_id || state.tenant;
    return `<div class="vp-grid"><section class="vp-card vp-wide"><div class="vp-card-head"><div><span class="vp-eyebrow">${esc(tr("agents"))}</span><h2>${esc(tr("actions"))}</h2></div><div class="vp-actions"><button type="button" class="button outline" data-action="new-agent">${esc(tr("new"))}</button><button type="button" class="button outline" data-action="reload-agents">${esc(tr("refresh"))}</button></div></div><div class="vp-row vp-agent-bar">${agentSelect()}<label>${esc(tr("tenantAssign"))}<select id="vp-agent-tenant"><option value="">—</option>${state.tenants.map((item) => `<option value="${item.id}" ${String(item.id) === String(assignment) ? "selected" : ""}>${esc(item.name)} · #${item.id}</option>`).join("")}</select></label><button class="button secondary" type="button" data-action="assign-tenant">${esc(tr("save"))}</button></div><div class="vp-editor-grid"><label class="vp-field vp-grow">${esc(tr("config"))}<textarea id="vp-agent-config" spellcheck="false">${esc(JSON.stringify(raw, null, 2))}</textarea></label><aside class="vp-side-actions"><button class="button outline" type="button" data-action="local-save">${esc(tr("localSave"))}</button><button class="button outline" type="button" data-action="pull-agent">${esc(tr("pull"))}</button><button class="button primary" type="button" data-action="push-agent">${esc(tr("push"))}</button><button class="button outline" type="button" data-action="clone-agent">${esc(tr("clone"))}</button><button class="button danger" type="button" data-action="delete-agent">${esc(tr("delete"))}</button></aside></div>${messageBox(tr("compare"))}<div class="vp-actions"><button type="button" class="button outline" data-action="compare-config">${esc(ac("compare"))}</button><button type="button" class="button outline" data-action="insert-policies">${esc(ac("insert"))}</button></div><pre class="vp-output" id="vp-agent-diff"></pre>${state.selectedAgent ? `<details class="vp-details"><summary>${esc(lt("liveTest"))}</summary><p class="vp-hint">${esc(lt("liveSafety"))}</p><div class="vp-form-grid"><label>${esc(lt("liveEnv"))}<select id="vp-live-environment"><option value="staging">${esc(lt("liveStage"))}</option><option value="production">${esc(lt("liveProd"))}</option></select></label><label class="vp-check"><input id="vp-live-confirm" type="checkbox">${esc(lt("liveConfirm"))}</label><button class="button primary" type="button" data-action="live-start">${esc(lt("liveStart"))}</button><button class="button danger" type="button" data-action="live-stop" disabled>${esc(lt("liveStop"))}</button><label class="vp-grow">${esc(lt("liveText"))}<input id="vp-live-message" maxlength="1000" autocomplete="off"></label><button class="button outline" type="button" data-action="live-send" disabled>${esc(lt("liveSend"))}</button></div><div id="vp-live-log" class="vp-live-log" role="log" aria-live="polite"></div></details>` : ""}<details class="vp-details"><summary>${esc(tr("branch"))}</summary><div class="vp-form-grid"><button class="button outline" type="button" data-action="branches">${esc(tr("branches"))}</button><label>${esc(tr("parentVersion"))}<input id="vp-parent-version"></label><label>${esc(tr("branchName"))}<input id="vp-branch-name"></label><button class="button outline" type="button" data-action="create-branch">${esc(tr("createBranch"))}</button><label>${esc(tr("targetBranch"))}<input id="vp-target-branch"></label><label>${esc(tr("branchId"))}<input id="vp-source-branch"></label><button class="button outline" type="button" data-action="merge-branch">${esc(tr("merge"))}</button><label>${esc(tr("versionId"))}<input id="vp-version-id"></label><label>${esc(tr("targetBranch"))}<input id="vp-restore-branch"></label><button class="button outline" type="button" data-action="restore-version">${esc(tr("restore"))}</button><label class="vp-grow">${esc(tr("deployment"))}<textarea id="vp-deploy-json">[{"branch_id":"main","percentage":100}]</textarea></label><button class="button primary" type="button" data-action="deploy">${esc(tr("deploy"))}</button></div><pre class="vp-output" id="vp-branches-output"></pre></details><details class="vp-details"><summary>${esc(tr("testOnly"))}</summary><div class="vp-form-grid"><label class="vp-grow">${esc(tr("testJson"))}<textarea id="vp-test-json">{\n  "agent_id": "${esc(state.selectedAgent || "agent_id")}",\n  "name": "OIM test"\n}</textarea></label><button class="button outline" type="button" data-action="save-test">${esc(tr("saveTest"))}</button><label class="vp-grow">${esc(tr("selectedTools"))}<textarea id="vp-test-ids">[]</textarea></label><label class="vp-check"><input type="checkbox" id="vp-confirm-tools">${esc(tr("confirmTools"))}</label><button class="button primary" type="button" data-action="run-tests">${esc(tr("runTest"))}</button></div></details></section></div>`;
  }
  function toolsPage() {
    const ids = state.tools.map((item) => item.id).filter(Boolean);
    return `<div class="vp-grid"><section class="vp-card"><div class="vp-card-head"><div><span class="vp-eyebrow">${esc(tr("tools"))}</span><h2>${esc(tr("items"))}</h2></div><button class="button outline" data-action="reload-tools" type="button">${esc(tr("refresh"))}</button></div><div class="vp-list">${state.tools.length ? state.tools.map((tool) => `<button class="vp-list-row" type="button" data-tool="${esc(tool.id)}"><span><strong>${esc(tool.name || tool.tool_config?.name || "Tool")}</strong><small>${esc(tool.tool_config?.type || tool.type || "provider")}</small></span><code>${esc(tool.id)}</code><i>›</i></button>`).join("") : `<p class="vp-empty">${esc(tr("empty"))}</p>`}</div>${messageBox(tr("providerManaged"))}</section><section class="vp-card"><div class="vp-card-head"><div><span class="vp-eyebrow">${esc(tr("actions"))}</span><h2>Webhook tool</h2></div></div><div class="vp-actions"><button class="button outline" type="button" data-action="duplicate-tool">${esc(tr("clone"))}</button><button class="button outline" type="button" data-action="load-tool-executions">${esc(tr("usage"))}</button></div><label class="vp-field">${esc(tr("toolsJson"))}<textarea id="vp-tool-json" spellcheck="false">{\n  "type": "webhook",\n  "name": "example_lookup",\n  "description": "Look up approved public information",\n  "api_schema": {\n    "url": "https://example.org/api/lookup",\n    "method": "POST",\n    "request_body_schema": {"type":"object","properties":{},"required":[],"additionalProperties":false}\n  }\n}</textarea></label><div class="vp-actions"><button class="button primary" type="button" data-action="create-tool">${esc(tr("create"))}</button><button class="button outline" type="button" data-action="save-tool">${esc(tr("save"))}</button><button class="button danger" type="button" data-action="delete-tool">${esc(tr("delete"))}</button></div><details class="vp-details"><summary>${esc(tr("webhookTest"))}</summary><div class="vp-form-grid"><label>${esc(tr("toolUrl"))}<input id="vp-test-url" type="url" placeholder="https://example.org/api"></label><label>${esc(tr("method"))}<select id="vp-test-method"><option>POST</option><option>GET</option><option>PUT</option><option>PATCH</option><option>DELETE</option></select></label><label>${esc(tr("headers"))}<textarea id="vp-test-headers">{}</textarea></label><label>${esc(tr("body"))}<textarea id="vp-test-body">{}</textarea></label><button class="button outline" type="button" data-action="test-tool">${esc(tr("webhookTest"))}</button></div>${messageBox(tr("safeTest"))}<pre class="vp-output" id="vp-tool-output"></pre></details><details class="vp-details"><summary>${esc(tr("useAgent"))}</summary>${agentSelect()}<label>${esc(tr("selectedTools"))}<textarea id="vp-tool-ids">${esc(JSON.stringify(ids, null, 2))}</textarea></label><button class="button secondary" type="button" data-action="assign-tools">${esc(tr("assignTools"))}</button>${messageBox(tr("toolsImpact"))}</details><div class="vp-card-head"><h3>${esc(tr("calendar"))}</h3></div><button class="button secondary" type="button" data-action="provision-calendar">${esc(tr("addCalendarTools"))}</button></section></div>`;
  }
  function calendarPage() {
    const settings = state.cached.calendar || { timezone: "Europe/Istanbul", duration_minutes: 60, buffer_minutes: 0, slot_interval_minutes: 30, alternative_window_minutes: 60, min_notice_minutes: 60, max_days_ahead: 180, business_hours: { mon: [["09:00", "17:00"]], tue: [["09:00", "17:00"]], wed: [["09:00", "17:00"]], thu: [["09:00", "17:00"]], fri: [["09:00", "17:00"]], sat: [], sun: [] }, holidays: [], blocked_intervals: [], staff: [] };
    return `<div class="vp-grid"><section class="vp-card"><span class="vp-eyebrow">${esc(tr("calendar"))}</span><h2>${esc(tr("calendarSettings"))}</h2><label class="vp-field"><textarea id="vp-calendar-settings" spellcheck="false">${esc(JSON.stringify(settings, null, 2))}</textarea></label><button class="button primary" type="button" data-action="save-calendar">${esc(tr("saveSettings"))}</button>${messageBox(tr("businessHours"))}${messageBox(tr("externalCalendar"))}</section><section class="vp-card"><span class="vp-eyebrow">${esc(tr("check"))}</span><h2>${esc(tr("date"))} &amp; ${esc(tr("start"))}</h2><div class="vp-form-grid"><label>${esc(tr("start"))}<input id="vp-calendar-start" type="datetime-local"></label><label>${esc(tr("duration"))}<input id="vp-duration" type="number" min="5" max="480" value="60"></label><button class="button outline" type="button" data-action="check-availability">${esc(tr("check"))}</button><label>${esc(tr("date"))}<input id="vp-calendar-date" type="date"></label><button class="button outline" type="button" data-action="load-slots">${esc(tr("slots"))}</button><button class="button outline" type="button" data-action="find-alternatives">${esc(tr("alternatives"))}</button></div><pre id="vp-calendar-result" class="vp-output"></pre><details class="vp-details"><summary>${esc(tr("book"))}</summary><div class="vp-form-grid"><label>${esc(tr("customerName"))}<input id="vp-book-name"></label><label>${esc(tr("phone"))}<input id="vp-book-phone" autocomplete="off"></label><label>${esc(tr("service"))}<input id="vp-book-service"></label><label>${esc(tr("notes"))}<input id="vp-book-notes"></label><button class="button primary" type="button" data-action="book-appointment">${esc(tr("book"))}</button></div></details></section><section class="vp-card vp-wide"><div class="vp-card-head"><div><span class="vp-eyebrow">${esc(tr("calendar"))}</span><h2>${esc(ct("appointments"))}</h2></div></div><div class="vp-form-grid"><label>${esc(ct("view"))}<select id="vp-calendar-view"><option value="day">${esc(ct("day"))}</option><option value="week">${esc(ct("week"))}</option><option value="month">${esc(ct("month"))}</option></select></label><label>${esc(tr("date"))}<input id="vp-calendar-date-view" type="date"></label><button class="button outline" type="button" data-action="load-appointments">${esc(ct("loadAppointments"))}</button></div><div id="vp-calendar-appointments" class="vp-list"><p class="vp-empty">${esc(ct("noAppointments"))}</p></div></section></div>`;
  }
  function knowledgePage() {
    const opts = state.docs.map((doc) => `<option value="${esc(doc.id)}" data-type="${esc(doc.type || doc.source_type || "text")}">${esc(doc.name || doc.id)} · ${esc(doc.type || doc.source_type || "doc")}</option>`).join("");
    return `<div class="vp-grid"><section class="vp-card"><div class="vp-card-head"><div><span class="vp-eyebrow">${esc(tr("knowledge"))}</span><h2>${esc(tr("items"))}</h2></div><button class="button outline" type="button" data-action="reload-docs">${esc(tr("refresh"))}</button></div><div class="vp-list">${state.docs.length ? state.docs.map((doc) => `<div class="vp-list-row"><span><strong>${esc(doc.name || doc.id)}</strong><small>${esc(doc.type || doc.source_type || "document")}</small></span><code>${esc(doc.id)}</code><button class="button danger small" type="button" data-action="delete-doc" data-id="${esc(doc.id)}">${esc(tr("delete"))}</button></div>`).join("") : `<p class="vp-empty">${esc(tr("empty"))}</p>`}</div><details class="vp-details" open><summary>${esc(tr("createDocument"))}</summary><div class="vp-form-grid"><label>${esc(tr("type"))}<select id="vp-doc-type"><option value="text">text</option><option value="url">url</option><option value="file">file</option></select></label><label>${esc(tr("name"))}<input id="vp-doc-name" maxlength="200"></label><label class="vp-doc-text vp-grow">${esc(tr("content"))}<textarea id="vp-doc-content"></textarea></label><label class="vp-doc-url">${esc(tr("url"))}<input id="vp-doc-url" type="url"></label><label class="vp-doc-file">${esc(tr("file"))}<input id="vp-doc-file" type="file" accept=".pdf,.docx,.txt,.md,.html,.epub"></label><label class="vp-doc-url vp-check"><input type="checkbox" id="vp-doc-auto">${esc(tr("autoSync"))}</label><button class="button primary" type="button" data-action="create-doc">${esc(tr("createDocument"))}</button></div><p class="vp-hint">${esc(tr("fileTypes"))}</p></details></section><section class="vp-card"><span class="vp-eyebrow">${esc(tr("agents"))}</span><h2>${esc(tr("assignDocs"))}</h2>${agentSelect()}<label class="vp-field">${esc(tr("selectDocs"))}<select id="vp-doc-select" multiple size="9">${opts}</select></label><button class="button secondary" type="button" data-action="assign-docs">${esc(tr("assignDocs"))}</button><pre id="vp-doc-result" class="vp-output"></pre></section></div>`;
  }
  function conversationsPage() {
    const items = state.cached.conversations || [];
    const imported = state.cached.imported || [];
    return `<div class="vp-grid"><section class="vp-card"><div class="vp-card-head"><div><span class="vp-eyebrow">${esc(tr("conversations"))}</span><h2>${esc(tr("conversation"))}</h2></div><button class="button outline" type="button" data-action="reload-conversations">${esc(tr("refresh"))}</button></div><div class="vp-list">${items.length ? items.map((item) => `<button class="vp-list-row" type="button" data-conversation="${esc(item.conversation_id)}"><span><strong>${esc(item.conversation_id)}</strong><small>${esc(item.status || "")} · ${esc(item.agent_id || "")}</small></span><span>${esc(item.call_duration_secs ?? "—")}s</span><i>›</i></button>`).join("") : `<p class="vp-empty">${esc(tr("empty"))}</p>`}</div><pre class="vp-output" id="vp-conversation-output"></pre></section><section class="vp-card"><span class="vp-eyebrow">${esc(tr("imported"))}</span><h2>${esc(tr("summary"))}</h2><div class="vp-list">${imported.length ? imported.map((item) => `<button class="vp-list-row" type="button" data-imported="${esc(item.conversation_id)}"><span><strong>${esc(item.conversation_id)}</strong><small>${esc(item.status)} · ${esc(item.duration_seconds || 0)}s</small></span><span>${esc(item.language || "")}</span><i>›</i></button>`).join("") : `<p class="vp-empty">${esc(tr("empty"))}</p>`}</div><pre class="vp-output" id="vp-imported-output"></pre></section></div>`;
  }
  function integrationsPage() {
    const status = state.cached.status || {};
    const config = state.cached.provider || {};
    const voices = state.voices.map((voice) => `<option value="${esc(voice.voice_id)}" ${voice.voice_id === config.voice_id ? "selected" : ""}>${esc(voice.name)} · ${esc(voice.voice_id)}</option>`).join("");
    const currentVoice = config.voice_id && !state.voices.some((voice) => voice.voice_id === config.voice_id) ? `<option value="${esc(config.voice_id)}" selected>${esc(config.voice_id)}</option>` : "";
    return `<div class="vp-grid"><section class="vp-card"><span class="vp-eyebrow">${esc(tr("integrations"))}</span><h2>${esc(status.configured ? tr("connected") : tr("disconnected"))}</h2><p>${esc(tr("connectHelp"))}</p><form id="vp-provider-form" class="vp-form-grid"><label>${esc(tr("providerKey"))}<input id="vp-api-key" type="password" autocomplete="new-password" maxlength="4096" placeholder="${esc(status.masked || tr("keyHint"))}"></label><label>${esc(tr("providerModel"))}<input id="vp-model" maxlength="100" value="${esc(config.model || "eleven_flash_v2_5")}"></label><label>${esc(tr("voice"))}<select id="vp-voice"><option value="">—</option>${currentVoice}${voices}</select></label><label class="vp-check"><input id="vp-enabled" type="checkbox" ${config.enabled ? "checked" : ""}>${esc(tr("enable"))}</label><button class="button primary" type="submit">${esc(tr("save"))}</button><button class="button outline" type="button" data-action="connection-test">${esc(tr("testConnection"))}</button><a class="button outline" href="#integrations" data-open-integrations>${esc(tr("openIntegrations"))}</a></form><p class="vp-hint">${esc(tr("voiceNote"))}</p><div class="vp-form-grid"><label>${esc(tr("previewText"))}<input id="vp-preview-text" maxlength="500" value="Hello, how can I help you today?"></label><button class="button outline" type="button" data-action="voice-preview">${esc(tr("preview"))}</button><audio id="vp-audio" controls hidden></audio></div><pre class="vp-output" id="vp-integration-result"></pre></section><section class="vp-card"><span class="vp-eyebrow">${esc(tr("workspace"))}</span><h2>${esc(tr("usage"))}</h2><pre id="vp-analytics-summary" class="vp-output">${esc(JSON.stringify(state.cached.analytics || {}, null, 2))}</pre><div class="vp-actions"><button class="button outline" type="button" data-action="load-voices">${esc(tr("voice"))}</button><button class="button outline" type="button" data-action="load-models">${esc(tr("providerModel"))}</button><button class="button outline" type="button" data-action="sync-all">${esc(tr("refresh"))}</button></div><p class="vp-hint">${esc(tr("noData"))}</p></section></div>`;
  }
  function analyticsPage() {
    const value = state.cached.analytics || {};
    const subscription = value.subscription || {};
    return `<div class="vp-grid vp-kpis"><article class="vp-stat"><span>${esc(tr("plan"))}</span><strong>${esc(subscription.tier || subscription.plan || "—")}</strong></article><article class="vp-stat"><span>${esc(tr("quota"))}</span><strong>${esc(subscription.character_count ?? subscription.character_limit ?? "—")} / ${esc(subscription.character_limit ?? "—")}</strong></article><article class="vp-stat"><span>${esc(tr("status"))}</span><strong>${esc(state.cached.status?.check_status || "—")}</strong></article><article class="vp-stat"><span>${esc(tr("items"))}</span><strong>${esc(state.cached.agents?.length ?? state.agents.length)}</strong></article><section class="vp-card vp-wide"><div class="vp-card-head"><div><span class="vp-eyebrow">ElevenLabs</span><h2>${esc(tr("usage"))}</h2></div><button class="button outline" type="button" data-action="load-analytics">${esc(tr("refresh"))}</button></div><pre class="vp-output">${esc(JSON.stringify(value, null, 2))}</pre></section></div>`;
  }
  function settingsPage() {
    const status = state.cached.status || {};
    return `<div class="vp-grid"><section class="vp-card"><span class="vp-eyebrow">${esc(tr("settings"))}</span><h2>${esc(tr("webhookUrl"))}</h2><label>${esc(tr("webhookUrl"))}<input readonly value="${esc(status.public_webhook_url || "")}"></label><label class="vp-field">${esc(tr("webhookSecret"))}<input id="vp-webhook-secret" type="password" maxlength="500" autocomplete="new-password" placeholder="${status.webhook_configured ? "••••••••" : ""}"></label><button class="button primary" type="button" data-action="save-webhook-secret">${esc(tr("saveSecret"))}</button><p class="vp-hint">HMAC-SHA256 signature is verified before OIM imports post-call transcripts.</p></section><section class="vp-card"><div class="vp-card-head"><div><span class="vp-eyebrow">${esc(tr("eventLog"))}</span><h2>${esc(tr("items"))}</h2></div><button class="button outline" type="button" data-action="load-events">${esc(tr("refresh"))}</button></div><div class="vp-list">${(state.cached.events || []).map((event) => `<div class="vp-list-row"><span><strong>${esc(event.action)}</strong><small>${esc(event.message)}</small></span><span class="vp-pill" data-state="${esc(event.status)}">${esc(event.status)}</span></div>`).join("") || `<p class="vp-empty">${esc(tr("empty"))}</p>`}</div></section></div>`;
  }
  const renderers = { "vp-agents": agentsPage, "vp-tools": toolsPage, "vp-calendar": calendarPage, "vp-knowledge": knowledgePage, "vp-conversations": conversationsPage, "vp-integrations": integrationsPage, "vp-analytics": analyticsPage, "vp-settings": settingsPage };
  async function loadTab() {
    const view = state.view;
    if (view === "vp-agents") {
      await loadAgents();
      const [voices, models, llms] = await Promise.allSettled([api(endpoint("voices?page_size=100")), api(endpoint("models")), api(endpoint("llms"))]);
      state.voices = voices.status === "fulfilled" ? unwrap(voices.value, ["voices"]) : [];
      state.models = models.status === "fulfilled" ? unwrap(models.value, ["models"]) : [];
      state.llms = llms.status === "fulfilled" ? unwrap(llms.value, ["models", "llms"]) : [];
    }
    if (view === "vp-tools") { await loadTools(); if (state.selectedTool && state.toolDashboard?.id !== state.selectedTool) await loadToolDashboard(state.selectedTool); }
    if (view === "vp-knowledge") await loadDocs();
    if (view === "vp-calendar" && state.tenant) { const data = await api(endpoint(`calendar?${query({ tenant_id: state.tenant })}`)); state.cached.calendar = data.settings; }
    if (view === "vp-integrations" || view === "vp-analytics") {
      const [statusResult, providersResult, analyticsResult] = await Promise.allSettled([api(endpoint("status")), api("/api/admin/providers"), api(endpoint("analytics"))]);
      state.cached.status = statusResult.status === "fulfilled" ? statusResult.value : {};
      state.cached.provider = providersResult.status === "fulfilled" ? providersResult.value.items?.find((item) => item.provider === "elevenlabs") || {} : {};
      state.cached.analytics = analyticsResult.status === "fulfilled" ? analyticsResult.value : { error: analyticsResult.reason?.message || tr("noData") };
      state.cached.agents = state.agents;
      try { state.voices = unwrap(await api(endpoint("voices?page_size=100")), ["voices"]); } catch {}
    }
    if (view === "vp-settings") { state.cached.status = await api(endpoint("status")); state.cached.events = (await api(endpoint("events"))).items || []; }
    if (view === "vp-conversations") {
      state.cached.conversations = unwrap(await api(endpoint("conversations?page_size=100")), ["conversations"]);
      state.cached.imported = state.tenant ? (await api(endpoint(`imported-conversations?tenant_id=${encodeURIComponent(state.tenant)}`))).items || [] : [];
    }
    if (view === "vp-tools" && !state.agents.length) await loadAgents();
    if (view === "vp-knowledge" && !state.agents.length) await loadAgents();
  }
  async function render() {
    if (state.role !== "admin" || !renderers[state.view]) return;
    loadingView();
    try { await loadTenants(); await loadTab(); rootFrame(renderers[state.view]()); }
    catch (error) { rootFrame(messageBox(error.message || tr("error"), "error")); }
  }
  function appendLiveLog(label, text) {
    const log = panel.querySelector("#vp-live-log");
    if (!log) return;
    const row = document.createElement("div");
    row.className = "vp-live-entry";
    row.textContent = `${label}: ${String(text || "").slice(0, 4000)}`;
    log.append(row);
    while (log.childElementCount > 200) log.firstElementChild.remove();
    log.scrollTop = log.scrollHeight;
  }
  function sendLiveAudio(live, samples) {
    if (!live.inputReady || live.socket?.readyState !== WebSocket.OPEN || !samples.length) return;
    const format = live.inputFormat || "pcm_16000";
    const pcmRate = /^pcm_(8000|16000|22050|24000|44100|48000)$/.exec(format);
    const mulaw = format === "ulaw_8000";
    if (!pcmRate && !mulaw) { appendLiveLog(lt("liveError"), `Unsupported input audio format: ${format}`); live.inputReady = false; return; }
    const rate = mulaw ? 8000 : Number(pcmRate[1]);
    const step = live.audioContext.sampleRate / rate;
    const count = Math.max(1, Math.floor(samples.length / step));
    const bytes = new Uint8Array(count * (mulaw ? 1 : 2));
    const view = mulaw ? null : new DataView(bytes.buffer);
    for (let i = 0; i < count; i++) {
      const position = i * step, low = Math.floor(position), high = Math.min(low + 1, samples.length - 1);
      const value = Math.max(-1, Math.min(1, samples[low] + (samples[high] - samples[low]) * (position - low)));
      const sample = Math.round(value < 0 ? value * 32768 : value * 32767);
      if (mulaw) {
        let magnitude = Math.min(32635, Math.abs(sample)), exponent = 7;
        magnitude += 0x84;
        for (let mask = 0x4000; exponent > 0 && (magnitude & mask) === 0; mask >>= 1) exponent--;
        const sign = sample < 0 ? 0x80 : 0;
        bytes[i] = (~(sign | (exponent << 4) | ((magnitude >> (exponent + 3)) & 0x0f))) & 0xff;
      } else view.setInt16(i * 2, sample, true);
    }
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += 0x8000) binary += String.fromCharCode(...bytes.subarray(offset, Math.min(offset + 0x8000, bytes.length)));
    live.socket.send(JSON.stringify({ user_audio_chunk: btoa(binary) }));
  }
  function playLiveAudio(live, encoded) {
    const format = live.outputFormat || "pcm_16000";
    const pcmRate = /^pcm_(\d+)$/.exec(format);
    const mulaw = format === "ulaw_8000";
    if (!pcmRate && !mulaw) { appendLiveLog(lt("liveError"), `Unsupported output audio format: ${format}`); return; }
    const raw = atob(encoded || ""), rate = mulaw ? 8000 : Number(pcmRate[1]);
    const samples = new Float32Array(mulaw ? raw.length : Math.floor(raw.length / 2));
    if (mulaw) {
      for (let i = 0; i < raw.length; i++) {
        const value = (~raw.charCodeAt(i)) & 255, sign = value & 128 ? -1 : 1, exponent = (value >> 4) & 7, mantissa = value & 15;
        samples[i] = sign * ((((mantissa << 3) + 0x84) << exponent) - 0x84) / 32768;
      }
    } else {
      const bytes = Uint8Array.from(raw, (character) => character.charCodeAt(0)), view = new DataView(bytes.buffer);
      for (let i = 0; i < samples.length; i++) samples[i] = view.getInt16(i * 2, true) / 32768;
    }
    if (!samples.length) return;
    const buffer = live.audioContext.createBuffer(1, samples.length, rate);
    buffer.copyToChannel(samples, 0);
    const source = live.audioContext.createBufferSource(); source.buffer = buffer; source.connect(live.audioContext.destination);
    live.sources.add(source); source.onended = () => live.sources.delete(source);
    const startAt = Math.max(live.audioContext.currentTime, live.nextAudioTime);
    source.start(startAt); live.nextAudioTime = startAt + buffer.duration;
  }
  function handleLiveMessage(live, message) {
    if (message.type === "ping") {
      setTimeout(() => { if (live.socket?.readyState === WebSocket.OPEN) live.socket.send(JSON.stringify({ type: "pong", event_id: message.ping_event?.event_id })); }, Math.max(0, Number(message.ping_event?.ping_ms) || 0));
    } else if (message.type === "conversation_initiation_metadata") {
      const metadata = message.conversation_initiation_metadata_event || {};
      live.conversationId = metadata.conversation_id || "";
      live.inputFormat = metadata.user_input_audio_format || "pcm_16000";
      live.inputReady = /^(pcm_(8000|16000|22050|24000|44100|48000)|ulaw_8000)$/.test(live.inputFormat);
      live.outputFormat = metadata.agent_output_audio_format || "pcm_16000";
      appendLiveLog(lt("liveReady"), `${live.conversationId} · ${metadata.user_input_audio_format || ""} → ${live.outputFormat}`);
      if (!live.inputReady) appendLiveLog(lt("liveError"), `Unsupported input audio format: ${live.inputFormat}`);
    } else if (message.type === "user_transcript") {
      appendLiveLog(lt("liveUser"), message.user_transcription_event?.user_transcript);
    } else if (message.type === "agent_response") {
      appendLiveLog(lt("liveAgent"), message.agent_response_event?.agent_response);
    } else if (message.type === "audio") {
      playLiveAudio(live, message.audio_event?.audio_base_64);
    } else if (message.type === "interruption") {
      for (const source of live.sources) { try { source.stop(); } catch {} }
      live.sources.clear(); live.nextAudioTime = live.audioContext.currentTime;
    } else if (message.type === "client_tool_call") {
      appendLiveLog(lt("liveTools"), JSON.stringify(message.client_tool_call || message));
      const call = message.client_tool_call || {};
      if (call.tool_call_id && live.socket?.readyState === WebSocket.OPEN) live.socket.send(JSON.stringify({ type: "client_tool_result", tool_call_id: call.tool_call_id, is_error: true, result: "Client tools are not executed by the OIM live test." }));
    } else if (["agent_tool_request", "agent_tool_response", "agent_tool_response_full_payload", "mcp_tool_call", "mcp_connection_status", "client_error", "guardrail_triggered", "queue_status"].includes(message.type)) {
      appendLiveLog(lt("liveTools"), JSON.stringify(message));
    }
  }
  async function stopLive(closeSocket = true) {
    const live = state.live;
    if (!live) return;
    state.live = null;
    if (closeSocket && live.socket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(live.socket.readyState)) live.socket.close();
    try { live.processor?.disconnect(); live.microphone?.disconnect(); live.mute?.disconnect(); } catch {}
    live.stream?.getTracks().forEach((track) => track.stop());
    for (const source of live.sources || []) { try { source.stop(); } catch {} }
    try { await live.audioContext?.close(); } catch {}
    const start = panel.querySelector('[data-action="live-start"]'), stop = panel.querySelector('[data-action="live-stop"]'), send = panel.querySelector('[data-action="live-send"]');
    if (start) start.disabled = false;
    if (stop) stop.disabled = true;
    if (send) send.disabled = true;
  }
  async function startLive() {
    if (!state.selectedAgent) throw new Error(tr("noAgent"));
    if (!panel.querySelector("#vp-live-confirm")?.checked) throw new Error(lt("liveConfirm"));
    if (!navigator.mediaDevices?.getUserMedia || !window.AudioContext) throw new Error(lt("liveMic"));
    await stopLive();
    const live = { socket: null, stream: null, audioContext: null, microphone: null, processor: null, mute: null, sources: new Set(), nextAudioTime: 0, inputFormat: "pcm_16000", inputReady: false, outputFormat: "pcm_16000" };
    state.live = live;
    try {
      live.audioContext = new AudioContext();
      await live.audioContext.resume();
      live.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      const data = await api(endpoint(`conversation-signed-url?${query({ agent_id: state.selectedAgent })}`));
      const signedUrl = new URL(data.signed_url);
      signedUrl.searchParams.set("environment", value("#vp-live-environment") || "staging");
      live.socket = new WebSocket(signedUrl.toString());
      live.socket.onopen = () => {
        if (state.live !== live) return;
        live.socket.send(JSON.stringify({ type: "conversation_initiation_client_data" }));
        live.microphone = live.audioContext.createMediaStreamSource(live.stream);
        live.processor = live.audioContext.createScriptProcessor(2048, 1, 1);
        live.mute = live.audioContext.createGain(); live.mute.gain.value = 0;
        live.processor.onaudioprocess = (event) => sendLiveAudio(live, event.inputBuffer.getChannelData(0));
        live.microphone.connect(live.processor); live.processor.connect(live.mute); live.mute.connect(live.audioContext.destination);
        const start = panel.querySelector('[data-action="live-start"]'), stop = panel.querySelector('[data-action="live-stop"]'), send = panel.querySelector('[data-action="live-send"]');
        if (start) start.disabled = true; if (stop) stop.disabled = false; if (send) send.disabled = false;
      };
      live.socket.onmessage = (event) => { try { handleLiveMessage(live, JSON.parse(event.data)); } catch (error) { appendLiveLog(lt("liveError"), error.message); } };
      live.socket.onerror = () => appendLiveLog(lt("liveError"), "WebSocket connection error");
      live.socket.onclose = () => { if (state.live === live) { appendLiveLog(lt("liveClosed"), live.conversationId || ""); stopLive(false); } };
    } catch (error) {
      await stopLive();
      throw error;
    }
  }
  function sendLiveText() {
    const live = state.live, input = panel.querySelector("#vp-live-message"), text = input?.value.trim() || "";
    if (!live || live.socket?.readyState !== WebSocket.OPEN) throw new Error(lt("liveClosed"));
    if (!text) return;
    live.socket.send(JSON.stringify({ type: "user_message", text }));
    appendLiveLog(lt("liveUser"), text); input.value = "";
  }
  function compareConfigs(local, remote) {
    const changes = [];
    const secretKey = /(?:api[_-]?key|token|secret|password|authorization|credential)/i;
    function visit(left, right, path) {
      if (changes.length >= 100) return;
      if (left && right && typeof left === "object" && typeof right === "object" && !Array.isArray(left) && !Array.isArray(right)) {
        for (const key of [...new Set([...Object.keys(left), ...Object.keys(right)])].sort()) visit(left[key], right[key], path ? `${path}.${key}` : key);
        return;
      }
      if (JSON.stringify(left) === JSON.stringify(right)) return;
      const key = path.split(".").at(-1) || "";
      if (secretKey.test(key)) changes.push({ path: path || "$", local: left ? "[configured]" : "[empty]", provider: right ? "[configured]" : "[empty]" });
      else changes.push({ path: path || "$", local: left === undefined ? "[missing]" : left, provider: right === undefined ? "[missing]" : right });
    }
    visit(local, remote, "");
    return changes;
  }
  const calendarPolicy = `<!-- OIM_CALENDAR_POLICY_START -->\nOIM calendar and customer-data rules:\n- Use get_current_datetime and the assigned OIM calendar timezone; never guess the current date or time. If a date expression is ambiguous, ask the customer to clarify it.\n- Check availability before saying a requested time is open. When it is busy, call find_alternative_slots and offer only returned options.\n- Get the customer's explicit confirmation of the service, date, time, and timezone before calling book_appointment.\n- Confirm a booking, cancellation, or reschedule only after the corresponding tool returns success=true. Recheck availability when moving a booking.\n- Verify the caller's phone number before finding, changing, or cancelling an appointment. Never disclose another customer's information.\n- Do not read JSON, tool errors, internal IDs, or technical details to the customer. If a tool fails, explain that the action was not completed.\n- Reply in the customer's language and do not invent business facts.\n<!-- OIM_CALENDAR_POLICY_END -->`;
  function getSelectedTool() { return state.tools.find((item) => item.id === state.selectedTool); }
  function toolBuilderMarkup() {
    const selected = getSelectedTool();
    const config = selected?.tool_config || selected || { type: "webhook", name: "example_lookup", description: "Look up approved public information", api_schema: { url: "https://example.org/api/lookup", method: "POST", request_body_schema: { type: "object", properties: {}, required: [], additionalProperties: false } } };
    const schema = { ...(config.api_schema || {}) }, endpointUrl = schema.url || "", method = schema.method || "POST";
    delete schema.url; delete schema.method;
    return `<details class="vp-details" open><summary>${esc(bt("builder"))}</summary><div class="vp-form-grid"><label>${esc(tr("name"))}<input id="vp-tool-name" maxlength="100" value="${esc(config.name || "")}"></label><label>${esc(bt("description"))}<input id="vp-tool-description" maxlength="1000" value="${esc(config.description || "")}"></label><label>${esc(bt("type"))}<select id="vp-tool-type">${["webhook", "client", "system", "code", "mcp"].map((type) => `<option value="${type}" ${config.type === type ? "selected" : ""}>${esc(bt(type))}</option>`).join("")}</select></label><label>${esc(bt("endpoint"))}<input id="vp-tool-url" type="url" value="${esc(endpointUrl)}" placeholder="https://example.org/api"></label><label>${esc(bt("method"))}<select id="vp-tool-method">${["GET", "POST", "PUT", "PATCH", "DELETE"].map((verb) => `<option ${method === verb ? "selected" : ""}>${verb}</option>`).join("")}</select></label><label class="vp-field vp-grow">${esc(bt("providerSchema"))}<textarea id="vp-tool-schema" spellcheck="false">${esc(JSON.stringify(schema, null, 2))}</textarea></label><p class="vp-hint vp-grow">${esc(bt("hint"))}</p><button class="button secondary" type="button" data-action="apply-tool-builder">${esc(bt("apply"))}</button></div></details>`;
  }
  function fillToolBuilder(config) {
    const valueOr = (selector, value) => { const input = panel.querySelector(selector); if (input) input.value = value; };
    const schema = { ...(config?.api_schema || {}) };
    valueOr("#vp-tool-name", config?.name || ""); valueOr("#vp-tool-description", config?.description || ""); valueOr("#vp-tool-type", config?.type || "webhook");
    valueOr("#vp-tool-url", schema.url || ""); valueOr("#vp-tool-method", schema.method || "POST");
    delete schema.url; delete schema.method; valueOr("#vp-tool-schema", JSON.stringify(schema, null, 2));
  }
  function toolDashboardMarkup() {
    const dashboard = state.toolDashboard;
    if (!dashboard || dashboard.id !== state.selectedTool) return `<span class="vp-eyebrow">${esc(tt("dashboard"))}</span><p class="vp-empty">${esc(tt("noExecution"))}</p>`;
    const executions = dashboard.executions || [], failed = executions.filter((item) => item.is_error).length;
    const latencies = executions.map((item) => Number(item.latency_secs)).filter(Number.isFinite);
    const average = latencies.length ? (latencies.reduce((sum, value) => sum + value, 0) / latencies.length).toFixed(2) : "—";
    const last = executions.reduce((latest, item) => Math.max(latest, Number(item.timestamp) || 0), 0);
    return `<div class="vp-card-head"><div><span class="vp-eyebrow">${esc(tt("dashboard"))}</span><h2>${esc(dashboard.name || dashboard.id)}</h2></div><span class="vp-pill">${esc(dashboard.type || "tool")}</span></div><div class="vp-grid vp-kpis"><article class="vp-stat"><span>${esc(tt("total"))}</span><strong>${executions.length}${dashboard.has_more ? "+" : ""}</strong></article><article class="vp-stat"><span>${esc(tt("successful"))}</span><strong>${Math.max(0, executions.length - failed)}</strong></article><article class="vp-stat"><span>${esc(tt("failed"))}</span><strong>${failed}</strong></article><article class="vp-stat"><span>${esc(tt("average"))}</span><strong>${average}${average === "—" ? "" : "s"}</strong></article><article class="vp-stat"><span>${esc(tt("lastUsed"))}</span><strong>${last ? esc(new Date(last * 1000).toLocaleString()) : "—"}</strong></article><article class="vp-stat"><span>${esc(tt("assigned"))}</span><strong>${dashboard.agents.length}</strong></article></div><div class="vp-list">${dashboard.agents.map((agent) => `<div class="vp-list-row"><span><strong>${esc(agent.name || agent.agent_id || agent.id || "Agent")}</strong><small>${esc(agent.agent_id || agent.id || "")}</small></span></div>`).join("") || `<p class="vp-empty">${esc(tr("empty"))}</p>`}</div>${dashboard.has_more ? messageBox(tt("more")) : ""}<details class="vp-details"><summary>${esc(tt("sample"))}</summary><pre class="vp-output">${esc(JSON.stringify(executions, null, 2))}</pre></details>`;
  }
  async function loadToolDashboard(toolId) {
    const tool = state.tools.find((item) => item.id === toolId);
    if (!tool) return;
    const [executionResult, dependencyResult] = await Promise.all([
      api(endpoint(`tools/${encodeURIComponent(toolId)}/executions?page_size=100`)),
      api(endpoint(`tools/${encodeURIComponent(toolId)}/dependent-agents?page_size=100`))
    ]);
    state.toolDashboard = { id: toolId, name: tool.name || tool.tool_config?.name || "Tool", type: tool.tool_config?.type || tool.type || "tool", executions: executionResult.executions || [], has_more: Boolean(executionResult.has_more), agents: dependencyResult.agents || [] };
    const host = panel.querySelector("#vp-tool-dashboard"); if (host) host.innerHTML = toolDashboardMarkup();
  }
  async function handleAction(event) {
    const openIntegration = event.target.closest("[data-open-integrations]");
    if (openIntegration) { event.preventDefault(); root.OIMSetView?.("integrations"); return; }
    const toolButton = event.target.closest("[data-tool]");
    if (toolButton) {
      state.selectedTool = toolButton.dataset.tool;
      panel.querySelectorAll("[data-tool]").forEach((item) => item.classList.remove("selected")); toolButton.classList.add("selected");
      const selected = state.tools.find((item) => item.id === toolButton.dataset.tool);
      const config = selected?.tool_config || selected || {};
      panel.querySelector("#vp-tool-json").value = JSON.stringify(config, null, 2); fillToolBuilder(config);
      if (selected) {
        try { await loadToolDashboard(selected.id); } catch (error) { notify(error.message || tr("error"), true); }
      }
      return;
    }
    const row = event.target.closest("[data-conversation], [data-imported]");
    if (row) {
      const isImported = row.hasAttribute("data-imported");
      const id = row.dataset.conversation || row.dataset.imported;
      try { const data = isImported ? await api(endpoint(`imported-conversations/${encodeURIComponent(id)}`)) : await api(endpoint(`conversations/${encodeURIComponent(id)}`)); panel.querySelector(isImported ? "#vp-imported-output" : "#vp-conversation-output").textContent = JSON.stringify(data, null, 2); } catch (error) { notify(error.message, true); }
      return;
    }
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const action = button.dataset.action;
    button.disabled = true;
    try {
      if (action === "apply-voice-settings") {
        const config = jsonValue("#vp-agent-config");
        config.conversation_config ||= {};
        config.conversation_config.tts ||= {};
        config.conversation_config.agent ||= {};
        const tts = config.conversation_config.tts;
        const model = value("#vp-agent-model"), voice = value("#vp-agent-voice");
        if (model) tts.model_id = model;
        if (voice) tts.voice_id = voice;
        tts.stability = Number(value("#vp-agent-stability"));
        tts.similarity_boost = Number(value("#vp-agent-similarity"));
        tts.speed = Number(value("#vp-agent-speed"));
        tts.optimize_streaming_latency = Number(value("#vp-agent-latency"));
        tts.style = Number(value("#vp-agent-style"));
        tts.use_speaker_boost = panel.querySelector("#vp-agent-speaker-boost").checked;
        tts.pronunciation_dictionary_locators = jsonValue("#vp-agent-pronunciation");
        if (!Array.isArray(tts.pronunciation_dictionary_locators)) throw new Error(tr("rawJson"));
        tts.agent_output_audio_format = value("#vp-agent-audio-format");
        config.conversation_config.agent.language = value("#vp-agent-language");
        panel.querySelector("#vp-agent-config").value = JSON.stringify(config, null, 2);
        notify(tr("saved"));
      }
      else if (action === "apply-agent-general") {
        const config = jsonValue("#vp-agent-config"); config.conversation_config ||= {}; config.conversation_config.agent ||= {}; config.conversation_config.agent.prompt ||= {};
        config.name = value("#vp-agent-name").trim(); config.conversation_config.agent.language = value("#vp-agent-general-language").trim(); config.conversation_config.agent.first_message = value("#vp-agent-first-message"); config.conversation_config.agent.prompt.prompt = value("#vp-agent-system-prompt");
        panel.querySelector("#vp-agent-config").value = JSON.stringify(config, null, 2); notify(tr("saved"));
      }
      else if (action === "apply-agent-llm") {
        const config = jsonValue("#vp-agent-config"); config.conversation_config ||= {}; config.conversation_config.agent ||= {}; config.conversation_config.agent.prompt ||= {}; const prompt = config.conversation_config.agent.prompt;
        const temperature = Number(value("#vp-agent-temperature")), maxTokens = Number(value("#vp-agent-max-tokens"));
        if (!Number.isFinite(temperature) || temperature < 0 || temperature > 2 || !Number.isInteger(maxTokens) || maxTokens < -1 || maxTokens > 100000) throw new Error("LLM temperature or token limit is invalid.");
        prompt.llm = value("#vp-agent-llm"); prompt.temperature = temperature; prompt.max_tokens = maxTokens;
        panel.querySelector("#vp-agent-config").value = JSON.stringify(config, null, 2); notify(tr("saved"));
      }
      else if (action === "apply-agent-conversation") {
        const config = jsonValue("#vp-agent-config"); config.conversation_config ||= {}; config.conversation_config.agent ||= {}; config.conversation_config.turn ||= {}; config.conversation_config.asr ||= {};
        config.conversation_config.turn.turn_timeout = Number(value("#vp-agent-turn-timeout")); config.conversation_config.turn.silence_end_call_timeout = Number(value("#vp-agent-silence-timeout")); config.conversation_config.turn.turn_eagerness = value("#vp-agent-turn-eagerness");
        const provider = value("#vp-agent-asr-provider").trim(); if (provider) config.conversation_config.asr.provider = provider;
        const keywords = jsonValue("#vp-agent-asr-keywords"); if (!Array.isArray(keywords)) throw new Error(tr("rawJson")); config.conversation_config.asr.keywords = keywords;
        if (!Number.isFinite(config.conversation_config.turn.turn_timeout) || config.conversation_config.turn.turn_timeout < 0 || !Number.isFinite(config.conversation_config.turn.silence_end_call_timeout)) throw new Error("Conversation timeouts are invalid.");
        panel.querySelector("#vp-agent-config").value = JSON.stringify(config, null, 2); notify(tr("saved"));
      }
      else if (action === "new-agent") { state.selectedAgent = ""; state.agent = null; state.local = null; rootFrame(agentsPage()); panel.querySelector("#vp-agent-config").value = JSON.stringify({ name: "New agent", conversation_config: {} }, null, 2); const create = document.createElement("button"); create.type = "button"; create.className = "button primary"; create.dataset.action = "create-agent"; create.textContent = tr("createAgent"); panel.querySelector(".vp-side-actions").prepend(create); }
      else if (action === "compare-config") { const diff = compareConfigs(jsonValue("#vp-agent-config"), editableAgent(state.agent) || {}); panel.querySelector("#vp-agent-diff").textContent = diff.length ? `${ac("changed")} (${diff.length}${diff.length === 100 ? "+" : ""})\n${JSON.stringify(diff, null, 2)}` : ac("same"); }
      else if (action === "insert-policies") { const config = jsonValue("#vp-agent-config"); const prompt = config.conversation_config?.agent?.prompt; if (!prompt || typeof prompt !== "object") throw new Error("Add conversation_config.agent.prompt to the agent config first."); const start = "<!-- OIM_CALENDAR_POLICY_START -->", end = "<!-- OIM_CALENDAR_POLICY_END -->", current = String(prompt.prompt || ""), existingStart = current.indexOf(start), existingEnd = current.indexOf(end); prompt.prompt = existingStart >= 0 && existingEnd > existingStart ? `${current.slice(0, existingStart)}${calendarPolicy}${current.slice(existingEnd + end.length)}` : `${current.trimEnd()}${current.trim() ? "\n\n" : ""}${calendarPolicy}`; panel.querySelector("#vp-agent-config").value = JSON.stringify(config, null, 2); notify(tr("saved")); }
      else if (action === "create-agent") { const config = jsonValue("#vp-agent-config"); const result = await api(endpoint("agents"), "POST", { config, tenant_id: Number(state.tenant) || null }); state.selectedAgent = result.agent_id; await loadAgents(); await chooseAgent(state.selectedAgent); notify(tr("success")); }
      else if (action === "reload-agents") { await loadAgents(); await render(); }
      else if (action === "local-save") { const data = await api(endpoint(`agents/${encodeURIComponent(state.selectedAgent)}/local`), "POST", { config: jsonValue("#vp-agent-config") }); state.local = { local: data.config, tenant_id: data.tenant_id, remote_hash: data.remote_hash }; notify(tr("saved")); }
      else if (action === "pull-agent") { if (!confirm(tr("externalConfirm"))) return; await api(endpoint(`agents/${encodeURIComponent(state.selectedAgent)}/pull`), "POST", {}); await chooseAgent(state.selectedAgent); notify(tr("success")); }
      else if (action === "push-agent") { if (!confirm(tr("externalConfirm"))) return; const local = await api(endpoint(`agents/${encodeURIComponent(state.selectedAgent)}/local`)); const data = await api(endpoint(`agents/${encodeURIComponent(state.selectedAgent)}/push`), "POST", { config: jsonValue("#vp-agent-config"), base_hash: local.remote_hash }); state.agent = data.config; notify(tr("success")); }
      else if (action === "clone-agent") { if (!state.selectedAgent) throw new Error(tr("noAgent")); const name = prompt(tr("name")); if (name === null) return; const result = await api(endpoint(`agents/${encodeURIComponent(state.selectedAgent)}/clone`), "POST", { name, tenant_id: state.tenant }); notify(`${tr("success")} ${result.agent_id || ""}`); await loadAgents(); }
      else if (action === "delete-agent") { if (!state.selectedAgent) throw new Error(tr("noAgent")); if (!confirm(tr("confirmDelete"))) return; await api(endpoint(`agents/${encodeURIComponent(state.selectedAgent)}`), "POST", { action: "delete", confirm_delete: true }); state.selectedAgent = ""; state.agent = null; await loadAgents(); await render(); notify(tr("success")); }
      else if (action === "assign-tenant") { if (!state.selectedAgent) throw new Error(tr("noAgent")); await api(endpoint(`agents/${encodeURIComponent(state.selectedAgent)}/tenant`), "POST", { tenant_id: Number(value("#vp-agent-tenant")) || null }); notify(tr("saved")); }
      else if (action === "branches") { const data = await api(endpoint(`agents/${encodeURIComponent(state.selectedAgent)}/branches`)); panel.querySelector("#vp-branches-output").textContent = JSON.stringify(data, null, 2); }
      else if (action === "create-branch") { if (!confirm(tr("externalConfirm"))) return; const data = await api(endpoint(`agents/${encodeURIComponent(state.selectedAgent)}/branches`), "POST", { parent_version_id: value("#vp-parent-version"), name: value("#vp-branch-name"), description: "Created in OIM" }); panel.querySelector("#vp-branches-output").textContent = JSON.stringify(data, null, 2); }
      else if (action === "merge-branch") { if (!confirm(tr("confirmMerge"))) return; const data = await api(endpoint(`agents/${encodeURIComponent(state.selectedAgent)}/branches/${encodeURIComponent(value("#vp-source-branch"))}/merge`), "POST", { target_branch_id: value("#vp-target-branch"), confirm_merge: true }); panel.querySelector("#vp-branches-output").textContent = JSON.stringify(data, null, 2); }
      else if (action === "deploy") { if (!confirm(tr("confirmDeploy"))) return; const data = await api(endpoint(`agents/${encodeURIComponent(state.selectedAgent)}/deployments`), "POST", { deployments: jsonValue("#vp-deploy-json"), confirm_deployment: true }); panel.querySelector("#vp-branches-output").textContent = JSON.stringify(data, null, 2); }
      else if (action === "restore-version") { if (!confirm(tr("confirmRestore"))) return; const data = await api(endpoint(`agents/${encodeURIComponent(state.selectedAgent)}/restore`), "POST", { version_id: value("#vp-version-id"), branch_id: value("#vp-restore-branch"), confirm_restore: true }); panel.querySelector("#vp-branches-output").textContent = JSON.stringify(data, null, 2); }
      else if (action === "save-test") { const result = await api(endpoint("tests"), "POST", { test: jsonValue("#vp-test-json") }); notify(`${tr("success")} ${result.provider?.id || ""}`); }
      else if (action === "run-tests") { if (!panel.querySelector("#vp-confirm-tools")?.checked) throw new Error(tr("confirmTools")); const tests = jsonValue("#vp-test-ids"); if (!confirm(tr("testOnly"))) return; const result = await api(endpoint(`run-tests/${encodeURIComponent(state.selectedAgent)}`), "POST", { tests, confirm_external_tools: true, name: "OIM test" }); panel.querySelector("#vp-branches-output") && (panel.querySelector("#vp-branches-output").textContent = JSON.stringify(result, null, 2)); notify(tr("success")); }
      else if (action === "reload-tools") { await loadTools(); await render(); }
      else if (action === "apply-tool-builder") {
        const config = jsonValue("#vp-tool-json"), type = value("#vp-tool-type");
        config.type = type; config.name = value("#vp-tool-name").trim(); config.description = value("#vp-tool-description").trim();
        if (!config.name) throw new Error(tr("name"));
        if (type === "webhook") {
          const url = value("#vp-tool-url"); let parsed;
          try { parsed = new URL(url); } catch { throw new Error(tr("toolUrl")); }
          if (parsed.protocol !== "https:") throw new Error(tr("toolUrl"));
          const schema = jsonValue("#vp-tool-schema"); if (!schema || Array.isArray(schema) || typeof schema !== "object") throw new Error(tr("rawJson"));
          config.api_schema = { ...schema, url: parsed.href, method: value("#vp-tool-method") };
        } else delete config.api_schema;
        panel.querySelector("#vp-tool-json").value = JSON.stringify(config, null, 2); notify(tr("saved"));
      }
      else if (action === "create-tool" || action === "save-tool") { const selected = getSelectedTool(); if (selected && action === "save-tool") { const deps = await api(endpoint(`tools/${encodeURIComponent(selected.id)}/dependent-agents`)); const count = deps.agents?.length || 0; if (count && !confirm(`${tr("toolsImpact")} ${count} ${tr("dependents")}. ${tr("externalConfirm")}`)) return; } const config = jsonValue("#vp-tool-json"); const url = selected && action === "save-tool" ? endpoint(`tools/${encodeURIComponent(selected.id)}`) : endpoint("tools"); await api(url, "POST", { tool_config: config }); notify(tr("success")); await loadTools(); }
      else if (action === "duplicate-tool") { const selected = getSelectedTool(); if (!selected) throw new Error(tr("empty")); const config = { ...(selected.tool_config || selected) }; delete config.id; delete config.created_at; config.name = `${config.name || selected.name || "Tool"} copy`.slice(0, 100); const result = await api(endpoint("tools"), "POST", { tool_config: config }); await loadTools(); panel.querySelector("#vp-tool-output").textContent = JSON.stringify(result, null, 2); notify(tr("success")); }
      else if (action === "load-tool-executions") { const selected = getSelectedTool(); if (!selected) throw new Error(tr("empty")); await loadToolDashboard(selected.id); }
      else if (action === "set-tool-enabled") {
        const selected = getSelectedTool(), agentId = value("#vp-agent"), enabled = button.dataset.enabled === "true";
        if (!selected) throw new Error(tr("empty")); if (!agentId) throw new Error(tr("noAgent"));
        if (!confirm(tr("externalConfirm"))) return;
        const agent = await api(endpoint(`agents/${encodeURIComponent(agentId)}`));
        const config = editableAgent(agent) || { conversation_config: {} }; config.conversation_config ||= {}; config.conversation_config.agent ||= {}; config.conversation_config.agent.prompt ||= {};
        const prompt = config.conversation_config.agent.prompt, assigned = Array.isArray(prompt.tool_ids) ? prompt.tool_ids : [];
        prompt.tool_ids = enabled ? [...new Set([...assigned, selected.id])] : assigned.filter((id) => id !== selected.id);
        await api(endpoint(`agents/${encodeURIComponent(agentId)}/tools`), "POST", { tool_ids: prompt.tool_ids });
        await loadToolDashboard(selected.id); notify(tr("saved"));
      }
      else if (action === "delete-tool") { const selected = getSelectedTool(); if (!selected) throw new Error(tr("empty")); const deps = await api(endpoint(`tools/${encodeURIComponent(selected.id)}/dependent-agents`)); const count = deps.agents?.length || 0; if (!confirm(`${tr("toolsImpact")} ${count} ${tr("dependents")}. ${tr("confirmDelete")}`)) return; await api(endpoint(`tools/${encodeURIComponent(selected.id)}/delete`), "POST", { confirm_delete: true, confirm_shared_delete: count > 0 }); await loadTools(); await render(); notify(tr("success")); }
      else if (action === "test-tool") { const result = await api(endpoint("tools/test"), "POST", { url: value("#vp-test-url"), method: value("#vp-test-method"), headers: jsonValue("#vp-test-headers"), body: jsonValue("#vp-test-body") }); panel.querySelector("#vp-tool-output").textContent = JSON.stringify(result, null, 2); }
      else if (action === "assign-tools") { const id = value("#vp-agent"); if (!id) throw new Error(tr("noAgent")); const result = await api(endpoint(`agents/${encodeURIComponent(id)}/tools`), "POST", { tool_ids: jsonValue("#vp-tool-ids") }); panel.querySelector("#vp-tool-output").textContent = JSON.stringify(result, null, 2); }
      else if (action === "provision-calendar") { if (!state.tenant) throw new Error(tr("noTenant")); if (!confirm(tr("externalConfirm"))) return; const result = await api(endpoint("calendar-tools"), "POST", { tenant_id: Number(state.tenant), agent_id: value("#vp-agent") || undefined }); panel.querySelector("#vp-tool-output").textContent = JSON.stringify(result, null, 2); await loadTools(); }
      else if (action === "reload-docs") { await loadDocs(); await render(); }
      else if (action === "create-doc") await createDocument();
      else if (action === "delete-doc") { const id = button.dataset.id; const dependents = await api(endpoint(`knowledge/${encodeURIComponent(id)}/dependent-agents`)); if (dependents.agents?.length) throw Object.assign(new Error(`${tr("confirmDeleteDoc")} ${dependents.agents.map((agent) => agent.name).join(", ")}`), { data: { agents: dependents.agents } }); if (!confirm(tr("confirmDeleteDoc"))) return; await api(endpoint(`knowledge/${encodeURIComponent(id)}/delete`), "POST", { confirm_delete: true }); await loadDocs(); await render(); notify(tr("success")); }
      else if (action === "assign-docs") await assignDocuments();
      else if (action === "reload-conversations") { state.cached.conversations = unwrap(await api(endpoint("conversations?page_size=100")), ["conversations"]); state.cached.imported = state.tenant ? (await api(endpoint(`imported-conversations?tenant_id=${encodeURIComponent(state.tenant)}`))).items || [] : []; await render(); }
      else if (action === "connection-test") { const result = await api(endpoint("connection-test"), "POST", {}); panel.querySelector("#vp-integration-result").textContent = JSON.stringify(result, null, 2); notify(tr("connected")); }
      else if (action === "voice-preview") await previewVoice(false);
      else if (action === "agent-voice-preview") await previewVoice(true);
      else if (action === "load-voices") { state.voices = unwrap(await api(endpoint("voices?page_size=100")), ["voices"]); state.tabLoaded = ""; await render(); }
      else if (action === "load-models") { const [models, llms] = await Promise.all([api(endpoint("models")), api(endpoint("llms"))]); panel.querySelector("#vp-integration-result").textContent = JSON.stringify({ models, llms }, null, 2); }
      else if (action === "sync-all") { const result = await api(endpoint("sync"), "POST", {}); panel.querySelector("#vp-integration-result").textContent = JSON.stringify(result, null, 2); }
      else if (action === "load-analytics") { state.cached.analytics = await api(endpoint("analytics")); await render(); }
      else if (action === "save-webhook-secret") { const result = await api(endpoint("webhook-secret"), "POST", { secret: value("#vp-webhook-secret") }); panel.querySelector("#vp-webhook-secret").value = ""; notify(result.configured ? tr("saved") : tr("disconnected")); }
      else if (action === "load-events") { state.cached.events = (await api(endpoint("events"))).items || []; await render(); }
      else if (action === "save-calendar") { const result = await api(endpoint("calendar"), "POST", { tenant_id: Number(state.tenant), settings: jsonValue("#vp-calendar-settings") }); state.cached.calendar = result.settings; notify(tr("saved")); }
      else if (action === "live-start") { await startLive(); notify(lt("liveReady")); }
      else if (action === "live-stop") { await stopLive(); appendLiveLog(lt("liveClosed"), ""); }
      else if (action === "live-send") sendLiveText();
      else if (action === "check-availability") { const start = value("#vp-calendar-start"); if (!start) throw new Error(tr("start")); const result = await api(endpoint(`calendar/availability?${query({ tenant_id: state.tenant, start, duration_minutes: value("#vp-duration"), service: value("#vp-calendar-service"), department: value("#vp-calendar-department") })}`)); panel.querySelector("#vp-calendar-result").textContent = JSON.stringify(result, null, 2); }
      else if (action === "load-slots") { const result = await api(endpoint(`calendar/slots?${query({ tenant_id: state.tenant, date: value("#vp-calendar-date"), duration_minutes: value("#vp-duration"), service: value("#vp-calendar-service"), department: value("#vp-calendar-department") })}`)); panel.querySelector("#vp-calendar-result").textContent = JSON.stringify(result, null, 2); }
      else if (action === "load-appointments") { const result = await api(endpoint(`calendar/appointments?${query({ tenant_id: state.tenant, date: value("#vp-calendar-date-view"), view: value("#vp-calendar-view") })}`)); const host = panel.querySelector("#vp-calendar-appointments"); host.innerHTML = result.items?.length ? result.items.map((item) => `<div class="vp-list-row"><span><strong>${esc(item.appointment_at)}</strong><small>${esc(item.service)} · ${esc(item.customer_name)} · ${esc(item.status)}</small></span><span>${esc(item.duration_minutes)} min</span></div>`).join("") : `<p class="vp-empty">${esc(ct("noAppointments"))}</p>`; }
      else if (action === "find-alternatives") { const start = value("#vp-calendar-start"); if (!start) throw new Error(tr("start")); const result = await api(endpoint(`calendar/alternatives?${query({ tenant_id: state.tenant, start, duration_minutes: value("#vp-duration"), service: value("#vp-calendar-service"), department: value("#vp-calendar-department") })}`)); panel.querySelector("#vp-calendar-result").textContent = JSON.stringify(result, null, 2); }
      else if (action === "book-appointment") { if (!state.tenant) throw new Error(tr("noTenant")); const at = value("#vp-calendar-start"); if (!at) throw new Error(tr("start")); const appointment = { customer_name: value("#vp-book-name"), phone: value("#vp-book-phone"), service: value("#vp-book-service"), department: value("#vp-book-department"), appointment_at: at, notes: value("#vp-book-notes"), duration_minutes: Number(value("#vp-duration")) || 60 }; const frequency = value("#vp-book-recurrence"); if (frequency) appointment.recurrence = { frequency, interval: 1, count: Number(value("#vp-book-recurrence-count")) || 4 }; const result = await api(endpoint("calendar/book"), "POST", { tenant_id: Number(state.tenant), appointment, call_id: `oim-admin-${crypto.randomUUID()}` }); panel.querySelector("#vp-calendar-result").textContent = JSON.stringify(result, null, 2); }
    } catch (error) { notify(error.message || tr("error"), true); const target = panel.querySelector("#vp-integration-result, #vp-tool-output, #vp-calendar-result, #vp-calendar-appointments, #vp-doc-result"); if (target) target.textContent = JSON.stringify(error.data || { error: error.message }, null, 2); }
    finally { if (button.isConnected) button.disabled = false; }
  }
  async function createDocument() {
    const type = value("#vp-doc-type"), body = { type, name: value("#vp-doc-name") };
    if (type === "text") body.content = value("#vp-doc-content");
    if (type === "url") { body.url = value("#vp-doc-url"); body.enable_auto_sync = panel.querySelector("#vp-doc-auto").checked; }
    if (type === "file") {
      const file = panel.querySelector("#vp-doc-file")?.files?.[0];
      if (!file) throw new Error(tr("file"));
      if (file.size > 20 * 1024 * 1024) throw new Error(tr("file"));
      body.filename = file.name; body.content_type = file.type || "application/octet-stream";
      body.content_base64 = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onerror = () => reject(new Error(tr("error"))); reader.onload = () => resolve(String(reader.result).split(",")[1] || ""); reader.readAsDataURL(file); });
    }
    const result = await api(endpoint("knowledge"), "POST", body);
    panel.querySelector("#vp-doc-result") && (panel.querySelector("#vp-doc-result").textContent = JSON.stringify(result, null, 2));
    await loadDocs(); await render(); notify(tr("success"));
  }
  async function assignDocuments() {
    const agentId = value("#vp-agent"); if (!agentId) throw new Error(tr("noAgent"));
    const ids = selectedItems("#vp-doc-select");
    const documents = ids.map((id) => { const item = state.docs.find((doc) => String(doc.id) === id); return { id, type: item?.type || item?.source_type || "file", name: item?.name || "", usage_mode: "auto" }; });
    const result = await api(endpoint(`agents/${encodeURIComponent(agentId)}/knowledge`), "POST", { documents });
    panel.querySelector("#vp-doc-result").textContent = JSON.stringify(result, null, 2); notify(tr("success"));
  }
  async function previewVoice(agent = false) {
    const voiceId = value(agent ? "#vp-agent-voice" : "#vp-voice");
    const modelId = value(agent ? "#vp-agent-model" : "#vp-model");
    const text = value(agent ? "#vp-agent-preview-text" : "#vp-preview-text");
    const result = await api("/api/admin/providers/preview", "POST", { provider: "elevenlabs", text, voice_id: voiceId, model_id: modelId });
    const bytes = Uint8Array.from(atob(result.audio), (char) => char.charCodeAt(0));
    const urlKey = agent ? "agentAudioUrl" : "audioUrl"; if (state[urlKey]) URL.revokeObjectURL(state[urlKey]);
    state[urlKey] = URL.createObjectURL(new Blob([bytes], { type: result.content_type || "audio/mpeg" }));
    const audio = panel.querySelector(agent ? "#vp-agent-audio" : "#vp-audio"); audio.src = state[urlKey]; audio.hidden = false; await audio.play().catch(() => {}); notify(tr("previewReady"));
  }
  async function handleSubmit(event) {
    if (event.target.id !== "vp-provider-form") return;
    event.preventDefault();
    try {
      const data = await api("/api/admin/providers", "POST", { provider: "elevenlabs", api_key: value("#vp-api-key"), model: value("#vp-model"), voice_id: value("#vp-voice"), enabled: panel.querySelector("#vp-enabled").checked, clear_key: false });
      panel.querySelector("#vp-api-key").value = ""; state.cached.provider = data.provider;
      notify(tr("saved")); await render();
    } catch (error) { notify(error.message, true); }
  }
  panel.addEventListener("click", handleAction);
  panel.addEventListener("submit", handleSubmit);
  panel.addEventListener("change", (event) => {
    if (event.target.matches("#vp-agent")) stopLive().then(() => chooseAgent(event.target.value)).catch((error) => notify(error.message || tr("error"), true));
    if (event.target.matches("#vp-calendar-provider")) {
      try {
        const editor = panel.querySelector("#vp-calendar-settings"), config = JSON.parse(editor.value);
        config.external_calendar_provider = event.target.value;
        editor.value = JSON.stringify(config, null, 2);
      } catch { notify(tr("rawJson"), true); }
    }
    if (event.target.matches("#vp-doc-type")) {
      const show = { text: ["vp-doc-text"], url: ["vp-doc-url"], file: ["vp-doc-file"] }[event.target.value] || [];
      panel.querySelectorAll(".vp-doc-text, .vp-doc-url, .vp-doc-file").forEach((item) => { item.hidden = !show.some((name) => item.classList.contains(name)); });
    }
  });
  panel.addEventListener("input", (event) => {
    if (event.target.matches("#vp-agent-stability, #vp-agent-similarity, #vp-agent-speed, #vp-agent-latency")) {
      const output = panel.querySelector(`#${event.target.id}-value`);
      if (output) output.value = Number(event.target.value).toFixed(event.target.id.endsWith("latency") ? 0 : 2);
    }
  });
  window.addEventListener("oim:sessionchange", (event) => { state.role = event.detail?.role || "guest"; if (state.role === "admin") render(); else { stopLive(); if (state.audioUrl) URL.revokeObjectURL(state.audioUrl); } });
  window.addEventListener("oim:viewchange", (event) => { const nextView = String(event.detail?.view || ""); if (state.live && nextView !== "vp-agents") stopLive(); if (nextView.startsWith("vp-")) { state.view = nextView; render(); } });
  window.addEventListener("oim:localechange", () => { if (state.role === "admin" && state.view.startsWith("vp-")) { if (state.live) stopLive(); render(); } });
  if (document.body.dataset.role === "admin") { state.role = "admin"; render(); }
})(window);
