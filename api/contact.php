<?php
// Envoie le message du formulaire de contact à l'adresse du Riad.
if($_SERVER['REQUEST_METHOD']!=='POST'||!empty($_POST['website'])){http_response_code(400);exit;}
$to='legrandalcazar@gmail.com';
$n=trim(strip_tags($_POST['prenom']??''));$e=filter_var($_POST['email']??'',FILTER_VALIDATE_EMAIL);
$t=trim(strip_tags($_POST['phone']??''));$m=trim(strip_tags($_POST['message']??''));
if(!$e||$m===''){http_response_code(422);exit;}
$h="From: Site Le Grand Alcazar <no-reply@".$_SERVER['HTTP_HOST'].">\r\nReply-To: $e\r\nContent-Type: text/plain; charset=UTF-8";
$ok=mail($to,'=?UTF-8?B?'.base64_encode('Nouveau message du site - '.$n).'?=',"Nom: $n\nE-mail: $e\nTéléphone: $t\n\n$m",$h);
http_response_code($ok?200:500);
