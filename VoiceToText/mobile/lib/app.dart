import 'package:material_ui/material_ui.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shadcn_flutter/shadcn_flutter.dart' as shad;
import 'package:shadcn_flutter_material/shadcn_flutter_material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'core.dart';

final router = GoRouter(initialLocation: '/', routes: [
  GoRoute(path: '/', builder: (_, __) => const SessionGate()),
  GoRoute(path: '/voice', builder: (_, __) => const VoiceScreen()),
  GoRoute(path: '/history', builder: (_, __) => const HistoryScreen()),
  GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
]);

class VoiceApp extends StatelessWidget {
  const VoiceApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialShadcnApp.router(
    theme: shad.ThemeData(colorScheme: shad.ColorSchemes.lightZinc(), radius: 0.5),
    routerConfig: router,
  );
}

class SessionGate extends StatefulWidget {
  const SessionGate({super.key});
  @override
  State<SessionGate> createState() => _SessionGateState();
}
class _SessionGateState extends State<SessionGate> {
  final email = TextEditingController(), password = TextEditingController();
  String? error;
  bool signup = false, busy = false;
  @override
  void dispose() { email.dispose(); password.dispose(); super.dispose(); }
  Future<void> submit() async {
    setState(() { busy = true; error = null; });
    try {
      if (signup) {
        await Supabase.instance.client.auth.signUp(email: email.text.trim(), password: password.text);
      } else {
        await Supabase.instance.client.auth.signInWithPassword(email: email.text.trim(), password: password.text);
      }
      if (mounted && Supabase.instance.client.auth.currentSession != null) context.go('/voice');
      else setState(() => error = 'Check your email to confirm your account.');
    } catch (e) { setState(() => error = e.toString()); }
    finally { if (mounted) setState(() => busy = false); }
  }
  @override
  Widget build(BuildContext context) {
    if (Supabase.instance.client.auth.currentSession != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) context.go('/voice'); });
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return Scaffold(body: Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 420), child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text(signup ? 'Create your account' : 'Welcome back', style: Theme.of(context).textTheme.headlineMedium),
      const SizedBox(height: 16),
      TextField(controller: email, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Email')),
      TextField(controller: password, obscureText: true, decoration: const InputDecoration(labelText: 'Password')),
      const SizedBox(height: 16),
      if (error != null) Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
      shad.PrimaryButton(onPressed: busy ? null : submit, child: Text(signup ? 'Sign up' : 'Sign in')),
      shad.GhostButton(onPressed: () => setState(() => signup = !signup), child: Text(signup ? 'Already have an account?' : 'Create an account')),
    ])))));
  }
}

class VoiceScreen extends ConsumerWidget {
  const VoiceScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final preferences = ref.watch(preferencesProvider);
    final voice = ref.watch(voiceProvider);
    return Scaffold(appBar: AppBar(title: const Text('Voice assistant'), actions: [IconButton(onPressed: () => context.go('/history'), icon: const Icon(Icons.history)), IconButton(onPressed: () => context.go('/settings'), icon: const Icon(Icons.settings))]), body: Padding(padding: const EdgeInsets.all(24), child: preferences.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('$e')),
      data: (value) => ListView(children: [
        Text('Speak naturally', style: Theme.of(context).textTheme.headlineMedium),
        Text('${languages[value.language]} · ${value.tone}'),
        const SizedBox(height: 32),
        shad.PrimaryButton(onPressed: voice.busy ? null : () => voice.recording ? ref.read(voiceProvider.notifier).stop(value) : ref.read(voiceProvider.notifier).start(), child: Text(voice.recording ? 'Stop recording' : 'Record voice')),
        if (voice.busy) const Padding(padding: EdgeInsets.all(16), child: Center(child: CircularProgressIndicator())),
        if (voice.error != null) Padding(padding: const EdgeInsets.only(top: 16), child: Text(voice.error!, style: TextStyle(color: Theme.of(context).colorScheme.error))),
        if (voice.item != null) ...[
          const SizedBox(height: 24),
          Text('Raw transcript', style: Theme.of(context).textTheme.titleLarge),
          SelectableText(voice.item!.raw),
          const SizedBox(height: 16),
          shad.PrimaryButton(onPressed: voice.busy ? null : () => ref.read(voiceProvider.notifier).rewrite(value), child: const Text('Polish text')),
          if (voice.item!.processed != null) ...[
            const SizedBox(height: 24),
            Text('Polished text', style: Theme.of(context).textTheme.titleLarge),
            SelectableText(voice.item!.processed!),
            shad.OutlineButton(onPressed: () => Clipboard.setData(ClipboardData(text: voice.item!.processed!)), child: const Text('Copy result')),
          ],
        ],
      ]),
    )));
  }
}

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(appBar: AppBar(title: const Text('History'), leading: BackButton(onPressed: () => context.go('/voice'))), body: ref.watch(historyProvider).when(
    loading: () => const Center(child: CircularProgressIndicator()),
    error: (e, _) => Center(child: Text('$e')),
    data: (items) => items.isEmpty ? const Center(child: Text('No recordings yet')) : ListView.builder(itemCount: items.length, itemBuilder: (context, index) {
      final item = items[index];
      return ListTile(title: Text(item.processed ?? item.raw, maxLines: 3, overflow: TextOverflow.ellipsis), subtitle: Text('${item.language} · ${item.tone}'), trailing: IconButton(icon: const Icon(Icons.delete_outline), onPressed: () async { await ref.read(apiProvider).delete(item.id); ref.invalidate(historyProvider); }), onTap: () => Clipboard.setData(ClipboardData(text: item.processed ?? item.raw)));
    }),
  ));
}

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(appBar: AppBar(title: const Text('Settings'), leading: BackButton(onPressed: () => context.go('/voice'))), body: ref.watch(preferencesProvider).when(
    loading: () => const Center(child: CircularProgressIndicator()),
    error: (e, _) => Center(child: Text('$e')),
    data: (value) => ListView(padding: const EdgeInsets.all(24), children: [
      DropdownButtonFormField<String>(initialValue: value.language, decoration: const InputDecoration(labelText: 'Default language'), items: languages.entries.map((entry) => DropdownMenuItem(value: entry.key, child: Text(entry.value))).toList(), onChanged: (v) { if (v != null) ref.read(preferencesProvider.notifier).save(value.copyWith(language: v)); }),
      DropdownButtonFormField<String>(initialValue: value.tone, decoration: const InputDecoration(labelText: 'Default tone'), items: tones.map((tone) => DropdownMenuItem(value: tone, child: Text(tone))).toList(), onChanged: (v) { if (v != null) ref.read(preferencesProvider.notifier).save(value.copyWith(tone: v)); }),
      SwitchListTile(title: const Text('Auto detect language'), value: value.autoDetect, onChanged: (v) => ref.read(preferencesProvider.notifier).save(value.copyWith(autoDetect: v))),
      const Text('Audio is deleted from this device after upload. Audio retention is not enabled in this version.'),
      const SizedBox(height: 24),
      shad.OutlineButton(onPressed: () async { await Supabase.instance.client.auth.signOut(); if (context.mounted) context.go('/'); }, child: const Text('Sign out')),
    ]),
  ));
}
