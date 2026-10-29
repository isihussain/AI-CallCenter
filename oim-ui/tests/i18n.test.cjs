const test=require("node:test"),assert=require("node:assert/strict");
const {environment,flush}=require("./helpers.cjs");
const catalogs=require("../locales.js");
const html='<html><body><label>Panel dili<select data-locale-select><option value="tr">TR</option><option value="en">EN</option><option value="ru">RU</option></select></label><button id="save">Ayarlar</button><input id="name" placeholder="Müşteri adı"><textarea id="greeting" placeholder="Lütfen bir karşılama metni yazın."></textarea><textarea id="knowledge"></textarea><table><tbody><tr><td>Ayarlar</td><td><button id="row-action">Ayarlar</button></td></tr></tbody></table><p data-user-content>Açılış mesajı</p><p id="welcome">Günaydın, Demo Studio</p><p id="status"></p></body></html>';
test("all locales have matching keys and preserve interpolation fields",()=>{
  for(const locale of ["en","ru"]){
    assert.deepEqual(Object.keys(catalogs[locale]).sort(),Object.keys(catalogs.tr).sort());
    for(const key of Object.keys(catalogs.tr)){
      assert.ok(catalogs[locale][key].trim(),key);
      assert.deepEqual((catalogs[locale][key].match(/\{\d+\}/g)||[]).sort(),(key.match(/\{\d+\}/g)||[]).sort(),key);
    }
  }
});
test("saved locale applies to text, placeholders, and document language",()=>{
  const {document,i18n}=environment(html,"en");
  assert.equal(document.documentElement.lang,"en");
  assert.equal(document.querySelector("#save").textContent,"Settings");
  assert.equal(document.querySelector("#name").placeholder,"Customer name");
  assert.equal(i18n.localeTag(),"en-GB");
});
test("locale changes preserve user content, form values, and event listeners",async()=>{
  const {document,window,i18n,storage}=environment(html);
  document.querySelector("#greeting").value="Здравствуйте! Original greeting.";
  document.querySelector("#knowledge").value="Özgün fiyat ve çalışma saatleri";
  let clicked=0;
  document.querySelector("#save").addEventListener("click",()=>clicked++);
  for(const locale of ["en","ru","tr","ru"]){i18n.setLocale(locale);await flush();}
  assert.equal(document.querySelector("#save").textContent,"Настройки");
  assert.equal(document.querySelector("#greeting").value,"Здравствуйте! Original greeting.");
  assert.equal(document.querySelector("#knowledge").value,"Özgün fiyat ve çalışma saatleri");
  assert.equal(document.querySelector("td").textContent,"Ayarlar");
  assert.equal(document.querySelector("#row-action").textContent,"Настройки");
  assert.equal(document.querySelector("[data-user-content]").textContent,"Açılış mesajı");
  assert.equal(document.querySelector("#welcome").textContent,"Доброе утро, Demo Studio");
  assert.equal(storage.get("oim.locale"),"ru");
  document.querySelector("#save").dispatchEvent(new window.Event("click"));
  assert.equal(clicked,1);
});
test("new loading and error messages are translated after DOM updates",async()=>{
  const {document,i18n}=environment(html,"en");
  document.querySelector("#status").textContent="Kaydediliyor…";
  await flush();
  assert.equal(document.querySelector("#status").textContent,"Saving…");
  document.querySelector("#status").textContent="Mesaj kaydedilemedi. Metniniz korunuyor; yeniden deneyin.";
  await flush();
  assert.match(document.querySelector("#status").textContent,/Your text is retained/);
  i18n.setLocale("ru");
  await flush();
  assert.match(document.querySelector("#status").textContent,/Текст сохранён/);
});
test("unknown locale and missing message have readable fallbacks",()=>{
  const {i18n,document}=environment(html,"unknown");
  assert.equal(document.documentElement.lang,"tr");
  assert.equal(i18n.t("Uncatalogued readable message"),"Uncatalogued readable message");
  i18n.setLocale("en");
  const saved=i18n.catalog.en.Ayarlar;
  delete i18n.catalog.en.Ayarlar;
  assert.equal(i18n.t("Ayarlar"),"Ayarlar");
  i18n.catalog.en.Ayarlar=saved;
  assert.equal(i18n.number(1234.5,{minimumFractionDigits:1}),"1,234.5");
});

