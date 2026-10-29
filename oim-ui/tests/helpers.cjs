const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const {parseHTML}=require("linkedom");
const UI=path.resolve(__dirname,"..");
function environment(html,locale="tr",fetch=()=>{throw Error("Unexpected fetch");}) {
  const {window}=parseHTML(html);
  const storage=new Map([["oim.locale",locale]]);
  Object.defineProperty(window.HTMLSelectElement.prototype,"value",{
    configurable:true,get(){return this.querySelector("option[selected]")?.value??this.querySelector("option")?.value??"";},
    set(value){for(const item of this.querySelectorAll("option")){if(item.value===String(value))item.setAttribute("selected","");else item.removeAttribute("selected");}},
  });
  class FormValues {
    constructor(form){this.values=[...form.querySelectorAll("[name]")].map(field=>[field.name,field.value]);}
    entries(){return this.values[Symbol.iterator]();}
  }
  const localStorage={getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,String(value))};
  const context=vm.createContext({window,document:window.document,localStorage,MutationObserver:window.MutationObserver,
    CustomEvent:window.CustomEvent,Event:window.Event,Intl,console,setTimeout,clearTimeout,URLSearchParams,AbortController,FormData:FormValues,fetch});
  function run(name){vm.runInContext(fs.readFileSync(path.join(UI,name),"utf8"),context,{filename:name});}
  run("locales.js");run("i18n.js");
  return {window,document:window.document,i18n:window.OIMI18n,context,storage,run};
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
module.exports={environment,flush,UI};

