import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:roastcraft/features/timer/presentation/cubit/timer_cubit.dart';
import 'package:roastcraft/features/timer/presentation/timer_view.dart';

import 'package:roastcraft/core/my_bloc_observer.dart';
import 'package:roastcraft/features/timer/ticker.dart';

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
