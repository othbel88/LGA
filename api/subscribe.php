<?php
// Inscription newsletter : enregistre l'adresse (subscribers.csv, hors dossier public) et prévient le Riad.
require __DIR__ . '/guard.php';
guard('subscribe', 5, 3600);
$e=filter_var($_POST['email']??'',FILTER_VALIDATE_EMAIL);
if(!$e||strlen($e)>254){http_response_code(422);exit;}
$safe=preg_match('/^[=+\-@\t\r]/',$e)?"'".$e:$e; // neutralise les formules Excel
@file_put_contents(__DIR__.'/../../subscribers.csv',date('c').',"'.str_replace('"','""',$safe)."\"\n",FILE_APPEND|LOCK_EX);
@mail('legrandalcazar@gmail.com','Nouvelle inscription newsletter',$e,"From: no-reply@legrandalcazar.com");
http_response_code(200);
