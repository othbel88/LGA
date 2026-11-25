
(function(){
 var b=document.querySelector('.burger'),n=document.querySelector('.nav');
 if(b)b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o)});
 // bandeau d'accueil : diaporama si js/slides.json contient des images, sinon la vidéo reste en fond
 var s=document.querySelector('.hero-slides');
 if(s){fetch(s.dataset.slides).then(function(r){return r.json()}).then(function(l){
  if(!l||!l.length)return;var v=document.querySelector('.hero-video');if(v)v.remove();
  l.forEach(function(u,i){var im=new Image();im.src=u;im.alt='';if(!i)im.className='on';s.appendChild(im)});
  var k=0,im=s.querySelectorAll('img');setInterval(function(){im[k].classList.remove('on');k=(k+1)%im.length;im[k].classList.add('on')},5000);
 }).catch(function(){})}
 // formulaires (contact + newsletter) -> endpoints PHP
 function ajax(f){f.addEventListener('submit',function(e){e.preventDefault();var ok=f.querySelector('.ok')||f.parentNode.querySelector('.ok');
  fetch(f.action,{method:'POST',body:new FormData(f)}).then(function(r){if(!r.ok)throw 0;f.reset();if(ok)ok.hidden=false}).catch(function(){
   var m=f.querySelector('[name=message]');var sub='Le Grand Alcazar';location.href='mailto:'+'legrandalcazar@gmail.com'+'?subject='+encodeURIComponent(sub)+'&body='+encodeURIComponent(m?m.value:'')})})}
 document.querySelectorAll('.cform,.newsletter').forEach(ajax);
})();
