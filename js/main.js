/* Le Grand Alcazar — v5 : interactions du site */
(function(){
 var D=document,H=D.documentElement;
 function q(s,r){return (r||D).querySelector(s)}
 function qa(s,r){return [].slice.call((r||D).querySelectorAll(s))}

 /* --- en-tête : transparent sur le bandeau d'accueil, plein ensuite --- */
 var hdr=q('.hdr'),home=D.body.classList.contains('p-home'),dyn=home||!!q('.pagehead'),stick=q('.stick');
 function onScroll(){
  var y=window.pageYOffset||H.scrollTop;
  if(hdr&&dyn)hdr.classList.toggle('solid',y>40||H.classList.contains('menu-open'));
  if(stick)stick.classList.toggle('show',y>(home?window.innerHeight*.7:320));
 }
 window.addEventListener('scroll',onScroll,{passive:true});onScroll();


 /* --- logo : devient blanc quand il passe sur un fond foncé --- */
 var lgo=q('.hdr .logo'),dkT=0;
 function lum(c){var m=c.match(/[\d.]+/g);if(!m)return null;var a=m.length>3?+m[3]:1;if(a<.5)return null;return (.299*m[0]+.587*m[1]+.114*m[2])/255}
 /* luminance réelle d'une photo/vidéo au point (x,y) — corrige l'ancienne
    hypothèse « toute image = fond sombre », fausse dès qu'une photo claire
    (zellige blanc, mur ivoire...) passe sous l'en-tête : le logo/menu
    passaient alors en blanc sur un fond en réalité clair, donc invisibles. */
 var _lc=null;
 function imgLum(el,x,y){
  try{
   var r=el.getBoundingClientRect();
   var iw=el.tagName==='VIDEO'?el.videoWidth:el.naturalWidth,ih=el.tagName==='VIDEO'?el.videoHeight:el.naturalHeight;
   if(!iw||!ih||!r.width||!r.height)return null;
   var fit=getComputedStyle(el).objectFit||'fill',nx,ny;
   if(fit==='cover'||fit==='contain'){
    var sc=fit==='cover'?Math.max(r.width/iw,r.height/ih):Math.min(r.width/iw,r.height/ih);
    nx=(x-r.left-(r.width-iw*sc)/2)/sc;ny=(y-r.top-(r.height-ih*sc)/2)/sc;
   }else{nx=(x-r.left)/r.width*iw;ny=(y-r.top)/r.height*ih}
   nx=Math.max(0,Math.min(iw-1,nx));ny=Math.max(0,Math.min(ih-1,ny));
   if(!_lc){_lc=D.createElement('canvas');_lc.width=3;_lc.height=3}
   var ctx=_lc.getContext('2d',{willReadFrequently:true});
   ctx.clearRect(0,0,3,3);
   ctx.drawImage(el,nx-4,ny-4,8,8,0,0,3,3);
   var d=ctx.getImageData(0,0,3,3).data,sum=0,n=0;
   for(var i=0;i<d.length;i+=4){if(d[i+3]>10){sum+=(.299*d[i]+.587*d[i+1]+.114*d[i+2])/255;n++}}
   return n?sum/n:null;
  }catch(e){return null}
 }
 function darkAt(x,y){
  var els=D.elementsFromPoint(x,y);
  for(var i=0;i<els.length;i++){var e=els[i];if(e.closest('.hdr')||e.closest('.wa')||e.closest('.stick'))continue;
   for(;e&&e!==D.documentElement;e=e.parentElement){
    if(e.tagName==='IMG'||e.tagName==='VIDEO'){var il=imgLum(e,x,y);return il===null?true:il<.45}
    var cs=getComputedStyle(e),l=lum(cs.backgroundColor);
    if(l!==null)return l<.45;
    if(cs.backgroundImage!=='none')return true;
   }
   return false}
  return false}
 var nv=q('.nav'),lgb=q('.lang-b');
 /* v8 : l'en-tête « solid » a désormais un fond plein uniforme sur tous les
    formats (voir style.css), donc une seule bascule dk pour tout l'en-tête —
    on échantillonne large (logo + centre du menu + bouton langue) plutôt que
    le seul point du logo, pour refléter correctement un fond composite. */
 function logoTone(){dkT=0;if(!hdr)return;
  var pts=[],n=0;
  [[lgo,[.5]],[nv,[.12,.3,.5,.7,.88]],[lgb,[.5]]].forEach(function(t){
   if(!t[0]||!hdr.classList.contains('solid'))return;
   var r=t[0].getBoundingClientRect(),y=r.top+r.height/2;
   t[1].forEach(function(p){pts.push(darkAt(r.left+r.width*p,y));n++})
  });
  var dark=0;pts.forEach(function(d){if(d)dark++});
  hdr.classList.toggle('dk', n>0 && dark*2>n)}
 window.addEventListener('scroll',function(){if(!dkT)dkT=requestAnimationFrame(logoTone)},{passive:true});
 window.addEventListener('resize',logoTone);setTimeout(logoTone,300);

 /* --- menu mobile --- */
 var b=q('.burger');
 function menu(open){H.classList.toggle('menu-open',open);if(b){b.setAttribute('aria-expanded',open)}onScroll()}
 if(b)b.addEventListener('click',function(){menu(!H.classList.contains('menu-open'))});
 qa('.mnav a').forEach(function(a){a.addEventListener('click',function(){menu(false)})});

 /* --- sélecteur de langue --- */
 var lg=q('.lang');
 if(lg){var lb=q('.lang-b',lg);
  lb.addEventListener('click',function(e){e.stopPropagation();var o=lg.classList.toggle('open');lb.setAttribute('aria-expanded',o)});
  D.addEventListener('click',function(e){if(!lg.contains(e.target)){lg.classList.remove('open');lb.setAttribute('aria-expanded','false')}});
 }
 D.addEventListener('keydown',function(e){if(e.key==='Escape'){menu(false);if(lg){lg.classList.remove('open')}}});

 /* --- bandeau d'accueil : diaporama (la 1re image est déjà dans la page) ---
    chargement réellement paresseux : une seule image supplémentaire est
    créée à la fois, juste avant d'être montrée (jamais la liste entière
    d'un coup), et l'image précédente est retirée du DOM une fois le fondu
    terminé — pour ne pas alourdir le chargement initial de l'accueil. */
 var s=q('.hero-slides');
 if(s){
  var dots=q('.hero-dots'),cur=qa('img',s)[0],urls=[],k=0,timer;
  fetch(s.dataset.slides).then(function(r){return r.json()}).then(function(l){
   if(!l||!l.length)return;
   urls=l;
   if(dots){dots.innerHTML='';urls.forEach(function(){dots.appendChild(D.createElement('i'))});var d=qa('i',dots);if(d[0])d[0].classList.add('on')}
   if(urls.length>1)timer=setInterval(function(){go(k+1)},5500);
  }).catch(function(){});
  function go(n){
   if(!urls.length||!cur)return;
   var next=(n+urls.length)%urls.length;
   if(next===k)return;
   var im=new Image();im.alt='';im.decoding='async';
   im.onload=function(){
    s.appendChild(im);
    void im.offsetWidth; // force le rendu avant la transition d'opacité
    im.classList.add('on');
    var old=cur;
    old.classList.remove('on');
    setTimeout(function(){if(old.parentNode)old.parentNode.removeChild(old)},1900);
    cur=im;k=next;
    if(dots){var d=qa('i',dots);d.forEach(function(x){x.classList.remove('on')});void dots.offsetWidth;if(d[k])d[k].classList.add('on')}
   };
   im.src=urls[next]; // onerror ignoré : le tour suivant retentera simplement
  }
  D.addEventListener('visibilitychange',function(){if(D.hidden){clearInterval(timer)}else if(urls.length>1){clearInterval(timer);timer=setInterval(function(){go(k+1)},5500)}});
 }

 /* --- vidéo de visite : le badge "lecture" couvre toute la zone, et
    disparaît dès que la vidéo démarre --- */
 qa('.vid').forEach(function(v){
  var vi=q('video',v);if(!vi)return;
  v.addEventListener('click',function(e){if(e.target===vi)return;vi.play()});
  ['play','playing'].forEach(function(ev){vi.addEventListener(ev,function(){v.classList.add('playing')})});
  ['pause','ended'].forEach(function(ev){vi.addEventListener(ev,function(){v.classList.remove('playing')})});
 });

 /* --- rail des suites --- */
 qa('.rail-wrap').forEach(function(w){
  var r=q('.rail',w),p=q('.rp',w),n=q('.rn',w);if(!r)return;
  var step=function(){var c=q('.card',r);return c?c.getBoundingClientRect().width+22:300};
  var rtl=getComputedStyle(r).direction==='rtl';
  if(p)p.addEventListener('click',function(){r.scrollBy({left:(rtl?1:-1)*step(),behavior:'smooth'})});
  if(n)n.addEventListener('click',function(){r.scrollBy({left:(rtl?-1:1)*step(),behavior:'smooth'})});
 });

 /* --- apparition douce au scroll --- */
 var targets=qa('.rv');
 if(!home){qa('.page .txt, .page .pics, .collage a.gi, .bo, .grid3 a.gi, .resgal a.gi, .serv .list, .car, .cform, .coords, .map, .embeds iframe, .avis-pics>*').forEach(function(e,i){if(!e.classList.contains('rv')){e.classList.add('rv');e.style.setProperty('--d',((i%4)*70)+'ms');targets.push(e)}})}
 if('IntersectionObserver' in window){
  var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}})},{rootMargin:'0px 0px -8% 0px',threshold:.06});
  targets.forEach(function(e){io.observe(e)});
 }else targets.forEach(function(e){e.classList.add('in')});

 /* --- formulaires (contact + newsletter) -> endpoints PHP --- */
 function ajax(f){f.addEventListener('submit',function(e){e.preventDefault();var ok=f.querySelector('.ok')||f.parentNode.querySelector('.ok');
  fetch(f.action,{method:'POST',body:new FormData(f)}).then(function(r){if(!r.ok)throw 0;f.reset();if(ok)ok.hidden=false}).catch(function(){
   var m=f.querySelector('[name=message]');var sub='Le Grand Alcazar';location.href='mailto:'+'legrandalcazar@gmail.com'+'?subject='+encodeURIComponent(sub)+'&body='+encodeURIComponent(m?m.value:'')})})}
 qa('.cform,.newsletter').forEach(ajax);
})();
