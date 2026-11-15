<?php
// Inscription newsletter : enregistre l'adresse (subscribers.csv, non public) et prévient le Riad.
if($_SERVER['REQUEST_METHOD']!=='POST'||!empty($_POST['website'])){http_response_code(400);exit;}
$e=filter_var($_POST['email']??'',FILTER_VALIDATE_EMAIL);if(!$e){http_response_code(422);exit;}
@file_put_contents(__DIR__.'/../../subscribers.csv',date('c').",$e\n",FILE_APPEND|LOCK_EX);
@mail('legrandalcazar@gmail.com','Nouvelle inscription newsletter',$e,"From: no-reply@".$_SERVER['HTTP_HOST']);
http_response_code(200);
