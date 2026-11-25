(function(){
var D=document;
function q(s,r){return (r||D).querySelector(s)}
function qa(s,r){return [].slice.call((r||D).querySelectorAll(s))}
var L=window.__lbL||{close:'Close',prev:'Previous',next:'Next'};
var ov,img,tt,dd,cnt,list=[],idx=0,last=null;
function build(){
 if(ov)return;
 ov=D.createElement('div');ov.className='lb';ov.hidden=true;ov.setAttribute('role','dialog');ov.setAttribute('aria-modal','true');
 ov.innerHTML='<button class="lb-x" type="button"></button><button class="lb-p" type="button"></button><button class="lb-n" type="button"></button><figure><img alt=""><figcaption><b></b><span></span></figcaption></figure><div class="lb-c"></div>';
 D.body.appendChild(ov);
 img=q('img',ov);tt=q('b',ov);dd=q('span',ov);cnt=q('.lb-c',ov);
 var x=q('.lb-x',ov),p=q('.lb-p',ov),n=q('.lb-n',ov);
 x.setAttribute('aria-label',L.close);p.setAttribute('aria-label',L.prev);n.setAttribute('aria-label',L.next);
 x.innerHTML='&times;';p.innerHTML='&#8249;';n.innerHTML='&#8250;';
 x.onclick=close;p.onclick=function(e){e.stopPropagation();go(-1)};n.onclick=function(e){e.stopPropagation();go(1)};
 ov.addEventListener('click',function(e){if(e.target===ov||e.target.tagName==='FIGURE')close()});
 D.addEventListener('keydown',function(e){if(ov.hidden)return;if(e.key==='Escape')close();else if(e.key==='ArrowLeft')go(L.rtl?1:-1);else if(e.key==='ArrowRight')go(L.rtl?-1:1)});
 var sx=null;ov.addEventListener('touchstart',function(e){sx=e.touches[0].clientX},{passive:true});
 ov.addEventListener('touchend',function(e){if(sx===null)return;var d=e.changedTouches[0].clientX-sx;sx=null;if(Math.abs(d)>50)go(d<0?1:-1)});
}
function show(){
 var a=list[idx];img.src=a.getAttribute('href');img.alt=a.getAttribute('data-t')||'';
 tt.textContent=a.getAttribute('data-t')||'';dd.textContent=a.getAttribute('data-d')||'';
 q('figcaption',ov).style.display=(tt.textContent||dd.textContent)?'':'none';
 cnt.textContent=(idx+1)+' / '+list.length;
 qa('.lb-p,.lb-n,.lb-c',ov).forEach(function(b){b.style.display=list.length>1?'':'none'});
}
function go(d){idx=(idx+d+list.length)%list.length;show()}
function open(a){
 build();var g=a.getAttribute('data-g');
 list=qa('a.gi[data-g="'+g+'"]');idx=list.indexOf(a);last=a;
 ov.hidden=false;D.documentElement.classList.add('lb-open');show();q('.lb-x',ov).focus();
}
function close(){ov.hidden=true;D.documentElement.classList.remove('lb-open');img.removeAttribute('src');if(last)last.focus()}
D.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a.gi');if(!a)return;e.preventDefault();open(a)});
/* carrousel */
qa('.car').forEach(function(c){
 var s=qa('.sl',c),i=0,t;
 function set(n){i=(n+s.length)%s.length;s.forEach(function(e,k){e.classList.toggle('on',k===i)});qa('.dots button',c).forEach(function(b,k){b.classList.toggle('on',k===i)})}
 var dots=q('.dots',c);if(dots)s.forEach(function(_,k){var b=D.createElement('button');b.type='button';b.setAttribute('aria-label',String(k+1));b.onclick=function(){set(k);rs()};dots.appendChild(b)});
 var p=q('.cp',c),n=q('.cn',c);if(p)p.onclick=function(){set(i-1);rs()};if(n)n.onclick=function(){set(i+1);rs()};
 function rs(){clearInterval(t);t=setInterval(function(){if(!D.hidden)set(i+1)},5000)}
 c.addEventListener('mouseenter',function(){clearInterval(t)});c.addEventListener('mouseleave',rs);
 var sx=null;c.addEventListener('touchstart',function(e){sx=e.touches[0].clientX},{passive:true});
 c.addEventListener('touchend',function(e){if(sx===null)return;var d=e.changedTouches[0].clientX-sx;sx=null;if(Math.abs(d)>50){set(i+(d<0?1:-1));rs()}});
 set(0);rs();
});
/* vidéo d'accueil : lecture automatique dès qu'elle apparaît à l'écran */
(function(){var v=q('.tour video');if(!v)return;
 v.muted=true;v.defaultMuted=true;v.setAttribute('muted','');v.setAttribute('playsinline','');
 var want=false;
 function go(){if(!want)return;var p=v.play();if(p&&p.catch)p.catch(function(){var r=function(){if(want)v.play().catch(function(){})};['click','keydown','touchstart'].forEach(function(e){D.addEventListener(e,r,{once:true,passive:true})})})}
 v.addEventListener('canplay',go);v.addEventListener('loadeddata',go);
 function seen(){var r=v.getBoundingClientRect(),h=window.innerHeight||D.documentElement.clientHeight;var vis=Math.min(r.bottom,h)-Math.max(r.top,0);return vis>Math.min(120,r.height*.25)}
 function check(){var s=seen();if(s&&!want){want=true;go()}else if(!s&&want){want=false;v.pause()}}
 window.addEventListener('scroll',check,{passive:true});window.addEventListener('resize',check);
 if('IntersectionObserver' in window)new IntersectionObserver(check,{threshold:[0,.1,.25,.5]}).observe(v);
 check();
})();
/* pré-remplissage du formulaire de contact (?service=...) */
try{var sv=new URLSearchParams(location.search).get('service');var m=q('.cform textarea');if(sv&&m&&!m.value)m.value=sv+'\n\n'}catch(e){}
})();
