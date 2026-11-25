
(function(){
 var root=document.querySelector('.acc'),csrf='';
 function api(a,body){return fetch('/api/auth.php?a='+a,{method:body===undefined?'GET':'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF':csrf},body:body===undefined?undefined:JSON.stringify(body)}).then(function(r){return r.json().then(function(j){if(!r.ok)throw j;return j})})}
 function refresh(){return api('me').then(function(j){csrf=j.csrf;return j.user}).catch(function(){return null})}
 // lien « S'identifier » de l'en-tête : affiche le prénom une fois connecté
 var lg=document.querySelector('.hdr .login');
 refresh().then(function(u){if(u&&lg){var s=lg.querySelector('span');s.textContent=(u.name||u.email).split(' ')[0]}if(root)render(u)});
 if(!root)return;
 var T=JSON.parse(root.dataset.i18n),signup=true;
 var q=function(s){return root.querySelector(s)};
 function render(u){q('.view-auth').classList.toggle('hid',!!u);q('.view-me').classList.toggle('hid',!u);if(u)q('.hello').textContent=T.hello+' '+(u.name||u.email)}
 function mode(su){signup=su;q('.ttl').textContent=su?T.t:T.tl;q('.sw-q').textContent=su?T.have:T.noacc;q('.sw-a').textContent=su?T.lg:T.su;
  q('.lbl-g').textContent=(su?T.su:T.lg)+' '+T.g;q('.lbl-f').textContent=(su?T.su:T.lg)+' '+T.f;q('.lbl-m').textContent=(su?T.su:T.lg)+' '+T.e;
  q('.mf button.btn').textContent=su?T.go_r:T.go_l;q('.mf [name=name]').style.display=su?'':'none';q('.mf [name=password]').autocomplete=su?'new-password':'current-password'}
 q('.sw-a').addEventListener('click',function(){mode(!signup)});
 q('.ab.m').addEventListener('click',function(){q('.mf').classList.add('open');q('.mf [name=email]').focus()});
 q('.mf').addEventListener('submit',function(e){e.preventDefault();var f=e.target,er=q('.err');er.textContent='';
  api(signup?'register':'login',{name:f.name.value,email:f.email.value,password:f.password.value}).then(function(j){csrf=j.csrf;render(j.user);if(lg)lg.querySelector('span').textContent=(j.user.name||j.user.email).split(' ')[0]}).catch(function(x){er.textContent=T[(x&&x.error)||'e4']||T.e4})});
 q('.out').addEventListener('click',function(){api('logout',{}).then(function(){return refresh()}).then(function(){render(null);if(lg)lg.querySelector('span').textContent=lg.dataset.label})});
})();
