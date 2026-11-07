import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:town_pass/util/web_message_handler/tp_web_message_handler.dart';

/// 呷藥囉：用手機作業系統內建的 TTS 朗讀（flutter_tts，MIT）。
///
/// 只使用不需要網路的離線語音，不呼叫雲端服務（比賽規定：推論在裝置端）。
/// 網頁端的對應模組見 microservice/frontend/tts/。
/// 每一步都有時間限制，保證一定回覆網頁；過程以 `[tts]` 開頭印在 log（logcat 可查）。
class _Tts {
  _Tts._();

  static final FlutterTts _tts = FlutterTts();
  static const _googleEngine = 'com.google.android.tts';
  static const _initTimeout = Duration(seconds: 3);
  static const _stepTimeout = Duration(milliseconds: 1500);

  static Future<void>? _init;
  static String? _voiceLang; // 已設定好語音的語言，相同語言不用再挑

  static void _log(String message) => debugPrint('[tts] $message');

  static Future<void> _ensureInit() {
    return _init ??= _doInit().timeout(_initTimeout).catchError((Object e) {
      _init = null; // 下次再試
      throw e;
    });
  }

  /// 先初始化引擎，讓第一次朗讀不用等。
  static void warmUp() {
    _ensureInit().then((_) => _log('warm up done'), onError: (Object e) => _log('warm up failed: $e'));
  }

  static Future<void> _doInit() async {
    _log('init start');
    if (Platform.isAndroid) {
      // 部分手機預設是廠商自己的 TTS 引擎；有 Google 語音引擎時優先使用
      final engines = await _tts.getEngines;
      final current = await _tts.getDefaultEngine;
      _log('engines=$engines default=$current');
      if (engines is List && engines.contains(_googleEngine) && current != _googleEngine) {
        await _tts.setEngine(_googleEngine);
        _log('engine set to $_googleEngine');
      }
    }
    if (Platform.isIOS) {
      // 靜音模式也要念得出來（長輩可能不小心切到靜音）
      await _tts.setSharedInstance(true);
      await _tts.setIosAudioCategory(
        IosTextToSpeechAudioCategory.playback,
        [IosTextToSpeechAudioCategoryOptions.duckOthers],
        IosTextToSpeechAudioMode.spokenAudio,
      );
    }
    await _tts.awaitSpeakCompletion(false); // 開始念就回覆網頁，不等念完
    _tts.setErrorHandler((message) => _log('engine error: $message'));
    _log('init done');
  }

  static String _norm(Object? lang) => '$lang'.replaceAll('_', '-').toLowerCase();

  /// 中文（國語）語音的優先順序；粵語（zh-HK、yue）不使用。
  static int _rank(String locale, String target) {
    if (locale == target) return 3;
    if (locale == 'cmn-hant-tw' || locale == 'zh-hant-tw') return 2;
    if (locale.startsWith('zh-hk') || locale.startsWith('yue')) return -1;
    if (locale.startsWith('zh') || locale.startsWith('cmn')) return 1;
    return -1;
  }

  /// 挑離線的中文語音並設定；回傳失敗原因，成功回傳 null。
  static Future<String?> _selectVoice(String lang) async {
    if (_voiceLang == lang) return null;
    final target = _norm(lang);
    final voices = await _tts.getVoices.timeout(_stepTimeout, onTimeout: () => null);
    if (voices == null) return 'voice_list_timeout';
    if (voices is! List) return 'no_voice_list';

    Map? best;
    var bestRank = -1;
    var hasChinese = false;
    for (final v in voices) {
      if (v is! Map) continue;
      final rank = _rank(_norm(v['locale']), target);
      if (rank < 0) continue;
      hasChinese = true;
      // Android 才有 network_required；iOS 的語音都在裝置上合成
      if (v['network_required'] == '1') continue;
      if (rank > bestRank) {
        best = v;
        bestRank = rank;
      }
    }
    _log('voices=${voices.length} chinese=$hasChinese chosen=${best?['name']} (${best?['locale']})');
    if (best == null) return hasChinese ? 'no_offline_voice' : 'no_chinese_voice';

    final ok = await _tts
        .setVoice({'name': '${best['name']}', 'locale': '${best['locale']}'})
        .timeout(_stepTimeout, onTimeout: () => 0);
    if (ok != 1) return 'set_voice_failed';
    _voiceLang = lang;
    return null;
  }

  static Future<Map<String, Object?>> speak(Object? message) async {
    final data = message is Map ? message : const {};
    final text = '${data['text'] ?? ''}'.trim();
    if (text.isEmpty) return {'ok': false, 'reason': 'empty_text'};
    final lang = '${data['lang'] ?? 'zh-TW'}';
    final rate = data['rate'] is num ? (data['rate'] as num).toDouble() : 0.85;
    _log('speak request (${text.length} chars, $lang, rate $rate)');

    try {
      await _ensureInit();
    } on TimeoutException {
      _log('init timeout');
      return {'ok': false, 'reason': 'engine_init_timeout'};
    } catch (e) {
      _log('init error: $e');
      return {'ok': false, 'reason': 'app_error'};
    }

    try {
      await _tts.stop().timeout(_stepTimeout, onTimeout: () => null);
      final reason = await _selectVoice(lang);
      if (reason != null) {
        _log('voice not ready: $reason');
        return {'ok': false, 'reason': reason};
      }
      // flutter_tts 的 0.5 是各平台的正常語速；網頁端的 rate 以 1.0 為正常
      await _tts.setSpeechRate((0.5 * rate).clamp(0.1, 1.0)).timeout(_stepTimeout, onTimeout: () => null);
      final result = await _tts.speak(text).timeout(_stepTimeout, onTimeout: () => null);
      _log('speak result=$result');
      if (result == 1) return {'ok': true};
      _voiceLang = null; // 下次重新挑語音
      return {'ok': false, 'reason': result == null ? 'speak_timeout' : 'speak_failed'};
    } catch (e) {
      _log('speak error: $e');
      _voiceLang = null;
      return {'ok': false, 'reason': 'app_error'};
    }
  }

  static Future<void> stop() async {
    try {
      await _tts.stop().timeout(_stepTimeout);
    } catch (_) {}
  }
}

/// 網頁送 { name: 'tts_speak', data: { text, lang, rate } }；
/// App 開始朗讀或失敗時回覆一次 { ok: true } 或 { ok: false, reason }。
class TtsSpeakMessageHandler extends TPWebMessageHandler {
  TtsSpeakMessageHandler() {
    _Tts.warmUp(); // WebView 建立時就先初始化
  }

  @override
  String get name => 'tts_speak';

  @override
  Future<void> handle({
    required Object? message,
    required WebUri? sourceOrigin,
    required bool isMainFrame,
    required Function(WebMessage replyWebMessage)? onReply,
  }) async {
    final result = await _Tts.speak(message);
    onReply?.call(replyWebMessage(data: result));
  }
}

/// 網頁送 { name: 'tts_stop', data: null }；停止朗讀，不回覆。
class TtsStopMessageHandler extends TPWebMessageHandler {
  @override
  String get name => 'tts_stop';

  @override
  Future<void> handle({
    required Object? message,
    required WebUri? sourceOrigin,
    required bool isMainFrame,
    required Function(WebMessage replyWebMessage)? onReply,
  }) async {
    await _Tts.stop();
  }
}
