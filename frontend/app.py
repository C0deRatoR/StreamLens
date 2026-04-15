"""
StreamLens Frontend — Cinematic Crimson Edition
Serves the single-page HTML app and proxies API calls to the FastAPI backend.
Run with: python frontend/app.py
"""

import os
import sys
import http.server
import urllib.request
import urllib.error
import json
import webbrowser
import threading
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
FRONTEND_PORT = 8501
BACKEND_URL   = os.environ.get("STREAMLENS_API", "http://localhost:8000")
STATIC_DIR    = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# ── HTML payload ─────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en" class="light">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>StreamLens — Cinematic Discovery</title>
<meta name="description" content="StreamLens: Context-aware, personalised movie recommendations with a cinematic editorial experience."/>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@200;300;400;500;600;700;800&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<script>
  tailwind.config = {
    darkMode: "class",
    theme: {
      extend: {
        colors: {
          "primary-fixed":              "#ffdad9",
          "background":                 "#fff8f7",
          "on-tertiary":                "#ffffff",
          "surface-container-high":     "#ffe1e1",
          "secondary":                  "#b60e3d",
          "surface-container-highest":  "#fcdbda",
          "on-surface-variant":         "#5c3f3f",
          "surface-dim":                "#f3d3d2",
          "outline":                    "#916f6e",
          "surface":                    "#fff8f7",
          "on-surface":                 "#281717",
          "on-primary":                 "#ffffff",
          "tertiary-container":         "#c73d4d",
          "primary-fixed-dim":          "#ffb3b3",
          "surface-container-low":      "#fff0f0",
          "surface-container-lowest":   "#ffffff",
          "on-background":              "#281717",
          "secondary-container":        "#da3054",
          "inverse-surface":            "#3f2b2b",
          "on-secondary":               "#ffffff",
          "tertiary":                   "#a52437",
          "surface-container":          "#ffe9e8",
          "surface-tint":               "#bf0030",
          "surface-variant":            "#fcdbda",
          "on-primary-fixed-variant":   "#920022",
          "outline-variant":            "#e6bdbc",
          "surface-bright":             "#fff8f7",
          "primary-container":          "#dc143c",
          "primary":                    "#b1002c",
          "inverse-on-surface":         "#ffedec"
        },
        borderRadius: { DEFAULT:"0.25rem", lg:"0.5rem", xl:"0.75rem", full:"9999px" },
        fontFamily:   { headline:["Manrope"], body:["Manrope"], label:["Manrope"] }
      }
    }
  }
</script>
<style>
  * { font-family: 'Manrope', sans-serif; }
  body { background-color: #fff8f7; color: #281717; }
  .material-symbols-outlined { font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24; }
  .fill-icon { font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24; }
  .crimson-gradient  { background: linear-gradient(45deg, #b1002c, #dc143c); }
  .crimson-shadow    { box-shadow: 0px 20px 40px rgba(147,0,10,0.08); }
  .frosted-glass     { background: rgba(255,248,247,0.85); backdrop-filter: blur(24px); }
  .hide-scrollbar::-webkit-scrollbar { display: none; }
  .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
  .text-ink { color: #920022; }
  /* Skeleton shimmer */
  @keyframes shimmer { 0%{background-position:-400px 0} 100%{background-position:400px 0} }
  .skeleton {
    background: linear-gradient(90deg, #ffe9e8 25%, #fff0f0 50%, #ffe9e8 75%);
    background-size: 800px 100%;
    animation: shimmer 1.4s infinite linear;
    border-radius: 0.5rem;
  }
  /* Page transitions */
  .page { display:none; opacity:0; transition: opacity 0.25s ease; }
  .page.active { display:block; opacity:1; }
  /* Star rating */
  .star { cursor:pointer; transition:transform 0.1s; }
  .star:hover { transform:scale(1.2); }
  /* Match bar */
  .match-bar-inner { transition: width 0.7s cubic-bezier(.4,0,0.2,1); }
  /* Scroll reveal */
  .reveal { opacity:0; transform:translateY(20px); transition: opacity .5s ease, transform .5s ease; }
  .reveal.visible { opacity:1; transform:translateY(0); }
  /* Toast */
  #toast { transition: opacity .3s, transform .3s; }
  /* Poster fallback */
  .poster-placeholder {
    background: linear-gradient(135deg, #ffe9e8 0%, #fcdbda 50%, #ffdad9 100%);
    display: flex; align-items: center; justify-content: center;
  }
  /* Fix onboarding: hide side/top nav */
  .onboarding-active #topnav,
  .onboarding-active aside { display: none !important; }
  .onboarding-active .page { margin-left: 0 !important; }
</style>
</head>
<body class="bg-background text-on-background selection:bg-primary-fixed selection:text-on-primary-fixed">

<!-- ══════════════════════════════════════════════════ TOP NAV ══ -->
<nav id="topnav" class="fixed top-0 w-full z-50 frosted-glass flex justify-between items-center px-6 md:px-8 py-4 crimson-shadow">
  <div class="flex items-center gap-8 md:gap-12">
    <button onclick="showPage('discover')" class="text-xl md:text-2xl font-black text-primary italic tracking-tighter">StreamLens</button>
    <div class="hidden md:flex gap-6 items-center text-sm font-semibold">
      <button id="nav-discover" onclick="showPage('discover')" class="text-primary font-bold border-b-2 border-primary pb-1 transition-colors">Discover</button>
      <button id="nav-browse"   onclick="showPage('browse')"   class="text-on-surface-variant hover:text-primary transition-colors pb-1">Browse</button>
      <button id="nav-rate"     onclick="showPage('rate')"     class="text-on-surface-variant hover:text-primary transition-colors pb-1">Rate Movies</button>
    </div>
  </div>
  <div class="flex items-center gap-3 md:gap-4">
    <!-- Search bar (desktop) -->
    <div class="relative hidden lg:block">
      <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-lg">search</span>
      <input id="nav-search" type="text" placeholder="Search films..."
        class="bg-surface-container-low border-none rounded-full py-2 pl-10 pr-4 w-56 text-sm focus:ring-2 focus:ring-primary outline-none transition-all"
        onkeydown="if(event.key==='Enter'){doNavSearch()}"
      />
    </div>
    <button onclick="showPage('profile')" class="p-2 hover:bg-surface-container rounded-full transition-colors">
      <span class="material-symbols-outlined text-on-surface-variant">tune</span>
    </button>
    <!-- Avatar -->
    <div class="w-9 h-9 rounded-full crimson-gradient flex items-center justify-center text-white font-black text-sm select-none cursor-pointer" onclick="showPage('profile')">
      <span id="avatar-letter">?</span>
    </div>
  </div>
</nav>

<!-- ══════════════════════════ SIDE NAV (xl+) ══ -->
<aside class="hidden xl:flex h-screen w-60 fixed left-0 top-0 flex-col py-8 gap-2 z-40 pt-24 bg-surface-container-low border-r border-outline-variant/10">
  <div class="px-6 mb-6">
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 crimson-gradient rounded-xl flex items-center justify-center">
        <span class="material-symbols-outlined fill-icon text-white text-sm">movie_filter</span>
      </div>
      <div>
        <p class="text-primary text-sm font-black tracking-tight">StreamLens</p>
        <p class="text-[10px] text-on-surface-variant font-medium">Cinematic Crimson</p>
      </div>
    </div>
  </div>
  <div id="sidenav-links" class="space-y-1 flex-1">
    <button onclick="showPage('discover')" id="side-discover"
      class="side-link w-full flex items-center gap-3 py-3 px-6 font-bold text-[11px] uppercase tracking-widest text-white crimson-gradient rounded-r-full shadow-lg shadow-primary/20">
      <span class="material-symbols-outlined fill-icon">home</span><span>Home</span>
    </button>
    <button onclick="showPage('browse')" id="side-browse"
      class="side-link w-full flex items-center gap-3 py-3 px-6 font-bold text-[11px] uppercase tracking-widest text-on-surface-variant hover:text-primary hover:translate-x-1 transition-all">
      <span class="material-symbols-outlined">explore</span><span>Browse</span>
    </button>
    <button onclick="showPage('rate')" id="side-rate"
      class="side-link w-full flex items-center gap-3 py-3 px-6 font-bold text-[11px] uppercase tracking-widest text-on-surface-variant hover:text-primary hover:translate-x-1 transition-all">
      <span class="material-symbols-outlined">star_border</span><span>Rate Movies</span>
    </button>
    <button onclick="showPage('profile')" id="side-profile"
      class="side-link w-full flex items-center gap-3 py-3 px-6 font-bold text-[11px] uppercase tracking-widest text-on-surface-variant hover:text-primary hover:translate-x-1 transition-all">
      <span class="material-symbols-outlined">tune</span><span>My Profile</span>
    </button>
  </div>
  <div class="px-6 py-4">
    <div id="api-status" class="flex items-center gap-2 mb-4">
      <span class="w-2 h-2 rounded-full bg-gray-300" id="api-dot"></span>
      <span class="text-[10px] text-on-surface-variant font-bold uppercase tracking-wider" id="api-label">Connecting…</span>
    </div>
    <p class="text-[9px] text-on-surface-variant/60 font-medium">StreamLens v2.0 · Cinematic Crimson</p>
  </div>
</aside>

<!-- ══════════════════════════ MOBILE BOTTOM NAV ══ -->
<nav class="md:hidden fixed bottom-0 left-0 right-0 frosted-glass flex justify-around items-center py-3 px-4 z-50 shadow-[0_-10px_30px_rgba(0,0,0,0.05)]">
  <button onclick="showPage('discover')" id="mob-discover" class="mob-link flex flex-col items-center gap-1 text-primary">
    <span class="material-symbols-outlined fill-icon">home</span>
    <span class="text-[9px] font-bold uppercase tracking-widest">Home</span>
  </button>
  <button onclick="showPage('browse')" id="mob-browse" class="mob-link flex flex-col items-center gap-1 text-on-surface-variant">
    <span class="material-symbols-outlined">explore</span>
    <span class="text-[9px] font-bold uppercase tracking-widest">Browse</span>
  </button>
  <button onclick="showPage('rate')" id="mob-rate" class="mob-link flex flex-col items-center gap-1 text-on-surface-variant">
    <span class="material-symbols-outlined">star_border</span>
    <span class="text-[9px] font-bold uppercase tracking-widest">Rate</span>
  </button>
  <button onclick="showPage('profile')" id="mob-profile" class="mob-link flex flex-col items-center gap-1 text-on-surface-variant">
    <span class="material-symbols-outlined">tune</span>
    <span class="text-[9px] font-bold uppercase tracking-widest">Profile</span>
  </button>
</nav>

<!-- ══════════════════════════════════════════════ TOAST ══ -->
<div id="toast" class="fixed bottom-20 md:bottom-6 left-1/2 -translate-x-1/2 z-[200] px-6 py-3 crimson-gradient text-white text-sm font-bold rounded-full shadow-2xl opacity-0 pointer-events-none translate-y-4">
  <span id="toast-msg"></span>
</div>

<!-- ════════════════════════════════════════════ PAGES ══ -->

<!-- ┌──────────────────────────────────────── ONBOARDING ──┐ -->
<div id="page-onboarding" class="page active min-h-screen flex flex-col items-center justify-center p-6 md:p-12">

  <!-- ambient blobs -->
  <div class="fixed inset-0 pointer-events-none z-[-1] overflow-hidden">
    <div class="absolute top-[-10%] right-[-5%] w-[40%] h-[60%] bg-primary/5 blur-[120px] rounded-full"></div>
    <div class="absolute bottom-[-10%] left-[-5%] w-[30%] h-[50%] bg-tertiary/5 blur-[100px] rounded-full"></div>
  </div>

  <section class="w-full max-w-5xl mx-auto flex flex-col items-center text-center mb-8 space-y-5 pt-4">
    <div class="inline-flex items-center gap-2">
      <span class="text-primary font-black italic tracking-tighter text-3xl">StreamLens</span>
    </div>
    <h1 class="text-5xl md:text-7xl font-light tracking-tight text-on-surface leading-tight">
      Your <span class="font-extrabold italic text-primary">Cinematic</span> Journey <br/>Starts Here.
    </h1>
    <p class="text-lg text-on-surface-variant max-w-xl leading-relaxed">
      Select the genres that define your taste — we'll personalise your discovery feed in real time.
    </p>
  </section>

  <!-- Name input -->
  <div class="w-full max-w-xl mx-auto mb-6">
    <label class="text-[11px] uppercase tracking-[0.2em] text-primary font-extrabold mb-2 block">Your Name</label>
    <input id="onboard-name" type="text" placeholder="e.g. Alex" maxlength="30"
      class="w-full bg-surface-container-lowest border-b-2 border-outline-variant/40 focus:border-primary text-2xl font-bold py-3 px-0 outline-none transition-colors placeholder:text-stone-300"/>
  </div>

  <!-- Genre bento grid -->
  <section id="genre-grid" class="w-full max-w-5xl mx-auto grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 pb-32">
    <!-- populated by JS -->
  </section>

  <!-- Floating CTA -->
  <footer id="onboard-footer" class="fixed bottom-0 w-full p-4 md:p-6 flex justify-center pointer-events-none z-40">
    <div class="frosted-glass rounded-full px-6 md:px-8 py-4 crimson-shadow pointer-events-auto flex items-center gap-6 md:gap-12 border border-outline-variant/10">
      <div class="hidden md:flex flex-col">
        <span class="text-[10px] uppercase tracking-widest font-black text-primary/60">Selected genres</span>
        <span id="genre-count" class="text-on-surface font-black text-lg">0</span>
      </div>
      <div class="flex items-center gap-3">
        <button onclick="skipOnboarding()" class="text-on-surface-variant font-bold px-5 py-3 rounded-full hover:bg-surface-container transition-colors text-sm">
          Skip
        </button>
        <button id="onboard-btn" onclick="finishOnboarding()"
          class="crimson-gradient text-white px-6 md:px-8 py-3 rounded-full font-bold shadow-lg shadow-primary/20 hover:scale-105 active:scale-95 transition-all flex items-center gap-2 text-sm">
          Initialize Discovery
          <span class="material-symbols-outlined text-sm">bolt</span>
        </button>
      </div>
    </div>
  </footer>
</div>

<!-- ┌──────────────────────────────────────── DISCOVER ──┐ -->
<div id="page-discover" class="page xl:ml-60 pt-16 pb-24 min-h-screen">

  <!-- Hero featured movie -->
  <section class="px-4 md:px-8 mt-1">
    <div id="hero-featured" class="relative w-full h-[160px] md:h-[200px] rounded-2xl overflow-hidden group bg-surface-container skeleton">
      <!-- populated by JS -->
    </div>
  </section>

  <!-- Context chips -->
  <section class="px-4 md:px-8 mt-4 overflow-x-auto hide-scrollbar">
    <div class="flex items-center gap-3 py-2">
      <div class="flex items-center gap-2 bg-surface-container-low px-5 py-2.5 rounded-full border border-outline-variant/15 flex-shrink-0">
        <span class="material-symbols-outlined text-primary text-lg">tune</span>
        <span class="text-on-surface font-bold text-sm">Vibe</span>
      </div>
      <div id="context-chips" class="flex gap-2 flex-shrink-0">
        <!-- populated by JS -->
      </div>
    </div>
  </section>

  <!-- Personalised feed -->
  <section class="px-4 md:px-8 mt-6">
    <div class="flex justify-between items-end mb-4">
      <div>
        <h2 class="text-3xl md:text-4xl font-extrabold text-on-surface tracking-tight">Personalised For You</h2>
        <p id="context-subtitle" class="text-on-surface-variant mt-1 font-medium text-sm">Loading your recommendations…</p>
      </div>
      <button onclick="loadMoreRecs()" id="explore-all-btn"
        class="text-primary font-bold flex items-center gap-1 text-sm group">
        Show More <span class="material-symbols-outlined text-sm transition-transform group-hover:translate-x-1">arrow_forward</span>
      </button>
    </div>
    <div id="rec-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      <!-- populated by JS -->
    </div>
    <div id="rec-loading" class="text-center py-12 text-on-surface-variant text-sm font-medium hidden">
      <div class="inline-block w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-2"></div>
      <p>Curating your selections…</p>
    </div>
  </section>

  <!-- Top rated section -->
  <section class="px-4 md:px-8 mt-8">
    <div class="flex items-center gap-4 mb-6">
      <div class="w-10 h-[2px] crimson-gradient"></div>
      <h2 class="text-xl font-extrabold tracking-tight text-on-surface uppercase tracking-widest text-sm">Top Rated This Week</h2>
    </div>
    <div id="top-scroll" class="flex gap-5 overflow-x-auto hide-scrollbar pb-4">
      <!-- populated by JS -->
    </div>
  </section>

  <!-- Editorial banner -->
  <section class="px-4 md:px-8 mt-8 mb-4">
    <div class="bg-surface-container-low rounded-2xl p-8 md:p-10 relative overflow-hidden">
      <div class="absolute top-0 right-0 w-1/3 h-full opacity-10 pointer-events-none">
        <div class="w-full h-full crimson-gradient rounded-full blur-[100px]"></div>
      </div>
      <div class="max-w-2xl relative z-10">
        <span class="text-primary font-black uppercase tracking-[0.2em] text-xs mb-4 block">Editorial Perspective</span>
        <h2 class="text-4xl md:text-5xl font-extrabold text-on-surface mb-6 leading-tight tracking-tighter">Beyond the <br/>Streaming Surface.</h2>
        <p class="text-lg text-on-surface-variant font-medium leading-relaxed mb-8">
          StreamLens is a curated gallery of cinematic achievement — designed for those who seek the extraordinary in every frame.
        </p>
        <button onclick="showPage('browse')" class="bg-on-surface text-background px-8 py-4 rounded-full font-bold hover:bg-primary transition-colors flex items-center gap-2">
          Explore the Archive <span class="material-symbols-outlined">north_east</span>
        </button>
      </div>
    </div>
  </section>
</div>

<!-- ┌──────────────────────────────────────── BROWSE ──┐ -->
<div id="page-browse" class="page xl:ml-60 pt-16 pb-24 px-4 md:px-12 min-h-screen">

  <!-- Search hero -->
  <section class="max-w-4xl mx-auto mt-2 mb-6">
    <span class="text-[11px] uppercase tracking-[0.2em] text-primary font-extrabold">Explore The Lens</span>
    <h1 class="text-3xl md:text-5xl font-extrabold tracking-tighter text-on-surface mt-1 mb-4">What are you watching?</h1>
    <div class="relative group">
      <input id="main-search" type="text" placeholder="Search movies by title…"
        class="w-full bg-surface-container-lowest border-none border-b-2 border-outline-variant/30 text-xl md:text-2xl font-bold py-5 pr-16 focus:border-primary focus:ring-0 outline-none transition-all placeholder:text-stone-300"
        onkeydown="if(event.key==='Enter'){doSearch()}"
      />
      <button onclick="doSearch()" class="absolute right-2 top-1/2 -translate-y-1/2 p-3 crimson-gradient text-white rounded-full shadow-xl shadow-primary/30 hover:scale-105 transition-transform">
        <span class="material-symbols-outlined text-2xl">search</span>
      </button>
    </div>
    <!-- Genre filter chips -->
    <div class="flex flex-wrap gap-2 mt-6" id="browse-genre-chips">
      <!-- populated by JS -->
    </div>
  </section>

  <!-- Search results -->
  <section class="max-w-7xl mx-auto mb-16" id="search-results-section" style="display:none;">
    <div class="flex justify-between items-end mb-6">
      <h2 class="text-2xl font-extrabold text-on-surface tracking-tight" id="search-results-title">Results</h2>
      <button onclick="clearSearch()" class="text-sm text-on-surface-variant font-bold hover:text-primary transition-colors">Clear</button>
    </div>
    <div id="search-results-grid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-5">
    </div>
  </section>

  <!-- Curated collections bento -->
  <section class="max-w-7xl mx-auto mb-16" id="collections-section">
    <div class="flex justify-between items-end mb-8">
      <div>
        <h2 class="text-3xl font-extrabold tracking-tight text-on-surface">Curated Collections</h2>
        <p class="text-on-surface-variant font-medium mt-1 text-sm">Hand-picked cinematic journeys.</p>
      </div>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-4 gap-5" style="height:auto;">
      <div class="md:col-span-2 md:row-span-2 relative rounded-[2rem] overflow-hidden group cursor-pointer min-h-[300px]"
           style="background:#fcdbda" onclick="filterByGenre('Drama')">
        <div class="absolute inset-0 bg-gradient-to-t from-primary/90 via-primary/20 to-transparent"></div>
        <div class="absolute inset-0 p-8 flex flex-col justify-end">
          <span class="px-3 py-1 bg-white/20 backdrop-blur-md text-white text-[10px] uppercase font-bold tracking-[0.2em] rounded-full w-fit mb-3">Spotlight</span>
          <h3 class="text-3xl font-black text-white tracking-tighter">Cinematic Drama</h3>
          <p class="text-white/80 text-sm mt-2 mb-5">Epic stories, unforgettable performances.</p>
          <button class="bg-white text-primary px-6 py-2.5 rounded-full font-bold text-sm uppercase tracking-widest hover:bg-primary-fixed transition-colors w-fit">Explore</button>
        </div>
      </div>
      <div class="relative rounded-[2rem] overflow-hidden group cursor-pointer min-h-[140px] bg-surface-container-high" onclick="filterByGenre('Action')">
        <div class="absolute inset-0 bg-gradient-to-r from-secondary/80 to-transparent"></div>
        <div class="absolute inset-0 flex flex-col justify-end p-6">
          <h3 class="text-xl font-bold text-white">High-Octane Action</h3>
        </div>
      </div>
      <div class="relative rounded-[2rem] overflow-hidden group cursor-pointer min-h-[140px] bg-surface-container" onclick="filterByGenre('Comedy')">
        <div class="absolute inset-0 bg-gradient-to-tr from-tertiary-container/90 to-transparent"></div>
        <div class="absolute inset-0 flex flex-col justify-end p-6">
          <h3 class="text-xl font-bold text-white">Comedy Gold</h3>
        </div>
      </div>
      <div class="relative rounded-[2rem] overflow-hidden group cursor-pointer min-h-[140px] bg-surface-container-high" onclick="filterByGenre('Thriller')">
        <div class="absolute inset-0 bg-gradient-to-br from-primary-container/90 to-transparent"></div>
        <div class="absolute inset-0 flex flex-col justify-end p-6">
          <h3 class="text-xl font-bold text-white">Noir Thriller</h3>
        </div>
      </div>
      <div class="relative rounded-[2rem] overflow-hidden group cursor-pointer min-h-[140px] bg-primary-fixed" onclick="filterByGenre('Sci-Fi')">
        <div class="absolute inset-0 flex flex-col justify-end p-6">
          <h3 class="text-xl font-bold text-ink">Sci-Fi Odyssey</h3>
        </div>
      </div>
    </div>
  </section>

  <!-- Trending scroll -->
  <section class="max-w-7xl mx-auto overflow-hidden">
    <div class="flex items-center gap-4 mb-6">
      <div class="w-10 h-[2px] crimson-gradient"></div>
      <h2 class="text-sm font-extrabold tracking-widest text-on-surface uppercase">Trending Now</h2>
    </div>
    <div id="trending-scroll" class="flex gap-5 overflow-x-auto hide-scrollbar pb-6">
      <!-- populated by JS -->
    </div>
  </section>
</div>

<!-- ┌──────────────────────────────────────── MOVIE DETAIL ──┐ -->
<div id="page-detail" class="page xl:ml-60 pt-0 pb-24 min-h-screen">
  <div id="detail-content">
    <!-- populated by JS -->
  </div>
</div>

<!-- ┌──────────────────────────────────────── RATE MOVIES ──┐ -->
<div id="page-rate" class="page xl:ml-60 pt-16 pb-24 px-4 md:px-12 min-h-screen">
  <div class="max-w-5xl mx-auto mt-2">
    <span class="text-[11px] uppercase tracking-[0.2em] text-primary font-extrabold">Your Ratings</span>
    <h1 class="text-4xl md:text-5xl font-extrabold tracking-tighter text-on-surface mt-2 mb-3">Rate Movies</h1>
    <p class="text-on-surface-variant font-medium mb-10">Rate movies to sharpen your personalised recommendations.</p>
    <!-- Quick search -->
    <div class="relative mb-8">
      <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant">search</span>
      <input id="rate-search" type="text" placeholder="Find a movie to rate…"
        class="w-full bg-surface-container-low border-none rounded-2xl py-4 pl-12 pr-4 text-base font-medium outline-none focus:ring-2 focus:ring-primary transition-all"
        oninput="rateSearch()"
      />
    </div>
    <div id="rate-results" class="space-y-3 mb-10">
      <!-- populated by JS -->
    </div>
    <hr class="border-outline-variant/20 my-10"/>
    <h2 class="text-2xl font-extrabold text-on-surface mb-6 tracking-tight">Your Rating History</h2>
    <div id="rating-history" class="space-y-3">
      <p class="text-on-surface-variant text-sm" id="no-ratings-msg">No ratings yet. Search for movies above to get started.</p>
    </div>
  </div>
</div>

<!-- ┌──────────────────────────────────────── PROFILE ──┐ -->
<div id="page-profile" class="page xl:ml-60 pt-16 pb-24 px-4 md:px-12 min-h-screen">
  <div class="max-w-3xl mx-auto mt-2">
    <div class="flex items-center gap-5 mb-10">
      <div class="w-16 h-16 rounded-full crimson-gradient flex items-center justify-center text-white font-black text-2xl" id="profile-avatar">?</div>
      <div>
        <h1 class="text-3xl font-extrabold text-on-surface tracking-tight" id="profile-name-display">Your Profile</h1>
        <p class="text-on-surface-variant font-medium text-sm">Context shapes your discovery feed</p>
      </div>
    </div>

    <!-- Name -->
    <div class="bg-surface-container-low rounded-3xl p-8 mb-5">
      <h2 class="text-xs uppercase tracking-widest text-primary font-extrabold mb-4">Display Name</h2>
      <input id="profile-name" type="text" placeholder="Enter your name"
        class="w-full bg-transparent border-b-2 border-outline-variant/30 focus:border-primary text-xl font-bold py-2 outline-none transition-colors"
        oninput="updateProfile()"
      />
    </div>

    <!-- Preferred Genres -->
    <div class="bg-surface-container-low rounded-3xl p-8 mb-5">
      <h2 class="text-xs uppercase tracking-widest text-primary font-extrabold mb-4">Preferred Genres</h2>
      <div id="profile-genres" class="flex flex-wrap gap-2">
        <!-- populated from onboarding -->
      </div>
    </div>

    <!-- Context controls -->
    <div class="bg-surface-container-low rounded-3xl p-8 mb-5">
      <h2 class="text-xs uppercase tracking-widest text-primary font-extrabold mb-6">Current Context</h2>
      <div class="space-y-5">
        <div>
          <label class="text-sm font-bold text-on-surface-variant mb-2 block">Time of Day</label>
          <div class="flex flex-wrap gap-2" id="ctx-time">
            <!-- populated -->
          </div>
        </div>
        <div>
          <label class="text-sm font-bold text-on-surface-variant mb-2 block">Your Mood</label>
          <div class="flex flex-wrap gap-2" id="ctx-mood">
          </div>
        </div>
        <div>
          <label class="text-sm font-bold text-on-surface-variant mb-2 block">Watching With</label>
          <div class="flex flex-wrap gap-2" id="ctx-social">
          </div>
        </div>
      </div>
    </div>

    <button onclick="saveProfileAndDiscover()"
      class="crimson-gradient text-white px-10 py-4 rounded-full font-bold shadow-lg shadow-primary/20 hover:scale-105 active:scale-95 transition-all flex items-center gap-2">
      <span class="material-symbols-outlined">bolt</span>
      Save & Refresh Recommendations
    </button>
  </div>
</div>

<!-- ════════════════════════════════════════ MOVIE CARD MODAL ══ -->
<div id="modal-overlay" class="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-end md:items-center justify-center p-0 md:p-6 hidden" onclick="closeModal(event)">
  <div id="modal-box" class="bg-surface w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-t-[2rem] md:rounded-[2rem] p-8 relative crimson-shadow" onclick="event.stopPropagation()">
    <button onclick="closeModal()" class="absolute top-6 right-6 w-9 h-9 rounded-full bg-surface-container flex items-center justify-center hover:bg-primary-fixed transition-colors">
      <span class="material-symbols-outlined text-primary">close</span>
    </button>
    <div id="modal-inner"></div>
  </div>
</div>


<!-- ════════════════════════════════════════ JAVASCRIPT ══ -->
<script>
const API = '/api';   // proxied through python server

// ── State ─────────────────────────────────────────────────────────────────
const state = {
  name:           '',
  genres:         [],       // selected preferred genres
  context:        { time:'Evening', mood:'Relaxed', social:'Solo' },
  userRatings:    {},       // { movieId: rating }
  allGenres:      [],
  recPage:        1,
  recAll:         [],
  currentPage:    'onboarding',
  featureMovies:  [],
};

// Map frontend context values to backend expected values
const TIME_MAP   = { 'Morning':'morning', 'Afternoon':'afternoon', 'Evening':'evening', 'Late Night':'late_night' };
const MOOD_MAP   = { 'Relaxed':'relaxed', 'Adventurous':'adventurous', 'Emotional':'thoughtful', 'Curious':'thoughtful', 'Tense':'intense' };
const SOCIAL_MAP = { 'Solo':'alone', 'With Partner':'date', 'With Friends':'friends', 'With Family':'family' };

const GENRE_ICONS = {
  Action:'local_fire_department', Adventure:'explore', Animation:'animation',
  Comedy:'sentiment_very_satisfied', Crime:'gavel', Documentary:'article',
  Drama:'theater_comedy', Fantasy:'auto_awesome', History:'history_edu',
  Horror:'skull', Musical:'music_note', Mystery:'search', Romance:'favorite',
  'Sci-Fi':'science', Thriller:'psychology', War:'flag', Western:'landscape',
  Children:'child_care', default:'movie_filter'
};
const TIME_OPTIONS   = ['Morning','Afternoon','Evening','Late Night'];
const MOOD_OPTIONS   = ['Relaxed','Adventurous','Emotional','Curious','Tense'];
const SOCIAL_OPTIONS = ['Solo','With Partner','With Friends','With Family'];
const CONTEXT_GENRES = {
  Evening:        ['Drama','Thriller','Romance','Mystery','Crime'],
  'Late Night':   ['Horror','Thriller','Sci-Fi','Crime'],
  Morning:        ['Comedy','Animation','Children','Documentary'],
  Afternoon:      ['Action','Adventure','Comedy','Fantasy'],
  Relaxed:        ['Drama','Romance','Documentary','Comedy'],
  Adventurous:    ['Adventure','Action','Sci-Fi','Fantasy','Western'],
  Emotional:      ['Drama','Romance','Musical'],
  Curious:        ['Documentary','Mystery','Sci-Fi','History'],
  Tense:          ['Thriller','Crime','Horror','Mystery'],
  'With Partner': ['Romance','Comedy','Drama','Musical'],
  'With Friends': ['Comedy','Action','Adventure','Sci-Fi','Fantasy'],
  'With Family':  ['Animation','Comedy','Children','Adventure'],
  Solo:           ['Drama','Sci-Fi','Mystery','Thriller'],
};

// Ensure genres is always an array (backend sometimes returns pipe-separated string)
function ensureGenresArray(genres) {
  if (!genres) return [];
  if (Array.isArray(genres)) return genres;
  if (typeof genres === 'string') return genres.split('|').filter(g => g && g !== '(no genres listed)');
  return [];
}

// ── Toast ──────────────────────────────────────────────────────────────────
let toastTimer;
function showToast(msg) {
  const t = document.getElementById('toast');
  document.getElementById('toast-msg').textContent = msg;
  t.style.opacity = '1'; t.style.transform = 'translate(-50%,0)';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>{ t.style.opacity='0'; t.style.transform='translate(-50%,16px)'; }, 2500);
}

// ── API proxy helpers ──────────────────────────────────────────────────────
async function apiFetch(path, opts={}) {
  try {
    const res = await fetch(API + path, opts);
    if (!res.ok) throw new Error(res.statusText);
    return res.json();
  } catch(e) {
    return null;
  }
}

// ── Page routing ───────────────────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const pg = document.getElementById('page-' + name);
  if (pg) { pg.classList.add('active'); }
  state.currentPage = name;
  updateNavHighlight(name);

  // Toggle onboarding mode (hides nav chrome)
  const body = document.body;
  const onboardFooter = document.getElementById('onboard-footer');
  if (name === 'onboarding') {
    body.classList.add('onboarding-active');
    if (onboardFooter) onboardFooter.style.display = '';
  } else {
    body.classList.remove('onboarding-active');
    if (onboardFooter) onboardFooter.style.display = 'none';
  }

  if (name === 'discover')    loadDiscover();
  if (name === 'browse')      loadBrowse();
  if (name === 'rate')        loadRatePage();
  if (name === 'profile')     loadProfilePage();

  window.scrollTo({ top:0, behavior:'smooth' });
}

function updateNavHighlight(name) {
  ['discover','browse','rate','profile'].forEach(n => {
    const navBtn  = document.getElementById('nav-'+n);
    const sideBtn = document.getElementById('side-'+n);
    const mobBtn  = document.getElementById('mob-'+n);
    const active  = (n === name);
    if (navBtn) {
      navBtn.className = active
        ? 'text-primary font-bold border-b-2 border-primary pb-1 transition-colors'
        : 'text-on-surface-variant hover:text-primary transition-colors pb-1';
    }
    if (sideBtn) {
      sideBtn.className = active
        ? 'side-link w-full flex items-center gap-3 py-3 px-6 font-bold text-[11px] uppercase tracking-widest text-white crimson-gradient rounded-r-full shadow-lg shadow-primary/20'
        : 'side-link w-full flex items-center gap-3 py-3 px-6 font-bold text-[11px] uppercase tracking-widest text-on-surface-variant hover:text-primary hover:translate-x-1 transition-all';
    }
    if (mobBtn) {
      mobBtn.className = active
        ? 'mob-link flex flex-col items-center gap-1 text-primary'
        : 'mob-link flex flex-col items-center gap-1 text-on-surface-variant';
      mobBtn.querySelector('.material-symbols-outlined').className =
        active ? 'material-symbols-outlined fill-icon' : 'material-symbols-outlined';
    }
  });
}

// ── Onboarding ─────────────────────────────────────────────────────────────
async function initGenreGrid() {
  const data = await apiFetch('/movies/genres');
  const list = data && data.genres ? data.genres : [
    'Action','Adventure','Animation','Comedy','Crime','Documentary',
    'Drama','Fantasy','Horror','Mystery','Romance','Sci-Fi','Thriller','Musical','History','Western','Children'];
  state.allGenres = list;

  const grid = document.getElementById('genre-grid');
  grid.innerHTML = '';
  list.forEach((g, i) => {
    const icon = GENRE_ICONS[g] || GENRE_ICONS.default;
    const large = (i === 0);
    const div = document.createElement('div');
    div.className = `relative overflow-hidden rounded-3xl p-7 flex flex-col justify-between cursor-pointer transition-all duration-300 border border-transparent
      ${large ? 'col-span-2 row-span-1 bg-surface-container-highest' : 'bg-surface-container-low'}
      hover:border-primary-fixed hover:-translate-y-1 group`;
    div.id = `genre-card-${i}`;
    div.innerHTML = `
      <span class="material-symbols-outlined text-primary text-4xl">${icon}</span>
      <div>
        <h3 class="text-xl font-bold text-ink">${g}</h3>
        <div class="h-1 w-0 bg-primary group-hover:w-full transition-all duration-500 mt-2"></div>
      </div>
      <div class="absolute top-4 right-4 opacity-0 group-[.selected]:opacity-100 transition-all">
        <span class="material-symbols-outlined fill-icon text-primary text-2xl">check_circle</span>
      </div>`;
    div.onclick = () => toggleGenre(g, div);
    grid.appendChild(div);
  });
}

function toggleGenre(g, el) {
  const idx = state.genres.indexOf(g);
  if (idx === -1) { state.genres.push(g); el.classList.add('selected','border-primary-fixed','bg-primary-fixed'); }
  else            { state.genres.splice(idx,1); el.classList.remove('selected','border-primary-fixed','bg-primary-fixed'); }
  document.getElementById('genre-count').textContent = state.genres.length;
}

function skipOnboarding() {
  state.name = 'Explorer';
  state.genres = ['Action','Drama','Sci-Fi'];
  finishOnboarding();
}

function finishOnboarding() {
  const nameInput = document.getElementById('onboard-name').value.trim();
  state.name = nameInput || 'Explorer';
  if (state.genres.length === 0) state.genres = ['Action','Drama','Sci-Fi'];
  document.getElementById('avatar-letter').textContent = state.name[0].toUpperCase();
  discoverLoaded = false; // force fresh load
  showPage('discover');
}

// ── Discover page ──────────────────────────────────────────────────────────
let discoverLoaded = false;
async function loadDiscover() {
  buildContextChips();
  loadPersonalized();
  if (!discoverLoaded) {
    discoverLoaded = true;
    loadTopRated();
    loadHeroFeatured();
  }
}

function buildContextChips() {
  const chips = document.getElementById('context-chips');
  const items = [
    { label: state.context.time,   ctx:'time'   },
    { label: state.context.mood,   ctx:'mood'   },
    { label: state.context.social, ctx:'social' },
  ];
  chips.innerHTML = items.map(it =>
    `<button onclick="showPage('profile')" class="flex-shrink-0 bg-primary text-on-primary px-5 py-2 rounded-full text-xs font-bold shadow-lg shadow-primary/20 hover:scale-105 transition-transform">${it.label}</button>`
  ).join('') + `
    <button class="flex-shrink-0 bg-surface-container text-on-surface-variant px-5 py-2 rounded-full text-xs font-bold hover:bg-surface-container-high transition-colors">All Categories</button>
    <button class="flex-shrink-0 bg-surface-container text-on-surface-variant px-5 py-2 rounded-full text-xs font-bold hover:bg-surface-container-high transition-colors">Deep Thrill</button>
    <button class="flex-shrink-0 bg-surface-container text-on-surface-variant px-5 py-2 rounded-full text-xs font-bold hover:bg-surface-container-high transition-colors">Cyberpunk</button>
  `;
}

async function loadPersonalized() {
  const grid = document.getElementById('rec-grid');
  const loading = document.getElementById('rec-loading');
  const subtitle = document.getElementById('context-subtitle');

  grid.innerHTML = skeletonCards(8);
  loading.classList.remove('hidden');

  // Build rated_movies array matching backend Pydantic schema
  const ratedMovies = Object.entries(state.userRatings).map(([id, r]) => ({
    movieId: parseInt(id),
    rating: parseFloat(r)
  }));

  const payload = {
    preferred_genres: state.genres.length ? state.genres : ['Drama','Action'],
    context: {
      time_of_day: TIME_MAP[state.context.time]   || 'evening',
      mood:        MOOD_MAP[state.context.mood]    || 'relaxed',
      social:      SOCIAL_MAP[state.context.social] || 'alone',
    },
    rated_movies: ratedMovies,
    top_k:        24,
  };

  const data = await apiFetch('/recommendations/personalized', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });

  loading.classList.add('hidden');
  if (data && data.recommendations && data.recommendations.length) {
    // Normalise genres to arrays
    data.recommendations.forEach(m => { m.genres = ensureGenresArray(m.genres); });
    state.recAll  = data.recommendations;
    state.recPage = 1;
    subtitle.textContent = `Based on your taste for ${state.genres.slice(0,3).join(', ') || 'great cinema'}`;
    renderRecGrid(state.recAll.slice(0, 8));
  } else {
    subtitle.textContent = 'Connect your backend to get personalised results';
    grid.innerHTML = `<div class="col-span-full text-center py-12">
      <span class="material-symbols-outlined text-5xl text-outline mb-4 block">signal_wifi_off</span>
      <p class="text-on-surface-variant font-medium">Could not reach the API backend.</p>
      <p class="text-sm text-on-surface-variant/70 mt-1">Start the FastAPI server at <code class="bg-surface-container px-2 py-0.5 rounded">localhost:8000</code></p>
    </div>`;
  }
}

function renderRecGrid(movies) {
  const grid = document.getElementById('rec-grid');
  grid.innerHTML = movies.map(m => movieCard(m, 'rec')).join('');
}

function loadMoreRecs() {
  const next = state.recAll.slice(0, (state.recPage + 1) * 8);
  renderRecGrid(next);
  state.recPage++;
  if (state.recPage * 8 >= state.recAll.length) {
    document.getElementById('explore-all-btn').style.display = 'none';
  }
}

async function loadHeroFeatured() {
  const hero = document.getElementById('hero-featured');
  const data = await apiFetch('/recommendations/top?top_k=10&sort_by=rating');
  const movies = data && data.movies ? data.movies : [];
  // Normalise genres
  movies.forEach(m => { m.genres = ensureGenresArray(m.genres); });
  if (!movies.length) { hero.innerHTML = defaultHeroBanner(); hero.classList.remove('skeleton'); return; }
  // Pick the first movie that has a poster, or just the first one
  const m = movies.find(mv => mv.poster_url) || movies[0];
  const poster = m.poster_url
    ? `<img src="${m.poster_url}" class="absolute inset-0 w-full h-full object-cover scale-105 group-hover:scale-100 transition-transform duration-700" alt="${m.title}"/>`
    : `<div class="absolute inset-0 crimson-gradient opacity-15"></div>`;
  hero.classList.remove('skeleton');
  hero.innerHTML = `
    ${poster}
    <div class="absolute inset-0 bg-gradient-to-t from-background via-background/50 to-transparent"></div>
    <div class="absolute bottom-0 left-0 p-4 md:p-6 w-full lg:w-3/4 z-10">
      <div class="flex items-center gap-2 mb-1">
        <span class="inline-block px-2 py-0.5 crimson-gradient text-white rounded-full text-[9px] font-bold tracking-widest uppercase">Featured</span>
        ${m.avg_rating ? `<span class="text-xs font-black text-primary">★ ${m.avg_rating.toFixed(1)}</span>` : ''}
      </div>
      <h1 class="text-xl md:text-2xl font-extrabold text-on-surface tracking-tight mb-1 leading-tight">${m.title}</h1>
      <p class="text-xs text-on-surface-variant font-medium mb-2">${(m.genres||[]).join(' · ')}</p>
      <div class="flex items-center gap-2">
        <button onclick="openDetail(${m.movieId})"
          class="crimson-gradient text-white px-4 py-1.5 rounded-full flex items-center gap-1 font-bold text-xs hover:scale-105 transition-transform">
          <span class="material-symbols-outlined text-sm">play_arrow</span> Details
        </button>
        <button onclick="showPage('browse')"
          class="bg-surface/80 backdrop-blur-md text-primary px-3 py-1.5 rounded-full flex items-center gap-1 font-bold text-xs hover:bg-surface transition-colors">
          <span class="material-symbols-outlined text-sm">add</span> Browse
        </button>
      </div>
    </div>`;
}

function defaultHeroBanner() {
  return `<div class="absolute inset-0 crimson-gradient opacity-10"></div>
    <div class="absolute bottom-0 left-0 p-4 md:p-6 z-10">
      <h1 class="text-2xl font-extrabold text-on-surface tracking-tight mb-2">Your <span class="text-primary italic">Cinema</span></h1>
      <button onclick="showPage('browse')" class="crimson-gradient text-white px-4 py-1.5 rounded-full font-bold text-xs">Start Exploring</button>
    </div>`;
}

async function loadTopRated() {
  const data = await apiFetch('/recommendations/top?top_k=10&sort_by=rating');
  let movies = data && data.movies ? data.movies : [];
  // Normalise genres
  movies.forEach(m => { m.genres = ensureGenresArray(m.genres); });
  const scroll = document.getElementById('top-scroll');
  if (!movies.length) { scroll.innerHTML = '<p class="text-sm text-on-surface-variant">No data from API.</p>'; return; }
  scroll.innerHTML = movies.map(m => `
    <div class="flex-none w-48 group cursor-pointer" onclick="openDetail(${m.movieId})">
      <div class="relative aspect-[2/3] rounded-2xl overflow-hidden mb-3 bg-surface-container">
        ${m.poster_url
          ? `<img src="${m.poster_url}" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" alt="${m.title}"/>`
          : `<div class="w-full h-full poster-placeholder"><span class="material-symbols-outlined text-primary/40 text-4xl">movie_filter</span></div>`}
        <div class="absolute top-2 right-2 crimson-gradient px-2 py-0.5 rounded text-[10px] font-black text-white">
          ${m.avg_rating ? m.avg_rating.toFixed(1) + '★' : '—'}
        </div>
      </div>
      <h4 class="font-bold text-on-surface text-sm group-hover:text-primary transition-colors line-clamp-2">${m.title}</h4>
      <p class="text-xs text-on-surface-variant font-medium">${(m.genres||[]).slice(0,2).join(' · ')}</p>
    </div>`).join('');
}

// ── Browse page ────────────────────────────────────────────────────────────
let browseLoaded = false;
async function loadBrowse() {
  if (!browseLoaded) {
    browseLoaded = true;
    buildBrowseGenreChips();
    loadTrending();
  }
}

async function buildBrowseGenreChips() {
  if (!state.allGenres.length) {
    const data = await apiFetch('/movies/genres');
    state.allGenres = data && data.genres ? data.genres : [];
  }
  const chips = document.getElementById('browse-genre-chips');
  chips.innerHTML = state.allGenres.map(g =>
    `<button onclick="filterByGenre('${g}')"
      class="px-4 py-1.5 bg-surface-container text-primary font-bold text-[11px] uppercase tracking-widest rounded-full hover:bg-primary hover:text-white transition-colors"
    >${g}</button>`
  ).join('');
}

async function doSearch() {
  const q = document.getElementById('main-search').value.trim();
  if (!q) return;
  await runSearch(q);
}

async function doNavSearch() {
  const q = document.getElementById('nav-search').value.trim();
  if (!q) return;
  showPage('browse');
  document.getElementById('main-search').value = q;
  await runSearch(q);
}

async function runSearch(q) {
  document.getElementById('search-results-section').style.display = 'block';
  document.getElementById('collections-section').style.display = 'none';
  document.getElementById('search-results-title').textContent = `Results for "${q}"`;
  const grid = document.getElementById('search-results-grid');
  grid.innerHTML = skeletonCards(5, 'aspect-[2/3]');

  const data = await apiFetch('/movies/search?q=' + encodeURIComponent(q) + '&limit=20');
  const movies = data && data.movies ? data.movies : [];
  // Normalise genres
  movies.forEach(m => { m.genres = ensureGenresArray(m.genres); });
  if (!movies.length) {
    grid.innerHTML = `<div class="col-span-full py-12 text-center text-on-surface-variant">No movies found for "${q}".</div>`;
    return;
  }
  grid.innerHTML = movies.map(m => posterCard(m)).join('');
}

async function filterByGenre(genre) {
  document.getElementById('main-search').value = genre;
  await runSearch(genre);
}

function clearSearch() {
  document.getElementById('main-search').value = '';
  document.getElementById('search-results-section').style.display = 'none';
  document.getElementById('collections-section').style.display = 'block';
}

async function loadTrending() {
  const data = await apiFetch('/recommendations/top?top_k=10&sort_by=popularity');
  let movies = data && data.movies ? data.movies : [];
  // Normalise genres
  movies.forEach(m => { m.genres = ensureGenresArray(m.genres); });
  const scroll = document.getElementById('trending-scroll');
  if (!movies.length) { scroll.innerHTML = '<p class="text-sm text-on-surface-variant">No data from API.</p>'; return; }
  scroll.innerHTML = movies.map(m => `
    <div class="flex-none w-56 group cursor-pointer" onclick="openDetail(${m.movieId})">
      <div class="relative aspect-[2/3] rounded-2xl overflow-hidden mb-3 bg-surface-container">
        ${m.poster_url
          ? `<img src="${m.poster_url}" class="absolute inset-0 w-full h-full object-cover" alt="${m.title}"/>`
          : `<div class="absolute inset-0 poster-placeholder"><span class="material-symbols-outlined text-primary/40 text-5xl">movie_filter</span></div>`}
        <div class="absolute top-3 right-3 bg-primary text-white text-[10px] font-bold px-2 py-0.5 rounded">HOT</div>
      </div>
      <h4 class="font-bold text-on-surface group-hover:text-primary transition-colors text-sm line-clamp-1">${m.title}</h4>
      <p class="text-xs text-on-surface-variant font-medium">${(m.genres||[]).slice(0,2).join(' · ')}</p>
    </div>`).join('');
}

// ── Movie Detail page ──────────────────────────────────────────────────────
async function openDetail(movieId) {
  showPage('detail');
  const content = document.getElementById('detail-content');
  content.innerHTML = `<div class="max-w-7xl mx-auto px-4 md:px-8 py-16 flex items-center justify-center min-h-[50vh]">
    <div class="text-center">
      <div class="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
      <p class="text-on-surface-variant">Loading…</p>
    </div>
  </div>`;

  const [movieData, simsData] = await Promise.all([
    apiFetch(`/movies/${movieId}`),
    apiFetch(`/recommendations/movie/${movieId}?top_k=5`)
  ]);

  if (!movieData) {
    content.innerHTML = `<div class="max-w-7xl mx-auto px-8 py-24 text-center">
      <p class="text-on-surface-variant text-lg">Could not load movie details.</p>
      <button onclick="history.back()" class="mt-6 text-primary font-bold">← Go Back</button>
    </div>`;
    return;
  }

  const m    = movieData;
  m.genres = ensureGenresArray(m.genres);
  const sims = simsData && simsData.recommendations ? simsData.recommendations : [];
  sims.forEach(s => { s.genres = ensureGenresArray(s.genres); });
  const stars = m.avg_rating ? '★'.repeat(Math.round(m.avg_rating / 5 * 5)) : '—';
  const myRating = state.userRatings[movieId] || 0;

  content.innerHTML = `
    <!-- Hero backdrop -->
    <section class="relative w-full h-[240px] md:h-[300px] overflow-hidden flex items-end">
      <div class="absolute inset-0">
        ${m.poster_url
          ? `<img src="${m.poster_url}" class="w-full h-full object-cover scale-105" alt="${m.title}"/>`
          : `<div class="w-full h-full crimson-gradient opacity-20"></div>`}
        <div class="absolute inset-0 bg-gradient-to-t from-background via-background/40 to-transparent"></div>
        <div class="absolute inset-0 bg-gradient-to-r from-background via-transparent to-transparent"></div>
      </div>
      <div class="relative z-10 w-full max-w-7xl mx-auto px-6 md:px-8 pb-6">
        <div class="flex items-center gap-3 mb-2">
          <button onclick="window.history.back()" class="text-on-surface-variant hover:text-primary transition-colors flex items-center gap-1 text-sm font-bold">
            <span class="material-symbols-outlined text-sm">arrow_back</span> Back
          </button>
        </div>
        <div class="flex flex-wrap items-center gap-3 mb-2">
          <div class="crimson-gradient px-3 py-1 rounded-full text-white flex items-center gap-2 shadow-lg shadow-primary/20">
            <span class="text-[10px] font-bold tracking-widest uppercase">Avg Rating</span>
            <span class="font-black text-base">${m.avg_rating ? m.avg_rating.toFixed(1) : '—'}</span>
          </div>
          ${m.year ? `<span class="text-xs font-bold text-on-surface-variant bg-surface-container/60 px-3 py-1 rounded-full">${m.year}</span>` : ''}
        </div>
        <h1 class="text-3xl md:text-4xl font-extrabold tracking-tighter text-on-surface mb-2 leading-tight">${m.title}</h1>
        <div class="flex flex-wrap items-center gap-3 text-on-surface-variant font-medium text-sm mb-4">
          ${m.avg_rating ? `<span class="flex items-center gap-1"><span class="material-symbols-outlined fill-icon text-primary text-sm">star</span>${m.avg_rating.toFixed(1)} (${(m.num_ratings||0).toLocaleString()} ratings)</span>` : ''}
          ${(m.genres||[]).map(g=>`<span>${g}</span>`).join('<span>·</span>')}
        </div>
        <div class="flex flex-wrap gap-3">
          <button onclick="openDetail(${movieId} /*noop - already here*/)"
            class="crimson-gradient text-white px-6 py-2.5 rounded-full font-bold text-sm flex items-center gap-2 hover:scale-105 transition-transform shadow-xl shadow-primary/30">
            <span class="material-symbols-outlined fill-icon text-base">play_arrow</span> Watch Preview
          </button>
          <button onclick="addToList(${movieId},'${(m.title||'').replace(/'/g,"\\'")}')" 
            class="bg-surface-container-lowest/80 backdrop-blur-md text-on-surface border border-outline-variant/20 px-5 py-2.5 rounded-full font-bold text-sm flex items-center gap-2 hover:bg-white transition-colors">
            <span class="material-symbols-outlined text-base">add</span> My List
          </button>
        </div>
      </div>
    </section>

    <!-- Content grid -->
    <section class="max-w-7xl mx-auto px-4 md:px-8 py-16">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div class="md:col-span-2 space-y-10">
          <div>
            <h2 class="text-2xl font-bold text-ink mb-5 flex items-center gap-3">
              About This Film
              <div class="h-[2px] w-16 crimson-gradient rounded-full"></div>
            </h2>
            <p class="text-lg text-on-surface-variant leading-relaxed font-light">
              ${(m.genres||[]).length ? `A ${m.genres.slice(0,3).join(', ')} film` : 'A cinematic experience'} 
              ${m.year ? `from ${m.year}` : ''}.
              ${m.num_ratings ? `Rated by ${m.num_ratings.toLocaleString()} viewers` : ''}
              ${m.avg_rating ? `with an average score of ${m.avg_rating.toFixed(2)}.` : '.'}
            </p>
          </div>
          <!-- Genre badges -->
          <div>
            <h2 class="text-sm uppercase tracking-widest text-primary font-extrabold mb-4">Genres</h2>
            <div class="flex flex-wrap gap-2">
              ${(m.genres||[]).map(g=>`
                <button onclick="filterByGenreAndBrowse('${g}')"
                  class="px-4 py-2 bg-surface-container text-on-surface-variant rounded-xl text-sm font-medium hover:bg-primary hover:text-white transition-colors">${g}</button>
              `).join('')}
            </div>
          </div>
          <!-- Similar movies -->
          ${sims.length ? `
          <div>
            <h2 class="text-2xl font-bold text-ink mb-6">More Like This</h2>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
              ${sims.map(s=>`
                <div class="group cursor-pointer" onclick="openDetail(${s.movieId})">
                  <div class="aspect-[2/3] rounded-2xl overflow-hidden bg-surface-container-low relative mb-2">
                    ${s.poster_url
                      ? `<img src="${s.poster_url}" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" alt="${s.title}"/>`
                      : `<div class="w-full h-full flex items-center justify-center"><span class="material-symbols-outlined text-primary/40 text-4xl">movie_filter</span></div>`}
                    <div class="absolute top-2 right-2 crimson-gradient px-2 py-0.5 rounded text-[10px] font-black text-white">
                      ${s.score ? Math.round(s.score*100)+'%' : ''}
                    </div>
                  </div>
                  <h4 class="font-bold text-on-surface text-sm group-hover:text-primary transition-colors line-clamp-2">${s.title}</h4>
                  <p class="text-xs text-on-surface-variant">${(s.genres||[]).slice(0,2).join(' · ')}</p>
                </div>`).join('')}
            </div>
          </div>` : ''}
        </div>

        <!-- Sidebar -->
        <div class="space-y-6">
          <div class="bg-surface-container-low p-7 rounded-3xl space-y-5">
            <h3 class="text-[11px] uppercase tracking-widest text-primary font-extrabold">Details</h3>
            <div class="space-y-3">
              ${m.year ? `<div class="flex justify-between py-2 border-b border-outline-variant/10"><span class="text-on-surface-variant text-sm">Year</span><span class="font-bold text-sm">${m.year}</span></div>` : ''}
              ${m.avg_rating ? `<div class="flex justify-between py-2 border-b border-outline-variant/10"><span class="text-on-surface-variant text-sm">Rating</span><span class="font-bold text-sm">${m.avg_rating.toFixed(2)} / 5</span></div>` : ''}
              ${m.num_ratings ? `<div class="flex justify-between py-2 border-b border-outline-variant/10"><span class="text-on-surface-variant text-sm">Votes</span><span class="font-bold text-sm">${m.num_ratings.toLocaleString()}</span></div>` : ''}
              <div class="flex justify-between py-2"><span class="text-on-surface-variant text-sm">Genres</span><span class="font-bold text-sm text-right ml-4">${(m.genres||[]).join(', ')}</span></div>
            </div>
          </div>

          <!-- Rate this movie -->
          <div class="bg-surface-container-low p-7 rounded-3xl">
            <h3 class="text-[11px] uppercase tracking-widest text-primary font-extrabold mb-4">Your Rating</h3>
            <div class="flex gap-1" id="detail-stars-${movieId}">
              ${[1,2,3,4,5].map(s=>`
                <button class="star text-2xl ${s<=myRating?'text-primary':'text-outline/30'}"
                  onclick="rateMovieDetail(${movieId},'${(m.title||'').replace(/'/g,"\\'")}',${s})"
                  onmouseover="previewStars(${movieId},${s})"
                  onmouseleave="resetStars(${movieId},${myRating})"
                >★</button>`).join('')}
            </div>
            <p class="text-xs text-on-surface-variant mt-2">${myRating ? `You rated this ${myRating}/5` : 'Tap to rate'}</p>
          </div>
        </div>
      </div>
    </section>`;
}

function filterByGenreAndBrowse(genre) {
  showPage('browse');
  setTimeout(()=>filterByGenre(genre), 50);
}

// ── Rate page ──────────────────────────────────────────────────────────────
function loadRatePage() {
  renderRatingHistory();
}

let rateSearchTimer;
function rateSearch() {
  clearTimeout(rateSearchTimer);
  const q = document.getElementById('rate-search').value.trim();
  if (!q) { document.getElementById('rate-results').innerHTML = ''; return; }
  rateSearchTimer = setTimeout(()=>doRateSearch(q), 400);
}

async function doRateSearch(q) {
  const container = document.getElementById('rate-results');
  container.innerHTML = `<p class="text-sm text-on-surface-variant">Searching…</p>`;
  const data = await apiFetch('/movies/search?q=' + encodeURIComponent(q) + '&limit=8');
  const movies = data && data.movies ? data.movies : [];
  // Normalise genres
  movies.forEach(m => { m.genres = ensureGenresArray(m.genres); });
  if (!movies.length) { container.innerHTML = `<p class="text-sm text-on-surface-variant">No movies found.</p>`; return; }
  container.innerHTML = movies.map(m => {
    const my = state.userRatings[m.movieId] || 0;
    return `<div class="flex items-center gap-4 bg-surface-container-low rounded-2xl px-5 py-4 hover:bg-surface-container-high transition-colors">
      ${m.poster_url
        ? `<img src="${m.poster_url}" class="w-12 h-16 object-cover rounded-xl flex-shrink-0" alt="${m.title}"/>`
        : `<div class="w-12 h-16 poster-placeholder flex-shrink-0 rounded-xl"><span class="material-symbols-outlined text-primary/40">movie_filter</span></div>`}
      <div class="flex-1 min-w-0">
        <p class="font-bold text-on-surface text-sm line-clamp-1">${m.title}</p>
        <p class="text-xs text-on-surface-variant">${(m.genres||[]).slice(0,3).join(' · ')}</p>
        <div class="flex gap-1 mt-2">
          ${[1,2,3,4,5].map(s=>`
            <button class="star text-base ${s<=my?'text-primary':'text-outline/30'}"
              onclick="rateMovie(${m.movieId},'${(m.title||'').replace(/'/g,"\\'")}',${s})"
            >★</button>`).join('')}
        </div>
      </div>
      <div class="text-xs text-on-surface-variant flex-shrink-0">${m.avg_rating ? m.avg_rating.toFixed(1)+'★' : ''}</div>
    </div>`;
  }).join('');
}

function rateMovie(movieId, title, score) {
  state.userRatings[movieId] = score;
  showToast(`Rated "${title}" ${score}/5 ⭐`);
  rateSearch(); // refresh the list
  renderRatingHistory();
  discoverLoaded = false; // force rec refresh next time
}

function rateMovieDetail(movieId, title, score) {
  state.userRatings[movieId] = score;
  showToast(`Rated "${title}" ${score}/5 ⭐`);
  // update stars in the detail view
  resetStars(movieId, score);
  discoverLoaded = false;
}

function previewStars(movieId, n) {
  const container = document.getElementById(`detail-stars-${movieId}`);
  if (!container) return;
  container.querySelectorAll('.star').forEach((s,i)=>{
    s.className = `star text-2xl ${i<n?'text-primary':'text-outline/30'}`;
  });
}
function resetStars(movieId, n) {
  const container = document.getElementById(`detail-stars-${movieId}`);
  if (!container) return;
  container.querySelectorAll('.star').forEach((s,i)=>{
    s.className = `star text-2xl ${i<n?'text-primary':'text-outline/30'}`;
  });
}

function renderRatingHistory() {
  const hist = document.getElementById('rating-history');
  const noMsg = document.getElementById('no-ratings-msg');
  const entries = Object.entries(state.userRatings);
  if (!entries.length) { noMsg.style.display='block'; return; }
  noMsg.style.display = 'none';
  hist.innerHTML = entries.map(([id, r])=>`
    <div class="flex items-center justify-between bg-surface-container-low rounded-2xl px-5 py-4">
      <div>
        <p class="font-bold text-on-surface text-sm">Movie #${id}</p>
        <div class="flex gap-0.5 mt-1">${[1,2,3,4,5].map(s=>`
          <span class="text-sm ${s<=r?'text-primary':'text-outline/30'}">★</span>`).join('')}
        </div>
      </div>
      <button onclick="delete state.userRatings[${id}]; renderRatingHistory();"
        class="text-xs text-on-surface-variant hover:text-primary transition-colors font-bold">Remove</button>
    </div>`).join('');
}

// ── Profile page ───────────────────────────────────────────────────────────
function loadProfilePage() {
  document.getElementById('profile-name').value = state.name;
  document.getElementById('profile-name-display').textContent = state.name || 'Your Profile';
  document.getElementById('profile-avatar').textContent = (state.name||'?')[0].toUpperCase();

  // Genre chips
  const gWrap = document.getElementById('profile-genres');
  gWrap.innerHTML = state.allGenres.map(g=>{
    const sel = state.genres.includes(g);
    return `<button onclick="toggleProfileGenre('${g}',this)"
      class="px-4 py-1.5 text-sm font-bold rounded-full transition-colors ${sel?'crimson-gradient text-white':'bg-surface-container text-on-surface-variant hover:bg-primary-fixed'}">${g}</button>`;
  }).join('');

  buildContextSelector('ctx-time',   TIME_OPTIONS,   'time');
  buildContextSelector('ctx-mood',   MOOD_OPTIONS,   'mood');
  buildContextSelector('ctx-social', SOCIAL_OPTIONS, 'social');
}

function buildContextSelector(containerId, options, key) {
  const el = document.getElementById(containerId);
  el.innerHTML = options.map(o=>`
    <button onclick="setContext('${key}','${o}',this)"
      class="px-4 py-1.5 text-sm font-bold rounded-full transition-colors ${state.context[key]===o?'crimson-gradient text-white':'bg-surface-container text-on-surface-variant hover:bg-primary-fixed'}">${o}</button>
  `).join('');
}

function setContext(key, val, btn) {
  state.context[key] = val;
  btn.closest('div').querySelectorAll('button').forEach(b=>{
    b.className = `px-4 py-1.5 text-sm font-bold rounded-full transition-colors ${b.textContent.trim()===val?'crimson-gradient text-white':'bg-surface-container text-on-surface-variant hover:bg-primary-fixed'}`;
  });
}

function toggleProfileGenre(g, btn) {
  const idx = state.genres.indexOf(g);
  if (idx===-1) { state.genres.push(g); btn.className = 'px-4 py-1.5 text-sm font-bold rounded-full crimson-gradient text-white'; }
  else          { state.genres.splice(idx,1); btn.className = 'px-4 py-1.5 text-sm font-bold rounded-full bg-surface-container text-on-surface-variant hover:bg-primary-fixed'; }
}

function updateProfile() { /* live; saves on button click */ }

function saveProfileAndDiscover() {
  state.name = document.getElementById('profile-name').value.trim() || 'Explorer';
  document.getElementById('avatar-letter').textContent = state.name[0].toUpperCase();
  discoverLoaded = false;
  showToast('Profile saved! Refreshing recommendations…');
  showPage('discover');
}

// ── My List / add to list ──────────────────────────────────────────────────
function addToList(movieId, title) {
  showToast(`"${title}" added to My List ✓`);
}

// ── Modal helpers ──────────────────────────────────────────────────────────
function openModal(html) {
  document.getElementById('modal-inner').innerHTML = html;
  document.getElementById('modal-overlay').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}
function closeModal(e) {
  if (e && e.target !== document.getElementById('modal-overlay')) return;
  document.getElementById('modal-overlay').classList.add('hidden');
  document.body.style.overflow = '';
}

// ── Card helpers ───────────────────────────────────────────────────────────
function movieCard(m, type='rec') {
  const score = m.score !== undefined ? Math.round(m.score * 100) : null;
  const rating = m.avg_rating ? m.avg_rating.toFixed(1) : null;
  return `
  <div class="group cursor-pointer" onclick="openDetail(${m.movieId})">
    <div class="relative rounded-[2rem] overflow-hidden bg-surface-container-highest flex flex-col crimson-shadow hover:shadow-2xl transition-all duration-300 hover:-translate-y-1">
      <div class="relative h-48 overflow-hidden">
        ${m.poster_url
          ? `<img src="${m.poster_url}" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" alt="${m.title}"/>`
          : `<div class="w-full h-full flex items-center justify-center bg-surface-container"><span class="material-symbols-outlined text-primary/30 text-5xl">movie_filter</span></div>`}
        ${score!==null ? `<div class="absolute bottom-3 right-3 crimson-gradient px-2.5 py-1 rounded-xl text-white text-xs font-bold">${score}% match</div>` : ''}
        ${m.genres&&m.genres.length ? `<div class="absolute top-3 left-3"><span class="crimson-gradient text-white px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-widest">${m.genres[0]}</span></div>` : ''}
      </div>
      <div class="p-5 flex-1 flex flex-col">
        <div class="flex justify-between items-start mb-2">
          <h3 class="text-base font-extrabold text-on-surface line-clamp-2 flex-1 mr-2">${m.title}</h3>
          ${rating?`<div class="flex items-center gap-1 flex-shrink-0"><span class="material-symbols-outlined fill-icon text-primary text-sm">star</span><span class="font-bold text-sm">${rating}</span></div>`:''}
        </div>
        <p class="text-xs text-on-surface-variant font-medium mb-3">${(m.genres||[]).slice(0,3).join(' · ')}</p>
        ${score!==null ? `
        <div class="mt-auto">
          <div class="flex justify-between text-[10px] text-on-surface-variant font-bold mb-1">
            <span>Match</span><span>${score}%</span>
          </div>
          <div class="w-full h-1 bg-surface-container rounded-full overflow-hidden">
            <div class="match-bar-inner h-full crimson-gradient rounded-full" style="width:${score}%"></div>
          </div>
        </div>` : ''}
      </div>
    </div>
  </div>`;
}

function posterCard(m) {
  return `
  <div class="group cursor-pointer" onclick="openDetail(${m.movieId})">
    <div class="aspect-[2/3] rounded-2xl overflow-hidden bg-surface-container-low relative mb-3">
      ${m.poster_url
        ? `<img src="${m.poster_url}" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" alt="${m.title}"/>`
        : `<div class="w-full h-full flex items-center justify-center"><span class="material-symbols-outlined text-primary/30 text-4xl">movie_filter</span></div>`}
      <div class="absolute inset-0 bg-primary/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
        <span class="material-symbols-outlined text-white text-4xl">arrow_forward</span>
      </div>
    </div>
    <h4 class="font-bold text-on-surface text-sm group-hover:text-primary transition-colors line-clamp-2">${m.title}</h4>
    <p class="text-xs text-on-surface-variant mt-0.5">${(m.genres||[]).slice(0,2).join(' · ')}</p>
  </div>`;
}

function skeletonCards(n, aspect='h-48') {
  return Array(n).fill(0).map(()=>`
    <div class="rounded-[2rem] overflow-hidden bg-surface-container-highest">
      <div class="${aspect} skeleton"></div>
      <div class="p-5 space-y-2">
        <div class="skeleton h-4 w-3/4"></div>
        <div class="skeleton h-3 w-1/2"></div>
      </div>
    </div>`).join('');
}

// ── API health check ───────────────────────────────────────────────────────
async function checkAPIHealth() {
  const dot   = document.getElementById('api-dot');
  const label = document.getElementById('api-label');
  const data  = await apiFetch('/health');
  if (data && data.status === 'ok') {
    // Check if all models are loaded
    const models = data.models || {};
    const allLoaded = models.content_based && models.collaborative && models.hybrid;
    if (allLoaded) {
      dot.className   = 'w-2 h-2 rounded-full bg-green-500';
      label.textContent = 'API Online';
    } else {
      dot.className   = 'w-2 h-2 rounded-full bg-yellow-400';
      label.textContent = 'Partial Load';
    }
  } else if (data) {
    dot.className   = 'w-2 h-2 rounded-full bg-yellow-400';
    label.textContent = 'Starting Up…';
  } else {
    dot.className   = 'w-2 h-2 rounded-full bg-red-400';
    label.textContent = 'API Offline';
  }
}

// ── Scroll reveal ──────────────────────────────────────────────────────────
const ro = new IntersectionObserver(entries => {
  entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
}, { threshold: 0.1 });
function attachReveal() {
  document.querySelectorAll('.reveal').forEach(el => ro.observe(el));
}

// ── Init ───────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  document.body.classList.add('onboarding-active');
  await initGenreGrid();
  checkAPIHealth();
  setInterval(checkAPIHealth, 30000);
});
</script>
</body>
</html>
"""

# ── Simple HTTP Server with API proxy ─────────────────────────────────────
class StreamLensHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silence default logging

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self._serve_html()
        elif self.path.startswith('/api/'):
            self._proxy_api()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith('/api/'):
            self._proxy_api()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _serve_html(self):
        data = HTML.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def _proxy_api(self):
        # Strip /api prefix → forward to backend
        target_path = self.path[4:]  # remove /api
        url = BACKEND_URL + target_path

        try:
            length  = int(self.headers.get('Content-Length', 0))
            body    = self.rfile.read(length) if length else None
            ct      = self.headers.get('Content-Type', '')
            headers = {}
            if ct:
                headers['Content-Type'] = ct

            req = urllib.request.Request(url, data=body, headers=headers,
                                         method=self.command)
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
                self.send_response(resp.status)
                self.send_header('Content-Type',
                                 resp.headers.get('Content-Type', 'application/json'))
                self.send_header('Content-Length', str(len(content)))
                self._cors_headers()
                self.end_headers()
                self.wfile.write(content)

        except urllib.error.HTTPError as e:
            content = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self._cors_headers()
            self.end_headers()
            self.wfile.write(content)

        except Exception:
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self._cors_headers()
            self.end_headers()
            self.wfile.write(b'{"detail":"Backend unavailable"}')

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')


def main():
    server = http.server.ThreadingHTTPServer(('0.0.0.0', FRONTEND_PORT), StreamLensHandler)
    url = f"http://localhost:{FRONTEND_PORT}"
    print(f"\n🎬  StreamLens — Cinematic Crimson Edition")
    print(f"   Frontend : {url}")
    print(f"   Backend  : {BACKEND_URL}")
    print(f"\n   Press Ctrl+C to stop.\n")

    def open_browser():
        import time; time.sleep(0.8)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n   Goodbye! 👋\n")
        server.server_close()


if __name__ == '__main__':
    main()
