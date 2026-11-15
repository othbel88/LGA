(function(){
var D=document,L=window.__bkL||{},U=L.ui||{},mon=(L.mon||'').split(','),dow=(L.dow||'').split(',');
var m,cur,sel,slot,svc,body;
function build(){
 if(m)return;
 m=D.createElement('div');m.className='bkm';m.hidden=true;
 m.innerHTML='<div class="bkb" role="dialog" aria-modal="true"><button class="bkx" type="button">&times;</button><h3></h3><p class="bks"></p><div class="bkc"></div><div class="bkt"></div><form class="bkf"><input name="prenom" required><input name="email" type="email" required><input name="phone" type="tel"><input name="people" type="number" min="1" max="20" value="2"><input name="website" class="hp" tabindex="-1" autocomplete="off"><button class="btn" type="submit"></button><p class="ok" hidden></p><p class="bke" hidden></p></form></div>';
 D.body.appendChild(m);
 var f=m.querySelector('form');
 f.prenom.placeholder=U.name;f.email.placeholder=U.email;f.phone.placeholder=U.phone;f.people.placeholder=L.people;f.querySelector('button').textContent=L.send;
 m.querySelector('.bkx').onclick=close;m.onclick=function(e){if(e.target===m)close()};
 D.addEventListener('keydown',function(e){if(!m.hidden&&e.key==='Escape')close()});
 f.onsubmit=function(e){e.preventDefault();if(!sel||!slot){m.querySelector('.bkc').classList.add('need');return}
  var d=sel.getFullYear()+'-'+p2(sel.getMonth()+1)+'-'+p2(sel.getDate());
  var msg=L.sel+': '+svc.s+' ('+svc.p+' MAD, '+svc.d+')\n'+U.date+': '+d+' '+slot+'\n'+L.people+': '+f.people.value;
  var fd=new FormData();fd.append('prenom',f.prenom.value);fd.append('email',f.email.value);fd.append('phone',f.phone.value);fd.append('website',f.website.value);fd.append('message',msg);
  var ok=f.querySelector('.ok'),er=f.querySelector('.bke');er.hidden=true;
  fetch('/LGA/api/contact.php',{method:'POST',body:fd}).then(function(r){if(!r.ok)throw 0;ok.textContent=L.ok;ok.hidden=false;f.querySelector('button').disabled=true}).catch(function(){
   er.textContent=L.err;er.hidden=false;location.href='mailto:legrandalcazar@gmail.com?subject='+encodeURIComponent(svc.s)+'&body='+encodeURIComponent(msg+'\n'+f.prenom.value+' '+f.phone.value)})};
}
function p2(n){return n<10?'0'+n:''+n}
function slots(){
 var t=m.querySelector('.bkt');t.innerHTML='';slot=null;if(!sel)return;
 var h=/table|مائدة/i.test(svc.s)||/Table d/.test(svc.s)?[12,13,19,20]:[9,10,11,12,14,15,16,17];
 var tl=D.createElement('p');tl.textContent=L.time;t.appendChild(tl);
 h.forEach(function(x){var b=D.createElement('button');b.type='button';b.textContent=p2(x)+':00';b.onclick=function(){slot=b.textContent;[].forEach.call(t.querySelectorAll('button'),function(y){y.classList.toggle('on',y===b)})};t.appendChild(b)});
}
function cal(){
 var c=m.querySelector('.bkc');c.classList.remove('need');
 var y=cur.getFullYear(),mo=cur.getMonth(),first=new Date(y,mo,1),off=(first.getDay()+6)%7,n=new Date(y,mo+1,0).getDate(),today=new Date();today.setHours(0,0,0,0);
 var h='<div class="bkh"><button type="button" class="pv">&#8249;</button><b>'+mon[mo]+' '+y+'</b><button type="button" class="nx">&#8250;</button></div><div class="bkg">';
 dow.forEach(function(d){h+='<i>'+d+'</i>'});
 for(var i=0;i<off;i++)h+='<span></span>';
 for(var d=1;d<=n;d++){var dt=new Date(y,mo,d),dis=dt<today,on=sel&&+sel===+dt;h+='<button type="button" data-d="'+d+'"'+(dis?' disabled':'')+(on?' class="on"':'')+'>'+d+'</button>'}
 c.innerHTML=h+'</div>';
 c.querySelector('.pv').onclick=function(){cur=new Date(y,mo-1,1);cal()};c.querySelector('.nx').onclick=function(){cur=new Date(y,mo+1,1);cal()};
 [].forEach.call(c.querySelectorAll('.bkg button'),function(b){b.onclick=function(){sel=new Date(y,mo,+b.getAttribute('data-d'));cal();slots()}});
}
function open(b){
 build();svc={s:b.getAttribute('data-s'),p:b.getAttribute('data-p'),d:b.getAttribute('data-d')};
 m.querySelector('h3').textContent=svc.s;var bs=m.querySelector('.bks');bs.textContent='';var bi=document.createElement('bdi');bi.dir='ltr';bi.textContent=svc.p+' MAD · '+svc.d;bs.appendChild(bi);bs.appendChild(document.createTextNode(' — '+L.note));
 sel=null;slot=null;cur=new Date();cur.setDate(1);cal();slots();
 var f=m.querySelector('form');f.querySelector('.ok').hidden=true;f.querySelector('.bke').hidden=true;f.querySelector('button').disabled=false;
 m.hidden=false;D.documentElement.classList.add('lb-open');
}
function close(){m.hidden=true;D.documentElement.classList.remove('lb-open')}
D.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('button.bk');if(b)open(b)});
})();
