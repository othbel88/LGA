#!/usr/bin/env python3
"""Génère le site v5 du Riad Le Grand Alcazar à partir de la réplique v4.7.
Usage: build.py <dossier_source_v4.7> <dossier_sortie>
Les textes et médias sont repris tels quels depuis les pages sources ;
seuls l'habillage (en-tête, pied de page, structure, CSS/JS) et la page d'accueil changent."""
import sys, os, re, json, shutil, glob, html as H
from functools import lru_cache
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rooms_data as R
import respimg

SRC, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
BUILD = os.path.dirname(os.path.abspath(__file__))
VER = '500'
# build de prévisualisation (recette v6) : LGA_PREVIEW=1 ajoute noindex partout + robots.txt
# bloquant + bandeau visuel « RECETTE » dans l'en-tête — jamais activé pour le build de
# production normal (LGA_PREVIEW absent par défaut).
PREVIEW = os.environ.get('LGA_PREVIEW') == '1'
HOT = 'https://le-grand-alcazar-riad.hotelrunner.com/bv3/search'
WA = 'https://wa.me/212662460760'
LANGS = ['fr', 'en', 'es', 'it', 'de', 'ar', 'zh', 'ko', 'ru']
NATIVE = {'fr': 'Français', 'en': 'English', 'es': 'Español', 'it': 'Italiano', 'de': 'Deutsch',
          'ar': 'العربية', 'zh': '中文', 'ko': '한국어', 'ru': 'Русский'}
FLAG = {'fr': 'FRA', 'en': 'USA', 'es': 'ESP', 'it': 'ITA', 'de': 'DEU', 'ar': 'SAU', 'zh': 'CHN', 'ko': 'KOR', 'ru': 'RUS'}
SLUGS = ['notre-histoire', 'suites-chambres-1', 'restaurant', 'services', 'commentaires-et-distinctions', 'contact',
         'book-online']
# images de bandeau (déjà présentes dans le site) pour les pages principales
BAND = {
    'histoire': '/assets/media/a0420c_d2fc2f46d8ed46af9432c61e78a296ba_mv2.jpg',
    'suites': '/assets/media/a0420c_8151b30e980a4f7799deabba3e7d8624_mv2.jpg',
    'restaurant': '/assets/media/bo-table.jpg',
    'book-online': '/assets/media/bo-tour.jpg',
}
RESP_URL_PREFIX = '/assets/media/_resp/'

def responsive_band(bg_img):
    """Correctif LCP mobile (25/11/2026, cf. NOTE-POUR-AUDITEUR.md) : le bandeau de page
    (--bg, background-image plein format) pesait jusqu'à 338 Ko et se chargeait en même
    temps que les 14 vignettes de la grille des chambres sur mobile, saturant la bande
    passante simulée — même avec fetchpriority=high. On sert désormais une variante bien
    plus légère sur mobile (≤960px, q68) et une variante desktop recompressée (≤1920px,
    q74), chacune préchargée seulement pour la largeur d'écran concernée (media sur le
    <link rel=preload>), avec bascule CSS équivalente via --bg/--bg-m (cf. style.css).
    Retourne (style_attr, preload_links_html). Retombe silencieusement sur le fichier
    d'origine si la source est introuvable (ne casse jamais le build)."""
    disk = os.path.join(SRC, bg_img.lstrip('/'))
    if not os.path.isfile(disk):
        return f' style="--bg:url({bg_img})"', f'<link rel="preload" as="image" href="{bg_img}" fetchpriority="high">'
    v = respimg.band_variants(disk)
    mobile_url = RESP_URL_PREFIX + os.path.basename(v['mobile'])
    desktop_url = RESP_URL_PREFIX + os.path.basename(v['desktop'])
    style = f' style="--bg:url({desktop_url});--bg-m:url({mobile_url})"'
    preload = (f'<link rel="preload" as="image" href="{mobile_url}" fetchpriority="high" media="(max-width:700px)">'
               f'<link rel="preload" as="image" href="{desktop_url}" fetchpriority="high" media="(min-width:701px)">')
    return style, preload
ICON_SVG = {
    'wa': '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.5 3.5A11.8 11.8 0 0 0 12 0C5.4 0 .1 5.3.1 11.9c0 2.1.6 4.2 1.6 6L0 24l6.300-1.700a11.900 11.900 0 0 0 5.700 1.500c6.600 0 11.900-5.300 11.900-11.900 0-3.200-1.200-6.200-3.400-8.400zM12 21.800a9.900 9.900 0 0 1-5-1.400l-.4-.2-3.700 1 1-3.600-.2-.4a9.900 9.900 0 0 1-1.500-5.300C2.200 6.400 6.600 2 12 2c2.600 0 5.100 1 6.900 2.900a9.800 9.800 0 0 1 2.900 7c0 5.400-4.400 9.900-9.800 9.900zm5.400-7.400c-.3-.1-1.800-.9-2.100-1s-.5-.1-.7.100-.8 1-1 1.200-.4.200-.7.100a8 8 0 0 1-4-3.500c-.3-.5.300-.5.900-1.600.1-.2 0-.4 0-.5l-1-2.300c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.100-.8.400s-1 1-1 2.500 1.100 2.900 1.200 3.100c.1.200 2.100 3.200 5.100 4.500 1.900.8 2.600.9 3.500.7.600-.1 1.800-.7 2-1.400s.3-1.300.2-1.400-.3-.2-.6-.3z"/></svg>',
    'chev': '<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M1 3l4 4 4-4"/></svg>',
}

# Libellés des sections (menu, accueil, titres de pages) — mêmes noms dans toutes les langues
SL = ['home', 'notre-histoire', 'suites-chambres-1', 'restaurant', 'services', 'commentaires-et-distinctions', 'contact']
_N = {
 # v6 : nouvelle arborescence éditoriale — La Maison / La Table / Avis & Distinctions /
 # Contact & Conciergerie remplacent les intitulés génériques précédents. 'Nos Services'
 # n'apparaît plus dans le menu principal (contenu repris par les sections Bien-être /
 # Expériences, cf. WELLBEING/EXPERIENCES) mais la page reste en ligne et accessible.
 'fr': ['Accueil', 'La Maison', 'Suites & Chambres', 'La Table', 'Nos Services', 'Avis', 'Contact'],
 'en': ['Home', 'The House', 'Suites & Rooms', 'The Table', 'Our Services', 'Reviews', 'Contact'],
 'es': ['Inicio', 'La Casa', 'Suites y Habitaciones', 'La Mesa', 'Nuestros Servicios', 'Opiniones', 'Contacto'],
 'it': ['Home', 'La Dimora', 'Suite e Camere', 'La Tavola', 'I Nostri Servizi', 'Recensioni', 'Contatti'],
 'de': ['Startseite', 'Das Haus', 'Suiten & Zimmer', 'Die Tafel', 'Unsere Services', 'Bewertungen', 'Kontakt'],
 'ar': ['الرئيسية', 'دارنا', 'الأجنحة والغرف', 'مائدتنا', 'خدماتنا', 'التقييمات', 'التواصل'],
 'zh': ['首页', '宅邸故事', '套房和客房', '餐桌', '我们的服务', '评价', '联系'],
 'ko': ['홈', '저택 이야기', '스위트 & 객실', '다이닝', '저희 서비스', '후기', '문의'],
 'ru': ['Главная', 'Наш дом', 'Люксы и номера', 'Стол', 'Наши услуги', 'Отзывы', 'Контакты'],
}
# Titres de page (H1) plus longs / signatures, distincts des libellés courts du menu ci-dessus —
# utilisés uniquement comme <h1> de la page concernée (via H1KEY), jamais dans le menu.
PAGEH1 = {
 'restaurant': {'fr': 'La Table — Saveurs de Fès', 'en': 'The Table — Flavors of Fez', 'es': 'La Mesa — Sabores de Fez',
                'it': 'La Tavola — Sapori di Fès', 'de': 'Die Tafel — Aromen von Fès', 'ar': 'مائدتنا — نكهات فاس',
                'zh': '餐桌 — 费斯风味', 'ko': '다이닝 — 페스의 맛', 'ru': 'Стол — Вкусы Феса'},
 'avis': {'fr': 'Avis & Distinctions', 'en': 'Reviews & Awards', 'es': 'Opiniones y Distinciones',
          'it': 'Recensioni e Riconoscimenti', 'de': 'Bewertungen & Auszeichnungen', 'ar': 'التقييمات والتكريمات',
          'zh': '评价与荣誉', 'ko': '후기 및 수상 내역', 'ru': 'Отзывы и награды'},
}
# audit SEO (phase 11/N) : méta-descriptions des 2 pages sans paragraphe de contenu long
# (Avis & Distinctions, Nos Services) — simple association titre de page réel + nom + ville,
# aucun fait inventé (pas de note, pas de nombre d'avis, pas de liste de prestations).
EXTRA_DESC = {
 'avis': {'fr': 'Avis clients et distinctions du Riad Le Grand Alcazar, à Fès.',
          'en': 'Guest reviews and awards of Le Grand Alcazar, a Riad in Fez.',
          'es': 'Opiniones de huéspedes y distinciones de Le Grand Alcazar, un Riad en Fez.',
          'it': 'Recensioni degli ospiti e riconoscimenti di Le Grand Alcazar, un Riad a Fès.',
          'de': 'Gästebewertungen und Auszeichnungen von Le Grand Alcazar, einem Riad in Fès.',
          'ar': 'آراء الضيوف وتكريمات لو غران ألكازار، رياض في فاس.',
          'zh': 'Le Grand Alcazar（费斯里亚德）的客户评价与所获荣誉。',
          'ko': '페스의 리아드, Le Grand Alcazar의 고객 후기와 수상 내역.',
          'ru': 'Отзывы гостей и награды Le Grand Alcazar — риада в Фесе.'},
 'services': {'fr': "Services et prestations du Riad Le Grand Alcazar, à Fès : bien-être, expériences et table d'hôtes.",
              'en': 'Services and amenities of Le Grand Alcazar, a Riad in Fez: wellness, experiences and table d’hôtes dining.',
              'es': 'Servicios y prestaciones de Le Grand Alcazar, un Riad en Fez: bienestar, experiencias y mesa compartida.',
              'it': "Servizi e prestazioni di Le Grand Alcazar, un Riad a Fès: benessere, esperienze e table d'hôtes.",
              'de': 'Services und Leistungen von Le Grand Alcazar, einem Riad in Fès: Wellness, Erlebnisse und Table d’hôtes.',
              'ar': 'خدمات لو غران ألكازار، رياض في فاس: الاسترخاء والعناية، والتجارب، والمائدة المشتركة.',
              'zh': 'Le Grand Alcazar（费斯里亚德）的服务项目：养生理疗、特色体验与家庭风味餐桌。',
              'ko': '페스의 리아드, Le Grand Alcazar의 서비스: 웰니스, 체험 프로그램, 가정식 테이블 도트.',
              'ru': 'Услуги Le Grand Alcazar — риада в Фесе: велнес, впечатления и табльдот.'},
}
NAV = {l: dict(zip(SL, v)) for l, v in _N.items()}
# titres d'accueil : bienvenue / découvrir / réserver
HIST = {'fr':'Une maison, notre histoire','en':'A house, our story','es':'Una casa, nuestra historia','it':'Una casa, la nostra storia','de':'Ein Haus, unsere Geschichte','ar':'بيت، وحكايتنا','zh':'一座老宅，我们的故事','ko':'한 채의 집, 우리의 이야기','ru':'Один дом — наша история'}
TXT = {
 'fr': ('Bienvenue au Grand Alcazar', 'Découvrez Le Grand Alcazar', 'Votre parenthèse fassie commence ici'),
 'en': ('Welcome to Le Grand Alcazar', 'Discover Le Grand Alcazar', 'Your Fez retreat begins here'),
 'es': ('Bienvenidos a Le Grand Alcazar', 'Descubra Le Grand Alcazar', 'Su retiro en Fez comienza aquí'),
 'it': ('Benvenuti a Le Grand Alcazar', 'Scopri Le Grand Alcazar', 'Il vostro rifugio a Fès comincia qui'),
 'de': ('Willkommen im Le Grand Alcazar', 'Entdecken Sie Le Grand Alcazar', 'Ihre Auszeit in Fès beginnt hier'),
 'ar': ('مرحبًا بكم في لو غران ألكازار', 'اكتشفوا لو غران ألكازار', 'استراحتكم الفاسية تبدأ هنا'),
 'zh': ('欢迎来到 Le Grand Alcazar', '探索 Le Grand Alcazar', '您的费斯之旅，由此开始'),
 'ko': ('Le Grand Alcazar에 오신 것을 환영합니다', 'Le Grand Alcazar를 만나보세요', '당신의 페스 휴식이 여기서 시작됩니다'),
 'ru': ('Добро пожаловать в Le Grand Alcazar', 'Откройте для себя Le Grand Alcazar', 'Ваш отдых в Фесе начинается здесь'),
}
H1KEY = {'suites': 'suites-chambres-1', 'restaurant': 'restaurant', 'services': 'services', 'avis': 'commentaires-et-distinctions', 'contact': 'contact'}

# --- v6 « L'âme de Fès » : signature de marque + copy du hero (refonte 2026) -------------
# surtitre, titre-signature, chapeau, bouton 1 (découvrir), bouton 2 (réserver)
HERO = {
 'fr': ('UNE ADRESSE CONFIDENTIELLE AU CŒUR DE FÈS', "L’âme de Fès. L’art de recevoir.",
        'Deux demeures historiques. Quatorze chambres et suites singulières. Une hospitalité profondément marocaine.',
        'Découvrir Le Grand Alcazar', 'Réserver votre séjour'),
 'en': ('A CONFIDENTIAL ADDRESS IN THE HEART OF FEZ', 'The soul of Fez. The art of hospitality.',
        'Two historic houses. Fourteen singular rooms and suites. A deeply Moroccan welcome.',
        'Discover Le Grand Alcazar', 'Book your stay'),
 'es': ('UNA DIRECCIÓN CONFIDENCIAL EN EL CORAZÓN DE FEZ', 'El alma de Fez. El arte de recibir.',
        'Dos casas históricas. Catorce habitaciones y suites singulares. Una hospitalidad profundamente marroquí.',
        'Descubrir Le Grand Alcazar', 'Reservar su estancia'),
 'it': ('UN INDIRIZZO RISERVATO NEL CUORE DI FÈS', "L’anima di Fès. L’arte dell’ospitalità.",
        "Due dimore storiche. Quattordici camere e suite uniche. Un’ospitalità profondamente marocchina.",
        'Scoprire Le Grand Alcazar', 'Prenotare il soggiorno'),
 'de': ('EINE DISKRETE ADRESSE IM HERZEN VON FES', 'Die Seele von Fès. Die Kunst der Gastfreundschaft.',
        'Zwei historische Häuser. Vierzehn einzigartige Zimmer und Suiten. Eine zutiefst marokkanische Gastfreundschaft.',
        'Le Grand Alcazar entdecken', 'Aufenthalt buchen'),
 'ar': ('عنوان سري في قلب فاس', 'روح فاس. فن الضيافة.',
        'منزلان تاريخيان. أربع عشرة غرفة وجناحًا فريدًا من نوعه. ضيافة مغربية أصيلة.',
        'اكتشفوا لو غران ألكازار', 'احجزوا إقامتكم'),
 'zh': ('费斯古城深处的私密居所', '费斯之魂，待客之道。',
        '两座历史宅邸，十四间风格各异的客房与套房，尽显摩洛哥待客之道。',
        '探索 Le Grand Alcazar', '预订您的行程'),
 'ko': ('페스 심장부의 은밀한 주소', '페스의 영혼, 환대의 기예.',
        '두 채의 유서 깊은 저택, 저마다 개성 있는 14개의 객실과 스위트, 깊이 있는 모로코식 환대.',
        'Le Grand Alcazar 둘러보기', '숙박 예약하기'),
 'ru': ('ПОТАЙНОЙ АДРЕС В СЕРДЦЕ ФЕСА', 'Душа Феса. Искусство гостеприимства.',
        'Два исторических дома. Четырнадцать неповторимых номеров и люксов. Глубоко марокканское гостеприимство.',
        'Познакомиться с Le Grand Alcazar', 'Забронировать пребывание'),
}

# Nouvelles sections homepage v6 : (titre de section, signature éditoriale, description courte)
# — contenu basé uniquement sur des prestations/équipements réels confirmés (hammam individuel,
# massages, bassin de la terrasse, visites/cours de cuisine déjà vendus sur /book-online).
WELLBEING = {
 'fr': ('Bien-être', 'Le temps de ralentir', "Un hammam individuel, des massages sur mesure et une terrasse avec bassin pour se rafraîchir : une parenthèse de calme au cœur de la médina."),
 'en': ('Wellness', 'Time to slow down', 'A private hammam, tailored massages and a rooftop terrace with a cooling pool — a quiet pause at the heart of the medina.'),
 'es': ('Bienestar', 'Tiempo para desacelerar', 'Un hammam privado, masajes a medida y una terraza con piscina para refrescarse: una pausa de calma en el corazón de la medina.'),
 'it': ('Benessere', 'Il tempo di rallentare', 'Un hammam privato, massaggi su misura e una terrazza con piscina per rinfrescarsi: una pausa di calma nel cuore della medina.'),
 'de': ('Wellness', 'Zeit, innezuhalten', 'Ein privates Hammam, maßgeschneiderte Massagen und eine Dachterrasse mit Erfrischungsbecken – eine ruhige Auszeit im Herzen der Medina.'),
 'ar': ('الاسترخاء والعناية', 'وقتٌ للتباطؤ', 'حمّام خاص، وجلسات تدليك مخصصة، وتراس بحوض للانتعاش: استراحة هادئة في قلب المدينة العتيقة.'),
 'zh': ('养生理疗', '放慢脚步的时光', '私人汉马蒸浴、定制按摩，还有带戏水池的露台——古城深处的静谧时光。'),
 'ko': ('웰니스', '느려지는 시간', '전용 함맘, 맞춤 마사지, 그리고 시원한 수영장이 있는 테라스—메디나 중심에서 누리는 고요한 휴식.'),
 'ru': ('Велнес', 'Время замедлить шаг', 'Отдельный хаммам, массаж по индивидуальному подходу и терраса с бассейном для прохлады — тихая передышка в сердце медины.'),
}
# v8 §10 (audit externe) : Bien-être n'avait qu'un seul bloc (texte + 1 carte Massage),
# sans jamais nommer le hammam ni la terrasse/bassin pourtant annoncés dans WELLBEING.
# On découpe le même texte, déjà traduit et validé dans WELLBEING ci-dessus, en 3 libellés
# de section (hammam / massage / terrasse) — aucune phrase nouvelle inventée, seulement
# le découpage des clauses existantes.
WB_SECTIONS = {
 'fr': ('Un hammam individuel', 'Des massages sur mesure', 'Une terrasse avec bassin'),
 'en': ('A private hammam', 'Tailored massages', 'A rooftop terrace with a cooling pool'),
 'es': ('Un hammam privado', 'Masajes a medida', 'Una terraza con piscina'),
 'it': ('Un hammam privato', 'Massaggi su misura', 'Una terrazza con piscina'),
 'de': ('Ein privates Hammam', 'Maßgeschneiderte Massagen', 'Eine Dachterrasse mit Erfrischungsbecken'),
 'ar': ('حمّام خاص', 'جلسات تدليك مخصصة', 'تراس بحوض للانتعاش'),
 'zh': ('私人汉马蒸浴', '定制按摩', '带戏水池的露台'),
 'ko': ('전용 함맘', '맞춤 마사지', '시원한 수영장이 있는 테라스'),
 'ru': ('Отдельный хаммам', 'Массаж по индивидуальному подходу', 'Терраса с бассейном для прохлады'),
}
EXPERIENCES = {
 'fr': ('Expériences', 'Vivre Fès autrement', "Cours de cuisine, visites guidées de la médina et des remparts, table d'hôtes : autant de façons de découvrir Fès avec nous."),
 'en': ('Experiences', 'Live Fez differently', "Cooking classes, guided tours of the medina and ramparts, table d'hôtes dinners — so many ways to discover Fez with us."),
 'es': ('Experiencias', 'Vivir Fez de otra manera', 'Clases de cocina, visitas guiadas por la medina y las murallas, mesa compartida: tantas formas de descubrir Fez con nosotros.'),
 'it': ('Esperienze', "Vivere Fès in un altro modo", "Corsi di cucina, visite guidate della medina e delle mura, table d'hôtes: tanti modi per scoprire Fès con noi."),
 'de': ('Erlebnisse', 'Fès anders erleben', "Kochkurse, geführte Touren durch die Medina und die Stadtmauern, Table d'hôtes – so viele Wege, Fès mit uns zu entdecken."),
 'ar': ('التجارب', 'عيشوا فاس بشكل مختلف', 'دروس في الطبخ، وجولات مرشدة في المدينة القديمة وأسوارها، ومائدة مشتركة: طرق عديدة لاكتشاف فاس برفقتنا.'),
 'zh': ('特色体验', '以另一种方式，体验费斯', '烹饪课程、古城与城墙向导之旅、家庭风味餐桌——与我们一同探索费斯的多种方式。'),
 'ko': ('체험 프로그램', '색다르게 만나는 페스', '요리 수업, 메디나와 성벽 가이드 투어, 가정식 테이블 도트—우리와 함께 페스를 만나는 다양한 방법.'),
 'ru': ('Впечатления', 'Открыть Фес по-новому', 'Кулинарные мастер-классы, экскурсии по медине и крепостным стенам, табльдот — множество способов открыть для себя Фес вместе с нами.'),
}
# v8 §11 (audit externe) : Expériences n'avait qu'une seule grille indifférenciée de 4
# prestations. On la scinde en 2 sections thématiques réelles, selon la nature même des
# prestations déjà vendues sur /book-online (aucune catégorie inventée) : les expériences
# vécues au Riad (table d'hôtes, cours de cuisine) et les sorties guidées dans Fès (visite
# de la médina, visite des remparts).
EXP_CULINARY_HEADING = {'fr': 'À table', 'en': 'At the table', 'es': 'En la mesa', 'it': 'A tavola',
                         'de': 'Bei Tisch', 'ar': 'على المائدة', 'zh': '美食时光', 'ko': '식탁에서', 'ru': 'За столом'}
EXP_EXCURSION_HEADING = {'fr': 'Partir à la découverte de Fès', 'en': 'Discovering Fès', 'es': 'Descubrir Fez',
                          'it': 'Scoprire Fès', 'de': 'Fès entdecken', 'ar': 'اكتشاف فاس', 'zh': '探索菲斯',
                          'ko': '페스 탐방', 'ru': 'Знакомство с Фесом'}
EXP_CULINARY_BASES = {"Table d'hôtes de spécialités maison", 'Cours de cuisine by Le Grand Alcazar'}
TERRASSE = {
 'fr': ('Fès à perte de vue', "Notre terrasse panoramique s'étend sur les deux maisons, avec une vue à 360° sur les toits de la médina et les collines de Fès."),
 'en': ('Fez as far as the eye can see', 'Our panoramic terrace spans both houses, with a 360° view over the rooftops of the medina and the hills of Fez.'),
 'es': ('Fez hasta donde alcanza la vista', 'Nuestra terraza panorámica se extiende sobre las dos casas, con una vista de 360° sobre los tejados de la medina y las colinas de Fez.'),
 'it': ("Fès a perdita d'occhio", 'La nostra terrazza panoramica si estende sulle due case, con una vista a 360° sui tetti della medina e sulle colline di Fès.'),
 'de': ('Fès, so weit das Auge reicht', 'Unsere Panoramaterrasse erstreckt sich über beide Häuser und bietet einen 360°-Blick über die Dächer der Medina und die Hügel von Fès.'),
 'ar': ('فاس على مرأى من البصر', 'يمتد تراسنا البانورامي فوق المنزلين، ويطل بزاوية 360 درجة على أسطح المدينة العتيقة وتلال فاس.'),
 'zh': ('极目远眺的费斯', '我们的全景露台横跨两座宅邸，360° 俯瞰古城屋顶与费斯的群山。'),
 'ko': ('시야가 닿는 끝까지, 페스', '두 채의 저택을 가로지르는 파노라마 테라스에서는 메디나의 지붕과 페스 언덕이 360도로 펼쳐집니다.'),
 'ru': ('Фес, насколько хватает взгляд', 'Наша панорамная терраса простирается над обоими домами, открывая обзор на 360° на крыши медины и холмы Феса.'),
}
# lien "Voir tous nos avis" (section avis/distinctions de l'accueil)
SEEALL = {'fr': 'Voir tous nos avis', 'en': 'See all our reviews', 'es': 'Ver todas nuestras opiniones', 'it': 'Vedi tutte le nostre recensioni',
          'de': 'Alle Bewertungen ansehen', 'ar': 'عرض جميع آراء ضيوفنا', 'zh': '查看全部评价', 'ko': '모든 후기 보기', 'ru': 'Смотреть все отзывы'}
# page dédiée Galerie : titre + sous-titre (pas de légendes de photos ici, reprises telles
# quelles des pages sources, cf. build_gallery_page)
GALLERY = {'fr': ('Galerie', 'Le Riad en images'), 'en': ('Gallery', 'Le Grand Alcazar in pictures'),
           'es': ('Galería', 'El Riad en imágenes'), 'it': ('Galleria', 'Il Riad in immagini'),
           'de': ('Galerie', 'Das Riad in Bildern'), 'ar': ('معرض الصور', 'الرياض في صور'),
           'zh': ('画廊', '图片中的里亚德'), 'ko': ('갤러리', '사진으로 보는 리아드'), 'ru': ('Галерея', 'Риад в фотографиях')}
# v8 §12 (audit externe) : la Galerie n'était qu'une juxtaposition de toutes les photos sans
# aucun filtre. On ajoute un filtre réel par 3 catégories qui reflètent la provenance exacte
# des photos déjà réutilisées (La Maison/architecture, Suites & Chambres, La Table) — mêmes
# libellés déjà traduits que les intitulés de menu (NAV), + un libellé "Tout" (nouveau, 9
# langues) pour l'option neutre.
GAL_ALL = {'fr': 'Tout', 'en': 'All', 'es': 'Todo', 'it': 'Tutto', 'de': 'Alle',
           'ar': 'الكل', 'zh': '全部', 'ko': '전체', 'ru': 'Все'}
# signatures éditoriales courtes (sous-titres) des sections existantes de l'accueil, pour une
# voix de marque cohérente d'un bout à l'autre de la page (reprennent des formules du cahier des charges)
SIG_HISTOIRE = {'fr': 'Deux demeures, une même âme', 'en': 'Two houses, one soul', 'es': 'Dos casas, una misma alma',
                 'it': "Due dimore, un'unica anima", 'de': 'Zwei Häuser, eine Seele', 'ar': 'منزلان، وروح واحدة',
                 'zh': '两座宅邸，同一灵魂', 'ko': '두 채의 집, 하나의 영혼', 'ru': 'Два дома, одна душа'}
SIG_SUITES = {'fr': 'Quatorze univers, une même élégance', 'en': 'Fourteen worlds, one elegance', 'es': 'Catorce universos, una misma elegancia',
              'it': "Quattordici universi, un'unica eleganza", 'de': 'Vierzehn Welten, eine Eleganz', 'ar': 'أربعة عشر عالمًا، أناقة واحدة',
              'zh': '十四种风格，同一种优雅', 'ko': '열네 개의 세계, 하나의 우아함', 'ru': 'Четырнадцать миров, одна элегантность'}
SIG_RESTO = {'fr': 'Fès se raconte aussi à table', 'en': 'Fez has its own story to tell at the table', 'es': 'Fez también se cuenta en la mesa',
             'it': 'Fès si racconta anche a tavola', 'de': 'Auch bei Tisch erzählt Fès seine Geschichte', 'ar': 'فاس تُروى أيضًا على المائدة',
             'zh': '费斯的故事，也在餐桌上展开', 'ko': '페스는 식탁에서도 이야기를 들려줍니다', 'ru': 'Фес рассказывает свою историю и за столом'}
# v8 §9 (audit externe) : La Table n'avait qu'un seul bloc indifférencié (texte + 1 photo)
# suivi d'une grille de plats sans aucune légende visible (noms/descriptions présents
# uniquement en attributs data-t/data-d, pour la lightbox). Ces deux titres découpent la
# page en sections distinctes — plats signature (légendes existantes rendues visibles,
# aucun plat/texte inventé) et ambiance (terrasse/patio, déjà dans le texte d'origine).
RESTO_DISH_HEADING = {'fr': 'Quelques plats de la maison', 'en': 'A few house specialities', 'es': 'Algunos platos de la casa',
                       'it': 'Alcuni piatti della casa', 'de': 'Einige Gerichte des Hauses', 'ar': 'بعض أطباق المنزل',
                       'zh': '几道家常菜', 'ko': '하우스 요리 몇 가지', 'ru': 'Несколько блюд от шеф-повара'}
RESTO_AMBIANCE_HEADING = {'fr': 'Terrasse ou patio', 'en': 'Terrace or patio', 'es': 'Terraza o patio',
                          'it': 'Terrazza o patio', 'de': 'Terrasse oder Patio', 'ar': 'التراس أو الفناء',
                          'zh': '露台或庭院', 'ko': '테라스 또는 파티오', 'ru': 'Терраса или патио'}

# v8 §4 (audit externe) : paires surtitre (petit label au-dessus) / grand titre (devient le
# <h1> du bandeau) pour les bandeaux de page — La Maison est traitée directement dans le HTML
# source (cf. .titles par langue) ; ici, les 4 pages qui passent par le mécanisme générique
# H1KEY/PAGEH1 (Suites & Chambres, Restaurant, Avis & Distinctions, Contact & Conciergerie).
# KICKER_* = surtitre, SIG_AVIS/SIG_CONTACT = grand titre (les grands titres de Suites et
# Restaurant réutilisent SIG_SUITES/SIG_RESTO ci-dessus, déjà traduits pour l'accueil).
KICKER_SUITES = {l: NAV[l]['suites-chambres-1'] for l in NAV}
KICKER_RESTO = {'fr': 'Saveurs de Fès', 'en': 'Flavors of Fez', 'es': 'Sabores de Fez', 'it': 'Sapori di Fès',
                 'de': 'Aromen von Fès', 'ar': 'نكهات فاس', 'zh': '费斯风味', 'ko': '페스의 맛', 'ru': 'Вкусы Феса'}
KICKER_AVIS = dict(PAGEH1['avis'])  # l'ancien h1 "Avis & Distinctions" devient le surtitre
KICKER_CONTACT = {'fr': 'Contact & Conciergerie', 'en': 'Contact & Concierge', 'es': 'Contacto y Conserjería',
                   'it': 'Contatti e Concierge', 'de': 'Kontakt & Concierge', 'ar': 'التواصل وخدمة الكونسيرج',
                   'zh': '联系与礼宾服务', 'ko': '문의 및 컨시어지', 'ru': 'Контакты и консьерж-сервис'}
SIG_AVIS = {'fr': 'Les mots de nos hôtes', 'en': 'In our guests’ words', 'es': 'En palabras de nuestros huéspedes',
            'it': 'Nelle parole dei nostri ospiti', 'de': 'In den Worten unserer Gäste', 'ar': 'بكلمات ضيوفنا',
            'zh': '宾客的心声', 'ko': '손님들의 이야기', 'ru': 'Словами наших гостей'}
# v8 §15 (audit externe) : les badges TripAdvisor/Restaurant Guru de .embeds dépendent de
# scripts tiers (jscache.com, awards.infcdn.net) qui peuvent échouer à charger (bloqueurs de
# pub, réseau) et laisser un encart vide. On ajoute un repli statique réel (aucune note ni
# chiffre inventés) : 2 liens déjà utilisés ailleurs sur le site (pied de page pour
# TripAdvisor, encart avis pour Booking.com) vers les pages d'avis authentiques.
AVIS_FALLBACK = {
 'fr': ('Nos avis sont aussi consultables directement sur TripAdvisor et Booking.com.', 'Voir sur TripAdvisor', 'Voir sur Booking.com'),
 'en': ('Our reviews can also be read directly on TripAdvisor and Booking.com.', 'View on TripAdvisor', 'View on Booking.com'),
 'es': ('Nuestras opiniones también pueden consultarse directamente en TripAdvisor y Booking.com.', 'Ver en TripAdvisor', 'Ver en Booking.com'),
 'it': ('Le nostre recensioni sono consultabili anche direttamente su TripAdvisor e Booking.com.', 'Vedi su TripAdvisor', 'Vedi su Booking.com'),
 'de': ('Unsere Bewertungen können auch direkt auf TripAdvisor und Booking.com eingesehen werden.', 'Auf TripAdvisor ansehen', 'Auf Booking.com ansehen'),
 'ar': ('يمكن الاطلاع على تقييماتنا أيضًا مباشرة على TripAdvisor و Booking.com.', 'عرض على TripAdvisor', 'عرض على Booking.com'),
 'zh': ('您也可以直接在 TripAdvisor 和 Booking.com 上查看我们的评价。', '在 TripAdvisor 上查看', '在 Booking.com 上查看'),
 'ko': ('저희 후기는 TripAdvisor와 Booking.com에서도 직접 확인하실 수 있습니다.', 'TripAdvisor에서 보기', 'Booking.com에서 보기'),
 'ru': ('Наши отзывы также можно посмотреть напрямую на TripAdvisor и Booking.com.', 'Смотреть на TripAdvisor', 'Смотреть на Booking.com'),
}
AVIS_TA_URL = 'https://www.tripadvisor.fr/Hotel_Review-g293733-d16805556-Reviews-Le_Grand_Alcazar-Fes_Fes_Boulemane_Region.html'
AVIS_BK_URL = 'https://www.booking.com/reviews/ma/hotel/le-grand-alcazar.html?aid=356980&lang=en-us&order=featuredreviews&page=1&r_lang=fr&rows=75'

def _add_avis_fallback(l, main):
    txt, ta_lbl, bk_lbl = AVIS_FALLBACK.get(l, AVIS_FALLBACK['fr'])
    fallback_html = (f'<div class="avis-fallback rv"><p>{H.escape(txt)}</p>'
                      f'<div class="avis-fallback-lnk"><a class="btn" href="{AVIS_TA_URL}" target="_blank" rel="noopener">{H.escape(ta_lbl)}</a>'
                      f'<a class="btn" href="{AVIS_BK_URL}" target="_blank" rel="noopener">{H.escape(bk_lbl)}</a></div></div>')
    return main.replace('<div class="embeds">', fallback_html + '<div class="embeds">', 1)
SIG_CONTACT = {'fr': 'Au plaisir de vous recevoir', 'en': 'We look forward to welcoming you', 'es': 'Será un placer recibirles',
                'it': 'Sarà un piacere accogliervi', 'de': 'Wir freuen uns, Sie zu empfangen', 'ar': 'يسعدنا استقبالكم',
                'zh': '期待您的光临', 'ko': '여러분을 맞이하게 되어 기쁩니다', 'ru': 'Будем рады принять вас'}
# v8 §16 (audit externe) : le formulaire de contact n'avait aucun moyen de catégoriser la
# demande (le texte de la page évoque pourtant déjà chambre/table/visite/massage). On ajoute
# un <select> réel, dont la valeur devient l'objet du message (cf. main.js, repli mailto) —
# catégories reprises des prestations déjà réelles du site (book-online), aucune inventée.
CONTACT_CATEGORY = {
 'fr': ['Sujet de la demande', 'Réservation (chambre/suite)', 'Table / repas', 'Visite guidée ou excursion', 'Bien-être (massage)', 'Autre demande'],
 'en': ['Subject of your request', 'Room/suite booking', 'Table / meal', 'Guided tour or excursion', 'Wellness (massage)', 'Other request'],
 'es': ['Motivo de su solicitud', 'Reserva de habitación/suite', 'Mesa / comida', 'Visita guiada o excursión', 'Bienestar (masaje)', 'Otra solicitud'],
 'it': ['Oggetto della richiesta', 'Prenotazione camera/suite', 'Tavola / pasto', 'Visita guidata o escursione', 'Benessere (massaggio)', 'Altra richiesta'],
 'de': ['Betreff Ihrer Anfrage', 'Zimmer-/Suitenbuchung', 'Tisch / Essen', 'Geführte Tour oder Ausflug', 'Wellness (Massage)', 'Sonstige Anfrage'],
 'ar': ['موضوع طلبكم', 'حجز غرفة/جناح', 'مائدة / وجبة', 'جولة مرشدة أو رحلة', 'استرخاء وعناية (تدليك)', 'طلب آخر'],
 'zh': ['咨询主题', '客房/套房预订', '餐桌用餐', '导览游览或短途游', '养生理疗（按摩）', '其他咨询'],
 'ko': ['문의 주제', '객실/스위트 예약', '식사', '가이드 투어 또는 여행', '웰니스(마사지)', '기타 문의'],
 'ru': ['Тема обращения', 'Бронирование номера/люкса', 'Стол / трапеза', 'Экскурсия с гидом', 'Велнес (массаж)', 'Другой запрос'],
}
# v8 §16 : repli réel si la carte Google Maps (iframe) ne charge pas — même adresse et même
# lien "Voir sur Google Maps" déjà présents sur la page, répétés sous la carte pour rester
# visibles même si l'iframe reste vide (réseau restreint, bloqueur).
MAP_FALLBACK = {
 'fr': 'La carte ne s’affiche pas ?', 'en': 'Map not displaying?', 'es': '¿No se ve el mapa?',
 'it': 'La mappa non si carica?', 'de': 'Karte wird nicht angezeigt?', 'ar': 'لا تظهر الخريطة؟',
 'zh': '地图无法显示？', 'ko': '지도가 표시되지 않나요?', 'ru': 'Карта не отображается?',
}

def _add_contact_extras(l, main):
    opts = CONTACT_CATEGORY.get(l, CONTACT_CATEGORY['fr'])
    select_html = (f'<select name="categorie"><option value="" selected disabled>{H.escape(opts[0])}</option>'
                   + ''.join(f'<option value="{H.escape(o)}">{H.escape(o)}</option>' for o in opts[1:]) + '</select>')
    main = main.replace('<textarea name="message"', select_html + '<textarea name="message"', 1)
    fb_txt = MAP_FALLBACK.get(l, MAP_FALLBACK['fr'])
    main = re.sub(r'(<div class="map">.*?</iframe>)', r'\1<p class="map-fallback">' + H.escape(fb_txt) + '</p>', main, count=1, flags=re.S)
    return main
SIG_GALERIE = {'fr': "Instants d'Alcazar", 'en': 'Moments of Alcazar', 'es': 'Instantes de Alcazar', 'it': 'Istanti di Alcazar',
               'de': 'Alcazar-Momente', 'ar': 'لحظات من الألكازار', 'zh': 'Alcazar 的瞬间', 'ko': 'Alcazar의 순간들', 'ru': 'Мгновения Alcazar'}
# v8 §6 (audit externe) : lien "voir la galerie complète" ajouté en bas de la galerie réduite
# de La Maison (cf. build_page, clé 'notre-histoire').
GAL_LINK = {'fr': 'Voir la galerie complète', 'en': 'View the full gallery', 'es': 'Ver la galería completa',
            'it': 'Vedi la galleria completa', 'de': 'Zur vollständigen Galerie', 'ar': 'عرض المعرض الكامل',
            'zh': '查看完整图库', 'ko': '전체 갤러리 보기', 'ru': 'Смотреть всю галерею'}
# v8 §6 : la galerie de La Maison (.gal-sec) a été resserrée aux seules photos
# histoire/architecture/artisanat (11 sur 23) ; les 12 photos de suites qu'elle contenait
# auparavant (hors-sujet sur cette page, déjà visibles sur Suites & Chambres) sont conservées
# ici telles quelles pour que la page Galerie agrégée (build_gallery_page) ne perde aucune
# photo déjà publiée, en attendant sa refonte complète en galerie filtrable (v8 §12).
_legacy_pics_path = os.path.join(BUILD, 'data', 'legacy_histoire_room_pics.json')
LEGACY_HISTOIRE_ROOM_PICS = json.load(open(_legacy_pics_path, encoding='utf8')) if os.path.exists(_legacy_pics_path) else {}
# clé -> (dict surtitre, dict grand titre) ; une clé absente d'ici garde son bandeau inchangé
# (filet de sécurité, ex. 'services' qui n'est pas dans la liste du §4).
BAND_SIG = {
    'suites': (KICKER_SUITES, SIG_SUITES),
    'restaurant': (KICKER_RESTO, SIG_RESTO),
    'avis': (KICKER_AVIS, SIG_AVIS),
    'contact': (KICKER_CONTACT, SIG_CONTACT),
}

# page dédiée Offres & Séjours : brouillon volontairement sobre — aucune offre/tarif/forfait
# n'existe ailleurs sur le site, donc pas d'invention de prix ou de remises : on explique
# comment composer un séjour sur-mesure à partir des pages réelles existantes, et on renvoie
# vers le moteur de réservation (tarifs réels en temps réel) et le contact pour le sur-mesure.
OFFERS = {
 'fr': ('Offres & Séjours', 'Composez votre séjour', 'Chaque séjour au Grand Alcazar se compose sur mesure : une chambre ou suite, une table, des moments de bien-être, des expériences à vivre à Fès. Les tarifs en temps réel sont disponibles sur notre moteur de réservation ; pour un séjour sur mesure ou un groupe, notre équipe se tient à votre disposition.'),
 'en': ('Offers & Stays', 'Compose your stay', 'Every stay at Le Grand Alcazar is tailor-made: a room or suite, a table, moments of wellness, experiences to live in Fez. Real-time rates are available on our booking engine; for a tailor-made stay or a group, our team is at your disposal.'),
 'es': ('Ofertas y Estancias', 'Componga su estancia', 'Cada estancia en Le Grand Alcazar se compone a medida: una habitación o suite, una mesa, momentos de bienestar, experiencias que vivir en Fez. Las tarifas en tiempo real están disponibles en nuestro motor de reservas; para una estancia a medida o un grupo, nuestro equipo está a su disposición.'),
 'it': ('Offerte & Soggiorni', 'Componete il vostro soggiorno', 'Ogni soggiorno a Le Grand Alcazar si compone su misura: una camera o suite, una tavola, momenti di benessere, esperienze da vivere a Fès. Le tariffe in tempo reale sono disponibili sul nostro motore di prenotazione; per un soggiorno su misura o un gruppo, il nostro team è a vostra disposizione.'),
 'de': ('Angebote & Aufenthalte', 'Gestalten Sie Ihren Aufenthalt', 'Jeder Aufenthalt im Le Grand Alcazar wird maßgeschneidert: ein Zimmer oder eine Suite, ein Tisch, Momente des Wohlbefindens, Erlebnisse in Fès. Die Echtzeitpreise finden Sie auf unserer Buchungsmaschine; für einen maßgeschneiderten Aufenthalt oder eine Gruppe steht Ihnen unser Team zur Verfügung.'),
 'ar': ('العروض والإقامات', 'صمّموا إقامتكم', 'كل إقامة في Le Grand Alcazar تُصمَّم على المقاس: غرفة أو جناح، مائدة، لحظات استرخاء، وتجارب تُعاش في فاس. الأسعار الحيّة متاحة على محرك الحجز لدينا؛ وللإقامة المصمّمة خصيصًا أو للمجموعات، فريقنا رهن إشارتكم.'),
 'zh': ('优惠与住宿方案', '定制您的行程', '每一次在 Le Grand Alcazar 的住宿都可量身定制：一间客房或套房、一席餐桌、惬意的养生时光，以及费斯当地的特色体验。实时房价请见我们的预订引擎；如需定制行程或团体预订，我们的团队随时为您服务。'),
 'ko': ('오퍼 & 스테이', '나만의 체류를 구성하세요', 'Le Grand Alcazar에서의 모든 체류는 맞춤 구성됩니다: 객실 또는 스위트, 식사, 웰니스의 순간, 그리고 페스에서 누리는 체험까지. 실시간 요금은 예약 엔진에서 확인하실 수 있으며, 맞춤 체류나 단체 문의는 저희 팀이 기꺼이 도와드립니다.'),
 'ru': ('Предложения и проживание', 'Составьте своё пребывание', 'Каждое пребывание в Le Grand Alcazar складывается индивидуально: номер или люкс, стол, моменты велнеса, впечатления от Феса. Актуальные тарифы в реальном времени доступны на нашей системе бронирования; для индивидуального пребывания или группы наша команда в вашем распоряжении.'),
}
# page dédiée Carnet de Fès : reprend telles quelles les excursions réelles déjà vendues et
# décrites sur l'ancienne page /services (titres + descriptions + photos originales), sans
# ajouter aucun contenu nouveau — simple mise en avant éditoriale de ce qui existe déjà.
CARNET = {
 'fr': ('Carnet de Fès', 'Au-delà du Riad'), 'en': ('The Fez Journal', 'Beyond the Riad'),
 'es': ('Cuaderno de Fez', 'Más allá del Riad'), 'it': ('Taccuino di Fès', 'Oltre il Riad'),
 'de': ('Fès-Notizbuch', 'Jenseits des Riads'), 'ar': ('دفتر فاس', 'ما وراء الرياض'),
 'zh': ('费斯札记', '里亚德之外'), 'ko': ('페스 노트', '리아드 너머'), 'ru': ('Блокнот Феса', 'За пределами риада'),
}
# v8 §14 (audit externe) : le Carnet de Fès ne distinguait pas les excursions réservables
# (contenu existant de /services) des articles éditoriaux. On ajoute 2 intitulés de section
# (nouveaux, 9 langues) et un premier article complet — sur un sujet déjà présent sur le
# site (l'excursion "Tanneries Chouara") mais traité ici en profondeur, avec des faits
# généraux sur Fès largement établis (classement UNESCO 1981, méthodes artisanales) plutôt
# que des informations propres au Riad.
CARNET_EXCURSIONS_H = {'fr': 'Excursions', 'en': 'Excursions', 'es': 'Excursiones', 'it': 'Escursioni',
                       'de': 'Ausflüge', 'ar': 'الرحلات', 'zh': '短途游览', 'ko': '투어', 'ru': 'Экскурсии'}
CARNET_ARTICLES_H = {'fr': 'Articles', 'en': 'Articles', 'es': 'Artículos', 'it': 'Articoli',
                     'de': 'Artikel', 'ar': 'مقالات', 'zh': '文章', 'ko': '아티클', 'ru': 'Статьи'}
CARNET_ARTICLE = {
 'fr': ('La tannerie Chouara, mille ans de savoir-faire à ciel ouvert',
        "À quelques pas de la médina, les cuves colorées de Chouara racontent l'un des plus vieux métiers de Fès.",
        ["Nichée au cœur de Fès el-Bali, la tannerie Chouara est l'une des trois tanneries historiques de la ville et l'une des plus anciennes au monde encore en activité. Les peaux y sont travaillées selon des méthodes restées pour l'essentiel inchangées depuis le Moyen Âge.",
         "Les cuves de pierre, remplies tour à tour de chaux, de fiente de pigeon puis de teintures naturelles (safran, indigo, grenade, henné), forment la mosaïque de couleurs que l'on observe depuis les terrasses environnantes — le meilleur point de vue pour comprendre ce savoir-faire sans gêner le travail des artisans, dans un quartier qui en vit encore aujourd'hui, transmis de génération en génération.",
         "La visite se fait toujours accompagnée d'un guide agréé, qui replace la tannerie dans l'histoire plus large de la médina de Fès, classée au patrimoine mondial de l'UNESCO depuis 1981."]),
 'en': ('The Chouara Tannery, a thousand years of open-air craftsmanship',
        "A few steps from the medina, Chouara's colourful vats tell the story of one of Fez's oldest trades.",
        ["Nestled in the heart of Fès el-Bali, the Chouara Tannery is one of the city's three historic tanneries and among the oldest still in operation in the world. Hides are still treated using methods that have remained largely unchanged since the Middle Ages.",
         "Stone vats, filled in turn with lime, pigeon droppings and then natural dyes (saffron, indigo, pomegranate, henna), form the mosaic of colours seen from the surrounding terraces — the best vantage point to take in the craft without disturbing the tanners, in a quarter still shaped by know-how passed down through generations.",
         "Visits are always guided by an accredited guide, who places the tannery within the wider history of the Medina of Fez, a UNESCO World Heritage Site since 1981."]),
 'es': ('La curtiduría de Chouara, mil años de artesanía al aire libre',
        'A pocos pasos de la medina, las tinas de colores de Chouara narran uno de los oficios más antiguos de Fez.',
        ["En el corazón de Fez el-Bali, la curtiduría de Chouara es una de las tres curtidurías históricas de la ciudad y una de las más antiguas del mundo aún en funcionamiento. Las pieles se siguen tratando con métodos que apenas han cambiado desde la Edad Media.",
         "Las tinas de piedra, llenadas sucesivamente de cal, excremento de paloma y luego tintes naturales (azafrán, índigo, granada, henna), forman el mosaico de colores que se observa desde las terrazas circundantes — el mejor mirador para apreciar el oficio sin molestar a los artesanos, en un barrio que aún vive de este saber hacer transmitido de generación en generación.",
         "La visita se realiza siempre con un guía acreditado, que sitúa la curtiduría en la historia más amplia de la medina de Fez, Patrimonio de la Humanidad por la UNESCO desde 1981."]),
 'it': ("La conceria Chouara, mille anni di maestria a cielo aperto",
        'A pochi passi dalla medina, le vasche colorate di Chouara raccontano uno dei mestieri più antichi di Fès.',
        ["Nel cuore di Fès el-Bali, la conceria Chouara è una delle tre concerie storiche della città e una delle più antiche al mondo ancora in attività. Le pelli vengono lavorate con metodi rimasti pressoché invariati dal Medioevo.",
         "Le vasche di pietra, riempite a turno di calce, guano di piccione e poi tinture naturali (zafferano, indaco, melograno, henné), formano il mosaico di colori che si osserva dalle terrazze circostanti — il punto di vista migliore per ammirare il mestiere senza disturbare gli artigiani, in un quartiere che vive ancora di questo sapere tramandato di generazione in generazione.",
         "La visita avviene sempre accompagnati da una guida accreditata, che inserisce la conceria nella storia più ampia della medina di Fès, Patrimonio dell'Umanità UNESCO dal 1981."]),
 'de': ('Die Gerberei Chouara – tausend Jahre Handwerk unter freiem Himmel',
        'Nur wenige Schritte von der Medina entfernt erzählen die bunten Becken von Chouara von einem der ältesten Gewerbe von Fès.',
        ["Im Herzen von Fès el-Bali gelegen, ist die Gerberei Chouara eine der drei historischen Gerbereien der Stadt und eine der ältesten noch aktiven Gerbereien der Welt. Die Häute werden dort mit Methoden bearbeitet, die sich seit dem Mittelalter kaum verändert haben.",
         "Die Steinbecken, abwechselnd gefüllt mit Kalk, Taubenkot und anschließend natürlichen Farbstoffen (Safran, Indigo, Granatapfel, Henna), bilden das Farbenmosaik, das man von den umliegenden Terrassen aus beobachten kann – der beste Aussichtspunkt, um das Handwerk zu erleben, ohne die Gerber bei der Arbeit zu stören, in einem Viertel, das noch immer von diesem über Generationen weitergegebenen Wissen lebt.",
         "Der Besuch erfolgt stets in Begleitung eines zugelassenen Reiseführers, der die Gerberei in die größere Geschichte der Medina von Fès einordnet, die seit 1981 zum UNESCO-Weltkulturerbe zählt."]),
 'ar': ('دباغة الشوارة... ألف عام من الحرفة تحت السماء المفتوحة',
        'على بعد خطوات من المدينة العتيقة، تروي أحواض الشوارة الملوّنة قصة واحدة من أقدم حرف فاس.',
        ["تقع دباغة الشوارة في قلب فاس البالي، وهي إحدى الدباغات التاريخية الثلاث بالمدينة، ومن أقدم الدباغات في العالم التي لا تزال تعمل حتى اليوم. وتُعالَج الجلود فيها وفق أساليب لم تتغيّر كثيرًا منذ العصور الوسطى.",
         "تُملأ الأحواض الحجرية بالتناوب بالجير وفضلات الحمام ثم بالأصباغ الطبيعية (الزعفران والنيلة والرمان والحناء)، لتشكّل تلك الفسيفساء الملوّنة التي تُشاهَد من الشرفات المحيطة — وهي أفضل موقع لمتابعة هذه الحرفة دون إزعاج الدبّاغين، في حيّ لا يزال يعيش على هذا الموروث المتناقَل من جيل إلى جيل.",
         "وتتم الزيارة دائمًا برفقة مرشد معتمد، يضع الدباغة في سياق تاريخ مدينة فاس الأوسع، المصنّفة تراثًا عالميًا لدى اليونسكو منذ عام 1981."]),
 'zh': ('舒瓦拉皮革染坊：千年露天手艺',
        '距古城仅几步之遥，舒瓦拉五彩斑斓的染池诉说着费斯最古老的手艺之一。',
        ["舒瓦拉染坊坐落于费斯古城（Fès el-Bali）中心，是城中三大历史染坊之一，也是世界上仍在运作的最古老染坊之一。这里处理皮革的方法，自中世纪以来几乎未曾改变。",
         "石制染池依次盛放石灰、鸽粪，再注入天然染料（藏红花、靛蓝、石榴、散沫花），形成从周围露台望去的斑斓色彩——这是欣赏这门手艺又不打扰匠人工作的最佳位置，这里的街区至今仍依靠代代相传的技艺维系。",
         "参观总是由持证导游陪同，他们会将染坊置于费斯古城更宏大的历史脉络中介绍——这座古城自1981年起被联合国教科文组织列为世界遗产。"]),
 'ko': ('슈아라 무두질 공방, 노천에서 이어지는 천 년의 기술',
        '메디나에서 몇 걸음 떨어진 곳, 슈아라의 색색 염색통은 페스에서 가장 오래된 수공예 중 하나를 들려줍니다.',
        ["페스 엘-발리 중심부에 자리한 슈아라 무두질 공방은 도시의 세 역사적 무두질 공방 중 하나이며, 세계에서 지금도 운영 중인 가장 오래된 곳 중 하나입니다. 이곳에서는 중세 이후 거의 변하지 않은 방식으로 가죽을 다듬습니다.",
         "돌로 만든 통에는 차례로 석회, 비둘기 배설물, 그리고 천연 염료(사프란, 인디고, 석류, 헤나)가 채워져 주변 테라스에서 바라보는 색색의 모자이크를 이룹니다 — 장인들의 작업을 방해하지 않으면서 이 기술을 감상할 수 있는 최적의 장소이며, 이 동네는 여전히 대대로 전해지는 이 기술로 살아갑니다.",
         "방문은 항상 공인 가이드와 동행하며, 가이드는 이 무두질 공방을 1981년부터 유네스코 세계유산으로 등재된 페스 메디나의 더 큰 역사 속에 자리매김해 줍니다."]),
 'ru': ('Дубильня Шуара: тысяча лет ремесла под открытым небом',
        'В нескольких шагах от медины разноцветные чаны Шуары рассказывают об одном из старейших ремёсел Феса.',
        ["Дубильня Шуара расположена в самом сердце Фес-эль-Бали и является одной из трёх исторических дубилен города, а также одной из старейших в мире, действующих и поныне. Кожу здесь обрабатывают способами, почти не менявшимися со времён Средневековья.",
         "Каменные чаны поочерёдно заполняют известью, голубиным помётом, а затем натуральными красителями (шафраном, индиго, гранатом, хной) — так рождается мозаика цветов, которую можно увидеть с окрестных террас: лучшая точка обзора, позволяющая наблюдать за ремеслом, не мешая мастерам, в квартале, который до сих пор живёт этим мастерством, передаваемым из поколения в поколение.",
         "Посещение всегда проходит в сопровождении аккредитованного гида, который рассказывает о дубильне в контексте истории медины Феса — объекта Всемирного наследия ЮНЕСКО с 1981 года."]),
}

# ---------------------------------------------------------------- lecture des sources
def lang_dir(l): return SRC if l == 'fr' else os.path.join(SRC, l)
def page_path(l, slug=None):
    p = lang_dir(l) if slug is None else os.path.join(lang_dir(l), slug)
    return os.path.join(p, 'index.html')
def read(l, slug=None):
    p = page_path(l, slug)
    return open(p, encoding='utf8').read() if os.path.exists(p) else None
_soup = {}
def soup(l, slug=None):
    k = (l, slug)
    if k not in _soup:
        t = read(l, slug)
        _soup[k] = BeautifulSoup(t, 'html.parser') if t else None
    return _soup[k]
def inner(el): return ''.join(str(c) for c in el.contents) if el else ''
def text(el): return el.get_text(' ', strip=True) if el else ''

def split_page(h):
    """Découpe une page source en morceaux réutilisables."""
    d = {}
    m = re.search(r'<html lang="([^"]+)" dir="([^"]+)">', h); d['lang'], d['dir'] = m.group(1), m.group(2)
    m = re.search(r'<head>(.*?)</head>', h, re.S); head = m.group(1)
    d['title'] = re.search(r'<title>.*?</title>', head).group(0)
    d['desc'] = (re.search(r'<meta name="description"[^>]*>', head) or [''])[0] if re.search(r'<meta name="description"[^>]*>', head) else ''
    d['links'] = ''.join(re.findall(r'<link rel="(?:canonical|alternate)"[^>]*>', head))
    d['body'] = re.search(r'<body class="([^"]*)"', h).group(1)
    d['logo'] = re.search(r'<a class="logo" href="([^"]*)">', h).group(1)
    nav = re.search(r'<nav class="nav">(.*?)</nav>', h, re.S).group(1)
    d['nav'] = [(m[0], H.unescape(m[2])) for m in re.findall(r'<a href="([^"]*)"( class="active" aria-current="page")?>(.*?)</a>', nav)]
    def _slug(h):
        x = h.rstrip('/').split('/')[-1]
        return 'home' if x in ('', d['lang']) else x
    d['nav'] = [(h, NAV[d['lang']].get(_slug(h), t)) for h, t in d['nav']]
    d['flags'] = re.findall(r'<a href="([^"]*)" class="flag( on)?" title="[^"]*" hreflang="([^"]*)"', h)
    m = re.search(r'<a class="book" href="[^"]*"[^>]*>(.*?)</a>', h, re.S); d['book'] = m.group(1)
    d['main'] = re.search(r'<main>(.*?)</main>', h, re.S).group(1)
    f = re.search(r'<footer class="ftr">(.*?)</footer>', h, re.S).group(1)
    d['f_addr'] = re.search(r'<div class="ftr-col addr">(.*?)</div>', f, re.S).group(1)
    news = re.search(r'<div class="ftr-col news">(.*?)</div>', f, re.S).group(1)
    d['f_news_t'] = re.search(r'<p>(.*?)</p>', news).group(1)
    d['f_ph'] = re.search(r'placeholder="([^"]*)"', news).group(1)
    d['f_btn'] = re.search(r'<button type="submit">(.*?)</button>', news).group(1)
    d['f_ok'] = re.search(r'<p class="ok" hidden>(.*?)</p>', news).group(1)
    d['f_ctc'] = re.search(r'<a class="ctc" href="([^"]*)">(.*?)</a>', f)
    d['f_ctc'] = (d['f_ctc'].group(1), d['f_ctc'].group(2))
    d['f_copy'] = re.search(r'<p class="copy">(.*?)</p>', f).group(1).replace('2020', '2026')
    d['f_social'] = re.findall(r'<a href="(https://(?:www\.tripadvisor|www\.facebook|www\.instagram)[^"]*)"[^>]*><img src="([^"]*)" alt="([^"]*)"', f)
    d['tail'] = h.split('</footer>')[1]
    return d

# ---------------------------------------------------------------- composants
def flag_url(l): return f'/assets/flags/{FLAG[l]}.png'

def header(d, solid, active_href):
    cur = d['lang']
    # v6 : « Nos Services » sort du menu principal, remplacé par Bien-être / Expériences,
    # qui pointent vers leurs pages dédiées (plus des ancres d'accueil).
    core = [(h, t) for h, t in d['nav'] if not re.search(r'/(covid-19|f.s-gourmet|services)$', h)]
    pre = '' if cur == 'fr' else f'/{cur}'
    home_href = pre if pre else '/'
    extra = [(pre + '/bien-etre', WELLBEING[cur][0]), (pre + '/experiences', EXPERIENCES[cur][0])]
    i = next((n for n, (h, t) in enumerate(core) if h.rstrip('/').endswith('suites-chambres-1')), len(core) - 1) + 1
    core = core[:i] + extra + core[i:]
    nav = ''.join(f'<a href="{h}"{" class=active aria-current=page" if h == active_href else ""}>{H.escape(t)}</a>'.replace('class=active aria-current=page', 'class="active" aria-current="page"') for h, t in core)
    langs = {hl: (href, on) for href, on, hl in d['flags']}
    items, chips = '', ''
    for l in LANGS:
        href, on = langs[l]
        cls = ' class="on"' if on else ''
        items += f'<a href="{href}" hreflang="{l}" lang="{l}"{cls}><img src="{flag_url(l)}" alt="" width="24" height="24"><span>{NATIVE[l]}</span></a>'
        chips += f'<a href="{href}" hreflang="{l}" lang="{l}"{cls}><img src="{flag_url(l)}" alt="" width="20" height="20">{NATIVE[l]}</a>'
    langbtn = f'<button class="lang-b" type="button" aria-haspopup="true" aria-expanded="false" aria-label="{NATIVE[cur]}"><img src="{flag_url(cur)}" alt="" width="20" height="20"><span>{cur.upper()}</span>{ICON_SVG["chev"]}</button>'
    return f'''<a class="skip" href="#main">⇩</a>
<header class="hdr{" solid" if solid else ""}"><div class="hdr-in">
<a class="logo" href="{d['logo']}" aria-label="Le Grand Alcazar"><img src="/assets/media/a0420c_011a87d4883b44b4bb8ab301d964b423_mv2.png" alt="Logo Le Grand Alcazar" width="1600" height="1302"></a>
<nav class="nav" aria-label="Menu">{nav}</nav>
<div class="tools">
<div class="lang">{langbtn}<div class="lang-m" role="menu">{items}</div></div>
<a class="book" href="{HOT}" target="_blank" rel="noopener">{d['book']}</a>
</div>
<button class="burger" type="button" aria-label="Menu" aria-expanded="false"><span></span><span></span><span></span></button>
</div></header>
<div class="mnav" id="mnav">{''.join(f'<a href="{h}"{" class=active" if h == active_href else ""}>{H.escape(t)}</a>' for h, t in core).replace('class=active', 'class="active"')}<a class="btn hot" href="{HOT}" target="_blank" rel="noopener">{d['book']}</a><div class="mlang">{chips}</div></div>'''

# v8 §17 (audit externe) : le footer ne comportait aucun lien de navigation (mandatory).
# On ajoute 2 colonnes de liens réels vers les pages existantes (en-têtes traduits, 9
# langues) — sans la page Offres & Séjours, volontairement non publiée (cf. §13).
FTR_NAV_H = {
 'fr': ('Découvrir', 'Votre séjour'), 'en': ('Explore', 'Your stay'),
 'es': ('Descubrir', 'Su estancia'), 'it': ('Scoprire', 'Il vostro soggiorno'),
 'de': ('Entdecken', 'Ihr Aufenthalt'), 'ar': ('استكشف', 'إقامتكم'),
 'zh': ('探索', '您的住宿'), 'ko': ('둘러보기', '당신의 숙박'), 'ru': ('Исследовать', 'Ваше пребывание'),
}
# v8 §4 (finalisation) : intitulés spécifiques au footer uniquement (le menu principal
# garde "La Table" / "Avis" tels quels — portée volontairement limitée au footer).
FTR_SAVEURS = {
 'fr': 'Saveurs de Fès', 'en': 'Flavours of Fez', 'es': 'Sabores de Fez', 'it': 'Sapori di Fes',
 'de': 'Aromen von Fès', 'ar': 'نكهات فاس', 'zh': '非斯风味', 'ko': '페스의 맛', 'ru': 'Вкусы Феса',
}
FTR_AVIS = {
 'fr': 'Avis & Distinctions', 'en': 'Reviews & Awards', 'es': 'Opiniones y Distinciones',
 'it': 'Recensioni e Riconoscimenti', 'de': 'Bewertungen & Auszeichnungen', 'ar': 'التقييمات والتكريمات',
 'zh': '评价与荣誉', 'ko': '후기 & 수상', 'ru': 'Отзывы и награды',
}
FTR_RESERVER = {
 'fr': 'Réserver', 'en': 'Book now', 'es': 'Reservar', 'it': 'Prenota',
 'de': 'Jetzt buchen', 'ar': 'احجزوا الآن', 'zh': '立即预订', 'ko': '지금 예약', 'ru': 'Забронировать',
}
FTR_NEWS_TAGLINE = {
 'fr': "Nos invitations, nos offres privilégiées et nos carnets d'inspiration pour découvrir Fès autrement.",
 'en': "Exclusive invitations, special offers, and inspiration for discovering Fez in a whole new way.",
 'es': "Nuestras invitaciones, nuestras ofertas exclusivas y nuestros cuadernos de inspiración para descubrir Fez de otra manera.",
 'it': "I nostri inviti, le nostre offerte esclusive e i nostri quaderni d'ispirazione per scoprire Fes in modo diverso.",
 'de': "Unsere Einladungen, unsere exklusiven Angebote und unsere Inspirationshefte, um Fès auf andere Weise zu entdecken.",
 'ar': "دعواتنا وعروضنا الحصرية ودفاتر إلهامنا لاكتشاف فاس بطريقة مختلفة.",
 'zh': "我们的邀请、专属优惠以及灵感手记，带您以不同方式探索非斯。",
 'ko': "페스를 색다르게 발견할 수 있는 초대, 특별 혜택, 그리고 영감 노트를 보내드립니다.",
 'ru': "Наши приглашения, эксклюзивные предложения и записные книжки вдохновения, чтобы открыть Фес по-новому.",
}

def footer(d):
    l = d['lang']
    sub = ''
    soc = ''.join(f'<a class="s" href="{u}" target="_blank" rel="noopener" aria-label="{a}"><img src="{i}" alt="" width="22" height="22"></a>' for u, i, a in d['f_social'])
    ps = re.findall(r'<p>(.*?)</p>', d['f_addr'], re.S)
    addr = re.sub(r'^.*?<br\s*/?>', '', ps[0], flags=re.S).strip()
    tel = re.search(r'<a [^>]*>.*?</a>', ps[1], re.S).group(0)
    mail = re.search(r'<a [^>]*>.*?</a>', ps[2], re.S).group(0)
    ic = lambda p: f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{p}</svg>'
    I_PIN = ic('<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>')
    I_TEL = ic('<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A15 15 0 0 1 3 6a2 2 0 0 1 2-2z"/>')
    I_MAIL = ic('<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 7l8.5 6 8.5-6"/>')
    pre = '' if l == 'fr' else f'/{l}'
    U = lambda slug: (pre if pre else '/') if slug == 'home' else f'{pre}/{slug}'
    nav_by_slug = {}
    for h, t in d['nav']:
        x = h.rstrip('/').split('/')[-1]
        sl = 'home' if x in ('', l) else x
        nav_by_slug[sl] = (h, t)
    def flink(slug, label=None, href=None):
        hh, tt = nav_by_slug.get(slug, (None, None))
        hh = href or hh or U(slug)
        tt = label or tt or slug
        return f'<a href="{hh}">{H.escape(tt)}</a>'
    col1_h, col2_h = FTR_NAV_H.get(l, FTR_NAV_H['fr'])
    nav1 = ''.join([
        flink('notre-histoire'),
        flink('suites-chambres-1'),
        flink('bien-etre', WELLBEING[l][0], U('bien-etre')),
        flink('experiences', EXPERIENCES[l][0], U('experiences')),
        flink('restaurant', FTR_SAVEURS.get(l, FTR_SAVEURS['fr'])),
        flink('galerie', GALLERY[l][0], U('galerie')),
        flink('offres-et-sejours', OFFERS[l][0], U('offres-et-sejours')),
    ])
    nav2 = ''.join([
        flink('commentaires-et-distinctions', FTR_AVIS.get(l, FTR_AVIS['fr'])),
        flink('carnet-de-fes', CARNET[l][0], U('carnet-de-fes')),
        flink('contact'),
        f'<a href="{HOT}" target="_blank" rel="noopener">{H.escape(FTR_RESERVER.get(l, FTR_RESERVER["fr"]))}</a>',
        flink('home'),
    ])
    ftr_nav = f'<div class="ftr-col ftrnav"><p class="ftrh">{H.escape(col1_h)}</p><nav>{nav1}</nav></div><div class="ftr-col ftrnav"><p class="ftrh">{H.escape(col2_h)}</p><nav>{nav2}</nav></div>'
    return f'''<footer class="ftr"><div class="ftr-in">
<div class="ftr-col"><a class="flogo" href="{d['logo']}" aria-label="Le Grand Alcazar"><img src="/assets/media/a0420c_011a87d4883b44b4bb8ab301d964b423_mv2.png" alt="" width="1600" height="1302" loading="lazy"></a></div>
{ftr_nav}
<div class="ftr-col news"><p>{d['f_news_t']}</p><p class="ftr-news-tag">{H.escape(FTR_NEWS_TAGLINE.get(l, FTR_NEWS_TAGLINE["fr"]))}</p>
<form class="newsletter" action="/api/subscribe.php" method="post"><input type="email" name="email" placeholder="{d['f_ph']}" required aria-label="{d['f_ph']}"><button type="submit">{d['f_btn']}</button><input type="text" name="website" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true"></form>
<p class="ok" hidden>{d['f_ok']}</p></div>
<div class="ftr-col"><div class="soc">{soc}</div></div>
<div class="ftr-info"><address><span class="it">{I_PIN}<span>{addr}</span></span><span class="it">{I_TEL}{tel}</span><span class="it">{I_MAIL}{mail}</span></address><a class="ctc" href="{d['f_ctc'][0]}">{d['f_ctc'][1]}</a></div>
<div class="ftr-sub"><p class="copy">{d['f_copy']}</p></div>
</div></footer>
<a class="wa" href="{WA}" target="_blank" rel="noopener" aria-label="WhatsApp">{ICON_SVG['wa']}</a>
<div class="stick"><a class="btn hot" href="{HOT}" target="_blank" rel="noopener">{d['book']}</a><a class="w" href="{WA}" target="_blank" rel="noopener" aria-label="WhatsApp">{ICON_SVG['wa']}</a></div>'''

def head(d, page_key, active_url, page_image=None):
    desc = d['desc']
    title_txt = re.sub(r'</?title>', '', d['title'])
    # SEO v7 §20 : Open Graph complet par page (au lieu d'un og:title/og:image génériques
    # partagés par toutes les pages) — og:description et og:url repris des valeurs déjà
    # calculées pour cette page (aucun texte nouveau), og:image la vraie photo de la page
    # quand elle existe (repli sur l'image générique sinon), og:locale dérivé de la langue
    # réelle de la page (codes ISO standards, pas une donnée propre à l'établissement).
    desc_m = re.search(r'content="([^"]*)"', desc)
    og_desc = H.escape(H.unescape(desc_m.group(1))) if desc_m else ''
    can_m = re.search(r'<link rel="canonical" href="([^"]*)">', d['links'])
    og_url = can_m.group(1) if can_m else ''
    if page_image:
        og_image = page_image if page_image.startswith('http') else f'https://www.legrandalcazar.com{page_image}'
    else:
        og_image = 'https://www.legrandalcazar.com/assets/img/og.jpg'
    OG_LOCALE = {'fr': 'fr_FR', 'en': 'en_US', 'es': 'es_ES', 'it': 'it_IT', 'de': 'de_DE',
                 'ar': 'ar_MA', 'zh': 'zh_CN', 'ko': 'ko_KR', 'ru': 'ru_RU'}
    locale = OG_LOCALE.get(d['lang'], 'fr_FR')
    locale_alt = ''.join(f'<meta property="og:locale:alternate" content="{OG_LOCALE[x]}">' for x in LANGS if x != d['lang'])
    og_title = H.escape(H.unescape(title_txt))
    og = (f'<meta property="og:type" content="website"><meta property="og:site_name" content="Le Grand Alcazar">'
          f'<meta property="og:locale" content="{locale}">{locale_alt}'
          f'<meta property="og:title" content="{og_title}">'
          + (f'<meta property="og:description" content="{og_desc}">' if og_desc else '')
          + (f'<meta property="og:url" content="{og_url}">' if og_url else '')
          + f'<meta property="og:image" content="{og_image}">'
          + '<meta name="twitter:card" content="summary_large_image">'
          + f'<meta name="twitter:title" content="{og_title}">'
          + (f'<meta name="twitter:description" content="{og_desc}">' if og_desc else ''))
    # audit SEO (phase 8/N) : x-default absent de toutes les pages réelles d'origine (Wix) —
    # on l'ajoute systématiquement, dérivé de la version FR déjà présente, sans rien inventer.
    if 'hreflang="x-default"' not in d['links']:
        m = re.search(r'<link rel="alternate" hreflang="fr" href="([^"]*)">', d['links'])
        if m:
            d['links'] += f'<link rel="alternate" hreflang="x-default" href="{m.group(1)}">'
    ld = ''
    if page_key == 'home':
        ld = '''<script type="application/ld+json">{"@context":"https://schema.org","@type":"Hotel","name":"Le Grand Alcazar - Riad","url":"https://www.legrandalcazar.com/","image":"https://www.legrandalcazar.com/assets/img/og.jpg","telephone":"+212662460760","email":"legrandalcazar@gmail.com","address":{"@type":"PostalAddress","streetAddress":"15, Derb El Guebbas, Batha","addressLocality":"Fès","postalCode":"30110","addressCountry":"MA"},"geo":{"@type":"GeoCoordinates","latitude":34.059989,"longitude":-4.9799971},"sameAs":["https://www.facebook.com/legrandalcazar/","https://www.instagram.com/legrandalcazar/"],"checkinTime":"14:00","petsAllowed":false}</script>'''
        ld = ld.replace(',"checkinTime":"14:00","petsAllowed":false', '')  # on n'invente pas d'horaires
    return f'''<!DOCTYPE html>
<html lang="{d['lang']}" dir="{d['dir']}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1,viewport-fit=cover">
{d['title']}{d['desc']}
{'<meta name="robots" content="noindex, nofollow, noarchive">' if PREVIEW else ''}
<meta name="theme-color" content="#131B3B">
{d['links']}
{og}
<link rel="icon" type="image/png" sizes="48x48" href="/assets/img/favicon-48.png"><link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500;1,600&family=DM+Sans:wght@400;500;600;700&family=Noto+Sans+Arabic:wght@300;400;500;600;700&display=swap" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500;1,600&family=DM+Sans:wght@400;500;600;700&family=Noto+Sans+Arabic:wght@300;400;500;600;700&display=swap"></noscript>
<script>document.documentElement.classList.add('js')</script>
<link rel="stylesheet" href="/css/style.css?v={VER}">{ld}</head>
<body class="{d['body']}{' preview' if PREVIEW else ''}">
{'<div class="preview-banner">APERÇU DE TRAVAIL — PAS LA VERSION EN LIGNE — NE PAS INDEXER</div>' if PREVIEW else ''}
'''

# v7 (audit externe §5, direction artistique) : famille de bandeau par page, pour sortir
# de la formule répétée « photo + filtre bleu + titre centré » sur toutes les pages
# intérieures. 'a' = Immersif, 'b'/'b-r' = Éditorial (b-r : photo à droite, pour alterner
# d'une page à l'autre), 'c' = Photographique. Toute clé absente garde l'ancien ph-img
# (filet de sécurité — comportement inchangé, zéro régression pour les pages non listées).
BAND_FAMILY = {
    'histoire': 'a',
    'suites': 'c',
    'restaurant': 'b',
}
# Les pages construites par leurs propres fonctions (bien-être, expériences, galerie,
# offres-et-séjours, carnet de Fès) appliquent directement les mêmes classes CSS plus bas
# dans ce fichier (build_extra_page, build_gallery_page, build_offers_page, build_carnet_page) —
# elles ne passent pas par page_head_band().

def breadcrumb_ld(l, label, url):
    """SEO v7 §20 : BreadcrumbList pour les pages construites par leurs fonctions dédiées
    (Bien-être, Expériences, Galerie, Offres & Séjours, Carnet de Fès), qui ne passent pas
    par build_page(). Mêmes règles que pour les autres pages : aucune URL/texte inventé."""
    pre = '' if l == 'fr' else f'/{l}'
    home_item = f'https://www.legrandalcazar.com{pre}/'
    crumb_ld = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': NAV[l].get('home', 'Accueil'), 'item': home_item},
        {'@type': 'ListItem', 'position': 2, 'name': label, 'item': url},
    ]}
    return f'<script type="application/ld+json">{json.dumps(crumb_ld, ensure_ascii=False)}</script>'

def _band_photo_html(img, alt=''):
    st, pre = responsive_band(img)
    # pour les familles b/c, la photo est un vrai <img> (pas un ::before CSS) : meilleure
    # légibilité du HTML, et le preload existant continue de cibler le bon fichier.
    m = re.search(r"--bg:url\(([^)]*)\)", st)
    desktop = m.group(1) if m else img
    return f'<div class="ph-photo"><img src="{desktop}" alt="{H.escape(alt)}" fetchpriority="high"></div>', pre

def page_head_band(key, main):
    """Sort le(s) titre(s) de la section pour en faire un bandeau de page.
    Retourne (bandeau, main_sans_titre, preload_html, img) — preload_html contient les deux
    <link rel=preload> (mobile/desktop) de l'image de bandeau, cf. responsive_band() ; img est
    le chemin de la photo réelle du bandeau (ou None), réutilisé pour l'Open Graph (§20 v7)."""
    fam = BAND_FAMILY.get(key)
    m = re.search(r'<div class="serv-hero">(.*?)</div>', main, re.S)
    if m:  # services : le titre + l'image existante deviennent le bandeau
        h1 = re.search(r'<h1>(.*?)</h1>', m.group(1)).group(1)
        img = re.search(r'<img src="([^"]*)"', m.group(1)).group(1)
        main = main.replace(m.group(0), '')
        st, pre = responsive_band(img)
        return f'<header class="pagehead ph-img"{st}><i class="orn c"></i><h1>{h1}</h1></header>', main, pre, img
    m = re.search(r'<div class="titles">(.*?)</div>', main, re.S)
    if m:  # histoire : RIAD / HOTEL-BOUTIQUE / RESTAURANT — Type A (Immersif)
        main = main.replace(m.group(0), '')
        img = BAND['histoire']
        st, pre = responsive_band(img)
        return f'<header class="pagehead ph-a"{st}><div class="ph-in"><i class="orn c"></i><div class="titles">{m.group(1)}</div></div></header>', main, pre, img
    # v8 §4 : signature éditoriale — un <p class="kicker"> optionnel, injecté juste avant le
    # <h1> (cf. H1KEY/PAGEH1/KICKER plus bas), est capturé avec lui et reporté dans le bandeau.
    m = re.search(r'(?:<p class="kicker">(.*?)</p>\s*)?<h1>(.*?)</h1>', main)
    if not m: return '', main, '', None
    kick_html = f'<p class="kicker">{m.group(1)}</p>' if m.group(1) else ''
    h1_html = m.group(2)
    main = main.replace(m.group(0), '', 1)
    img = BAND.get(key)
    if fam in ('b', 'b-r') and img:
        photo_html, pre = _band_photo_html(img, re.sub('<[^>]+>', '', h1_html))
        rcls = ' ph-b-r' if fam == 'b-r' else ''
        band = (f'<header class="pagehead ph-b{rcls}"><div class="ph-grid">'
                f'<div class="ph-txt"><i class="orn c"></i>{kick_html}<h1>{h1_html}</h1></div>{photo_html}</div></header>')
        return band, main, pre, img
    if fam == 'c' and img:
        photo_html, pre = _band_photo_html(img, re.sub('<[^>]+>', '', h1_html))
        band = f'<header class="pagehead ph-c"><i class="orn c"></i>{kick_html}<h1>{h1_html}</h1>{photo_html}</header>'
        return band, main, pre, img
    cls = 'pagehead ph-img' if img else 'pagehead'
    st, pre = (responsive_band(img) if img else ('', ''))
    return f'<header class="{cls}"{st}><i class="orn c"></i>{kick_html}<h1>{h1_html}</h1></header>', main, pre, img

def _restructure_restaurant(l, main):
    """v8 §9 (audit externe) : La Table n'avait qu'un seul bloc indifférencié (texte + 1
    photo), suivi d'une grille de 6 plats sans aucune légende visible (noms/descriptions
    présents uniquement en attributs data-t/data-d, pour la lightbox). On découpe en 3
    sections distinctes : intro/chef (inchangée), plats signature (légendes existantes
    rendues visibles — réutilise .pcard/.pimg/.pb, déjà utilisés pour Bien-être/Expériences),
    et ambiance (terrasse/patio — reprend la 3e phrase et le bouton déjà présents, sans rien
    ajouter)."""
    s = BeautifulSoup(main, 'html.parser')
    txt = s.select_one('.txt')
    ps = txt.select('p') if txt else []
    btn = txt.select_one('a.btn') if txt else None
    ambiance_p = ps[-1] if len(ps) >= 3 else None
    if ambiance_p: ambiance_p.extract()
    if btn: btn.extract()
    resgal = s.select_one('.resgal')
    if resgal:
        dishes = ''
        for a in resgal.select('a.gi'):
            img_src = a.get('href', '')
            name = a.get('data-t', '')
            desc_lines = [x.strip() for x in (a.get('data-d') or '').split('\n') if x.strip()]
            desc_html = f'<p class="pm">{"<br>".join(H.escape(x) for x in desc_lines)}</p>' if desc_lines else ''
            dishes += (f'<figure class="pcard dish"><div class="pimg"><img src="{img_src}" alt="{H.escape(name)}" loading="lazy"></div>'
                       f'<figcaption class="pb"><h3>{H.escape(name)}</h3>{desc_html}</figcaption></figure>')
        new_dishes = BeautifulSoup(
            f'<div class="resto-dishes"><h2>{H.escape(RESTO_DISH_HEADING[l])}</h2>'
            f'<div class="pgrid">{dishes}</div></div>', 'html.parser')
        resgal.replace_with(new_dishes)
    if ambiance_p or btn:
        amb_html = f'<div class="resto-ambiance"><h2>{H.escape(RESTO_AMBIANCE_HEADING[l])}</h2>'
        if ambiance_p: amb_html += str(ambiance_p)
        if btn: amb_html += str(btn)
        amb_html += '</div>'
        section = s.select_one('section.page.resto')
        if section: section.append(BeautifulSoup(amb_html, 'html.parser'))
    return str(s)

_WIX_DESC = 'first category luxury Riad'
def auto_desc(main_html):
    """Audit SEO (phase 11/N) : plusieurs pages (La Maison, Suites & Chambres, La Table,
    Avis, Contact, Services) n'avaient qu'une méta-description Wix générique en anglais,
    identique sur les 9 langues. On en extrait une vraie à partir du premier paragraphe
    de contenu réel déjà présent sur la page (aucun texte inventé), tronqué proprement."""
    try:
        s = BeautifulSoup(main_html, 'html.parser')
    except Exception:
        return ''
    for p in s.find_all('p'):
        t = re.sub(r'\s+', ' ', p.get_text(' ', strip=True)).strip()
        if len(t) >= 50:
            if len(t) > 155:
                cut = t[:155].rsplit(' ', 1)[0]
                t = cut + '…'
            return t
    return ''

def tune_main(main):
    main = main.replace('<a class="btn" href="https://le-grand-alcazar-riad.hotelrunner', '<a class="btn hot" href="https://le-grand-alcazar-riad.hotelrunner')
    main = main.replace('<button class="btn bk"', '<button class="btn hot bk"')
    main = main.replace('<form class="cform"', '<form class="cform"')
    # a11y : champ honeypot (anti-robot) du formulaire de contact — même correctif que celui du
    # footer (cf. footer()) : masqué visuellement par CSS mais pas du DOM, Lighthouse le signale
    # comme élément focusable caché sans aria-hidden. N'affecte pas la détection anti-spam (le
    # champ reste soumis normalement, seul son statut d'accessibilité change).
    main = re.sub(r'(<input type="text" name="website" class="hp" tabindex="-1" autocomplete="off")(?!\s+aria-hidden)', r'\1 aria-hidden="true"', main)
    return main

# ---------------------------------------------------------------- accueil (composé à partir des pages existantes)
def home_main(l, d):
    fr_nav = {u.split('/')[-1]: t for u, t in d['nav']}
    label = lambda slug: fr_nav.get(slug, '')
    S = lambda slug: soup(l, slug) or soup('fr', slug)
    hist, suites, resto, serv, boo = S('notre-histoire'), S('suites-chambres-1'), S('restaurant'), S('services'), S('book-online')
    avis = S('commentaires-et-distinctions')
    home = soup(l)
    pre = '' if l == 'fr' else f'/{l}'
    U = lambda slug: f'{pre}/{slug}'
    tour_h2 = text(home.select_one('.tour h2'))
    _, h_video, h_close = TXT[l]
    kick, h_hero, h_desc, btn_discover, btn_book = HERO[l]
    tour_btn = home.select_one('.tour a.btn')
    slides = json.load(open(os.path.join(SRC, 'js/slides.json')))
    first = slides[0]
    # 1. carrousel d'images — signature de marque « L'âme de Fès. L'art de recevoir. »
    hero = f'''<section class="hero" id="hero"><div class="hero-slides" data-slides="/js/slides.json"><img src="{first}" class="on" alt="" fetchpriority="high" decoding="async"></div>
<div class="hero-in"><span class="kicker">{H.escape(kick)}</span><h1>{H.escape(h_hero)}</h1><p class="hero-desc">{H.escape(h_desc)}</p>
<div class="hero-cta"><a class="btn light" href="{U('notre-histoire')}">{H.escape(btn_discover)}</a><a class="btn hot" href="{HOT}" target="_blank" rel="noopener">{H.escape(btn_book)}</a></div></div>
<div class="hero-meta"><span class="hero-dots"><i class="on"></i></span></div><span class="scrollcue" aria-hidden="true"></span></section>'''
    # 2. Notre histoire
    paras = hist.select('.txt p')
    pics = [i['src'] for i in hist.select('.pics img')]
    intro = f'''<section class="sec" id="histoire"><div class="in intro">
<div class="arches rv"><img src="{pics[0]}" alt="" loading="lazy" width="1000" height="1470"><img src="{pics[1]}" alt="" loading="lazy" width="1000" height="1200"></div>
<div class="intro-txt rv"><i class="orn"></i><h2>{H.escape(HIST[l])}</h2><div class="eyebrow">{H.escape(SIG_HISTOIRE[l])}</div>{paras[0]}{paras[-1]}
<div style="display:flex;gap:20px;flex-wrap:wrap;align-items:center"><a class="link arrow" href="{U('notre-histoire')}">{H.escape(label('notre-histoire'))}</a><a class="link arrow" href="{U('galerie')}">{H.escape(GALLERY[l][0])}</a><a class="link arrow" href="{U('carnet-de-fes')}">{H.escape(CARNET[l][0])}</a></div></div></div></section>'''
    # 3. Vidéo
    vid = f'''<section class="sec sand tour" id="visite"><div class="in"><h2 class="rv">{H.escape(h_video)}</h2>
<div class="vid rv"><video src="/assets/video/tour.mp4" poster="/assets/img/tour-poster.jpg" controls muted playsinline preload="metadata"></video><span class="play-badge" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></span></div>
<a class="btn" href="{U('suites-chambres-1')}">{inner(tour_btn)}</a></div></section>'''
    # 4. Nos Suites & Chambres
    sp = suites.select('.suites > p')
    cards = ''
    # v8 §6 : la galerie de La Maison (hist, .gal-sec) a été resserrée aux seules photos
    # histoire/architecture/artisanat — les sélections ci-dessous (rail Suites, photos
    # Terrasse) ne doivent plus en dépendre. On reconstitue l'ensemble complet d'origine
    # (23 photos) en fusionnant ce qui reste dans .gal-sec avec les photos retirées,
    # conservées telles quelles dans LEGACY_HISTOIRE_ROOM_PICS — rendu de l'accueil inchangé.
    _legacy_html = LEGACY_HISTOIRE_ROOM_PICS.get(l) or LEGACY_HISTOIRE_ROOM_PICS.get('fr', '')
    _legacy_soup = BeautifulSoup(_legacy_html, 'html.parser')
    for a in _legacy_soup.select('a.gi[data-g="h1"]')[:6]:
        cards += f'<a class="card" href="{U("suites-chambres-1")}"><div class="ph"><img src="{a["href"]}" alt="{H.escape(a.get("data-t",""))}" loading="lazy" width="900" height="1200"></div><h3>{H.escape(a.get("data-t",""))}</h3><p>{H.escape(a.get("data-d",""))}</p></a>'
    su_btn = suites.select_one('a.btn')
    st = f'''<section class="sec dark" id="suites"><div class="in"><div class="sec-top"><div class="sec-head rv"><i class="orn"></i><h2>{H.escape(label('suites-chambres-1'))}</h2><div class="eyebrow">{H.escape(SIG_SUITES[l])}</div><p>{inner(sp[0])}</p></div></div>
<div class="rail-wrap rv"><div class="rail" tabindex="0">{cards}</div><div class="rail-nav"><button class="rp" type="button" aria-label="‹">‹</button><button class="rn" type="button" aria-label="›">›</button></div></div>
<div class="rv" style="display:flex;gap:14px;flex-wrap:wrap;margin-top:24px"><a class="btn hot" style="margin-top:0" href="{HOT}" target="_blank" rel="noopener">{inner(su_btn)}</a><a class="btn light" style="margin-top:0" href="{U('suites-chambres-1')}">{H.escape(label('suites-chambres-1'))}</a><a class="link arrow" style="margin-top:14px" href="{U('offres-et-sejours')}">{H.escape(OFFERS[l][0])}</a></div></div></section>'''
    # 5. Notre Restaurant
    rp = resto.select('.txt p'); rbtn = resto.select_one('.txt a.btn')
    rmain = resto.select_one('.pics img')['src']
    rg = [a['href'] for a in resto.select('.resgal a.gi')][:3]
    rs = f'''<section class="sec" id="restaurant"><div class="in resto-h">
<div class="photos rv"><img src="{rmain}" alt="" loading="lazy" width="1200" height="750"><img src="{rg[0]}" alt="" loading="lazy" width="600" height="600"><img src="{rg[2]}" alt="" loading="lazy" width="600" height="600"></div>
<div class="rv"><i class="orn"></i><div class="eyebrow">{H.escape(KICKER_RESTO[l])}</div><h2>{H.escape(label('restaurant'))}</h2>{rp[0]}{rp[1]}<a class="btn" href="{rbtn['href']}">{inner(rbtn)}</a></div></div></section>'''
    # 6. Nos Services = les prestations réservables (page book-online)
    FROM = {'fr': 'À partir de {p} MAD', 'en': 'From {p} MAD', 'es': 'Desde {p} MAD', 'it': 'Da {p} MAD', 'de': 'Ab {p} MAD',
            'ar': 'ابتداءً من {p} MAD', 'zh': '{p} MAD 起', 'ko': '{p} MAD부터', 'ru': 'от {p} MAD'}
    def base(t):
        if ' - ' in t: return t.split(' - ')[0].strip()
        return re.sub(r'\s+(30 min|1 h)$', '', t).strip()
    items = []
    for art in boo.select('article.bo'):
        btn = art.select_one('button.bk')
        meta = text(art.select_one('.meta'))
        parts = [x.strip() for x in meta.split('·')]
        t = text(art.select_one('h2'))
        items.append(dict(img=art.select_one('img')['src'], t=t, base=base(t), price=int(btn['data-p']), dur=btn['data-d'],
                          where=' · '.join(parts[2:]) if len(parts) > 2 else '', btn=btn, pr=text(art.select_one('.meta b'))))
    groups = []
    for it in items:
        if groups and groups[-1][0]['base'] == it['base']: groups[-1].append(it)
        else: groups.append([it])
    # classement structurel (confirmé sur la source FR) : le dernier groupe = les 2 formules de
    # massage → section Bien-être ; tous les groupes précédents (visites, cours de cuisine,
    # table d'hôtes) → section Expériences. L'ordre des prestations est identique dans les 9 langues.
    wellbeing_groups = groups[-1:] if groups else []
    experience_groups = groups[:-1]
    def render_cards(gs):
        xs = ''
        for g in gs:
            f = g[0]
            if len(g) == 1:
                btn = f['btn']; btn['class'] = ['btn', 'hot', 'bk']
                pr, title, meta = f['pr'], f['t'], ' · '.join(x for x in [f['dur'], f['where']] if x)
                action = str(btn)
            else:  # plusieurs formules : un seul encart, le choix se fait sur la page /book-online
                pr = FROM[l].format(p=min(x['price'] for x in g)); title = f['base']
                meta = ' · '.join(x for x in [' / '.join(x['dur'] for x in g), f['where']] if x)
                blabel = inner(f['btn'])
                action = f'<a class="btn hot" href="{U("book-online")}">{blabel}</a>'
            xs += f'<article class="pcard rv"><div class="pimg"><img src="{f["img"]}" alt="" loading="lazy" width="800" height="600"><span class="pr">{H.escape(pr)}</span></div><div class="pb"><h3>{H.escape(title)}</h3><p class="pm">{H.escape(meta)}</p>{action}</div></article>'
        return xs
    serv_btn = serv.select_one('a.btn')
    # 6. Bien-être (hammam individuel + massages — équipements confirmés sur la page Services)
    wb_title, wb_tag, wb_desc = WELLBEING[l]
    wb = f'''<section class="sec sand" id="bien-etre"><div class="in"><div class="sec-head c rv"><i class="orn c"></i><h2><a href="{U('bien-etre')}">{H.escape(wb_title)}</a></h2><p class="eyebrow">{H.escape(wb_tag)}</p><p>{H.escape(wb_desc)}</p></div><div class="pgrid">{render_cards(wellbeing_groups)}</div>
<div style="text-align:center" class="rv"><a class="btn ghost" href="{U('book-online')}">{inner(serv_btn)}</a></div></div></section>'''
    # 7. Expériences (visites guidées, cours de cuisine, table d'hôtes)
    xp_title, xp_tag, xp_desc = EXPERIENCES[l]
    xp = f'''<section class="sec" id="experiences"><div class="in"><div class="sec-head c rv"><i class="orn c"></i><h2><a href="{U('experiences')}">{H.escape(xp_title)}</a></h2><p class="eyebrow">{H.escape(xp_tag)}</p><p>{H.escape(xp_desc)}</p></div><div class="pgrid">{render_cards(experience_groups)}</div>
<div style="text-align:center" class="rv"><a class="btn ghost" href="{U('book-online')}">{inner(serv_btn)}</a></div></div></section>'''
    # 8. Terrasse panoramique (photos réelles de la page Notre Histoire)
    terr_title, terr_desc = TERRASSE[l]
    # v8 §6 : une des 2 photos ("La terrasse") a été retirée de .gal-sec (hors-sujet
    # histoire/architecture/artisanat) — on la retrouve dans LEGACY_HISTOIRE_ROOM_PICS pour
    # que cette section de l'accueil garde ses 2 photos d'origine.
    _terr_legacy_html = LEGACY_HISTOIRE_ROOM_PICS.get(l) or LEGACY_HISTOIRE_ROOM_PICS.get('fr', '')
    _terr_full = BeautifulSoup(str(hist.select_one('.gal-sec') or '') + _terr_legacy_html, 'html.parser')
    terr_pics = [a['href'] for a in _terr_full.select('a.gi[data-g="h3"]') if 'errass' in a.get('data-t', '')][:2]
    # v8 §18 (audit externe) : secours déclenché seulement si 0 correspondance (bug) —
    # une correspondance partielle (1 sur 2, ex. après traduction d'une seule des deux
    # sources) perdait silencieusement la 2e photo. On sécurise avec un vrai secours à 2.
    if len(terr_pics) < 2: terr_pics = [a['href'] for a in _terr_full.select('a.gi[data-g="h3"]')][:2]
    terr = f'''<section class="sec dark" id="terrasse"><div class="in intro"><div class="arches rv">{''.join(f'<img src="{p}" alt="" loading="lazy" width="1000" height="1300">' for p in terr_pics)}</div>
<div class="intro-txt rv"><i class="orn"></i><h2>{H.escape(terr_title)}</h2><p>{H.escape(terr_desc)}</p></div></div></section>'''
    # 9. Avis & distinctions (badges réels de la page Commentaires & Distinctions — aucun avis inventé)
    avis_pics = [a['href'] for a in avis.select('.avis-pics a.gi')][:3] if avis else []
    av = ''
    if avis_pics:
        av = f'''<section class="sec sand" id="avis"><div class="in"><div class="sec-head c rv"><i class="orn c"></i><div class="eyebrow">{H.escape(KICKER_AVIS[l])}</div><h2>{H.escape(SIG_AVIS[l])}</h2></div>
<div class="avis-pics rv" style="display:flex;gap:18px;justify-content:center;flex-wrap:wrap">{''.join(f'<img src="{p}" alt="" loading="lazy" width="260" height="260" style="max-width:220px;height:auto">' for p in avis_pics)}</div>
<div style="text-align:center" class="rv"><a class="btn ghost" href="{U('commentaires-et-distinctions')}">{H.escape(SEEALL[l])}</a></div></div></section>'''
    # clôture
    closing = f'''<section class="closing"><img class="bg" src="{slides[3]}" alt="" loading="lazy"><h2 class="rv">{H.escape(h_close)}</h2>
<a class="btn hot rv" href="{HOT}" target="_blank" rel="noopener">{d['book']}</a><a class="tel rv" href="tel:+212662460760">+212 (0) 6 62 460 760</a></section>'''
    return hero + intro + vid + st + rs + wb + xp + terr + av + closing

# ------------------------------------------------- pages dédiées Bien-être / Expériences
# Réutilisent les prestations réelles de /book-online (mêmes données que les sections
# homepage WELLBEING/EXPERIENCES) — aucun contenu inventé.
FROM_PRICE = {'fr': 'À partir de {p} MAD', 'en': 'From {p} MAD', 'es': 'Desde {p} MAD', 'it': 'Da {p} MAD', 'de': 'Ab {p} MAD',
              'ar': 'ابتداءً من {p} MAD', 'zh': '{p} MAD 起', 'ko': '{p} MAD부터', 'ru': 'от {p} MAD'}

def prestation_groups(l):
    boo = soup(l, 'book-online') or soup('fr', 'book-online')
    def base(t):
        if ' - ' in t: return t.split(' - ')[0].strip()
        return re.sub(r'\s+(30 min|1 h)$', '', t).strip()
    items = []
    for art in boo.select('article.bo'):
        btn = art.select_one('button.bk')
        meta = text(art.select_one('.meta'))
        parts = [x.strip() for x in meta.split('·')]
        t = text(art.select_one('h2'))
        items.append(dict(img=art.select_one('img')['src'], t=t, base=base(t), price=int(btn['data-p']), dur=btn['data-d'],
                          where=' · '.join(parts[2:]) if len(parts) > 2 else '', btn=btn, pr=text(art.select_one('.meta b'))))
    groups = []
    for it in items:
        if groups and groups[-1][0]['base'] == it['base']: groups[-1].append(it)
        else: groups.append([it])
    return groups[-1:], groups[:-1]  # wellbeing_groups, experience_groups

def render_prestation_cards(l, gs, U):
    xs = ''
    for g in gs:
        f = g[0]
        if len(g) == 1:
            btn = f['btn']; btn['class'] = ['btn', 'hot', 'bk']
            pr, title, meta = f['pr'], f['t'], ' · '.join(x for x in [f['dur'], f['where']] if x)
            action = str(btn)
        else:
            pr = FROM_PRICE[l].format(p=min(x['price'] for x in g)); title = f['base']
            meta = ' · '.join(x for x in [' / '.join(x['dur'] for x in g), f['where']] if x)
            blabel = inner(f['btn'])
            action = f'<a class="btn hot" href="{U("book-online")}">{blabel}</a>'
        xs += f'<article class="pcard rv"><div class="pimg"><img src="{f["img"]}" alt="" loading="lazy" width="800" height="600"><span class="pr">{H.escape(pr)}</span></div><div class="pb"><h3>{H.escape(title)}</h3><p class="pm">{H.escape(meta)}</p>{action}</div></article>'
    return xs

def build_extra_page(l, kind):
    """kind : 'bien-etre' ou 'experiences'. Page dédiée construite sur le gabarit (nav/pied
    de page) de /book-online, avec les prestations réelles regroupées en cartes."""
    h = read(l, 'book-online') or read('fr', 'book-online')
    d = split_page(h)
    pre = '' if l == 'fr' else f'/{l}'
    U = lambda slug: f'{pre}/{slug}'
    url = f'{pre}/{kind}'
    wellbeing_groups, experience_groups = prestation_groups(l)
    if kind == 'bien-etre':
        title, tag, desc = WELLBEING[l]
        # v8 §10 (audit externe) : le bandeau reprenait la même photo que la carte « Massage »
        # juste en dessous (répétition visible au premier scroll). On y met plutôt une vraie
        # photo de la terrasse (déjà confirmée et utilisée pour la section Terrasse de l'accueil),
        # pour représenter aussi le hammam/bassin évoqués dans le texte, sans en inventer de photo.
        groups, bg_img = wellbeing_groups, '/assets/media/a0420c_cac7a68441a54dfc9f9255a7eb2a7677_mv2.jpg'
    else:
        title, tag, desc = EXPERIENCES[l]
        groups = experience_groups
        bg_img = experience_groups[0][0]['img'] if experience_groups and experience_groups[0] else '/assets/media/bo-tour.jpg'
    d['title'] = f'<title>{H.escape(title)} | Le Grand Alcazar</title>'
    d['desc'] = f'<meta name="description" content="{H.escape(desc)}">'
    can = f'https://www.legrandalcazar.com{url}'
    alts = ''
    for x in LANGS:
        xpre = '' if x == 'fr' else f'/{x}'
        alts += f'<link rel="alternate" hreflang="{x}" href="https://www.legrandalcazar.com{xpre}/{kind}">'
    alts += f'<link rel="alternate" hreflang="x-default" href="https://www.legrandalcazar.com/{kind}">'
    d['links'] = f'<link rel="canonical" href="{can}">' + alts + breadcrumb_ld(l, title, can)
    d['body'] = f'p-{kind.replace("-", "")} l-{l}'
    d['flags'] = [((('' if x == 'fr' else f'/{x}') + f'/{kind}'), ' on' if x == l else '', x) for x in LANGS]
    photo_html, _band_pre = _band_photo_html(bg_img, title)
    d['links'] += _band_pre
    # Type B (Éditorial, v7 §5) : photo à droite pour Bien-être, à gauche pour Expériences —
    # alternance volontaire pour ne pas répéter la même composition d'une page à l'autre.
    rcls = ' ph-b-r' if kind == 'bien-etre' else ''
    # v8 §4 : surtitre (ex-titre, "Bien-être"/"Expériences") + grand titre (ex-tag, la
    # signature éditoriale) — mêmes libellés déjà traduits dans WELLBEING/EXPERIENCES,
    # seuls les rôles visuels sont inversés (surtitre petit au-dessus, grand titre en h1).
    band = (f'<header class="pagehead ph-b{rcls}"><div class="ph-grid">'
            f'<div class="ph-txt"><i class="orn c"></i><p class="kicker">{H.escape(title)}</p><h1>{H.escape(tag)}</h1></div>{photo_html}</div></header>')
    cards = render_prestation_cards(l, groups, U)
    if kind == 'bien-etre':
        # v8 §10 : 3 sections éditoriales réelles (hammam / massage / terrasse-bassin) —
        # aucune photo ni texte inventés : la photo et la légende du bassin viennent de
        # La Maison (déjà réelles et traduites quand elles existent), le massage réutilise
        # la carte réservable existante ; le hammam, sans photo dédiée disponible sur le
        # site, reste volontairement en texte seul (pas de photo de substitution inventée).
        hammam_lbl, massage_lbl, terrasse_lbl = WB_SECTIONS.get(l, WB_SECTIONS['fr'])
        hist = soup(l, 'notre-histoire') or soup('fr', 'notre-histoire')
        bassin_img = '/assets/media/a0420c_2914afb2862b46a68e9c98afb97b416e_mv2.jpg'
        bassin_a = hist.select_one(f'a.gi[href="{bassin_img}"]') if hist else None
        bassin_cap = bassin_a.get('data-d', '') if bassin_a else ''
        bassin_photo, bassin_pre = _band_photo_html(bassin_img, terrasse_lbl)
        d['links'] += bassin_pre
        bassin_cap_html = f'<p class="pm">{H.escape(bassin_cap)}</p>' if bassin_cap else ''
        main = f'''<main id="main">{band}<section class="page suites"><div class="in" style="max-width:1120px;margin:0 auto">
<p>{H.escape(desc)}</p>
<div class="wb-sec wb-hammam"><i class="orn c"></i><h2>{H.escape(hammam_lbl)}</h2></div>
<div class="wb-sec wb-massage"><h2>{H.escape(massage_lbl)}</h2><div class="pgrid">{cards}</div></div>
<div class="wb-sec wb-terrasse"><div class="wb-terrasse-grid"><div class="wb-terrasse-txt"><h2>{H.escape(terrasse_lbl)}</h2>{bassin_cap_html}</div><div class="wb-terrasse-img">{bassin_photo}</div></div></div>
</div></section></main>'''
    elif kind == 'experiences':
        # v8 §11 : 2 sections thématiques réelles au lieu d'une grille indifférenciée —
        # découpage par nature des prestations (au Riad vs sorties guidées), sans aucune
        # catégorie ni fait inventés.
        culinary = [g for g in groups if g[0]['base'] in EXP_CULINARY_BASES]
        excursions = [g for g in groups if g[0]['base'] not in EXP_CULINARY_BASES]
        culinary_cards = render_prestation_cards(l, culinary, U) if culinary else ''
        excursion_cards = render_prestation_cards(l, excursions, U) if excursions else ''
        sections = ''
        if culinary_cards:
            sections += f'<div class="wb-sec wb-massage"><h2>{H.escape(EXP_CULINARY_HEADING[l])}</h2><div class="pgrid">{culinary_cards}</div></div>'
        if excursion_cards:
            sections += f'<div class="wb-sec wb-massage"><h2>{H.escape(EXP_EXCURSION_HEADING[l])}</h2><div class="pgrid">{excursion_cards}</div></div>'
        main = f'''<main id="main">{band}<section class="page suites"><div class="in" style="max-width:1120px;margin:0 auto">
<p>{H.escape(desc)}</p>
{sections}
</div></section></main>'''
    else:
        main = f'''<main id="main">{band}<section class="page suites"><div class="in" style="max-width:1120px;margin:0 auto">
<p>{H.escape(desc)}</p>
<div class="pgrid" style="margin-top:32px">{cards}</div>
</div></section></main>'''
    out = head(d, kind, url, page_image=bg_img) + header(d, solid=False, active_href=url) + '\n' + main + '\n' + footer(d)
    out += d['tail'].replace('?v=451', f'?v={VER}').replace('<script src="/js/account.js"></script>', '')
    bk = re.search(r'<script>window\.__bkL=.*?</script>', h, re.S).group(0)
    out = out.replace('<script src="/js/gallery.js', bk + f'<script src="/js/booking.js?v={VER}"></script><script src="/js/gallery.js', 1)
    dest = os.path.join(OUT, '' if l == 'fr' else l, kind, 'index.html')
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, 'w', encoding='utf8').write(out)
    return dest

def build_gallery_page(l):
    """Page dédiée Galerie : réutilise telles quelles les photos (et légendes) déjà présentes
    sur La Maison (3 collages) et La Table (6 photos du restaurant) — aucune image ni légende
    nouvelle, juste une vue d'ensemble en un seul endroit."""
    h = read(l, 'book-online') or read('fr', 'book-online')
    d = split_page(h)
    pre = '' if l == 'fr' else f'/{l}'
    url = f'{pre}/galerie'
    title, tag = GALLERY[l]
    hist = soup(l, 'notre-histoire') or soup('fr', 'notre-histoire')
    resto = soup(l, 'restaurant') or soup('fr', 'restaurant')
    gal_sec = hist.select_one('.gal-sec')
    bg_img = [img['src'] for img in hist.select('.pics img')][:1]
    bg_img = bg_img[0] if bg_img else '/assets/media/bo-tour.jpg'
    resto_pics = resto.select('.resgal a.gi')
    for a in resto_pics: a['data-cat'] = 'table'
    resto_collage = ''.join(str(a) for a in resto_pics)
    legacy_room_pics = LEGACY_HISTOIRE_ROOM_PICS.get(l) or LEGACY_HISTOIRE_ROOM_PICS.get('fr', '')
    _legacy_soup = BeautifulSoup(legacy_room_pics, 'html.parser')
    for a in _legacy_soup.select('a.gi'): a['data-cat'] = 'suites'
    legacy_room_pics = str(_legacy_soup)
    d['title'] = f'<title>{H.escape(title)} | Le Grand Alcazar</title>'
    d['desc'] = f'<meta name="description" content="{H.escape(tag)}">'
    can = f'https://www.legrandalcazar.com{url}'
    alts = ''
    for x in LANGS:
        xpre = '' if x == 'fr' else f'/{x}'
        alts += f'<link rel="alternate" hreflang="{x}" href="https://www.legrandalcazar.com{xpre}/galerie">'
    alts += f'<link rel="alternate" hreflang="x-default" href="https://www.legrandalcazar.com/galerie">'
    d['links'] = f'<link rel="canonical" href="{can}">' + alts + breadcrumb_ld(l, title, can)
    d['body'] = f'p-galerie l-{l}'
    d['flags'] = [((('' if x == 'fr' else f'/{x}') + '/galerie'), ' on' if x == l else '', x) for x in LANGS]
    photo_html, _band_pre = _band_photo_html(bg_img, title)
    d['links'] += _band_pre
    # Type C (Photographique, v7 §5/§13) : fond clair, pas de filtre bleu — la galerie
    # elle-même est l'identité visuelle de cette page.
    # v8 §4 : surtitre "Galerie" (GALLERY[l][0]) + grand titre éditorial SIG_GALERIE — le
    # 2e élément de GALLERY reste utilisé tel quel pour la méta-description (desc ci-dessus).
    band = f'<header class="pagehead ph-c"><i class="orn c"></i><p class="kicker">{H.escape(title)}</p><h1>{H.escape(SIG_GALERIE[l])}</h1>{photo_html}</header>'
    gal_inner = gal_sec.decode_contents() if gal_sec else ''
    _gi_soup = BeautifulSoup(gal_inner, 'html.parser')
    for a in _gi_soup.select('a.gi'): a['data-cat'] = 'maison'
    gal_inner = str(_gi_soup)
    # v8 §12 : filtre réel (Tout / La Maison / Suites & Chambres / La Table) — mêmes libellés
    # déjà traduits que le menu principal (NAV), + GAL_ALL pour l'option "Tout".
    cats = [('', GAL_ALL[l]), ('maison', NAV[l]['notre-histoire']),
            ('suites', NAV[l]['suites-chambres-1']), ('table', NAV[l]['restaurant'])]
    filter_html = '<div class="gal-filter">' + ''.join(
        f'<button type="button" class="{"on" if c == "" else ""}" data-cat="{c}">{H.escape(lbl)}</button>'
        for c, lbl in cats) + '</div>'
    main = f'<main id="main">{band}<section class="page">{filter_html}<div class="gal-sec" style="margin-top:0">{gal_inner}<div class="collage">{legacy_room_pics}{resto_collage}</div></div></section></main>'
    out = head(d, 'galerie', url, page_image=bg_img) + header(d, solid=False, active_href=url) + '\n' + main + '\n' + footer(d)
    out += d['tail'].replace('?v=451', f'?v={VER}').replace('<script src="/js/account.js"></script>', '')
    dest = os.path.join(OUT, '' if l == 'fr' else l, 'galerie', 'index.html')
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, 'w', encoding='utf8').write(out)
    return dest

def build_offers_page(l):
    """Page dédiée Offres & Séjours (brouillon, cf. cahier des charges) : volontairement sobre —
    aucun forfait ni tarif n'existe ailleurs sur le site, donc pas de prix inventés. On explique
    comment composer un séjour à partir des pages réelles existantes, et on renvoie vers le
    moteur de réservation (tarifs réels en temps réel) et le contact pour le sur-mesure."""
    h = read(l, 'book-online') or read('fr', 'book-online')
    d = split_page(h)
    nav_map = {u.split('/')[-1]: t for u, t in d['nav']}
    pre = '' if l == 'fr' else f'/{l}'
    U = lambda slug: f'{pre}/{slug}'
    url = f'{pre}/offres-et-sejours'
    title, tag, desc = OFFERS[l]
    parts = [(nav_map.get('suites-chambres-1', 'Suites & Chambres'), U('suites-chambres-1')),
             (WELLBEING[l][0], U('bien-etre')),
             (EXPERIENCES[l][0], U('experiences')),
             (nav_map.get('contact', 'Contact'), U('contact'))]
    d['title'] = f'<title>{H.escape(title)} | Le Grand Alcazar</title>'
    d['desc'] = f'<meta name="description" content="{H.escape(desc)}">'
    can = f'https://www.legrandalcazar.com{url}'
    alts = ''
    for x in LANGS:
        xpre = '' if x == 'fr' else f'/{x}'
        alts += f'<link rel="alternate" hreflang="{x}" href="https://www.legrandalcazar.com{xpre}/offres-et-sejours">'
    alts += '<link rel="alternate" hreflang="x-default" href="https://www.legrandalcazar.com/offres-et-sejours">'
    d['links'] = f'<link rel="canonical" href="{can}">' + alts + breadcrumb_ld(l, title, can)
    d['body'] = f'p-offres l-{l}'
    d['flags'] = [((('' if x == 'fr' else f'/{x}') + '/offres-et-sejours'), ' on' if x == l else '', x) for x in LANGS]
    photo_html, _band_pre = _band_photo_html('/assets/media/bo-tour.jpg', title)
    d['links'] += _band_pre
    # Type B (Éditorial, v7 §5/§14), photo à droite : la page reste volontairement sobre
    # (aucun forfait officiel) mais sort du même filtre bleu que les autres pages v6.
    # v8 §4 : même convention surtitre/grand-titre que Bien-être/Expériences/Galerie
    # (kicker = titre court, h1 = signature éditoriale) — jusqu'ici inversée sur cette page.
    band = (f'<header class="pagehead ph-b ph-b-r"><div class="ph-grid">'
            f'<div class="ph-txt"><i class="orn c"></i><p class="kicker">{H.escape(title)}</p><h1>{H.escape(tag)}</h1></div>{photo_html}</div></header>')
    # v8 §13 (audit externe) : remplace les 4 boutons texte par 4 tuiles réelles (mêmes
    # photos et libellés déjà utilisés ailleurs sur le site — suite, table, bien-être,
    # expériences), qui illustrent concrètement "composez votre séjour" sans aucun forfait
    # ni prix inventés ; le lien Contact et le CTA de réservation restent en texte simple.
    legacy0 = LEGACY_HISTOIRE_ROOM_PICS.get(l) or LEGACY_HISTOIRE_ROOM_PICS.get('fr', '')
    _sm = re.search(r'href="([^"]+)"', legacy0)
    suite_img = _sm.group(1) if _sm else '/assets/media/bo-tour.jpg'
    tiles = [
        (suite_img, nav_map.get('suites-chambres-1', 'Suites & Chambres'), U('suites-chambres-1')),
        ('/assets/media/bo-table.jpg', nav_map.get('restaurant', 'La Table'), U('restaurant')),
        ('/assets/media/bo-massage.jpg', WELLBEING[l][0], U('bien-etre')),
        ('/assets/media/bo-cuisine.jpg', EXPERIENCES[l][0], U('experiences')),
    ]
    tiles_html = ''.join(
        f'<a class="pcard rv" href="{href}"><div class="pimg"><img src="{img}" alt="" loading="lazy" width="800" height="600"></div>'
        f'<div class="pb"><h3>{H.escape(lbl)}</h3></div></a>' for img, lbl, href in tiles)
    contact_label, contact_href = parts[-1]
    main = f'''<main id="main">{band}<section class="page suites"><div class="in" style="max-width:1120px;margin:0 auto;text-align:center">
<p style="max-width:760px;margin-inline:auto">{H.escape(desc)}</p>
<div class="pgrid" style="margin-top:32px">{tiles_html}</div>
<div style="margin-top:36px;display:flex;gap:14px;flex-wrap:wrap;justify-content:center">
<a class="btn hot" href="{HOT}" target="_blank" rel="noopener">{d['book']}</a>
<a class="btn" href="{contact_href}">{H.escape(contact_label)}</a>
</div>
</div></section></main>'''
    out = head(d, 'offres-et-sejours', url, page_image='/assets/media/bo-tour.jpg') + header(d, solid=False, active_href=url) + '\n' + main + '\n' + footer(d)
    out += d['tail'].replace('?v=451', f'?v={VER}').replace('<script src="/js/account.js"></script>', '')
    dest = os.path.join(OUT, '' if l == 'fr' else l, 'offres-et-sejours', 'index.html')
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, 'w', encoding='utf8').write(out)
    return dest

def build_carnet_page(l):
    """Page dédiée Carnet de Fès : reprend telles quelles les excursions réelles déjà décrites
    sur l'ancienne page /services (titres + descriptions + photos originales, data-t/data-d),
    à l'exclusion du Restaurant et des Cours de cuisine déjà mis en avant ailleurs — aucun
    contenu nouveau, simple mise en avant éditoriale de l'existant. v8 §14 : distingue
    désormais ces excursions réservables d'un premier article éditorial complet (sur un sujet
    déjà présent sur le site, cf. CARNET_ARTICLE)."""
    h = read(l, 'book-online') or read('fr', 'book-online')
    d = split_page(h)
    pre = '' if l == 'fr' else f'/{l}'
    url = f'{pre}/carnet-de-fes'
    title, tag = CARNET[l]
    serv = soup(l, 'services') or soup('fr', 'services')
    items = serv.select('.grid3 a.gi')[2:]  # on laisse de côté Restaurant / Cours de cuisine
    bg_img = items[0]['href'] if items else '/assets/media/bo-tour.jpg'
    cards = ''
    for a in items:
        img, t, desc = a.select_one('img')['src'], a.get('data-t', ''), a.get('data-d', '').split('\n')[0]
        cards += f'<article class="pcard rv"><div class="pimg"><img src="{img}" alt="{H.escape(t)}" loading="lazy" width="800" height="600"></div><div class="pb"><h3>{H.escape(t)}</h3><p class="pm">{H.escape(desc)}</p></div></article>'
    # v8 §14 : le premier article s'appuie sur la photo réelle "Tanneries Chouara" déjà
    # présente sur /services (aucune nouvelle photo).
    tannerie_a = next((a for a in items if a.get('data-t', '') == 'Tanneries Chouara'), None)
    art_img = tannerie_a.select_one('img')['src'] if tannerie_a else bg_img
    art_title, art_chapo, art_paras = CARNET_ARTICLE.get(l, CARNET_ARTICLE['fr'])
    article_html = (f'<article class="carnet-art"><div class="pimg"><img src="{art_img}" alt="{H.escape(art_title)}" loading="lazy" width="1000" height="750"></div>'
                     f'<div class="carnet-art-txt"><h3>{H.escape(art_title)}</h3><p class="chapo">{H.escape(art_chapo)}</p>'
                     + ''.join(f'<p>{H.escape(p)}</p>' for p in art_paras) + '</div></article>')
    d['title'] = f'<title>{H.escape(title)} | Le Grand Alcazar</title>'
    d['desc'] = f'<meta name="description" content="{H.escape(tag)}">'
    can = f'https://www.legrandalcazar.com{url}'
    alts = ''
    for x in LANGS:
        xpre = '' if x == 'fr' else f'/{x}'
        alts += f'<link rel="alternate" hreflang="{x}" href="https://www.legrandalcazar.com{xpre}/carnet-de-fes">'
    alts += '<link rel="alternate" hreflang="x-default" href="https://www.legrandalcazar.com/carnet-de-fes">'
    # SEO v7 §20 : schéma Article (mise en avant éditoriale des excursions réelles du riad) —
    # pas de date de publication : aucune date réelle n'étant disponible, on n'en invente pas.
    article_ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': title, 'description': tag,
                  'publisher': {'@type': 'Organization', 'name': 'Le Grand Alcazar - Riad'}}
    if items:
        article_ld['image'] = f"https://www.legrandalcazar.com{items[0]['href']}"
    d['links'] = (f'<link rel="canonical" href="{can}">' + alts + breadcrumb_ld(l, title, can)
                  + f'<script type="application/ld+json">{json.dumps(article_ld, ensure_ascii=False)}</script>')
    d['body'] = f'p-carnet l-{l}'
    d['flags'] = [((('' if x == 'fr' else f'/{x}') + '/carnet-de-fes'), ' on' if x == l else '', x) for x in LANGS]
    photo_html, _band_pre = _band_photo_html(bg_img, title)
    d['links'] += _band_pre
    # Type B (Éditorial, v7 §5/§15), photo à gauche — alterne avec Offres & Séjours (à droite).
    # v8 §4 : même convention surtitre/grand-titre que Bien-être/Expériences/Galerie/Offres.
    band = (f'<header class="pagehead ph-b"><div class="ph-grid">'
            f'<div class="ph-txt"><i class="orn c"></i><p class="kicker">{H.escape(title)}</p><h1>{H.escape(tag)}</h1></div>{photo_html}</div></header>')
    main = f'''<main id="main">{band}<section class="page suites"><div class="in" style="max-width:1120px;margin:0 auto">
<div class="wb-sec wb-massage"><h2>{H.escape(CARNET_EXCURSIONS_H[l])}</h2><div class="pgrid" style="margin-top:0">{cards}</div></div>
<div class="wb-sec carnet-articles"><h2>{H.escape(CARNET_ARTICLES_H[l])}</h2>{article_html}</div>
</div></section></main>'''
    out = head(d, 'carnet-de-fes', url, page_image=bg_img) + header(d, solid=False, active_href=url) + '\n' + main + '\n' + footer(d)
    out += d['tail'].replace('?v=451', f'?v={VER}').replace('<script src="/js/account.js"></script>', '')
    dest = os.path.join(OUT, '' if l == 'fr' else l, 'carnet-de-fes', 'index.html')
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, 'w', encoding='utf8').write(out)
    return dest

# ---------------------------------------------------------------- construction
def build_page(l, slug):
    h = read(l, slug)
    if h is None: return
    d = split_page(h)
    key = (d['body'].split()[0].replace('p-', ''))
    is_home = key == 'home'
    active = None
    for hr, t in d['nav']:
        pass
    m = re.search(r'<a href="([^"]*)" class="active" aria-current="page">', re.search(r'<nav class="nav">(.*?)</nav>', h, re.S).group(1))
    active = m.group(1) if m else None
    if is_home:
        main = home_main(l, d)
        band = ''
        band_img = None
    else:
        main = tune_main(d['main'])
        if key in H1KEY:
            if key in BAND_SIG:
                # v8 §4 : surtitre + grand titre — le grand titre devient le <h1> du bandeau,
                # le surtitre est injecté juste devant (cf. page_head_band, qui le recapture).
                kick_d, sig_d = BAND_SIG[key]
                kick_txt = kick_d.get(l) or NAV[l][H1KEY[key]]
                h1_txt = sig_d.get(l) or NAV[l][H1KEY[key]]
                repl = '<p class="kicker">' + H.escape(kick_txt) + '</p><h1>' + H.escape(h1_txt) + '</h1>'
            else:
                h1_txt = PAGEH1.get(key, {}).get(l) or NAV[l][H1KEY[key]]
                repl = '<h1>' + H.escape(h1_txt) + '</h1>'
            main = re.sub(r'<h1>.*?</h1>', repl, main, count=1, flags=re.S)
        band, main, band_preload, band_img = page_head_band(key, main)
        # performance (audit, régression LCP mobile relevée sur "Suites & Chambres" : l'image de
        # bandeau n'est posée qu'en arrière-plan CSS d'un ::before, invisible au preload scanner
        # du navigateur, donc découverte très tardivement sur mobile) : on la précharge
        # explicitement dès le <head>, pour toutes les pages à bandeau image — avec, depuis le
        # 25/11/2026, une variante mobile nettement plus légère (cf. responsive_band()) pour
        # résoudre réellement le LCP (et non plus seulement le découvrir plus tôt).
        d['links'] += band_preload
        if key == 'suites':
            # a11y : un <h2> (masqué visuellement) précède la grille, pour ne pas sauter
            # de h1 à h3 (noms de chambres) — cf. priorité accessibilité de l'état des lieux.
            heading = f'<h2 class="sr-only">{H.escape(R.UI["rooms_heading"][l])}</h2>'
            main = re.sub(r'<div class="car">.*?</div></div>(?=\s*<a class="btn)', lambda m: heading + rooms_grid(l), main, count=1, flags=re.S)
        if key == 'contact':
            main = re.sub(r'(<section class="page contact">)\s*<h2>.*?</h2>', r'\1', main, count=1, flags=re.S)
            main = _add_contact_extras(l, main)
        if key == 'restaurant': main = _restructure_restaurant(l, main)
        if key == 'avis': main = _add_avis_fallback(l, main)
        if key == 'histoire':
            # v8 §6 (audit externe) : la galerie du bas a été resserrée en amont (source HTML,
            # 9 langues) aux seules photos histoire/architecture/artisanat ; on y ajoute ici un
            # lien vers la page Galerie complète, comme demandé. Le lien est placé APRÈS la
            # fermeture de .gal-sec (et non dedans) pour ne pas être repris par
            # build_gallery_page(), qui réutilise .gal-sec tel quel.
            gal_pre = '' if l == 'fr' else f'/{l}'
            gal_link = f'<a class="btn" href="{gal_pre}/galerie" style="margin-top:20px">{H.escape(GAL_LINK[l])}</a>'
            main = re.sub(r'(<div class="gal-sec"><div class="collage">.*?</div></div>)',
                           lambda m: m.group(1) + gal_link, main, count=1, flags=re.S)
    if _WIX_DESC in d['desc'] or not d['desc']:
        real_desc = HERO[l][2] if is_home else (auto_desc(band + main) or EXTRA_DESC.get(key, {}).get(l))
        if real_desc:
            d['desc'] = f'<meta name="description" content="{H.escape(real_desc)}">'
    # SEO v7 §20 : BreadcrumbList sur toutes les pages intérieures (2 niveaux : Accueil > page),
    # à partir de l'URL canonique déjà présente (aucune URL inventée) et du libellé de nav réel.
    if not is_home:
        pre = '' if l == 'fr' else f'/{l}'
        home_item = f'https://www.legrandalcazar.com{pre}/'
        can_m = re.search(r'<link rel="canonical" href="([^"]*)">', d['links'])
        page_item = can_m.group(1) if can_m else f'{home_item}{slug}'
        crumb_label = next((t for hr, t in d['nav'] if hr == active), NAV[l].get(key, d.get('title', '')))
        home_label = NAV[l].get('home', 'Accueil')
        crumb_ld = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': home_label, 'item': home_item},
            {'@type': 'ListItem', 'position': 2, 'name': crumb_label, 'item': page_item},
        ]}
        d['links'] += f'<script type="application/ld+json">{json.dumps(crumb_ld, ensure_ascii=False)}</script>'
    # SEO v7 §20 : schéma Restaurant sur la page La Table — faits déjà publiés uniquement
    # (nom, type de cuisine, adresse de l'établissement) ; pas d'horaires ni de gamme de prix
    # inventés, aucune donnée de ce type n'existant ailleurs sur le site.
    if key == 'restaurant':
        resto_img_m = re.search(r'<div class="pics"><img src="([^"]*)"', main)
        resto_ld = {'@context': 'https://schema.org', '@type': 'Restaurant', 'name': 'Le Grand Alcazar - Riad',
                    'servesCuisine': 'Moroccan',
                    'address': {'@type': 'PostalAddress', 'streetAddress': '15, Derb El Guebbas, Batha',
                                'addressLocality': 'Fès', 'postalCode': '30110', 'addressCountry': 'MA'},
                    'telephone': '+212662460760', 'url': (can_m.group(1) if can_m else '')}
        if resto_img_m: resto_ld['image'] = f'https://www.legrandalcazar.com{resto_img_m.group(1)}'
        d['links'] += f'<script type="application/ld+json">{json.dumps(resto_ld, ensure_ascii=False)}</script>'
    out = head(d, 'home' if is_home else key, active, page_image=band_img) + header(d, solid=not (is_home or band), active_href=active)
    out += f'\n<main id="main">{band}{main}</main>\n' + footer(d)
    tail = d['tail'].replace('?v=451', f'?v={VER}').replace('<script src="/js/account.js"></script>', '')
    if is_home:
        bo = read(l, 'book-online') or read('fr', 'book-online')
        bk = re.search(r'<script>window\.__bkL=.*?</script>', bo, re.S).group(0)
        tail = tail.replace('<script src="/js/gallery.js', bk + f'<script src="/js/booking.js?v={VER}"></script><script src="/js/gallery.js', 1)
    out += tail
    out = out.replace(' | <a href="mailto:', ' <span class="sep">|</span> <a href="mailto:')
    out = out.replace('+212 (0) 662 460 760', '<bdi dir="ltr">+212 (0) 662 460 760</bdi>')
    out = out.replace('output=embed" loading="lazy"', 'output=embed" loading="eager"')
    out = out.replace('<div class="map"><iframe src="https://maps.google.com/maps?q=34.059989,-4.9799971&amp;', '<div class="map"><div class="mapf"><iframe src="https://maps.google.com/maps?q=34.059989,-4.9799971&amp;ll=34.059989,-4.9799971&amp;')
    out = out.replace('</iframe><a class="btn" href="https://www.google.com/maps/place', '</iframe><i class="mpin" aria-hidden="true"></i></div><a class="btn" href="https://www.google.com/maps/place')
    out = out.replace('Réserver votre table', 'Réservez votre table').replace('Réserver nos prestations', 'Réservez nos prestations').replace('Découvrir nos suites', 'Découvrez nos suites')
    dest = os.path.join(OUT, '' if l == 'fr' else l, slug or '', 'index.html')
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, 'w', encoding='utf8').write(out)
    return dest


# ---------------------------------------------------------------- suites & chambres (pages détail + grille)
def room_photos(slug):
    """Photos déposées dans build/rooms/<slug>/ (1.jpg, 2.jpg…), triées numériquement.
    v8 (dernières corrections) : exclut les vignettes générées (1-card.jpg, 1-card-420.jpg,
    1-card-720.jpg — cf. room_card_photo/room_card_responsive), qui n'étaient pas filtrées
    ici et se glissaient dans la galerie de la fiche comme autant de quasi-doublons de la
    photo n°1 (plusieurs fois, en plus de la répétition bandeau/galerie déjà corrigée)."""
    fs = glob.glob(os.path.join(BUILD, 'rooms', slug, '*.jpg'))
    fs = [f for f in fs if '-card' not in os.path.basename(f)]
    fs.sort(key=lambda f: int(re.sub(r'\D', '', os.path.basename(f)) or 0))
    return [f'/assets/media/rooms/{slug}/{os.path.basename(f)}' for f in fs]

@lru_cache(maxsize=None)
def room_card_photo(slug):
    """Vignette compressée (900px de large max) de la 1re photo, pour la grille liste
    uniquement — perf (LCP mobile) ; la photo pleine résolution reste utilisée en lightbox
    et sur la fiche détaillée. Retombe sur l'originale si la vignette n'existe pas."""
    thumb_fs = os.path.join(BUILD, 'rooms', slug, '1-card.jpg')
    if os.path.isfile(thumb_fs):
        try:
            from PIL import Image
            with Image.open(thumb_fs) as im:
                w, h = im.size
            return f'/assets/media/rooms/{slug}/1-card.jpg', w, h
        except Exception:
            pass
    ph = room_photos(slug)
    return (ph[0], 900, 1100) if ph else (None, 900, 1100)

@lru_cache(maxsize=None)
def room_card_responsive(slug):
    """Correctif LCP mobile (25/11/2026) : la vignette 900px (ci-dessus) reste bien plus
    large que sa taille d'affichage réelle (~170-360px selon le nombre de colonnes de la
    grille), et les 14 vignettes se chargent toutes en même temps au premier affichage —
    ce qui sature la bande passante mobile simulée et retarde même les ressources
    préchargées en priorité haute (mesuré par trace réseau réelle, cf. NOTE-POUR-AUDITEUR.md
    / TODO.md). On génère donc deux largeurs (420/720) en JPEG et WebP, servies via <picture>
    avec srcset+sizes, sans jamais toucher à la photo pleine résolution (fiche/lightbox).
    Retourne None si la vignette source est absente."""
    thumb_fs = os.path.join(BUILD, 'rooms', slug, '1-card.jpg')
    if not os.path.isfile(thumb_fs):
        return None
    out_dir = os.path.join(BUILD, 'rooms', slug)
    variants = respimg.card_variants(thumb_fs, out_dir, '1-card')
    base_url = f'/assets/media/rooms/{slug}/'
    return {
        w: {'jpg': base_url + os.path.basename(v['jpg']),
            'webp': base_url + os.path.basename(v['webp']),
            'w': v['w'], 'h': v['h']}
        for w, v in variants.items()
    }

def room_ready(slug): return bool(room_photos(slug)) and bool(R.ROOMS[slug].get('desc'))
def room_url(l, slug): return ('' if l == 'fr' else f'/{l}') + '/suites-chambres-1/' + R.ROOMS[slug]['path']

def room_facts(l, r):
    T = lambda k: R.UI[k][l]
    out = []
    if r.get('people'): out.append((T('cap'), T('p1') if r['people'] == 1 else T('pN').format(n=r['people'])))
    if r.get('size'): out.append((T('size'), f"\u2066{r['size']} m²\u2069"))
    if r.get('beds'):
        # v8 (dernières corrections, lot 2) : lits doubles/queen/king présentés avant les lits
        # individuels, pluriel grammaticalement correct au-delà de 1 (ex. "2 single bed" ->
        # "2 single beds"), et mention de la configuration alternative modulable uniquement
        # quand elle est confirmée (cf. beds_alt). L'annotation est accolée au lit réellement
        # modulable (king/queen, jamais aux lits 1 place déjà existants par ailleurs dans la
        # même chambre) : plusieurs chambres ont à la fois des lits 1 place ET un king/queen
        # modulable (ex. Diamant, Grenat...), donc on ne peut plus se contenter de l'ajouter
        # en fin de chaîne — cela l'aurait accolée à tort aux lits 1 place déjà présents.
        ordered = sorted(r['beds'], key=lambda nt: 1 if nt[1] == 'single' else 0)
        parts = []
        for n, t in ordered:
            txt = (R.BED_PLURAL[t][l] if n != 1 and t in R.BED_PLURAL else R.BED[t][l]).format(n=n)
            if r.get('beds_alt') and t != 'single':
                txt += R.BED_ALT_TWIN[l]
            parts.append(txt)
        out.append((T('beds'), ' · '.join(parts)))
    if r.get('floor'): out.append((T('floor'), R.FLOOR[r['floor']][l]))
    return out

def room_card(l, slug, eager=False):
    r = R.ROOMS[slug]; ph = room_photos(slug); T = lambda k: R.UI[k][l]
    ready = room_ready(slug)
    tag = R.TAG[r['tag']][l] if r.get('tag') else ''
    meta = ''
    if r.get('people'): meta = T('p1') if r['people'] == 1 else T('pN').format(n=r['people'])
    if r.get('size'): meta += (' · ' if meta else '') + f"\u2066{r['size']} m²\u2069"
    href = room_url(l, slug) + '/'
    if ph:
        src, w, h = room_card_photo(slug)
        # perf (LCP mobile, 25/11/2026) : les premières cartes visibles restent en chargement
        # eager (pas de lazy loading pour du contenu déjà dans le viewport), mais SANS
        # fetchpriority=high — l'hypothèse que plusieurs images "haute priorité" en parallèle
        # du vrai bandeau LCP ralentissaient ce dernier a été testée (Lighthouse avant/après
        # ce retrait : 83 → 82, LCP simulé 4.7s → 4.8s) : aucun effet mesurable. Laissé sans
        # fetchpriority malgré tout, par principe (ne pas marquer "haute priorité" une image
        # qui n'est pas la ressource LCP), mais ce n'est pas ce qui explique le score restant.
        ld = '' if eager else ' loading="lazy"'
        fp = ''
        resp = room_card_responsive(slug)
        img_tag = f'<img src="{src}" alt="{H.escape(r["name"])}"{ld}{fp} width="{w}" height="{h}">'
        if resp:
            # 2 colonnes (mobile/tablette, <=980px) : cartes ~45vw ; 3 colonnes (desktop) : ~33vw
            # plafonnées à la largeur réelle de la grille (conteneur max 1120px, 3 colonnes).
            sizes = '(max-width:980px) 46vw, 360px'
            webp_srcset = ', '.join(f"{v['webp']} {w_}w" for w_, v in resp.items())
            jpg_srcset = ', '.join(f"{v['jpg']} {w_}w" for w_, v in resp.items())
            img_tag = (f'<picture>'
                       f'<source type="image/webp" srcset="{webp_srcset}" sizes="{sizes}">'
                       f'<img src="{src}" srcset="{jpg_srcset}" sizes="{sizes}" '
                       f'alt="{H.escape(r["name"])}"{ld}{fp} width="{w}" height="{h}">'
                       f'</picture>')
        img = f'<div class="rph">{img_tag}</div>'
    else:
        img = '<div class="rph soon"><i class="orn c"></i></div>'
    if ready:
        cls = 'rcard'
        sub = (f'<p class="rt">{H.escape(tag)}</p>' if tag else '') + (f'<p class="rm">{H.escape(meta)}</p>' if meta else '')
    else:
        cls, sub = 'rcard is-soon', f'<p class="rt">{H.escape(T("soon"))}</p>'
    return f'<a class="{cls} rv" href="{href}">{img}<div class="rb"><h3>{H.escape(r["name"])}</h3>{sub}<span class="go">{H.escape(T("view"))}</span></div></a>'

def rooms_grid(l):
    return '<div class="rgrid">' + ''.join(room_card(l, s, eager=(i < 3)) for i, s in enumerate(R.ORDER)) + '</div>'

def build_room_page(l, slug, base):
    """base = split_page de la page 'suites-chambres-1' de la langue l."""
    r = R.ROOMS[slug]; T = lambda k: R.UI[k][l]
    ph = room_photos(slug); ready = room_ready(slug)
    d = dict(base)
    pre = '' if l == 'fr' else f'/{l}'
    list_url = f'{pre}/suites-chambres-1'
    kind = T('kind_' + r['kind'])
    tag = R.TAG[r['tag']][l] if r.get('tag') else ''
    facts = room_facts(l, r)
    title = f'{r["name"]} | Le Grand Alcazar'
    d['title'] = f'<title>{H.escape(title)}</title>'
    dsc = f'{r["name"]}' + (f' – {tag}' if tag else '') + ('. ' + ' · '.join(v for k, v in facts[:2]) if facts else '') + '. Le Grand Alcazar, Riad, Fès.'
    d['desc'] = f'<meta name="description" content="{H.escape(dsc)}">'
    can = 'https://www.legrandalcazar.com' + room_url(l, slug)
    alts = ''.join(f'<link rel="alternate" hreflang="{x}" href="https://www.legrandalcazar.com{room_url(x, slug)}">' for x in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="https://www.legrandalcazar.com{room_url("fr", slug)}">'
    d['links'] = f'<link rel="canonical" href="{can}">' + alts + ('' if ready else '<meta name="robots" content="noindex,follow">')
    if ready:
        d['links'] += breadcrumb_ld(l, r['name'], can)
    d['body'] = f'p-room l-{l}'
    d['flags'] = [(room_url(x, slug) + '/', ' on' if x == l else '', x) for x in LANGS]
    active = next((h for h, t in d['nav'] if h.rstrip('/').split('/')[-1] == 'suites-chambres-1'), list_url)
    # --- bandeau (v8 §8, audit externe) : famille C (Photographique), comme le catalogue
    # Suites & Chambres et la Galerie — remplace l'ancien bandeau photo plein format + filtre
    # bleu (ph-img), repris telle quelle sur les 14 fiches (y compris Émeraude et Diamant,
    # encore à l'ancien style). photo_html/preload via _band_photo_html, même mécanisme que
    # page_head_band pour les autres pages de famille C.
    sub = tag or kind
    if ph:
        photo_html, _band_pre = _band_photo_html(ph[0], r['name'])
        d['links'] += _band_pre
    else:
        photo_html = ''
    band = (f'<header class="pagehead ph-c"><i class="orn c"></i><h1>{H.escape(r["name"])}</h1>'
            + (f'<h2>{H.escape(sub)}</h2>' if sub else '') + photo_html + '</header>')
    crumb = f'<a class="back" href="{list_url}/">{H.escape(T("back"))}</a>'
    if ph:
        # v8 (dernières corrections) : la 1re photo sert déjà de bandeau plein format
        # au-dessus (ph[0], cf. photo_html) — on évite de la répéter comme vignette
        # principale de la galerie juste en dessous ; fichiers sources conservés tels quels.
        gal_photos = ph[1:] if len(ph) > 1 else ph
        num_offset = 2 if len(ph) > 1 else 1
        thumbs = ''
        for i, p in enumerate(gal_photos):
            thumbs += f'<a class="gi rgal-{"m" if i == 0 else "s"}" href="{p}" data-g="room" data-t="{H.escape(r["name"])}"><img src="{p}" alt="{H.escape(r["name"])} – {i+num_offset}" loading="{"eager" if i == 0 else "lazy"}" width="1200" height="900"></a>'
        gal = f'<div class="rgal">{thumbs}</div>'
        fl = ''.join(f'<div><dt>{H.escape(k)}</dt><dd>{H.escape(v)}</dd></div>' for k, v in facts)
        am = ''.join(f'<li>{H.escape(R.AMEN[a][l])}</li>' for a in r.get('amen', []))
        card = (f'<aside class="rside"><dl class="rfacts">{fl}</dl><p class="rincl">{H.escape(T("incl"))}</p>'
                f'<a class="btn hot" href="{HOT}" target="_blank" rel="noopener">{d["book"]}</a>'
                f'<a class="rwa" href="{WA}" target="_blank" rel="noopener">{ICON_SVG["wa"]}<span>{H.escape(T("wa"))}</span></a>'
                f'<p class="rtimes">{H.escape(T("ci"))}<br>{H.escape(T("co"))}</p></aside>')
        if ready:
            # v8 (finalisation, demande explicite d'Othmane) : desc + encart combo Grenat/Grenadine
            # réellement traduits dans les 9 langues (rooms_data.py), plus de lang="fr" forcé —
            # chaque langue affiche désormais son propre texte éditorial.
            combo_html = ''
            if r.get('link_room'):
                other = R.ROOMS[r['link_room']]
                link_txt = T('communicating').format(n=other['name'])
                # v8 (dernières corrections) : encart éditorial distinct (fond teinté, filet or),
                # au lieu d'un simple paragraphe enchaîné dans le flux du texte — même contenu
                # (47 m², 6 personnes, 2 salles de bain, balcon, literie modulable), lien
                # réciproque et condition de disponibilité simultanée conservés à l'identique.
                combo_html = (f'<aside class="rcombo-box"><i class="orn"></i>'
                               f'<p class="rlink"><a href="{room_url(l, r["link_room"])}">{H.escape(link_txt)} →</a></p>'
                               f'<p class="rcombo">{H.escape(R.COMBO_GRENAT_GRENADINE[l])}</p></aside>')
            body = (f'<div class="rtop">{gal}{card}</div><div class="rtxt"><p class="dc">{H.escape(r["desc"][l])}</p>{combo_html}</div>'
                    f'<div class="ramen"><h3>{H.escape(T("amen"))}</h3><ul>{am}</ul></div>')
            # SEO v7 §20 : schéma HotelRoom — uniquement sur les fiches complètes, à partir des
            # seuls faits déjà présents dans rooms_data.py (aucun prix inventé : les tarifs réels,
            # variables, vivent uniquement sur le moteur de réservation). description dans la
            # langue de la page depuis la traduction complète des 14 fiches (v8 finalisation).
            room_ld = {
                '@context': 'https://schema.org', '@type': 'HotelRoom', 'name': r['name'],
                'description': re.sub(r'\s+', ' ', r['desc'][l]).strip(),
            }
            if ph: room_ld['image'] = f'https://www.legrandalcazar.com{ph[0]}'
            if r.get('people'): room_ld['occupancy'] = {'@type': 'QuantitativeValue', 'maxValue': r['people']}
            if r.get('size'): room_ld['floorSize'] = {'@type': 'QuantitativeValue', 'value': r['size'], 'unitCode': 'MTK'}
            if r.get('amen'):
                room_ld['amenityFeature'] = [{'@type': 'LocationFeatureSpecification', 'name': R.AMEN[a]['en']} for a in r['amen']]
            d['links'] += f'<script type="application/ld+json">{json.dumps(room_ld, ensure_ascii=False)}</script>'
        else:
            body = (f'<div class="rtop">{gal}{card}</div><div class="rsoon rsoon-s"><p>{H.escape(T("soon"))}</p></div>')
    else:
        body = f'<div class="rsoon"><i class="orn c"></i><p>{H.escape(T("soon"))}</p><a class="btn hot" href="{HOT}" target="_blank" rel="noopener">{d["book"]}</a></div>'
    others = [s for s in R.ORDER if s != slug and room_photos(s)]
    i0 = R.ORDER.index(slug)
    others.sort(key=lambda s: (R.ORDER.index(s) - i0) % len(R.ORDER))
    more = ''
    if others and ph:
        more = f'<section class="rmore"><h3>{H.escape(T("more"))}</h3><div class="rgrid r3">' + ''.join(room_card(l, s) for s in others[:3]) + '</div></section>'
    main = f'<main id="main">{band}<section class="page room">{crumb}{body}{more}</section></main>'
    # v8 (dernières corrections) : header solid=True — le bandeau de titre (pagehead ph-c)
    # n'est pas une photo plein format sous le header (elle arrive plus bas, après le H1),
    # donc le header transparent/blanc (conçu pour un hero sombre) n'était pas lisible sur
    # fond ivoire ; header(solid=True) applique la variante lisible déjà utilisée sur les
    # autres pages sans hero plein format (cf. build_page, l. ~1358).
    out = head(d, 'room', active, page_image=(ph[0] if ph else None)) + header(d, solid=True, active_href=active) + '\n' + main + '\n' + footer(d)
    out += d['tail'].replace('?v=451', f'?v={VER}').replace('<script src="/js/account.js"></script>', '')
    dest = os.path.join(OUT, '' if l == 'fr' else l, 'suites-chambres-1', *r['path'].split('/'), 'index.html')
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, 'w', encoding='utf8').write(out)
    if '/' in r['path']:  # dossier intermédiaire /chambre/ : renvoie vers la liste
        mid = os.path.join(os.path.dirname(os.path.dirname(dest)), 'index.html')
        if not os.path.exists(mid):
            open(mid, 'w', encoding='utf8').write(f'<!DOCTYPE html><html lang="{l}"><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url={list_url}/"><link rel="canonical" href="https://www.legrandalcazar.com{list_url}"></head><body><a href="{list_url}/">{list_url}/</a></body></html>')
    return dest, ready

def build_rooms():
    for slug in R.ORDER:
        room_card_responsive(slug)  # génère 1-card-{420,720}.{jpg,webp} avant la copie ci-dessous
        for p in (glob.glob(os.path.join(BUILD, 'rooms', slug, '*.jpg'))
                  + glob.glob(os.path.join(BUILD, 'rooms', slug, '*.webp'))):
            t = os.path.join(OUT, 'assets/media/rooms', slug); os.makedirs(t, exist_ok=True); shutil.copy2(p, t)
    n, urls = 0, []
    for l in LANGS:
        base = split_page(read(l, 'suites-chambres-1'))
        for slug in R.ORDER:
            dest, ready = build_room_page(l, slug, base); n += 1
            if ready: urls.append('https://www.legrandalcazar.com' + room_url(l, slug))
    sm = os.path.join(OUT, 'sitemap.xml')
    if os.path.exists(sm) and urls:
        x = open(sm, encoding='utf-8').read()
        x = x.replace('</urlset>', ''.join(f'<url><loc>{u}</loc></url>\n' for u in urls) + '</urlset>')
        open(sm, 'w', encoding='utf-8').write(x)
    print('pages suites/chambres :', n, '- publiées :', len(urls), 'URL')


def harden_csp():
    """Remplace 'unsafe-inline' par les empreintes sha256 des scripts intégrés (CSP, défense en profondeur)."""
    import hashlib, base64
    hashes = set()
    for f in glob.glob(os.path.join(OUT, '**', 'index.html'), recursive=True):
        html = open(f, encoding='utf-8').read()
        for m in re.finditer(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S):
            code = m.group(1)
            if code.strip() == '':
                continue
            # v7 §20 (ajout des schémas JSON-LD supplémentaires) : un <script type="application/
            # ld+json"> n'est pas exécuté comme script par le navigateur (type MIME non JS) — il
            # n'a donc pas besoin d'empreinte CSP script-src, et chacun étant unique par page/langue
            # (URL, libellés), les compter ferait gonfler .htaccess sans aucun bénéfice de sécurité.
            tag_open = html[m.start():m.start() + html[m.start():].index('>') + 1]
            if 'application/ld+json' in tag_open:
                continue
            h = base64.b64encode(hashlib.sha256(code.encode('utf-8')).digest()).decode('ascii')
            hashes.add("'sha256-%s'" % h)
    ht = os.path.join(OUT, '.htaccess')
    if not hashes or not os.path.exists(ht):
        return
    c = open(ht, encoding='utf-8').read()
    src_list = "'self' " + ' '.join(sorted(hashes))
    c2 = re.sub(r"script-src 'self' 'unsafe-inline'", "script-src " + src_list, c, count=1)
    if c2 != c:
        open(ht, 'w', encoding='utf-8').write(c2)
        print('CSP durcie :', len(hashes), 'empreintes de scripts intégrés')

def generate_sitemap():
    """Regénère sitemap.xml à partir des pages réellement construites (plus fiable que l'ancien
    fichier statique, qui datait du site Wix et ne listait ni les fiches chambres, ni les
    nouvelles pages v6 bien-etre/experiences/galerie/offres-et-sejours/carnet-de-fes). Exclut
    les pages marquées noindex (chambres sans descriptif validé) et book-online (page
    transactionnelle, déjà exclue du sitemap sur l'ancien site). Un seul <url> par version
    linguistique, avec les alternates hreflang complets (dont x-default) sur chacune."""
    base = 'https://www.legrandalcazar.com'
    exclude = {'book-online'}
    skip_dirs = {'assets', 'api', 'private', 'js', 'css', 'embeds', 'tools'}
    clusters = {}
    for root, dirs, files in os.walk(OUT):
        if 'index.html' not in files:
            continue
        rel = os.path.relpath(root, OUT)
        parts = [] if rel == '.' else rel.split(os.sep)
        if parts and parts[0] in skip_dirs:
            continue
        if parts and parts[0] in LANGS and parts[0] != 'fr':
            lang, rest = parts[0], parts[1:]
        else:
            lang, rest = 'fr', parts
        if rest and rest[0] in exclude:
            continue
        html = open(os.path.join(root, 'index.html'), encoding='utf-8').read()
        if 'noindex' in html:
            continue
        pre = '' if lang == 'fr' else f'/{lang}'
        url = base + (('/' if lang == 'fr' else pre) if not rest else pre + '/' + '/'.join(rest))
        cluster = '/'.join(rest) or 'home'
        clusters.setdefault(cluster, {})[lang] = url
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for cluster, by_lang in sorted(clusters.items()):
        default_url = by_lang.get('fr') or sorted(by_lang.values())[0]
        for lang, url in sorted(by_lang.items()):
            out.append('<url>')
            out.append(f'<loc>{H.escape(url)}</loc>')
            for xl, xurl in sorted(by_lang.items()):
                out.append(f'<xhtml:link rel="alternate" hreflang="{xl}" href="{H.escape(xurl)}"/>')
            out.append(f'<xhtml:link rel="alternate" hreflang="x-default" href="{H.escape(default_url)}"/>')
            out.append('</url>')
    out.append('</urlset>')
    open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8').write('\n'.join(out))
    n_urls = sum(len(v) for v in clusters.values())
    print('sitemap régénéré :', len(clusters), 'pages ×', 'langues —', n_urls, 'URL au total')

def main():
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(OUT)
    # fichiers repris tels quels
    for item in ['assets', 'api', 'embeds', 'tools', 'private', 'js', 'robots.txt', 'sitemap.xml', '.htaccess']:
        s = os.path.join(SRC, item); t = os.path.join(OUT, item)
        if os.path.isdir(s): shutil.copytree(s, t)
        elif os.path.exists(s): shutil.copy2(s, t)
    if PREVIEW:
        # recette v6 : interdiction d'indexation totale (en plus du noindex par page) + pas de
        # sitemap pour une version qui ne doit jamais apparaître dans un moteur de recherche.
        open(os.path.join(OUT, 'robots.txt'), 'w', encoding='utf-8').write('User-agent: *\nDisallow: /\n')
        sm_path = os.path.join(OUT, 'sitemap.xml')
        if os.path.exists(sm_path): os.remove(sm_path)
    sm = os.path.join(OUT, 'sitemap.xml')
    if os.path.exists(sm):
        x = open(sm, encoding='utf-8').read()
        x = re.sub(r'\s*<url>(?:(?!</url>).)*?(?:covid|g(?:ou|%C3%B3|o)urmet|f(?:%C3%A8|è|e)s-gourmet|compte)(?:(?!</url>).)*?</url>', '', x, flags=re.S | re.I)
        open(sm, 'w', encoding='utf-8').write(x)
    bk = os.path.join(OUT, 'js', 'booking.js')
    if os.path.exists(bk):
        j = open(bk, encoding='utf-8').read()
        old = "m.querySelector('.bks').textContent=svc.p+' MAD · '+svc.d+' — '+L.note;"
        new = "var bs=m.querySelector('.bks');bs.textContent='';var bi=document.createElement('bdi');bi.dir='ltr';bi.textContent=svc.p+' MAD · '+svc.d;bs.appendChild(bi);bs.appendChild(document.createTextNode(' — '+L.note));"
        if old in j: open(bk, 'w', encoding='utf-8').write(j.replace(old, new))
    for f in ('auth.php','oauth.php'):
        p=os.path.join(OUT,'api',f)
        if os.path.exists(p): os.remove(p)
    # nouveaux assets
    os.makedirs(os.path.join(OUT, 'assets/img'), exist_ok=True)
    for f in glob.glob(os.path.join(BUILD, 'img/*')): shutil.copy2(f, os.path.join(OUT, 'assets/img'))
    shutil.copy2(os.path.join(BUILD, 'poster.jpg'), os.path.join(OUT, 'assets/img/tour-poster.jpg'))
    os.makedirs(os.path.join(OUT, 'css'), exist_ok=True)
    shutil.copy2(os.path.join(BUILD, 'style.css'), os.path.join(OUT, 'css/style.css'))
    shutil.copy2(os.path.join(BUILD, 'main.js'), os.path.join(OUT, 'js/main.js'))
    n = 0
    for l in LANGS:
        for slug in [None] + SLUGS:
            if build_page(l, slug): n += 1
        for kind in ('bien-etre', 'experiences'):
            build_extra_page(l, kind); n += 1
        build_gallery_page(l); n += 1
        build_offers_page(l); n += 1
        build_carnet_page(l); n += 1
    build_rooms()
    # perf (25/11/2026) : variantes mobile/desktop des images de bandeau (cf. responsive_band()),
    # générées pendant build_page()/build_extra_page()/etc. ci-dessus, mises en cache sous
    # build/_bandcache/ entre deux builds — copiées vers la sortie une fois toutes générées.
    if os.path.isdir(respimg.BAND_CACHE_DIR):
        resp_out = os.path.join(OUT, 'assets', 'media', '_resp')
        os.makedirs(resp_out, exist_ok=True)
        for f in glob.glob(os.path.join(respimg.BAND_CACHE_DIR, '*')):
            shutil.copy2(f, resp_out)
    harden_csp()
    if not PREVIEW:
        generate_sitemap()
    print('pages générées :', n)

if __name__ == '__main__':
    main()
