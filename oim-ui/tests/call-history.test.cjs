const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const {environment,flush,UI}=require("./helpers.cjs");
const html=fs.readFileSync(path.join(UI,"index.html"),"utf8");
function fixture(url,count=123){
  const query=new URL(url,"http://localhost").searchParams;
  const page=Number(query.get("page")||1),size=Number(query.get("page_size")||50);
  return {items:Array.from({length:Math.max(0,Math.min(size,count-(page-1)*size))},(_,i)=>({call_id:"demo-"+((page-1)*size+i),caller:"demo caller",status:"ended",started_at:1793232000,ended_at:1793232120,billed_credits:0.5})),
    pagination:{page,page_size:size,total:count,total_pages:Math.ceil(count/size),has_next:page*size<count,has_previous:page>1,snapshot_id:200},
    summary:{total_calls:count,completed_calls:count,average_duration_seconds:120,billed_credits:count/2,total_tokens:1230,metered_calls:count,estimated_openai_usd:1.23},
    filters:{timezone:"UTC"},traffic:[]};
}
test("table pages do not truncate dashboard totals and exports collect all pages",async()=>{
  const requests=[];
  const env=environment(html,"en",async url=>{requests.push(url);return {ok:true,json:async()=>fixture(url)};});
  env.run("call-history.js");
  await env.window.CallHistory.setContext({tenantId:2,role:"admin",tenantName:"Demo Studio",balance:50});
  assert.equal([...env.document.querySelectorAll("#calls tbody tr")].filter(row=>!row.className.includes("call-review-row")).length,25);
  assert.equal(env.document.querySelector("#metric-calls").textContent,"123");
  assert.match(env.document.querySelector("#call-page-info").textContent,/1 \/ 5/);
  env.document.querySelector("#call-next").dispatchEvent(new env.window.Event("click"));
  await flush();
  assert.ok(requests.some(url=>new URL(url,"http://localhost").searchParams.get("page")==="2"));
  const report=await env.window.CallHistory.collectAll();
  assert.equal(report.items.length,123);
  assert.equal(new Set(report.items.map(x=>x.call_id)).size,123);
  assert.ok(requests.some(url=>url.includes("snapshot_id=200")&&url.includes("page_size=100")));
  assert.ok(requests.every(url=>url.includes("tenant_id=2")));
});
test("a failed export page rejects the report instead of returning a partial file",async()=>{
  let fail=false;
  const env=environment(html,"tr",async url=>{
    const query=new URL(url,"http://localhost").searchParams;
    if(fail&&query.get("page")==="2")return {ok:false,json:async()=>({error:"Çağrılar yüklenemedi."})};
    return {ok:true,json:async()=>fixture(url)};
  });
  env.run("call-history.js");
  await env.window.CallHistory.setContext({tenantId:2,role:"customer",tenantName:"Demo",balance:0});
  fail=true;
  await assert.rejects(env.window.CallHistory.collectAll(),/Çağrılar yüklenemedi/);
});
test("a slow previous tenant response cannot overwrite the new tenant",async()=>{
  let resolveFirst;
  const env=environment(html,"en",url=>{
    if(new URL(url,"http://localhost").searchParams.get("tenant_id")==="2")return new Promise(resolve=>{resolveFirst=()=>resolve({ok:true,json:async()=>fixture(url,123)});});
    return Promise.resolve({ok:true,json:async()=>fixture(url,4)});
  });
  env.run("call-history.js");
  const first=env.window.CallHistory.setContext({tenantId:2,role:"admin",tenantName:"First demo",balance:1});
  await env.window.CallHistory.setContext({tenantId:3,role:"admin",tenantName:"Second demo",balance:2});
  resolveFirst();await first;
  assert.equal(env.document.querySelector("#metric-calls").textContent,"4");
  assert.match(env.document.querySelector("#calls tbody").textContent,/Second demo/);
  assert.doesNotMatch(env.document.querySelector("#calls tbody").textContent,/First demo/);
});
test("changing locale redraws call controls without changing filter values",async()=>{
  const env=environment(html,"tr",async url=>({ok:true,json:async()=>fixture(url,2)}));
  env.run("call-history.js");
  await env.window.CallHistory.setContext({tenantId:2,role:"customer",tenantName:"Demo",balance:12.5});
  const caller=env.document.querySelector('[name="caller"]');caller.value="keep-user-input";
  env.i18n.setLocale("ru");await flush();
  assert.equal(caller.value,"keep-user-input");
  assert.match(env.document.querySelector("#call-page-info").textContent,/Страница/);
  assert.match(env.document.querySelector("#call-status").textContent,/UTC/);
});
test("call review opens accessibly and saves an editable local transcript draft",async()=>{
  const writes=[];
  const env=environment(html,"en",async(url,options={})=>{
    if(options.method==="POST"){
      writes.push(JSON.parse(options.body));
      return {ok:true,json:async()=>({ok:true})};
    }
    const data=fixture(url,1);
    data.items[0].transcript="\nMüşteri: I need to ask about a refund\nAI: I can explain the policy";
    data.items[0].quality_score=100;
    data.items[0].quality_coverage=3;
    data.items[0].quality_signals=[{key:"completed",value:true},{key:"assistant_responded",value:true},{key:"knowledge_helpful",value:null},{key:"follow_up_recorded",value:true}];
    return {ok:true,json:async()=>data};
  });
  env.run("call-history.js");
  await env.window.CallHistory.setContext({tenantId:2,role:"customer",tenantName:"Demo",balance:12});
  const toggle=env.document.querySelector(".call-review-toggle");
  assert.equal(toggle.getAttribute("aria-expanded"),"false");
  toggle.dispatchEvent(new env.window.Event("click"));
  assert.equal(toggle.getAttribute("aria-expanded"),"true");
  const detail=env.document.querySelector(".call-review-row");
  const draft=detail.querySelector("button[type=button]");
  draft.dispatchEvent(new env.window.Event("click"));
  const summary=detail.querySelector("textarea");
  assert.match(summary.value,/I need to ask about a refund/);
  detail.querySelector("form").dispatchEvent(new env.window.Event("submit"));
  await flush();await flush();
  assert.equal(writes.length,1);
  assert.equal(writes[0].call_id,"demo-0");
  assert.match(writes[0].summary,/I need to ask about a refund/);
  assert.match(env.document.querySelector("#calls tbody").textContent,/100%/);
});

