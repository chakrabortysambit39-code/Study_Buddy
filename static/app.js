let mode="tutor", history=[], count=0;

const chat=document.getElementById("chat"), input=document.getElementById("input"), send=document.getElementById("send");

document.querySelectorAll(".mode").forEach(btn=>btn.addEventListener("click",()=>{
  document.querySelectorAll(".mode").forEach(x=>x.classList.remove("active"));
  btn.classList.add("active"); mode=btn.dataset.mode;
}));

function usePrompt(text){input.value=text; input.focus(); sendMessage()}
function handleKey(e){if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage()}}

function addMessage(role,text){
  document.getElementById("welcome")?.remove();
  const el=document.createElement("div"); el.className="message "+role;
  el.innerHTML='<div class="avatar">'+(role==="user"?"🙂":"✦")+'</div><div class="bubble"></div>';
  el.querySelector(".bubble").textContent=text; chat.appendChild(el); chat.scrollTop=chat.scrollHeight; return el;
}

async function sendMessage(){
  const message=input.value.trim(); if(!message)return;
  addMessage("user",message); history.push({role:"user",content:message}); input.value="";
  send.disabled=true; const typing=addMessage("assistant","Thinking…"); typing.querySelector(".bubble").className="bubble typing";
  try{
    const r=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message,mode,history:history.slice(0,-1).slice(-10)})});
    const data=await r.json(); typing.remove();
    if(!r.ok) throw new Error(data.error||"Something went wrong");
    addMessage("assistant",data.answer); history.push({role:"assistant",content:data.answer});
    count++; document.getElementById("questions").textContent=count; document.getElementById("streak").textContent=count;
  }catch(e){typing.remove();addMessage("assistant","⚠️ "+e.message)}
  finally{send.disabled=false;input.focus()}
}
function newChat(){history=[];count=0;document.getElementById("questions").textContent="0";document.getElementById("streak").textContent="0";chat.innerHTML='<div class="welcome" id="welcome"><div class="hero-icon">📚</div><h1>What are we learning today?</h1><p>Ask anything. Study Buddy will teach it step-by-step.</p></div>'}
