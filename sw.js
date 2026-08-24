const CACHE="teksar-monitoreo-v3";
self.addEventListener("install",e=>{ self.skipWaiting(); });
self.addEventListener("activate",e=>{
  e.waitUntil(
    caches.keys().then(ks=>Promise.all(ks.map(k=>caches.delete(k)))).then(()=>self.clients.claim())
  );
});
self.addEventListener("fetch",e=>{
  // Network-first: siempre intenta traer lo ultimo de la red
  e.respondWith(
    fetch(e.request).then(r=>{
      const copia=r.clone();
      caches.open(CACHE).then(c=>c.put(e.request,copia)).catch(()=>{});
      return r;
    }).catch(()=>caches.match(e.request))
  );
});
