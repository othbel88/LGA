<?php
// Copiez ce fichier en config.php et renseignez vos identifiants.
return [
  'site_url' => 'https://www.legrandalcazar.com',      // adresse du site (sans slash final)
  'google'   => ['id' => '', 'secret' => ''],          // console.cloud.google.com > Identifiants > ID client OAuth (URI de redirection : site_url/api/oauth.php?cb=google)
  'facebook' => ['id' => '', 'secret' => ''],          // developers.facebook.com > App > Connexion Facebook (URI de redirection : site_url/api/oauth.php?cb=facebook)
];
