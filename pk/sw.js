/* Pada Kośa offline cache. Build 1286475-63-256.
   HTML is network-first so a redeploy is picked up; the data files are
   immutable for a given build, so they are cache-first. */
var C = "pk-1286475-63-256";
var SHELL = ["./", "./index.html", "./data/words.txt", "./data/meta.json",
             "./assets/vijayadv.woff2"];
self.addEventListener("install", function(e){
  e.waitUntil(caches.open(C).then(function(c){ return c.addAll(SHELL); })
    .then(function(){ return self.skipWaiting(); }).catch(function(){}));
});
self.addEventListener("activate", function(e){
  e.waitUntil(caches.keys().then(function(ks){
    return Promise.all(ks.map(function(k){ return k === C ? null : caches.delete(k); }));
  }).then(function(){ return self.clients.claim(); }));
});
self.addEventListener("fetch", function(e){
  if (e.request.method !== "GET") return;
  var u = new URL(e.request.url);
  if (u.origin !== location.origin) return;
  var isDoc = e.request.mode === "navigate" || u.pathname.endsWith(".html");
  if (isDoc){
    e.respondWith(fetch(e.request).then(function(r){
      var copy = r.clone();
      caches.open(C).then(function(c){ c.put(e.request, copy); });
      return r;
    }).catch(function(){ return caches.match(e.request); }));
    return;
  }
  e.respondWith(caches.match(e.request).then(function(hit){
    return hit || fetch(e.request).then(function(r){
      if (r.ok){ var copy = r.clone();
        caches.open(C).then(function(c){ c.put(e.request, copy); }); }
      return r;
    });
  }));
});
