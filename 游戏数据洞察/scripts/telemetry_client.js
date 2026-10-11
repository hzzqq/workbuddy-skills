/*
 * GameTelemetry — 网页小游戏游玩数据采集 SDK（零依赖，纯原生 JS）
 * ------------------------------------------------------------------
 * 用法：
 *   <script src="telemetry_client.js"></script>
 *   <script>
 *     GameTelemetry.init({ gameId: 'my-game', collectorUrl: 'http://localhost:8765' });
 *     // 关键行为处埋点：
 *     GameTelemetry.track('level_fail', { level: 3, reason: 'timeout' });
 *   </script>
 *
 * 自动采集（无需手写）：
 *   session_start / session_end / visibility / error(运行时报错)
 *
 * 数据流向：浏览器 -> POST http://localhost:8765/event (batch) -> 本地 .jsonl
 * 注意：collector 未启动或离线时静默丢弃，绝不阻断游戏运行。
 */
(function (global) {
  'use strict';

  var GameTelemetry = {
    cfg: {
      gameId: 'unknown',
      collectorUrl: 'http://localhost:8765',
      batch: 20,
      flushMs: 5000,
      auto: true,
      endpoint: '/event'
    },
    _buf: [],
    _sid: null,
    _page: '',

    init: function (o) {
      o = o || {};
      this.cfg.gameId = o.gameId || 'unknown';
      this.cfg.collectorUrl = o.collectorUrl || 'http://localhost:8765';
      if (typeof o.batch === 'number') this.cfg.batch = o.batch;
      if (typeof o.flushMs === 'number') this.cfg.flushMs = o.flushMs;
      if (typeof o.auto === 'boolean') this.cfg.auto = o.auto;

      this._sid = 's-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
      try { this._page = location.pathname; } catch (e) { this._page = 'unknown'; }

      var self = this;
      if (this.cfg.auto && typeof window !== 'undefined') {
        this.track('session_start', {});

        window.addEventListener('beforeunload', function () {
          self.track('session_end', {});
          self._flush(true);
        });
        document.addEventListener('visibilitychange', function () {
          self.track('visibility', { hidden: document.hidden });
        });
        window.addEventListener('error', function (e) {
          var stack = (e.error && e.error.stack) || '';
          self.track('error', { message: e.message, stack: stack, file: e.filename, line: e.lineno });
        });
        setInterval(function () { self._flush(); }, this.cfg.flushMs);
      }
      return this;
    },

    track: function (type, payload) {
      payload = payload || {};
      this._buf.push({
        ts: Date.now(),
        session_id: this._sid,
        type: type,
        gameId: this.cfg.gameId,
        payload: payload,
        ua: (typeof navigator !== 'undefined') ? navigator.userAgent : '',
        page: this._page
      });
      if (this._buf.length >= this.cfg.batch) this._flush();
      return this;
    },

    _flush: function () {
      if (!this._buf.length) return;
      var batch = this._buf.splice(0, this._buf.length);
      var url = this.cfg.collectorUrl.replace(/\/$/, '') + this.cfg.endpoint;
      var body = JSON.stringify(batch);
      try {
        if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
          navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }));
        } else if (typeof fetch !== 'undefined') {
          fetch(url, { method: 'POST', mode: 'no-cors', body: body, keepalive: true });
        }
      } catch (e) {
        /* 离线或 collector 未起：静默丢，不阻断游戏 */
      }
    }
  };

  global.GameTelemetry = GameTelemetry;
  if (typeof module !== 'undefined' && module.exports) module.exports = GameTelemetry;
})(typeof window !== 'undefined' ? window : this);
