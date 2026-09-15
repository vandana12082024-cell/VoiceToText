import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'app.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  const url = String.fromEnvironment('SUPABASE_URL');
  const key = String.fromEnvironment('SUPABASE_PUBLISHABLE_KEY');
  if (url.isEmpty || key.isEmpty) {
    throw StateError('Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY with --dart-define.');
  }
  await Supabase.initialize(url: url, publishableKey: key);
  runApp(const ProviderScope(child: VoiceApp()));
}
