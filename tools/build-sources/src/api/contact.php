<?php
// Envoie le message du formulaire de contact à l'adresse du Riad.
require __DIR__ . '/guard.php';
guard('contact', 5, 3600);
$to='legrandalcazar@gmail.com';
$n=mb_substr(trim(preg_replace('/[\r\n]+/',' ',strip_tags($_POST['prenom']??''))),0,80);
$e=filter_var($_POST['email']??'',FILTER_VALIDATE_EMAIL);
$t=mb_substr(trim(preg_replace('/[\r\n]+/',' ',strip_tags($_POST['phone']??''))),0,40);
$m=mb_substr(trim(strip_tags($_POST['message']??'')),0,5000);
if(!$e||strlen($e)>254||$m===''){http_response_code(422);exit;}
$h="From: Site Le Grand Alcazar <no-reply@legrandalcazar.com>\r\nReply-To: $e\r\nContent-Type: text/plain; charset=UTF-8";
$ok=mail($to,'=?UTF-8?B?'.base64_encode('Nouveau message du site - '.$n).'?=',"Nom: $n\nE-mail: $e\nTéléphone: $t\n\n$m",$h);
http_response_code($ok?200:500);
