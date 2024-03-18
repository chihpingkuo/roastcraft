import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:roastcraft/cubit/timer_cubit.dart';

import 'package:roastcraft/my_bloc_observer.dart';
import 'package:roastcraft/ticker.dart';
import 'package:roastcraft/worker.dart';

void main() {
  Bloc.observer = const MyBlocObserver();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Timer',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const MyHomePage(),
    );
  }
}

class MyHomePage extends StatelessWidget {
  const MyHomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => TimerCubit(ticker: const Ticker()),
      child: const TimerView(),
    );
  }
}

class TimerView extends StatelessWidget {
  const TimerView({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Flutter Timer')),
      body: const Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: <Widget>[
          Padding(
            padding: EdgeInsets.symmetric(vertical: 100.0),
            child: Center(child: TimerText()),
          ),
          Actions(),
        ],
      ),
    );
  }
}

class TimerText extends StatelessWidget {
  const TimerText({super.key});
  @override
  Widget build(BuildContext context) {
    final duration = context.select((TimerCubit cubit) => cubit.state.duration);
    final minutesStr =
        ((duration / 60) % 60).floor().toString().padLeft(2, '0');
    final secondsStr = (duration % 60).floor().toString().padLeft(2, '0');
    return Text(
      '$minutesStr:$secondsStr',
      style: Theme.of(context).textTheme.displayLarge,
    );
  }
}

class Actions extends StatelessWidget {
  const Actions({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<TimerCubit, TimerState>(
      buildWhen: (prev, state) => prev.status != state.status,
      builder: (context, state) {
        return Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            ...switch (state.status) {
              TimerStatus.initial => [
                  FloatingActionButton(
                    child: const Icon(Icons.play_arrow),
                    onPressed: () => context.read<TimerCubit>().start(),
                  ),
                ],
              TimerStatus.runInProgress => [
                  FloatingActionButton(
                    child: const Icon(Icons.pause),
                    onPressed: () => context.read<TimerCubit>().pause(),
                  ),
                  FloatingActionButton(
                    child: const Icon(Icons.replay),
                    onPressed: () => context.read<TimerCubit>().reset(),
                  ),
                ],
              TimerStatus.runPause => [
                  FloatingActionButton(
                    child: const Icon(Icons.play_arrow),
                    onPressed: () => context.read<TimerCubit>().resume(),
                  ),
                  FloatingActionButton(
                    child: const Icon(Icons.replay),
                    onPressed: () => context.read<TimerCubit>().reset(),
                  ),
                ],
              TimerStatus.runComplete => [
                  FloatingActionButton(
                    child: const Icon(Icons.replay),
                    onPressed: () => context.read<TimerCubit>().reset(),
                  ),
                ]
            }
          ],
        );
      },
    );
  }
}
