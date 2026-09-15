import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

const languages = <String, String>{'auto': 'Auto detect', 'en': 'English', 'hi': 'Hindi', 'hinglish': 'Hinglish', 'ta': 'Tamil', 'tanglish': 'Tanglish', 'kn': 'Kannada', 'kanglish': 'Kanglish', 'ml': 'Malayalam', 'manglish': 'Manglish'};
const tones = <String>['natural', 'casual', 'formal', 'professional', 'short'];

class Transcript {
  Transcript(this.id, this.raw, this.processed, this.language, this.tone);
  final String id, raw, language, tone;
  final String? processed;
  factory Transcript.fromJson(Map<String, dynamic> json) => Transcript(json['id'] as String, json['raw_text'] as String, json['processed_text'] as String?, json['language'] as String, json['tone'] as String);
}

class Preferences {
  const Preferences({this.language = 'auto', this.tone = 'natural', this.autoDetect = true, this.saveAudio = false});
  final String language, tone;
  final bool autoDetect, saveAudio;
  factory Preferences.fromJson(Map<String, dynamic> json) => Preferences(language: json['default_language'] as String, tone: json['default_tone'] as String, autoDetect: json['auto_detect_language'] as bool, saveAudio: json['save_audio'] as bool);
  Map<String, dynamic> toJson() => {'default_language': language, 'default_tone': tone, 'auto_detect_language': autoDetect, 'save_audio': saveAudio};
  Preferences copyWith({String? language, String? tone, bool? autoDetect, bool? saveAudio}) => Preferences(language: language ?? this.language, tone: tone ?? this.tone, autoDetect: autoDetect ?? this.autoDetect, saveAudio: saveAudio ?? this.saveAudio);
}

class ApiRepository {
  ApiRepository(this._dio);
  final Dio _dio;
  Future<dynamic> _data(Response response) {
    final body = response.data as Map<String, dynamic>;
    if (body['success'] != true) throw Exception((body['error'] as Map?)?['message'] ?? 'Request failed');
    return Future.value(body['data']);
  }
  Future<Preferences> preferences() async => Preferences.fromJson(await _data(await _dio.get('/preferences')) as Map<String, dynamic>);
  Future<Preferences> savePreferences(Preferences value) async => Preferences.fromJson(await _data(await _dio.patch('/preferences', data: value.toJson())) as Map<String, dynamic>);
  Future<Transcript> transcribe(String path, String language, String tone) async {
    final form = FormData.fromMap({'audio': await MultipartFile.fromFile(path, filename: 'recording.m4a', contentType: DioMediaType('audio', 'mp4')), 'language': language, 'tone': tone});
    return Transcript.fromJson(await _data(await _dio.post('/transcriptions', data: form)) as Map<String, dynamic>);
  }
  Future<Transcript> rewrite(Transcript item, String language, String tone) async => Transcript.fromJson(await _data(await _dio.post('/rewrite', data: {'transcription_id': item.id, 'language': language, 'tone': tone})) as Map<String, dynamic>);
  Future<List<Transcript>> history() async => (await _data(await _dio.get('/history')) as List).map((item) => Transcript.fromJson(item as Map<String, dynamic>)).toList();
  Future<void> delete(String id) async => _data(await _dio.delete('/history/$id'));
}

final apiProvider = Provider<ApiRepository>((ref) {
  const baseUrl = String.fromEnvironment('API_BASE_URL');
  if (baseUrl.isEmpty) throw StateError('Set API_BASE_URL with --dart-define.');
  final dio = Dio(BaseOptions(baseUrl: '$baseUrl/api/v1', connectTimeout: const Duration(seconds: 10), receiveTimeout: const Duration(seconds: 60)));
  dio.interceptors.add(InterceptorsWrapper(onRequest: (options, handler) {
    final token = Supabase.instance.client.auth.currentSession?.accessToken;
    if (token != null) options.headers['Authorization'] = 'Bearer $token';
    handler.next(options);
  }));
  ref.onDispose(() => dio.close());
  return ApiRepository(dio);
});

final preferencesProvider = AsyncNotifierProvider<PreferencesController, Preferences>(PreferencesController.new);
class PreferencesController extends AsyncNotifier<Preferences> {
  @override
  Future<Preferences> build() => ref.read(apiProvider).preferences();
  Future<void> save(Preferences value) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => ref.read(apiProvider).savePreferences(value));
  }
}

final historyProvider = FutureProvider<List<Transcript>>((ref) => ref.read(apiProvider).history());

class VoiceState {
  const VoiceState({this.recording = false, this.busy = false, this.item, this.error});
  final bool recording, busy;
  final Transcript? item;
  final String? error;
}

final voiceProvider = NotifierProvider<VoiceController, VoiceState>(VoiceController.new);
class VoiceController extends Notifier<VoiceState> {
  final _recorder = AudioRecorder();
  @override
  VoiceState build() {
    ref.onDispose(_recorder.dispose);
    return const VoiceState();
  }
  Future<void> start() async {
    try {
      if (!await _recorder.hasPermission()) throw Exception('Microphone permission is required');
      final dir = await getTemporaryDirectory();
      await _recorder.start(const RecordConfig(encoder: AudioEncoder.aacLc), path: '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}.m4a');
      state = const VoiceState(recording: true);
    } catch (e) { state = VoiceState(error: e.toString()); }
  }
  Future<void> stop(Preferences preferences) async {
    String? path;
    try {
      path = await _recorder.stop();
      if (path == null) throw Exception('No audio was recorded');
      state = const VoiceState(busy: true);
      final item = await ref.read(apiProvider).transcribe(path, preferences.language, preferences.tone);
      state = VoiceState(item: item);
      ref.invalidate(historyProvider);
    } catch (e) { state = VoiceState(error: e.toString()); }
    finally { if (path != null) { try { await File(path).delete(); } catch (_) {} } }
  }
  Future<void> rewrite(Preferences preferences) async {
    final item = state.item;
    if (item == null) return;
    state = VoiceState(busy: true, item: item);
    try {
      final result = await ref.read(apiProvider).rewrite(item, preferences.language, preferences.tone);
      state = VoiceState(item: result);
      ref.invalidate(historyProvider);
    } catch (e) { state = VoiceState(item: item, error: e.toString()); }
  }
}
