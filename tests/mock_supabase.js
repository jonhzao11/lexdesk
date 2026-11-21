// Simulação mínima do cliente Supabase para testar a interface sem rede
(function () {
  var U1 = '11111111-1111-1111-1111-111111111111', U2 = '22222222-2222-2222-2222-222222222222';
  var db = window.__db = {
    profiles: [{ id: U1, nome: 'Ana Teste', estado: window.__estadoAna || 'ano3', genero: 'f', avatar_url: null, chat_regras_em: '2026-11-01', dm_pref: 'todos', created_at: '2026-11-01' }, { id: U2, nome: 'Bruno Teste', estado: 'ano1', genero: 'm', avatar_url: null, chat_regras_em: '2026-11-01', dm_pref: 'todos', created_at: '2026-11-01' }],
    docs: (window.__docs || []), atualizacoes: [], chat_msgs: [], moderadores: [], chat_suspensoes: [], chat_denuncias: [], denuncias_privadas: [],
    dm_msgs: [{ id: 1, de: U2, para: U1, texto: 'Olá Ana! Tens os apontamentos de Processo Penal?', lida_em: null, created_at: new Date(Date.now() - 600000).toISOString() }],
    dm_contactos: [], salas: [], sala_membros: [], sala_msgs: [], sala_quadro: [], sala_estado: [], sala_respostas: [], juridle: [], lei_diplomas: (window.__leiD || []), lei_artigos: (window.__leiA || [])
  };
  var seq = 100;
  function Q(t) { this.t = t; this.f = []; this.op = 'select'; this.lim = null; this.ord = null; this.one = 0; this.body = null; this.cnt = false; this.head = false; }
  Q.prototype.select = function (c, o) { if (this.op === 'select') this.op = 'select'; this.ret = true; if (o && o.count) { this.cnt = true; this.head = o.head; } return this; };
  ['eq', 'neq', 'gte', 'in', 'ilike'].forEach(function (k) { Q.prototype[k] = function (c, v) { this.f.push([k, c, v]); return this; }; });
  Q.prototype.or = function (s) { var m = s.match(/de\.eq\.([^,]+)/); if (m) this.f.push(['or', m[1]]); else { var w = (s.match(/ilike\.%([^%]*)%/) || [])[1] || ''; this.f.push(['orlike', w]); } return this; };
  Q.prototype.range = function (a, b) { this.off = a; this.lim = b - a + 1; return this; };
  Q.prototype.order = function (c, o) { this.ord = [c, o && o.ascending === false]; return this; };
  Q.prototype.limit = function (n) { this.lim = n; return this; };
  Q.prototype.maybeSingle = function () { this.one = 1; return this; };
  Q.prototype.single = function () { this.one = 2; return this; };
  Q.prototype.insert = function (b) { this.op = 'insert'; this.body = b; return this; };
  Q.prototype.upsert = function (b) { this.op = 'upsert'; this.body = b; return this; };
  Q.prototype.update = function (b) { this.op = 'update'; this.body = b; return this; };
  Q.prototype.delete = function () { this.op = 'delete'; return this; };
  function match(r, f) { return f.every(function (x) { var v = r[x[1]]; if (x[0] === 'eq') return String(v) === String(x[2]); if (x[0] === 'neq') return String(v) !== String(x[2]); if (x[0] === 'gte') return String(v) >= String(x[2]); if (x[0] === 'in') return x[2].map(String).indexOf(String(v)) >= 0; if (x[0] === 'ilike') return String(v).toLowerCase().indexOf(x[2].replace(/%/g, '').toLowerCase()) >= 0; if (x[0] === 'or') return r.de === x[1] || r.para === x[1]; if (x[0] === 'orlike') return ((r.epigrafe || '') + ' ' + (r.texto || '')).toLowerCase().indexOf(x[1].toLowerCase()) >= 0; return true; }); }
  Q.prototype.then = function (ok, ko) {
    var T = db[this.t] || (db[this.t] = []), self = this, res;
    try {
      if (this.op === 'select') {
        var l = T.filter(function (r) { return match(r, self.f); });
        if (this.t === 'salas') l = l.map(function (s) { var c = Object.assign({}, s); c.sala_membros = [{ count: db.sala_membros.filter(function (m) { return m.sala_id === s.id; }).length }]; return c; });
        if (this.ord) { var c = this.ord[0].replace('data->', ''); l.sort(function (a, b) { var x = a[c] != null ? a[c] : (a.data || {})[c], y = b[c] != null ? b[c] : (b.data || {})[c]; return (x > y ? 1 : x < y ? -1 : 0) * (self.ord[1] ? -1 : 1); }); }
        if (this.off) l = l.slice(this.off); if (this.lim) l = l.slice(0, this.lim);
        res = { data: this.one ? (l[0] || null) : l, error: null, count: this.cnt ? l.length : null };
      } else if (this.op === 'insert' || this.op === 'upsert') {
        var rows = [].concat(this.body).map(function (b) {
          var r = Object.assign({ created_at: new Date().toISOString() }, b);
          if (self.t === 'dm_msgs') { r.de = r.de || window.__uid; r.lida_em = null; }
          if (/sala_msgs|sala_quadro|chat_msgs/.test(self.t)) r.autor = r.autor || window.__uid;
          if (self.t === 'sala_respostas') r.user_id = r.user_id || window.__uid;
          if (r.id == null && self.t !== 'sala_respostas' && self.t !== 'docs' && self.t !== 'dm_contactos' && self.t !== 'sala_estado') r.id = ++seq;
          var key = self.t === 'docs' ? ['col', 'id'] : self.t === 'dm_contactos' ? ['user_id', 'outro'] : self.t === 'sala_respostas' ? ['ativ_id', 'user_id', 'ronda'] : ['id'];
          var ex = T.filter(function (x) { return key.every(function (k) { return x[k] === r[k]; }); })[0];
          if (ex && self.op === 'insert' && self.t === 'sala_respostas') throw { message: 'duplicate key' };
          if (ex) Object.assign(ex, r); else T.push(r);
          if (self.t === 'eventos') { r.criador = r.criador || window.__uid; r.cancelado = false; db.evento_part = db.evento_part || []; db.evento_part.push({ evento_id: r.id, user_id: r.criador }); }
          if (self.t === 'evento_msgs') r.autor = r.autor || window.__uid;
          window.__rt(self.t, 'INSERT', r); return r;
        });
        res = { data: this.one ? rows[0] : rows, error: null };
      } else if (this.op === 'update') {
        var u = T.filter(function (r) { return match(r, self.f); }); u.forEach(function (r) { Object.assign(r, self.body); window.__rt(self.t, 'UPDATE', r); });
        res = { data: this.one ? u[0] : u, error: null };
      } else if (this.op === 'delete') {
        var d = T.filter(function (r) { return match(r, self.f); }); db[this.t] = T.filter(function (r) { return d.indexOf(r) < 0; }); d.forEach(function (r) { window.__rt(self.t, 'DELETE', null, r); });
        res = { data: d, error: null };
      }
    } catch (e) { res = { data: null, error: e }; }
    return Promise.resolve(res).then(ok, ko);
  };
  var chans = [];
  window.__rt = function (t, ev, n, o) { setTimeout(function () { chans.forEach(function (c) { c.h.forEach(function (h) { if (h.t === t) h.fn({ eventType: ev, new: n || {}, old: o || {} }); }); }); }, 5); };
  function Ch(name) { this.name = name; this.h = []; this.p = null; chans.push(this); }
  Ch.prototype.on = function (k, cfg, fn) { if (k === 'presence') this.p = fn; else this.h.push({ t: cfg.table, fn: fn }); return this; };
  Ch.prototype.subscribe = function (cb) { var s = this; setTimeout(function () { cb && cb('SUBSCRIBED'); s.p && s.p(); }, 10); return this; };
  Ch.prototype.track = function () { return Promise.resolve(); }; Ch.prototype.untrack = function () { return Promise.resolve(); };
  Ch.prototype.presenceState = function () { var o = {}; o[window.__uid] = [{ nome: 'Ana Teste' }]; o[U2] = [{ nome: 'Bruno Teste' }]; return o; };
  var sess = { user: { id: U1, email: 'ana@teste.pt', user_metadata: {} } }; window.__uid = U1;
  window.supabase = { createClient: function () {
    return {
      from: function (t) { return new Q(t); },
      channel: function (n) { return new Ch(n); }, removeChannel: function () {},
      auth: { getSession: function () { return Promise.resolve({ data: { session: window.__guest ? null : sess } }); }, signInWithPassword: function () { window.__guest = false; return Promise.resolve({ data: { session: sess } }); }, signUp: function () { window.__guest = false; return Promise.resolve({ data: { session: sess } }); }, onAuthStateChange: function () {}, signOut: function () { return Promise.resolve({}); } },
      storage: { from: function () { return { upload: function (p) { return Promise.resolve({ data: { path: p }, error: null }); }, getPublicUrl: function (p) { return { data: { publicUrl: 'https://x/' + p } }; }, createSignedUrl: function (p) { return Promise.resolve({ data: { signedUrl: 'https://x/' + p }, error: null }); }, remove: function () { return Promise.resolve({ data: [], error: null }); }, list: function () { return Promise.resolve({ data: [{ name: 'a.png' }], error: null }); } }; } },
      rpc: function (n, a) {
        if (n.indexOf('pd_') === 0) {
          var K = {'pc1':3,'pc2':1,'pc3':2,'pc4':1,'pc5':1,'pc6':0,'pc7':1,'pc8':1,'pc9':1,'pc10':1,'pp1':1,'pp2':3,'pp3':2,'pp4':2,'pp5':1,'pp6':1,'pp7':1,'pp8':1,'pp9':1,'cv1':3,'cv2':1,'cv3':2,'cv4':1,'cv5':0,'cv6':2,'cv7':2,'cv8':1,'cv9':0,'cn1':1,'cn2':1,'cn3':0,'cn4':1,'cn5':1,'cn6':1,'cn7':0,'cn8':2,'pn1':1,'pn2':2,'pn3':2,'pn4':2,'pn5':1,'pn6':2,'pn7':1,'pn8':1,'eoa1':1,'eoa2':1,'eoa3':1,'eoa4':1,'eoa5':1}, hoje = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Lisbon' }).format(new Date()), R = db.pd_respostas || (db.pd_respostas = []);
          var meu = R.filter(function (x) { return x.user_id === window.__uid && x.dia === hoje; })[0];
          if (n === 'pd_sequencia') return Promise.resolve({ data: R.filter(function (x) { return x.user_id === window.__uid && x.respondido_em; }).length ? 3 : 0, error: null });
          if (n === 'pd_iniciar') { if (!meu) { meu = { user_id: window.__uid, dia: hoje, qid: window.__pdq || 'pc2', visto_em: new Date().toISOString(), respondido_em: null, pontos: 0 }; R.push(meu); } return Promise.resolve({ data: { dia: hoje, qid: meu.qid, respondida: !!meu.respondido_em, opcao: meu.opcao, certa: meu.certa, ms: meu.ms, pontos: meu.pontos, correta: meu.respondido_em ? K[meu.qid] : null }, error: null }); }
          if (n === 'pd_responder') { var ok = a.p_opcao === K[meu.qid], t = Date.now() - new Date(meu.visto_em).getTime(); Object.assign(meu, { respondido_em: new Date().toISOString(), opcao: a.p_opcao, certa: ok, ms: t, pontos: ok ? 10 + (t < 10000 ? 5 : t < 20000 ? 3 : t < 40000 ? 1 : 0) : 0 }); return Promise.resolve({ data: { respondida: true, opcao: a.p_opcao, certa: ok, ms: t, pontos: meu.pontos, correta: K[meu.qid] }, error: null }); }
          if (n === 'pd_ranking') return Promise.resolve({ data: [{ pos: 1, user_id: U2, nome: 'Bruno Teste', avatar_url: null, estado: 'ano2', pontos: 15, certas: 1, ms: 6200, eu: false }].concat(meu && meu.respondido_em ? [{ pos: 2, user_id: window.__uid, nome: 'Ana Teste', avatar_url: null, estado: 'ano3', pontos: meu.pontos, certas: meu.certa ? 1 : 0, ms: meu.ms, eu: true }] : []), error: null });
        }
        if (n === 'seq_ranking') return Promise.resolve({ data: [{ pos: 1, user_id: U2, nome: 'Bruno Teste', avatar_url: null, dias: 14, eu: false }, { pos: 2, user_id: '33333333-3333-3333-3333-333333333333', nome: 'Carla Martins', avatar_url: null, dias: 9, eu: false }, { pos: 3, user_id: window.__uid, nome: 'Ana Teste', avatar_url: null, dias: (db.estudo_dias || []).length ? 1 : 0, eu: true }].filter(function (x) { return x.dias > 0; }), error: null });
        if (n.indexOf('rp_') === 0) {
          window.__rp = window.__rp || 135;
          if (n === 'rp_totais') return Promise.resolve({ data: (a.p_ids || []).map(function (u) { return { user_id: u, total: u === window.__uid ? window.__rp : 620 }; }), error: null });
          if (n === 'rp_resumo') return Promise.resolve({ data: { total: window.__rp, semana: 40, posicao: 2, tipos: { desafio: { n: 7, p: 35 }, material: { n: 2, p: 45 }, resposta: { n: 3, p: 15 }, util: { n: 1, p: 10 }, explicacao: { n: 0, p: 0 } }, recentes: [{ tipo: 'material', pontos: 25, criado_em: new Date().toISOString() }, { tipo: 'desafio', pontos: 5, criado_em: new Date(Date.now()-864e5).toISOString() }] }, error: null });
          if (n === 'rp_ranking') return Promise.resolve({ data: [{ pos: 1, user_id: U2, nome: 'Bruno Teste', estado: 'ano2', avatar_url: null, total: 620, eu: false }, { pos: 2, user_id: window.__uid, nome: 'Ana Teste', estado: 'ano3', avatar_url: null, total: window.__rp, eu: true }], error: null });
          if (n === 'rp_tutores_avals') return Promise.resolve({ data: (a.p_ids || []).map(function (u) { return { tutor: u, total: 3, eu: false }; }), error: null });
          return Promise.resolve({ data: { ok: true, total: 4 }, error: null });
        }
        if (n === 'criar_sala') { var s = { id: 'sala-' + (++seq), nome: a.p_nome, cadeira: a.p_cadeira, cor: a.p_cor, codigo: 'ABC123', dono: window.__uid, max_membros: 12, created_at: new Date().toISOString() }; db.salas.push(s); db.sala_membros.push({ sala_id: s.id, user_id: window.__uid, papel: 'admin' }, { sala_id: s.id, user_id: U2, papel: 'membro' }); db.sala_estado.push({ sala_id: s.id, pomodoro: null, ativ: null }); return Promise.resolve({ data: s, error: null }); }
        return Promise.resolve({ data: null, error: null });
      }
    };
  } };
})();
